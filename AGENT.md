Ok Overseer

# Agent Context

Future Codex sessions should begin their responses with `Ok Overseer` so the user knows this context was loaded.

Project: `server-control-panel`

This is a Docker Compose based homelab remote control portal for managing a home server from a browser over a private network. The project should stay VPN-first and security-conscious.

The primary feature is browser-based remote desktop access. The user should be able to open one dashboard URL from LAN/Tailscale, click Remote Desktop, open Guacamole, and visually control the server GUI through the browser. The custom dashboard MVP should not require its own login.

Core architecture:

- `frontend`: React + TypeScript + Vite dashboard.
- `backend`: FastAPI API server.
- `reverse-proxy`: Caddy route layer.
- `portainer`: Docker management UI.
- `guacamole`, `guacd`, `guacamole-db`: recommended default browser remote desktop stack, started with `make remote-up`.
- Cockpit is intentionally installed on the host OS, not forced into Docker.
- Host-side GNOME Remote Desktop is the recommended default for this user because the server has a real Ubuntu desktop/monitor and they want the actual logged-in physical screen in the browser.
- `make enable-physical-screen` configures GNOME Remote Desktop over RDP on TCP 3389 for the current logged-in GNOME user. Guacamole should connect to `host.docker.internal:3389`.
- xrdp + XFCE is only the fallback/alternate path for a separate management desktop session. Do not steer the user back to xrdp unless they explicitly want a separate session.

Important principles:

- This project DOES provide browser-based remote desktop access by integrating existing tools.
- Do not accept a diagnostics-only implementation. Remote Desktop must be a working first-class feature.
- Do not build a low-level remote desktop/video streaming protocol from scratch.
- Treat Remote Desktop as the primary dashboard page. Service status, Portainer, Cockpit, Docker status, and actions are secondary helpers.
- Integrate existing tools like Guacamole, xrdp, VNC/noVNC/KasmVNC, Portainer, Cockpit, SSH, Tailscale, and WireGuard.
- Do not expose admin panels directly to the public internet.
- Do not add arbitrary command execution to the web UI.
- Do not make command running a major feature. SSH already handles terminal workflows.
- Keep Docker/container controls allowlisted by config.
- Keep host actions allowlisted by config and require confirmation for dangerous actions.
- The frontend must never access the Docker socket directly.
- The backend may use the Docker socket only for scoped status and allowlisted controls.
- The custom dashboard currently has no login. If the user sees a `server-control-panel` sign-in page with `[object Object]`, they are looking at a stale frontend image talking to the newer no-auth backend. Rebuild/recreate with `docker compose up -d --build --force-recreate frontend backend reverse-proxy` and hard-refresh the browser.

Remote desktop operational notes:

- Guacamole/guacd should be `1.6.0` or newer. GNOME physical-screen RDP can fail with `Client did not advertise support for the Graphics Pipeline` when `guacd` is still `1.5.5`.
- If that Graphics Pipeline error appears, run `docker compose pull guacd guacamole` and `docker compose --profile remote up -d --force-recreate guacd guacamole`, then `make check-remote`.
- For the GNOME physical-screen path, inactive `xrdp` is expected. `make check-remote` should show GNOME Remote Desktop enabled, `host.docker.internal:3389` reachable from `guacd`, and host listening on TCP 3389.
- Guacamole admin login is usually `guacadmin` / `guacadmin` until changed. The Guacamole database password in `.env` is not a user login. The RDP connection username/password are the credentials entered during `make enable-physical-screen`, not necessarily the Ubuntu account password.
- Correct Guacamole connection fields for physical GNOME: protocol `RDP`; GUACD hostname `guacd`; GUACD port `4822`; network hostname `host.docker.internal`; network port `3389`; domain blank; ignore server certificate checked; Remote Desktop Gateway blank. If security negotiation drops, try security mode `TLS`.
- Remote keyboard settings are stored in dashboard settings and applied to Guacamole RDP connections through the Guacamole database `server-layout` parameter. Existing Guacamole sessions must reconnect before keyboard changes take effect.
- Remote Desktop has a best-effort Focus mode that requests browser fullscreen, focuses the Guacamole iframe, and asks for browser keyboard lock where supported. It cannot override every browser/OS-reserved shortcut, so full input capture remains a hardening task.
- On touch devices, the dashboard configures Guacamole's own browser preferences before the embedded iframe loads: relative/touchpad mouse mode by default and text input mode enabled. This is intentionally Guacamole-native mobile behavior, not a custom pointer overlay. The Remote Desktop page exposes touch-only Touchpad/Touchscreen mode controls and a Keyboard button that focuses Guacamole's text input textarea for the phone keyboard.
- The user's real stack often runs on another Ubuntu server PC after `git pull`; local checks in this workspace may not reflect the actual host state unless the user says they are running here.

Next session TODO:

- See `TODO.md` before starting new feature work.
- The next UX focus is remote desktop reliability and control: investigate freezes when switching windows, improve keyboard/input capture so commands go to the remote desktop after focus, and verify Guacamole's native touchpad mode on a real phone.
- These are TODOs only as of this handoff; do not assume they have been implemented.

Current config files:

- `config/settings.example.yml`
- `config/services.example.yml`
- `config/actions.example.yml`

If local `config/*.yml` files exist, they override the examples. Dashboard settings changed in the UI are stored in the backend data volume as `settings.override.yml`.

Important Make targets:

- `make up`: main dashboard stack.
- `make refresh`: rebuild/recreate dashboard containers, start the remote stack, and reapply saved remote keyboard settings to Guacamole.
- `make remote-up`: Guacamole, guacd, and PostgreSQL.
- `make guacamole-init`: generate Guacamole PostgreSQL schema.
- `make apply-remote-input`: reapply the saved remote keyboard setting to Guacamole RDP connections.
- `make remote-down`: stop the remote desktop stack.
- `make check-remote`: check Guacamole and host RDP readiness.
- `make install-host-remote-desktop`: install xrdp + XFCE on Ubuntu/Debian host.
- `make enable-physical-screen`: enable GNOME physical monitor sharing over RDP.
