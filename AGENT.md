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
- Host-side xrdp + XFCE is the recommended MVP remote desktop service. Guacamole should connect to `host.docker.internal:3389` over RDP.
- If the server has a physical GNOME monitor session, prefer GNOME Remote Desktop via `make enable-physical-screen` so Guacamole controls the actual logged-in screen instead of a separate xrdp session.

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

Current config files:

- `config/settings.example.yml`
- `config/services.example.yml`
- `config/actions.example.yml`

If local `config/*.yml` files exist, they override the examples. Dashboard settings changed in the UI are stored in the backend data volume as `settings.override.yml`.

Important Make targets:

- `make up`: main dashboard stack.
- `make remote-up`: Guacamole, guacd, and PostgreSQL.
- `make guacamole-init`: generate Guacamole PostgreSQL schema.
- `make remote-down`: stop the remote desktop stack.
- `make check-remote`: check Guacamole and host RDP readiness.
- `make install-host-remote-desktop`: install xrdp + XFCE on Ubuntu/Debian host.
- `make enable-physical-screen`: enable GNOME physical monitor sharing over RDP.
