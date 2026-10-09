# Progress

Milestone registry. Full instructions are in `guidelines/milestones/`. Keep the
checkboxes here in sync with each milestone file.

## Milestone 01 — Web terminal (`guidelines/milestones/01-web-terminal.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] Terminal image builds and is served at `/terminal/` through Caddy
- [x] Cross-origin websocket refused; dashboard origin reaches the host SSH password prompt
- [x] Unsafe usernames refused
- [x] Desktop and phone layout without horizontal overflow
- [ ] User logs in and runs commands on the real server
- [ ] User confirms typing works on a real phone

## Milestone 02 — Disk usage explorer (`guidelines/milestones/02-disk-usage-explorer.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make test` passes
- [x] `/api/disk-usage` lists folders largest first and marks other mounts
- [x] Unsafe paths refused (400/404)
- [x] Drill-down UI works on desktop and phone
- [ ] Extra drives open from their buttons on the real server

## Milestone 03 — One-command setup and reboot recovery (`guidelines/milestones/03-setup-and-reboot.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make help` is accurate and grouped
- [x] `make setup` is safe and produces a working Guacamole schema
- [x] `make preflight` and `make doctor` work
- [ ] `make up` on the real server starts all 8 containers and prints URLs
- [ ] Stack returns after a real reboot without running `make`

## Milestone 04 — GPU usage on the Status page (`guidelines/milestones/04-gpu-status.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make test` passes
- [x] Backend reads NVIDIA GPU usage and VRAM when the GPU override is active
- [x] GPU card hidden when no NVIDIA runtime is available
- [ ] User sees the GPU card on the real server after `make up`

## Milestone 05 — Terminal UI frontend (`guidelines/milestones/05-tui-frontend.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make tui` opens the TUI against the running stack
- [x] Every tab loads real data from the running backend
- [x] Headless Textual tests drive every tab and pass in `make test`
- [x] Confirmation rules match the browser
- [x] Unsafe SSH usernames refused
- [ ] User confirms the TUI works on the real server

## Milestone 06 — Steam control and Remote Play (`guidelines/milestones/06-steam-control.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make test` passes, including the forced command refusing every verb except status/start/stop
- [x] `GET /api/steam` reports `not set up` before setup; stop without confirmation returns 409
- [x] The forced command reports a running Steam and does not start a second copy
- [x] The Steam card fits desktop and phone widths
- [x] Real SSH path: `status` works and other commands are refused
- [x] Big Picture is allowed end to end; tests pass
- [ ] On the real server: Start, Big Picture, and Stop work from the phone
- [ ] User pairs a Steam Link device and streams a game

## Milestone 07 — `make up` sets up everything (`guidelines/milestones/07-guided-make-up.md`)

Status: implemented; waiting for confirmation on the real server.

- [x] `make env` creates `.env` once and never overwrites it
- [x] Without a TTY, host setup only reports the real state
- [x] With answers, it creates a working Guacamole connection and changes the `guacadmin` password
- [x] "n" is remembered; `make setup-host` asks again
- [x] `make test` still passes
- [ ] On the real server, one `make up` finishes setup and the phone reaches the desktop

## Milestone 06 — Experimental Sunshine + Moonlight-Web stream (`guidelines/milestones/06-sunshine-stream-experiment.md`)

Status: in progress (experiment on the `exp` branch).

- [x] Moonlight-Web served at `/stream/`
- [x] `make install-sunshine` installs and starts Sunshine
- [ ] Moonlight-Web pairs with Sunshine
- [ ] Physical screen streams with keyboard, mouse and audio
- [ ] Works from a phone
- [ ] User decides whether to keep it

## Backlog (no milestone file yet)

These are described in `handoff.md` under "Known Unfinished Work". Write a
milestone file before starting one.

- Containerized frontend development (`docker-compose.dev.yaml`, no host npm)
- Remote desktop reliability and stronger input capture
- Remote audio through Guacamole/RDP
