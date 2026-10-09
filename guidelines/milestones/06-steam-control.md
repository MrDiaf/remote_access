# Milestone 06 — Steam control and Remote Play

## Objective

Let the user play the server's Steam games on a phone, TV, or another PC
through Steam Remote Play. From the dashboard and the TUI they can start Steam
(normal or Big Picture) on the logged-in desktop and quit it cleanly, with a
live Running/Stopped status and a short pairing guide.

User decisions (2026-10-09): clients are the Steam Link app (phone/tablet/TV)
and Steam on another PC. Away from home they use Steam's own relay (Remote
Play Anywhere), so the project opens no firewall ports. The setup help is a
guide in the web app, not automated Steam configuration.

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
`make enable-steam-control`) accepts only `status`, `start`, `bigpicture`, and
`stop`.
Anything else exits 2. `restrict` removes pty, forwarding, and agent access.
The key lives in `data/steam-control/` (gitignored) and is mounted read-only
at `/steam-control`. The whole folder is mounted, so a key created while the
backend runs works without recreating the container.

- `start`: runs `systemd-run --user --unit=scp-steam --collect <steam>`, so
  Steam inherits the GNOME session's `DISPLAY`/`WAYLAND_DISPLAY` from the
  user's systemd manager. If no desktop session exists, it refuses with
  `no-session`.
- `bigpicture`: starts Steam with `-gamepadui`, or, when Steam is already
  running, hands it `steam://open/bigpicture` (also through `systemd-run`, so
  it has the desktop environment).
- `stop`: runs `steam -shutdown` and waits up to 30 s. It never kills Steam,
  because a game may still be saving.
- `status`: looks for the real client (`.../ubuntu12_32/steam`), not the
  `/usr/games/steam` launcher script or its dialogs, so it also sees a Steam
  that was opened by hand. While the `scp-steam` unit is active but the client
  is not up yet, it reports `starting`, or `setup-needed` when the apt
  package's one-time Install dialog is waiting on the desktop.
- `start`/`bigpicture` never launch again while a launch is pending, and
  `stop` on a pending launch just stops the unit (it never runs `-shutdown`,
  which would bootstrap an uninstalled Steam). `-shutdown` and steam:// URLs
  go to whichever install (apt or snap) is actually running.
- Steam binary: `/usr/games/steam` (apt/.deb), falling back to
  `/snap/bin/steam`.

API: `GET /api/steam`, `POST /api/steam/start`, `POST /api/steam/bigpicture`,
and `POST /api/steam/stop`.
Stop requires `{"confirmed": true}` and otherwise returns 409.

## Scope

- Backend: `steam_control.py`, `SteamStatus` model, three routes,
  `openssh-client` in the image, and tests.
- `docker-compose.yml`: key mount and SSH host/port environment.
- `Makefile`: `enable-steam-control` and `data-dirs`.
- Frontend: Steam card on the Actions page (Start / Big Picture / Stop) with
  a collapsible Remote Play guide that links to the remote desktop for the
  pairing PIN, and `StatusBadge` tones for the new states.
- TUI: Steam line, guide text, and the `s` and `b` keys on the Actions tab,
  with tests.
- `scripts/check-host.sh`: an optional "Steam control" section.

Out of scope: launching specific games, changing Steam's own settings,
opening Remote Play ports in ufw (the user chose Steam's relay), and autostart
on login.

## Accepted limitations

- Steam can start only while someone is logged in to the desktop. This is the
  same requirement as the physical-screen remote desktop.
- If Steam ignores `-shutdown` (for example, while a game is closing), the
  card shows `stopping`. The user finishes the job through the remote desktop.
- The host runs an installed copy of `scripts/host/steam-control.sh`.
  `make up` (`setup-host.sh`) replaces it whenever it differs from the
  repository.
- GNOME on Wayland is a weak Remote Play host. Valve has open reports of black
  or frozen video (steam-for-linux #10315, #13585), mostly when streaming the
  desktop or Big Picture. Games usually stream. The guide says to start the
  game directly. The project cannot fix this.
- With ufw active and no Remote Play ports open, home streaming may also take
  the slower relay path. If that matters, add ufw rules for UDP 27031–27036
  and TCP 27036–27037 from the LAN only.

## Completion criteria

- [x] `make test` passes, including the forced command refusing every verb
      except status/start/stop
- [x] `GET /api/steam` reports `not set up` before setup, and stop without
      confirmation returns 409
- [x] The forced command reports a running Steam (snap) on this workstation and
      does not start a second copy
- [x] The Steam card fits desktop and phone widths without horizontal overflow
- [x] Through the real SSH path on this workstation, `status` reports the open
      Steam and `bash -c id` is refused by the forced command
- [x] Big Picture is allowed end to end (backend, API, card, TUI `b`); tests pass
- [ ] On the real server: Start, Big Picture, and Stop work from the phone
- [ ] User pairs a Steam Link device and streams a game

## Verification

- `docker compose config -q`, `make build` (includes `tsc && vite build`),
  `make test`: 13 backend tests OK, 12 TUI tests OK.
- One-off backend container: `GET /api/steam` → `not set up`;
  `POST /api/steam/stop {}` → 409; `POST /api/steam/reboot` → 404.
- `SSH_ORIGINAL_COMMAND=status scripts/host/steam-control.sh` → `running`
  (snap Steam open on this workstation). `start` → `running` (no second
  copy). `"bash -i"` → `refused`, exit 2.
- Headless Chrome screenshots of `/#actions` at 1280×900 and 390×1000.
- After the user set up Steam control here: the backend container's ssh, with
  the real key → `status` = `running`; `bash -c id` and `bigpicture-typo` →
  `refused`, exit 2. `setup-host.sh` replaced the outdated installed script.
- Remote Play additions: `make test` → 14 backend and 13 TUI tests OK. The
  rendered DOM shows Big Picture enabled while Steam runs.
- 2026-10-09 regression, fixed: after `apt install steam-installer`, the
  launcher waiting on its first-run dialog counted as running, so each Big
  Picture click stacked another dialog (6), and Stop bootstrapped the
  install. After the fix: status `stopped` with nothing running; `make test`
  → 14 backend and 13 TUI tests OK.
- Not run here: `start`, `bigpicture`, and `stop` against the real Steam,
  because they would change the user's open Steam.
