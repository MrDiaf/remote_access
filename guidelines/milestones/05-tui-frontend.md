# Milestone 05 — Terminal UI (TUI) frontend

## Objective

Offer every dashboard feature in a keyboard-driven terminal UI, so the server
can be managed from an SSH session or a local console without a browser.

## Dependencies

None. Uses the existing backend API (`/api/*`) unchanged.

## Existing-state check

Before implementation:

1. Inspect `tui/`, the `tui` service in `docker-compose.yml`, and `make tui`.
2. Evaluate every completion criterion below and preserve what already works.
3. Implement only what is missing.

Do not read other milestone files unless strictly necessary.

## Scope

- `tui/` (Python + Textual app, Dockerfile, tests)
- `docker-compose.yml`: `tui` service in its own `tui` profile, so `make up`
  never starts it
- `Makefile`: `make tui`, `make test` also runs the TUI tests
- README, handoff

Out of scope: backend API changes, dashboard login, and drawing the remote
desktop image in the terminal.

## Feature parity

| Browser page | TUI tab |
| --- | --- |
| Remote Desktop | Guacamole/guacd/DB/RDP status, connection hint, input preferences, Guacamole URL, apply keyboard layout. The desktop image itself needs a browser. |
| Terminal | SSH login to the host (the TUI suspends and runs `ssh`, same validation as the web terminal) |
| Services | Service table with status and detail |
| Status | CPU, RAM, GPUs, drives, uptime/load, network totals and addresses, disk usage explorer (drives, drill-down, up, rescan) |
| Docker | Container table; start/stop/restart allowlisted containers with confirmation |
| Actions | Action list; run, confirm when required or dangerous, show result and output |
| Settings | Server name, keyboard layouts, release shortcut, links, allowed containers; save, then apply the layout to Guacamole |

## Required work

- Talk only to the backend HTTP API. The TUI gets no Docker socket and no
  shell of its own.
- API failures show as notifications and never crash the app.
- Run in a container through `make tui`, with no Python needed on the host.

## Completion criteria

- [x] `make tui` opens the TUI against the running stack
- [x] Every tab in the parity table loads real data from the running backend
- [x] Headless Textual tests drive every tab against a fake API and pass in `make test`
- [x] Docker and Action runs require confirmation exactly when the browser does
- [x] Unsafe SSH usernames are refused by the TUI terminal
- [ ] User confirms the TUI works on the real server (interactive use, including an SSH session from the Terminal tab)

## Implementation notes

- Python + Textual 8.2.8 (`tui/scp_tui/`), API client on the standard library
  (`urllib`), so Textual is the only dependency.
- `tui` Compose service in the `tui` profile, `SCP_API_URL=http://backend:8000`,
  and its own `tui-ssh` volume for the pinned host key. `make tui` passes
  `SCP_DASHBOARD_URL` so the Remote tab shows a clickable Guacamole URL.
- Keyboard layout lists are copied from `frontend/src/remoteInputOptions.ts`;
  keep the two in sync.
- The browser's static "Setup Checklist" on the Remote Desktop page is not
  copied. It still describes the xrdp path, not the default GNOME path.

## Verification

- `make test`: backend 6 OK; TUI 10 OK. The TUI tests cover every tab, drive
  drill-down, up and rescan, the Docker choice plus confirmation, actions
  confirming only when required, disabled actions, settings save then apply,
  unsafe SSH usernames, API errors shown as notifications, and number keys
  switching tabs while a table has focus.
- A headless run against the live backend (read-only; nothing saved, no
  container or action run): Remote 4 status rows and 3 input rows; Services
  10; Status 8 stat rows (including the RTX 3060 and the `bulk` drive);
  Docker 30 containers; Actions 3; disk usage of `/` 21 entries; Settings
  loaded `Home Server` / `sv-se-qwerty`. No API errors.
- `make tui` in a pseudo-terminal: rendered `server-control-panel — Home
  Server` with live data, quit on `q`, exit code 0.
- Bug found and fixed during verification: number keys did not switch tabs
  while a table had focus, because TabbedContent jumped back to the focused
  pane. A regression test covers it.
