"""Continuous, low-bandwidth network quality recorder.

Each target gets one ping per second, recorded as one 30-second sample
(sent, received, latency). No speed tests: three targets cost roughly 250
bytes per second in total. Samples live in SQLite in the data volume for 30
days, so the graphs and the copy-paste report cover past problems.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import sqlite3
import struct
import subprocess
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .models import NetworkEvent, NetworkHistory, NetworkPoint, NetworkReport, NetworkTarget, NetworkTargetSummary

log = logging.getLogger(__name__)

DB_PATH = Path(os.environ.get("DATA_DIR", "data")) / "network.sqlite3"
HOST_ROUTES = Path(os.environ.get("HOST_ROOT", "/host-root")) / "proc/1/net/route"
SAMPLE_PINGS = 30  # one ping per second, so one sample every 30 seconds
RETENTION_SECONDS = 30 * 24 * 3600
EVENT_BUCKET = 60  # problems are found per minute
EVENT_LOSS = 10.0  # internet packet loss (%) that counts as a problem minute
BUCKETS = (60, 300, 900, 1800, 3600, 7200, 21600)
MAX_POINTS = 300

SUMMARY = re.compile(r"(\d+) packets transmitted, (\d+) received")
RTT = re.compile(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms")

# Tailscale's public list of its relay (DERP) servers.
TAILSCALE_DERP_MAP = "https://controlplane.tailscale.com/derpmap/default"
TAILSCALE_RECHECK = 24 * 3600  # look for the nearest relay again once a day
TAILSCALE_RETRY = 300  # retry interval while the list cannot be fetched

_started = False
_tailscale: NetworkTarget | None = None  # the nearest relay, once found


def host_gateway() -> str | None:
    """The host's default gateway (the home router), from its routing table."""
    override = os.environ.get("NETMON_GATEWAY", "").strip()
    if override:
        return override
    try:
        lines = HOST_ROUTES.read_text().splitlines()[1:]
    except OSError:
        return None
    for line in lines:
        fields = line.split()
        if len(fields) > 2 and fields[1] == "00000000" and fields[2] != "00000000":
            return socket.inet_ntoa(struct.pack("<I", int(fields[2], 16)))
    return None


def targets() -> list[NetworkTarget]:
    found = []
    gateway = host_gateway()
    if gateway:
        found.append(NetworkTarget(id="router", label="Router", host=gateway, internet=False))
    found.append(NetworkTarget(id="cloudflare", label="Cloudflare", host="1.1.1.1", internet=True))
    found.append(NetworkTarget(id="google", label="Google", host="8.8.8.8", internet=True))
    if os.environ.get("NETMON_TAILSCALE", "").strip().lower() != "off":
        found.append(
            _tailscale or NetworkTarget(id="tailscale", label="Tailscale", host="-", internet=True, note="finding the nearest relay")
        )
    return found


def _quick_ping(host: str) -> float | None:
    try:
        completed = subprocess.run(
            ["ping", "-n", "-q", "-c", "2", "-i", "0.2", "-W", "2", host], capture_output=True, text=True, timeout=10
        )
    except subprocess.TimeoutExpired:
        return None
    parsed = parse_ping(completed.stdout)
    return parsed[2] if parsed else None


def choose_relay(derp_map: dict, measure: Callable[[str], float | None], region_code: str | None = None) -> NetworkTarget | None:
    """The Tailscale relay region with the lowest latency (or the given region), as a ping target."""
    candidates = []
    for region in derp_map.get("Regions", {}).values():
        if region_code and region.get("RegionCode") != region_code:
            continue
        if region.get("Avoid") and not region_code:
            continue
        node = next((n for n in region.get("Nodes", []) if n.get("IPv4") and not n.get("STUNOnly")), None)
        if node:
            candidates.append((region.get("RegionName", region.get("RegionCode", "?")), node["IPv4"]))
    if not candidates:
        return None
    with ThreadPoolExecutor(max_workers=16) as pool:
        latencies = list(pool.map(lambda candidate: measure(candidate[1]), candidates))
    measured = [(ms, name, ip) for (name, ip), ms in zip(candidates, latencies) if ms is not None]
    if not measured:
        return None
    _, name, ip = min(measured)
    note = f"relay: {name}" if region_code else f"nearest relay: {name}"
    return NetworkTarget(id="tailscale", label="Tailscale", host=ip, internet=True, note=note)


def nearest_tailscale_relay() -> NetworkTarget | None:
    """NETMON_TAILSCALE: empty/auto = lowest ping, a region code such as `ams`
    (from `tailscale netcheck`) = that region, anything else = that host."""
    setting = os.environ.get("NETMON_TAILSCALE", "").strip().lower()
    region_code = setting if re.fullmatch(r"[a-z]{2,5}", setting) and setting not in ("auto", "off") else None
    if setting and setting not in ("auto", "off") and not region_code:
        return NetworkTarget(id="tailscale", label="Tailscale", host=setting, internet=True)
    try:
        with urllib.request.urlopen(TAILSCALE_DERP_MAP, timeout=15) as response:
            derp_map = json.load(response)
    except (OSError, ValueError):
        return None
    return choose_relay(derp_map, _quick_ping, region_code)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        "CREATE TABLE IF NOT EXISTS samples ("
        " ts INTEGER NOT NULL, target TEXT NOT NULL, sent INTEGER NOT NULL, received INTEGER NOT NULL,"
        " rtt_avg REAL, rtt_max REAL, jitter REAL)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS samples_ts ON samples (ts)")
    return db


def parse_ping(output: str) -> tuple[int, int, float | None, float | None, float | None] | None:
    """(sent, received, avg ms, max ms, jitter ms) from `ping -q` output."""
    summary = SUMMARY.search(output)
    if not summary:
        return None
    sent, received = int(summary.group(1)), int(summary.group(2))
    rtt = RTT.search(output)
    if not rtt:
        return sent, received, None, None, None
    return sent, received, float(rtt.group(2)), float(rtt.group(3)), float(rtt.group(4))


def _sample(host: str) -> tuple[int, int, float | None, float | None, float | None]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            ["ping", "-n", "-q", "-c", str(SAMPLE_PINGS), "-i", "1", "-W", "2", host],
            capture_output=True,
            text=True,
            timeout=SAMPLE_PINGS + 15,
        )
        parsed = parse_ping(completed.stdout)
    except subprocess.TimeoutExpired:
        parsed = None
    if parsed is None:
        # ping gave up at once (e.g. "Network is unreachable"): count the whole
        # window as lost, and wait it out so the loop keeps its pace.
        time.sleep(max(0.0, SAMPLE_PINGS - (time.monotonic() - started)))
        return SAMPLE_PINGS, 0, None, None, None
    return parsed


def _record_forever(target: NetworkTarget, until: float | None = None) -> None:
    while until is None or time.time() < until:
        ts = int(time.time())
        try:
            sent, received, avg, worst, jitter = _sample(target.host)
            with _connect() as db:
                db.execute(
                    "INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ts, target.id, sent, received, avg, worst, jitter),
                )
                if target.id == "cloudflare":
                    db.execute("DELETE FROM samples WHERE ts < ?", (ts - RETENTION_SECONDS,))
        except Exception:  # keep recording through odd failures
            log.exception("network monitor sample for %s failed", target.host)
            time.sleep(SAMPLE_PINGS)


def _record_tailscale_forever() -> None:
    """Find the nearest Tailscale relay (again each day) and record it."""
    global _tailscale
    while True:
        relay = nearest_tailscale_relay()
        if relay is None:
            time.sleep(TAILSCALE_RETRY)
            continue
        _tailscale = relay
        _record_forever(relay, until=time.time() + TAILSCALE_RECHECK)


def start() -> None:
    """Start one recorder thread per target (once per process)."""
    global _started
    if _started or os.environ.get("NETMON_ENABLED", "1") == "0":
        return
    _started = True
    for target in targets():
        if target.id == "tailscale":
            runner, args = _record_tailscale_forever, ()
        else:
            runner, args = _record_forever, (target,)
        threading.Thread(target=runner, args=args, name=f"netmon-{target.id}", daemon=True).start()


def _rows(since: int) -> list[tuple]:
    with _connect() as db:
        return db.execute(
            "SELECT ts, target, sent, received, rtt_avg, rtt_max FROM samples WHERE ts >= ? ORDER BY ts", (since,)
        ).fetchall()


def _loss(sent: int, received: int) -> float:
    return round(100.0 * (sent - received) / sent, 2) if sent else 0.0


class _Acc:
    """Running totals for a group of samples."""

    def __init__(self) -> None:
        self.sent = self.received = 0
        self.rtt_weighted = 0.0
        self.rtt_max: float | None = None

    def add(self, sent: int, received: int, avg: float | None, worst: float | None) -> None:
        self.sent += sent
        self.received += received
        if avg is not None and received:
            self.rtt_weighted += avg * received
        if worst is not None:
            self.rtt_max = worst if self.rtt_max is None else max(self.rtt_max, worst)

    @property
    def loss(self) -> float:
        return _loss(self.sent, self.received)

    @property
    def avg(self) -> float | None:
        return round(self.rtt_weighted / self.received, 1) if self.received else None


def find_events(rows: list[tuple], internet_ids: set[str], now: int) -> list[NetworkEvent]:
    """Merge minutes with >= EVENT_LOSS internet packet loss into problem periods."""
    minutes: dict[int, tuple[_Acc, _Acc]] = {}
    for ts, target, sent, received, avg, worst in rows:
        internet, router = minutes.setdefault(ts // EVENT_BUCKET * EVENT_BUCKET, (_Acc(), _Acc()))
        (internet if target in internet_ids else router).add(sent, received, avg, worst)

    events: list[NetworkEvent] = []
    current: dict | None = None
    for minute in sorted(minutes):
        internet, router = minutes[minute]
        if not internet.sent or internet.loss < EVENT_LOSS:
            continue
        # One quiet (or unmeasured) minute between bad ones keeps a period open.
        if current and minute - current["end"] <= 2 * EVENT_BUCKET:
            current["end"] = minute + EVENT_BUCKET
            current["internet"].append(internet.loss)
            current["router"].append(router.loss if router.sent else None)
        else:
            current = {"start": minute, "end": minute + EVENT_BUCKET, "internet": [internet.loss], "router": [router.loss if router.sent else None]}
            events.append(current)  # type: ignore[arg-type]

    result = []
    for event in events:  # type: ignore[assignment]
        router_values = [value for value in event["router"] if value is not None]
        result.append(
            NetworkEvent(
                start=event["start"],
                end=min(event["end"], now),
                internet_loss=round(sum(event["internet"]) / len(event["internet"]), 1),
                worst_internet_loss=max(event["internet"]),
                router_loss=round(sum(router_values) / len(router_values), 1) if router_values else None,
            )
        )
    return result


def history(hours: int) -> NetworkHistory:
    hours = max(1, min(hours, RETENTION_SECONDS // 3600))
    now = int(time.time())
    since = now - hours * 3600
    span = hours * 3600
    bucket = next((size for size in BUCKETS if span / size <= MAX_POINTS), BUCKETS[-1])
    rows = _rows(since)
    found = targets()
    known = {target.id for target in found}

    grouped: dict[str, dict[int, _Acc]] = {target.id: {} for target in found}
    totals: dict[str, _Acc] = {target.id: _Acc() for target in found}
    for ts, target, sent, received, avg, worst in rows:
        if target not in known:
            continue
        grouped[target].setdefault(ts // bucket * bucket, _Acc()).add(sent, received, avg, worst)
        totals[target].add(sent, received, avg, worst)

    series = {
        target_id: [
            NetworkPoint(t=start, loss=acc.loss, avg_ms=acc.avg, max_ms=acc.rtt_max, sent=acc.sent)
            for start, acc in sorted(buckets.items())
        ]
        for target_id, buckets in grouped.items()
    }
    summaries = [
        NetworkTargetSummary(
            id=target.id,
            sent=totals[target.id].sent,
            received=totals[target.id].received,
            loss=totals[target.id].loss,
            avg_ms=totals[target.id].avg,
            max_ms=totals[target.id].rtt_max,
        )
        for target in found
    ]
    internet_ids = {target.id for target in found if target.internet}
    return NetworkHistory(
        hours=hours,
        bucket_seconds=bucket,
        since=since,
        now=now,
        first_sample=rows[0][0] if rows else None,
        targets=found,
        series=series,
        summary=summaries,
        events=find_events(rows, internet_ids, now),
    )


def _clock(ts: int, with_date: bool = True) -> str:
    return time.strftime("%Y-%m-%d %H:%M" if with_date else "%H:%M", time.localtime(ts))


def _ms(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f} ms" if value >= 100 else f"{value:.1f} ms"


def report(hours: int, server_name: str) -> NetworkReport:
    data = history(hours)
    zone = time.strftime("%Z")
    lines = [
        f"Network quality report: {server_name}",
        f"Period: {_clock(data.since)} to {_clock(data.now)} ({zone}), last {data.hours} h",
        "Method: one ping per second to each target, recorded in 30-second samples. No speed tests.",
    ]
    if data.first_sample is None:
        lines.append("\nNo measurements in this period yet.")
        return NetworkReport(hours=data.hours, text="\n".join(lines) + "\n")
    if data.first_sample > data.since + 300:
        lines.append(f"Measurements start at {_clock(data.first_sample)}.")

    labels = {
        target.id: f"{target.label} ({target.host}{', ' + target.note if target.note else ''})" for target in data.targets
    }
    width = max(len(label) for label in labels.values())
    lines += ["", f"{'Target'.ljust(width)}  Packet loss  Avg latency  Worst latency"]
    for item in data.summary:
        lines.append(
            f"{labels[item.id].ljust(width)}  {f'{item.loss:.2f}%' if item.sent else 'no data':>11}  {_ms(item.avg_ms):>11}  {_ms(item.max_ms):>13}"
        )

    lines += ["", f"Problems (minutes with {EVENT_LOSS:.0f}% or more packet loss to the internet):"]
    if not data.events:
        lines.append("None.")
    for event in data.events:
        minutes = max(1, round((event.end - event.start) / 60))
        where = ""
        if event.router_loss is not None:
            where = (
                f"; router {event.router_loss:.0f}% at the same time (inside the home network)"
                if event.router_loss >= EVENT_LOSS / 2
                else f"; router fine ({event.router_loss:.0f}%), so outside the home network"
            )
        lines.append(
            f"- {_clock(event.start)} to {_clock(event.end, with_date=_clock(event.start)[:10] != _clock(event.end)[:10])} ({minutes} min): "
            f"{event.internet_loss:.0f}% loss to the internet, worst minute {event.worst_internet_loss:.0f}%{where}"
        )

    # Loss to the internet per hour (per day for long periods), as a table.
    step = 3600 if data.hours <= 48 else 86400
    internet_ids = {target.id for target in data.targets if target.internet}
    router_id = next((target.id for target in data.targets if not target.internet), None)
    periods: dict[int, tuple[_Acc, _Acc]] = {}
    for ts, target, sent, received, avg, worst in _rows(data.since):
        local = time.localtime(ts)
        into = local.tm_min * 60 + local.tm_sec + (local.tm_hour * 3600 if step == 86400 else 0)
        start = ts - into
        internet, router = periods.setdefault(start, (_Acc(), _Acc()))
        if target in internet_ids:
            internet.add(sent, received, avg, worst)
        elif target == router_id:
            router.add(sent, received, avg, worst)
    unit = "Hour" if step == 3600 else "Day"
    lines += ["", f"{unit:<16}  Internet loss  Internet avg  Router loss"]
    for start in sorted(periods):
        internet, router = periods[start]
        label = _clock(start) if step == 3600 else time.strftime("%Y-%m-%d", time.localtime(start))
        router_text = f"{router.loss:.2f}%" if router.sent else "-"
        lines.append(f"{label:<16}  {f'{internet.loss:.2f}%':>13}  {_ms(internet.avg):>12}  {router_text:>11}")

    lines += [
        "",
        "How to read this: loss to the router as well points to the home network (Wi-Fi, cable, or the",
        "router itself). Loss only to the internet targets points to the internet provider's side.",
    ]
    return NetworkReport(hours=data.hours, text="\n".join(lines) + "\n")
