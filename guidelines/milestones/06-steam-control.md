# Milestone 06 — Start and quit Steam from the dashboard

## Objective

Let the user start Steam on the server's logged-in desktop, and quit it
cleanly, from the dashboard and the TUI, with a live Running/Stopped status.

## Dependencies

None. Uses the host SSH server that the Terminal page already relies on.

## Existing-state check

Before making changes:

1. Inspect `backend/app/steam_control.py`, `scripts/host/steam-control.sh`,
   `scripts/enable-steam-control.sh`, and the Steam card in
   `frontend/src/pages/ActionsPage.tsx`.
2. Evaluate every completion criterion below and run `make test`.
3. Implement only what is missing.

## Design

The backend runs in a container, while Steam must run inside the host's GNOME
session. The backend therefore SSHes to `host.docker.internal` with its own
key, and `~/.ssh/authorized_keys` pins that key to a forced command:

```text
restrict,command="~/.local/bin/scp-steam-control" ssh-ed25519 … scp-steam-control
```

The forced command (`scripts/host/steam-control.sh`, installed by
`make enable-steam-control`) accepts only `status`, `start`, and `stop`.
Anything else exits 2. `restrict` removes pty, forwarding, and agent access.
The key lives in `data/steam-control/` (gitignored) and is mounted read-only
at `/steam-control`. The whole folder is mounted, so a key created while the
backend runs works without recreating the container.

- `start`: runs `systemd-run --user --unit=scp-steam --collect <steam>`, so
  Steam inherits the GNOME session's `DISPLAY`/`WAYLAND_DISPLAY` from the
  user's systemd manager. If no desktop session exists, it refuses with
  `no-session`.
- `stop`: runs `steam -shutdown` and waits up to 30 s. It never kills Steam,
  because a game may still be saving.
- `status`: `pgrep -x steam` for the user, so it also sees a Steam that was
  opened by hand.
- Steam binary: `/usr/games/steam` (apt/.deb), falling back to
  `/snap/bin/steam`.

API: `GET /api/steam`, `POST /api/steam/start`, and `POST /api/steam/stop`.
Stop requires `{"confirmed": true}` and otherwise returns 409.

## Scope

- Backend: `steam_control.py`, `SteamStatus` model, three routes,
  `openssh-client` in the image, and tests.
- `docker-compose.yml`: key mount and SSH host/port environment.
- `Makefile`: `enable-steam-control` and `data-dirs`.
- Frontend: Steam card on the Actions page, `StatusBadge` tones for the new
  states.
- TUI: Steam line and `s` key on the Actions tab, with tests.
- `scripts/check-host.sh`: an optional "Steam control" section.

Out of scope: launching specific games, Steam Remote Play/streaming
configuration, and autostart on login.

## Accepted limitations

- Steam can start only while someone is logged in to the desktop. This is the
  same requirement as the physical-screen remote desktop.
- If Steam ignores `-shutdown` (for example, while a game is closing), the
  card shows `stopping`. The user finishes the job through the remote desktop.
- Updating `scripts/host/steam-control.sh` requires rerunning
  `make enable-steam-control`, because the host runs an installed copy.

## Completion criteria

- [x] `make test` passes, including the forced command refusing every verb
      except status/start/stop
- [x] `GET /api/steam` reports `not set up` before setup, and stop without
      confirmation returns 409
- [x] The forced command reports a running Steam (snap) on this workstation and
      does not start a second copy
- [x] The Steam card fits desktop and phone widths without horizontal overflow
- [ ] On the real server: answer yes to Steam control in `make up` (or run
      `make enable-steam-control`), then Start opens Steam on the desktop
      and Stop quits it, from the phone

## Verification

- `docker compose config -q`, `make build` (includes `tsc && vite build`),
  `make test`: 13 backend tests OK, 12 TUI tests OK.
- One-off backend container: `GET /api/steam` → `not set up`;
  `POST /api/steam/stop {}` → 409; `POST /api/steam/reboot` → 404.
- `SSH_ORIGINAL_COMMAND=status scripts/host/steam-control.sh` → `running`
  (snap Steam open on this workstation). `start` → `running` (no second
  copy). `"bash -i"` → `refused`, exit 2.
- Headless Chrome screenshots of `/#actions` at 1280×900 and 390×1000.
- Not run here: the full SSH round trip. It needs `make enable-steam-control`,
  which edits `~/.ssh/authorized_keys`, and quitting Steam would close the
  user's open Steam.
