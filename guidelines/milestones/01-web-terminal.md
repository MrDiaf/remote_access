# Milestone 01 — Web terminal

## Objective

Give the dashboard a Terminal page that opens a shell on the Ubuntu host from
a desktop or phone browser, gated by the host's normal SSH login.

## Dependencies

None.

## Existing-state check

Before implementation:

1. Inspect `terminal/`, the `terminal` service in `docker-compose.yml`, the
   `/terminal*` route in `proxy/Caddyfile`, and
   `frontend/src/pages/TerminalPage.tsx`.
2. Evaluate every completion criterion below and preserve what already works.
3. Implement only what is missing.

Do not read other milestone files unless strictly necessary.

## Product decision

On 2026-09-25 the user chose an SSH-authenticated web terminal. This replaces
the earlier rule "no arbitrary command execution in the dashboard" for this
page only. The dashboard stays login-free, so the terminal must never open a
shell without the host's own SSH authentication.

## Scope

- `terminal/` (ttyd + OpenSSH client image and login script)
- `docker-compose.yml` (`terminal` service, `terminal-ssh` volume)
- `proxy/Caddyfile` (`/terminal*` route)
- Frontend: Terminal page, nav entry, styles
- `.env.example`, README, handoff

Out of scope: a custom PTY or websocket backend, a privileged or host-namespace
container, Docker socket access for the terminal, and dashboard login.

## Required work

- ttyd serves `/terminal/` behind Caddy with `--check-origin` so other sites
  cannot open the websocket.
- Every session runs only `terminal-login`. It asks for a username (unless
  `TERMINAL_SSH_USER` is set), validates it, and `exec`s `ssh` to
  `TERMINAL_SSH_HOST:TERMINAL_SSH_PORT`.
- Usernames that could be parsed as ssh options or hosts are refused.
- The host key is pinned on first use and kept in the `terminal-ssh` volume.
- The container runs as a non-root user with no published port.
- The dashboard embeds the terminal and also links to it in its own tab.

## Completion criteria

- [x] `docker compose build terminal` succeeds
- [x] `/terminal/` returns HTTP 200 through Caddy
- [x] A websocket from the dashboard origin is accepted; one from another origin is refused
- [x] Through Caddy, the session shows `Username:` and then the host's SSH password prompt
- [x] Usernames `-oProxyCommand=id`, `a b`, `root@evil`, and an empty name are refused
- [x] Terminal page renders on desktop (1280 px) and phone (390 px) widths without horizontal page overflow
- [ ] User logs in and runs commands from the Terminal page on the real server
- [ ] User confirms typing works on a real phone

## Verification

- Isolated test network with the built terminal, backend, frontend, and Caddy
  images on port 18080 (the running stack was not touched).
- `curl` websocket upgrade with matching Origin → `101`; with
  `Origin: http://evil.example` → refused (ttyd logs "refuse to serve WS client
  from different origin").
- A Python websocket client through Caddy sent `ronny` and received
  `ronny@host.docker.internal's password:`.
- `printf '<name>\n' | docker run --rm -i server-control-panel-terminal terminal-login`
  printed `Invalid username.` for each unsafe name.
- Playwright screenshots at 1280×1000 and 390×844 showed no horizontal overflow.
