# Agent Handoff

Last refreshed: 2026-10-09

## Why This File Exists

This is the shared context for an agent starting a later session. It records
the current product decisions, architecture, operational facts, accepted
limitations, and next work so a new agent does not have to reconstruct them
from commit history.

Read this file after the root `AGENTS.md`, then use `PLAN.md` to select one
milestone. The selected self-contained file under `guidelines/milestones/` is
the authority for that milestone's execution details.

## Current State

The product is `server-control-panel`, a Docker Compose based homelab control
portal. Its primary purpose is to let the user open one private dashboard URL
from a desktop or phone, enter Guacamole, and control the actual Ubuntu server
desktop in the browser.

The dashboard and physical remote-desktop path exist. The Status page reports
the main disk and mounted drives discovered below the configured
`HOST_MEDIA_PATH` and `HOST_MOUNT_PATH`. Remote keyboard settings, a best-effort focus mode, and
baseline mobile input controls also exist. The user manually tested the phone
touchpad/keyboard flow and accepted it as minimally working. It remains a
little wonky, but polishing it is deferred unless the user explicitly reopens
that work.

Added on 2026-09-25 (implemented and verified in isolation; the user still has
to confirm them on the real server):

- a Terminal page: ttyd in the `terminal` container, embedded at `/terminal/`,
  which runs only `ssh` to the host;
- a disk usage explorer on the Status page (`GET /api/disk-usage`), which
  reads the host filesystem through a read-only `/` → `/host-root` bind;
- one-command lifecycle: `make setup`, `make up` (everything, including the
  Guacamole profile, with `--wait`), `make down` (everything), and
  `make doctor` (reboot readiness).

Added on 2026-09-28: the Status page shows NVIDIA GPU usage and VRAM. The
Makefile adds `docker-compose.gpu.yml` (GPU `utility` access for the backend)
only when Docker has the `nvidia` runtime; otherwise the GPU card is hidden.

Added on 2026-10-06: a terminal UI (`tui/`, Python + Textual, `make tui`) with
every dashboard feature except the remote desktop picture itself. It uses only
the backend HTTP API (no Docker socket) and runs in the `tui` Compose profile,
so `make up` never starts it. Its keyboard layout lists duplicate
`frontend/src/remoteInputOptions.ts`. When a browser page gains a feature,
add it to the matching TUI tab and to `tui/tests/test_tui.py`.

Added on 2026-10-09: Steam Remote Play support. A Steam card on the Actions
page (and `s`/`b` on the TUI Actions tab) starts Steam on the logged-in
desktop, normally or in Big Picture, and quits it cleanly. A collapsible guide
explains Steam Link pairing; streaming away from home uses Steam's relay, and
no ports are opened. GNOME Wayland can stream black video; see milestone 06. The
backend SSHes to the host with a key that `authorized_keys` pins to
`scripts/host/steam-control.sh` (status/start/stop only). `make up` offers to
set it up when Steam is installed. This is unverified on the real server.

Added on 2026-10-09 (user decision): `make up` is the whole setup. After the
containers are healthy, `scripts/setup-host.sh` checks each one-time host step
and asks `[Y/n]` about the missing ones: Docker on boot, the SSH server, GNOME
RDP sharing, the Guacamole connection, the default `guacadmin` password, and
Steam control. "n" is remembered in `data/host-setup.skip`; `make setup-host`
asks again. New one-time host steps belong in that script, not in a separate
README instruction. GNOME automatic login is only pointed out, never changed.

The next unfinished areas are:

1. a Docker-based development workflow that does not require host npm;
2. remote desktop reliability and stronger input capture;
3. remote audio output through Guacamole/RDP when possible.

Planning lives in `PLAN.md` (registry) and `guidelines/milestones/`
(one file per milestone). General project rules are in `guidelines/*.md`. The
earlier `instructions.md` and `milestones/` were removed from the working
tree. Their unfinished items are listed in the `PLAN.md` backlog and under
"Known Unfinished Work" below.

## Architecture

- `frontend`: React, TypeScript, and Vite dashboard.
- `backend`: FastAPI API server.
- `reverse-proxy`: Caddy routing layer.
- `portainer`: Docker management UI.
- `terminal`: ttyd + OpenSSH client, non-root, no published port. Caddy
  routes `/terminal*` to it. `--check-origin` blocks cross-site websockets.
  The host key is stored in the `terminal-ssh` volume.
- `guacamole`, `guacd`, `guacamole-db`: browser remote-desktop stack in the
  `remote` Compose profile. The Makefile always passes `--profile remote`, so
  `make up` and `make down` include it.
- Cockpit: intentionally installed on the host OS.
- GNOME Remote Desktop over RDP: default way to expose the real, logged-in
  physical Ubuntu desktop.
- xrdp with XFCE: alternate way to provide a separate management desktop, not
  the default physical-screen path.

The browser path is:

```text
browser -> Caddy/dashboard -> Guacamole -> guacd
        -> host.docker.internal:3389 -> GNOME Remote Desktop
```

`make enable-physical-screen` configures GNOME Remote Desktop for the current
logged-in GNOME user. The server normally needs an active GNOME login for the
physical-screen path.

## Durable Product And Security Decisions

- The project must provide working browser remote desktop, not diagnostics
  alone.
- Use established remote-access tools. Do not build a low-level streaming
  protocol.
- Keep the dashboard LAN/Tailscale/WireGuard-first.
- Do not expose dashboard, Guacamole, Portainer, Cockpit, RDP, or VNC directly
  to the public internet.
- The custom dashboard has no login for the current MVP. Guacamole, Portainer,
  and Cockpit keep their own authentication.
- The only command execution in the web UI is the Terminal page, and it is
  gated by the host's SSH login (user decision, 2026-09-25). Do not add
  unauthenticated shells, a host-namespace or privileged terminal container,
  or Docker socket access for the terminal.
- The backend can read the whole host filesystem read-only (`/host-root`) for
  disk usage. The API returns only names and sizes, never file contents. Keep
  it that way.
- Container and host controls must be allowlisted. Dangerous host actions must
  require confirmation.
- The only host action that crosses from a container to the host is Steam
  control. It uses an SSH key restricted by `restrict,command=` to a script
  that accepts only `status`/`start`/`stop`. Any new host action must use the
  same forced-command pattern (one key and one script per purpose), never a
  general SSH key or a shell.
- The frontend must never access the Docker socket. The backend may use it only
  for scoped status and allowlisted controls.
- Production frontend builds already happen in a `node:22-alpine` Docker stage.
  Do not ask the user to install host npm.

## Implemented Remote Input Behavior

- Dashboard settings let the user select both local and remote keyboard
  layouts.
- The saved remote layout is applied to Guacamole RDP connections as the
  `server-layout` database parameter. An open session must reconnect before a
  layout change takes effect.
- The dashboard stores a preferred remote-input release shortcut for future
  stronger capture behavior.
- Focus mode makes a best effort to request browser fullscreen, focus the
  Guacamole iframe, and use Keyboard Lock where supported. Browsers and
  operating systems may still reserve shortcuts.
- Touch devices default to Guacamole's relative/touchpad mouse mode and text
  input mode through `GUAC_PREFERENCES`.
- The remote page overlays Keyboard and Touchpad/Touchscreen controls on the
  frame. The keyboard control focuses a dashboard-owned textarea and forwards
  text/backspace to Guacamole's native text input.
- Switching Touchpad/Touchscreen uses an explicit two-choice control and a
  temporary blank iframe reload so Guacamole's unload behavior does not restore
  the old preference.

## Known Unfinished Work

### Containerized development

Add `docker-compose.dev.yaml` with a Node/Vite development service, a source
bind mount, container-owned persistent `node_modules`, a predictable safe port,
and Make wrappers. Keep host npm unnecessary.

### Reliability and full input capture

Investigate, with evidence:

- remote screen freezes when switching windows in Ubuntu;
- black screen or failed capture when fullscreen is enabled inside Ubuntu;
- keyboard commands remaining on the local browser/PC after the remote frame is
  focused;
- practical limits of Fullscreen, Keyboard Lock, Pointer Lock, iframe focus,
  and browser/OS-reserved shortcuts;
- correct use of the configured release shortcut.

First determine whether a failure is visible on the physical monitor, in GNOME
Remote Desktop logs, in guacd/Guacamole, or only in the browser.

### Remote audio

Start with Guacamole RDP audio redirection. Check the connection's
`disable-audio` setting, browser playback permissions, guacd/FreeRDP channel
support, and whether GNOME Remote Desktop exposes speaker audio for the
physical-screen session.

Only if that path is proven unavailable should the project evaluate an
xrdp/PipeWire or PulseAudio path for a separate session, another established
browser remote desktop stack, or an explicitly approved audio bridge. Do not
start by building custom audio streaming.

## Operational Facts

Important commands:

- `make setup`: create `.env` with a random DB password (never overwrites)
  and the Guacamole schema. `make up` does this too.
- `make setup-host`: ask again about every one-time host step, including
  steps skipped earlier.
- `make up`: create `.env` if missing, preflight checks, build, start every
  service, wait for healthy, run the host setup (prompts only for missing
  steps), apply the remote keyboard layout, and print URLs. Safe to repeat.
- `make down` (also `make shutdown` / `make maintenance-stop`): stop every
  service and keep volumes.
- `make doctor`: read-only reboot readiness check (`scripts/check-host.sh`),
  then `check-remote`.
- `make test`: backend unit tests in the backend image (`backend/tests/`).
- `make refresh`: force-recreate the dashboard containers after an update.
- `make remote-up`: start Guacamole, guacd, and PostgreSQL.
- `make remote-down`: stop the remote-desktop stack.
- `make guacamole-init`: generate the PostgreSQL schema.
- `make apply-remote-input`: apply the saved remote keyboard layout to
  Guacamole RDP connections.
- `make check-remote`: inspect Guacamole and host RDP readiness.
- `make enable-physical-screen`: configure GNOME physical-screen RDP.
- `make enable-steam-control`: install the Steam forced command, create the
  backend's key in `data/steam-control/`, and authorize it (no sudo). Revoke
  by deleting the `scp-steam-control` line from `~/.ssh/authorized_keys`.
- `make install-host-remote-desktop`: install the alternate xrdp/XFCE path.

Important state:

- Example configuration lives under `config/*.example.yml`.
- Local `config/*.yml` files override the examples when present.
- UI settings are stored in the backend data volume as
  `settings.override.yml`.
- The backend sees host-mounted media read-only at `/host-media` and
  `/host-mnt`; the host roots default to `/run/media` and `/mnt` and can be
  changed with `HOST_MEDIA_PATH` and `HOST_MOUNT_PATH`.
  `HOST_MEDIA_HOST_ROOTS` passes the host paths so each drive card has a
  `host_path` that the disk usage panel can open.
- Reboot behavior: every container is `restart: unless-stopped`, so the stack
  returns once Docker starts. The physical-screen path also needs a logged-in
  GNOME session (automatic login). Automatic login may leave the GNOME
  keyring locked, which can block GNOME Remote Desktop credentials. This is
  unverified on the real server.
- `make up` has not yet been run against the user's live stack with these
  changes. The first run recreates the backend (new host mount) and adds
  `scp-terminal`.
- The user's live stack often runs on another Ubuntu server after `git pull`.
  Checks in this workspace may not represent that server.

## Guacamole And RDP Troubleshooting Context

- Use Guacamole/guacd `1.6.0` or newer. Version `1.5.5` can fail against GNOME
  physical-screen RDP with `Client did not advertise support for the Graphics
  Pipeline`.
- If that error occurs, pull and recreate `guacd` and `guacamole`, then run
  `make check-remote`.
- For the GNOME physical-screen path, inactive xrdp is expected.
- Guacamole should reach `host.docker.internal:3389` from `guacd`.
- Guacamole's default admin credentials are commonly `guacadmin` / `guacadmin`
  until changed. The PostgreSQL password is not a Guacamole user password.
- The RDP username/password are those entered during
  `make enable-physical-screen`; they are not necessarily the Ubuntu login.
- Physical-screen connection basics: protocol RDP, guacd host `guacd`, guacd
  port `4822`, network host `host.docker.internal`, network port `3389`, blank
  domain, blank Remote Desktop Gateway, and ignored server certificate. Try
  security mode `TLS` if negotiation drops.
- If the dashboard shows a stale sign-in page with `[object Object]`, rebuild
  and force-recreate frontend, backend, and reverse proxy, then hard-refresh the
  browser.

## Recommended Start For The Next Agent

1. Read the root documentation, `guidelines/`, `PLAN.md`, and the chosen
   milestone file in the required order.
2. Confirm which milestone the user's request belongs to.
3. Inspect current code and `git status`; do not infer implementation from the
   milestone status alone.
4. For host-dependent remote work, collect browser symptoms, guacd logs, GNOME
   Remote Desktop logs, and physical-monitor behavior before changing the
   architecture.
5. Update the selected milestone and this handoff with verified outcomes before
   ending the session.
