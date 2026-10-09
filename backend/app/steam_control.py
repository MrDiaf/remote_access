from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .models import SteamStatus


# Written by scripts/enable-steam-control.sh on the host and mounted read-only.
# The key only works for scripts/host/steam-control.sh (authorized_keys forced
# command), so the backend can ask for status/start/bigpicture/stop and nothing else.
KEY_DIR = Path(os.environ.get("STEAM_CONTROL_DIR", "/steam-control"))
KNOWN_HOSTS = Path(os.environ.get("DATA_DIR", "data")) / "steam-control-known_hosts"
SSH_HOST = os.environ.get("STEAM_CONTROL_SSH_HOST", "host.docker.internal")
SSH_PORT = os.environ.get("STEAM_CONTROL_SSH_PORT", "22")

VERBS = ("status", "start", "bigpicture", "stop")
# The host script waits up to 30 s for Steam to quit cleanly.
TIMEOUTS = {"status": 15, "start": 30, "bigpicture": 30, "stop": 60}
SAFE_USER = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._-]*$")

MESSAGES = {
    "running": "Steam is running.",
    "stopped": "Steam is not running.",
    "starting": "Steam is starting on the desktop.",
    "stopping": "Steam was asked to quit and is still closing.",
}
NOT_SET_UP = SteamStatus(
    configured=False,
    state="not set up",
    message="Run make up on the server and answer yes to Steam control.",
)


def _ssh_user() -> str | None:
    if not (KEY_DIR / "id_ed25519").is_file():
        return None
    try:
        user = (KEY_DIR / "user").read_text().strip()
    except OSError:
        return None
    return user if SAFE_USER.match(user) else None


def ssh_command(user: str, verb: str) -> list[str]:
    return [
        "ssh",
        "-T",
        "-i", str(KEY_DIR / "id_ed25519"),
        "-o", "BatchMode=yes",
        "-o", "IdentitiesOnly=yes",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
        "-p", SSH_PORT,
        "-l", user,
        "--",
        SSH_HOST,
        verb,
    ]


def parse_result(code: int, output: str) -> SteamStatus:
    first_line = output.strip().splitlines()[0] if output.strip() else ""
    word, _, detail = first_line.partition(":")
    word = word.strip()
    if code == 0 and word in MESSAGES:
        return SteamStatus(configured=True, state=word, message=MESSAGES[word])
    if word == "no-session":
        return SteamStatus(
            configured=True,
            state="no desktop",
            message="Nobody is logged in to the desktop, so Steam has nowhere to open.",
        )
    if word == "setup-needed":
        return SteamStatus(
            configured=True,
            state="needs setup",
            message="Steam's one-time installer is waiting on the server's desktop. Open the remote desktop, click Install, and sign in.",
        )
    if word == "missing":
        return SteamStatus(configured=True, state="not installed", message=detail.strip() or first_line)
    if code == 255:
        return SteamStatus(configured=True, state="unreachable", message=f"Cannot reach the host over SSH: {output.strip()}")
    return SteamStatus(configured=True, state="error", message=output.strip() or f"Exited with code {code}")


def _run(verb: str) -> SteamStatus:
    if verb not in VERBS:
        raise ValueError(f"Unsupported Steam command: {verb}")
    user = _ssh_user()
    if user is None:
        return NOT_SET_UP
    try:
        completed = subprocess.run(
            ssh_command(user, verb),
            check=False,
            capture_output=True,
            shell=False,
            text=True,
            timeout=TIMEOUTS[verb],
        )
    except subprocess.TimeoutExpired:
        return SteamStatus(configured=True, state="error", message="The host did not answer in time.")
    except FileNotFoundError:
        return SteamStatus(configured=True, state="error", message="ssh is missing from the backend image; run make refresh.")
    return parse_result(completed.returncode, completed.stdout.strip() or completed.stderr.strip())


def get_steam_status() -> SteamStatus:
    return _run("status")


def control_steam(verb: str) -> SteamStatus:
    if verb not in ("start", "bigpicture", "stop"):
        raise ValueError(f"Unsupported Steam command: {verb}")
    return _run(verb)
