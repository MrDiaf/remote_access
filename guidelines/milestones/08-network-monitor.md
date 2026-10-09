# Milestone 08 — Network quality recorder

## Objective

Record the home connection's quality around the clock so the user can show
the internet provider (or an assistant) when and how badly it failed. A Network
page shows graphs and problem periods, and offers a plain-text report to copy
or download. Measuring must not load the connection: packet loss and latency
only, no speed tests.

## Dependencies

None. Uses the backend's existing read-only host view (`/host-root`) and data
volume.

## Existing-state check

1. Inspect `backend/app/network_monitor.py`, `GET /api/network` and
   `GET /api/network/report`, `frontend/src/pages/NetworkPage.tsx`,
   `frontend/src/components/LineChart.tsx`, and the TUI `NetworkTab`.
2. Evaluate the criteria below; implement only what is missing.

## Design

- One thread per target in the backend (started by FastAPI's lifespan; tests
  never start it). Each runs `ping -n -q -c 30 -i 1 -W 2` and stores one row
  per 30 s: sent, received, average/max latency, and jitter (mdev).
  - If ping fails at once (for example "Network is unreachable"), the window
    counts as 100% loss.
  - About 84 bytes per ping each way, for four targets: roughly 350 B/s.
- Targets:
  - the host's default gateway (router), read from
    `/host-root/proc/1/net/route` (`NETMON_GATEWAY` overrides);
  - Cloudflare `1.1.1.1` and Google `8.8.8.8`;
  - a Tailscale relay (DERP) server, added 2026-10-09 because the user mostly
    reaches the server through Tailscale. The relay comes from Tailscale's
    public DERP map: by default the region with the lowest ping, re-picked
    daily and retried every 5 minutes while the map is unreachable.
    `NETMON_TAILSCALE` in `.env` pins a region code (such as `ams`, as in
    `tailscale netcheck`), takes a host, or turns it `off`. Tailscale's own
    choice can differ from the lowest ping (here, Amsterdam vs Helsinki).
  - Router loss separates home-network trouble from provider trouble.
- Storage: SQLite `network.sqlite3` in the backend data volume (WAL). Rows
  older than 30 days are deleted as new ones arrive.
- `GET /api/network?hours=N`:
  - per-target series in buckets (60 s … 6 h, at most 300 points), totals,
    and problem periods;
  - a problem period is consecutive minutes with ≥ 10% internet loss, where
    one quiet minute in between does not split it;
  - each period carries the router's loss at the same time.
- `GET /api/network/report?hours=N`:
  - plain text in server local time (`/etc/localtime` is mounted): per-target
    table, problem list with a home/provider verdict, and an hourly table
    (daily above 48 h);
  - ends with a short "how to read this".
- `NETMON_ENABLED=0` turns the recorder off.
- Page:
  - 24 h / 7 d / 30 d range, three status tiles (icon + label + value);
  - two separate line charts (loss %, latency ms; never one dual-axis chart)
    with a legend, line-end labels on wide screens, and a crosshair tooltip
    that also works by keyboard;
  - a problem list and the report with Copy (falls back to
    `execCommand('copy')` on plain-HTTP LAN) and Download.
  - Series colors are categorical slots 1–3, validated as a set (dataviz
    validator: CVD ΔE 9.2, normal-vision 27.6; the aqua contrast warning is
    covered by labels, the legend, and the report table).
- TUI: Network tab, number key 8. It is last so the existing number keys keep
  their tabs. It has a summary table, loss and latency sparklines, problems,
  and the report; `d`/`w`/`m` change the range and `c` copies.

## Accepted limitations

- Pings go through Docker's NAT; that adds well under a millisecond and does
  not create loss.
- A provider that deprioritizes ICMP can show ping loss that real traffic does
  not have. Loss to both internet targets at the same time is the stronger
  signal.
- While the server or Docker is off, nothing is recorded. The graphs show
  gaps, and the report states when measurements start.
- The dashboard has no dark theme, so the charts are light-only.

## Completion criteria

- [x] `make test`: ping parsing, gateway detection, buckets, problem periods
      with the home/provider verdict, report text, and the TUI Network tab
- [x] The live backend records the router (192.168.0.1), 1.1.1.1, 8.8.8.8,
      and a Tailscale relay every 30 s, and the report shows the real numbers
- [x] The page renders 24 h of data on desktop and phone without horizontal overflow
- [ ] User confirms the Copy button and a multi-day graph on the real server

## Verification

- `make test`: 30 backend and 14 TUI tests OK (relay choice, region pin,
  override, off, "no data" rows).
- Live: automatic relay = Helsinki (65.109.143.62, about 28 ms ping);
  `NETMON_TAILSCALE=ams` → Amsterdam (176.58.93.248), Tailscale's own
  preferred region on this machine. The four-color palette passes the dataviz
  validator (adjacent CVD ΔE 9.1, normal-vision 22.9).
- Live: `/api/network?hours=1` lists the three targets and real samples;
  `/api/network/report` matches them, with times in CEST.
- A throwaway backend plus proxy with 26 h of synthetic data (a 10-minute
  outage and a 30-minute flaky period) was screenshotted through Firefox
  WebDriver BiDi at 1280×900 and 390×800. Both problem periods were listed
  with "router fine: outside the home network".
