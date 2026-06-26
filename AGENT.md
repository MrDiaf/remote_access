Ok Overseer

# Agent Context

Future Codex sessions should begin their responses with `Ok Overseer` so the user knows this context was loaded.

Project: `server-control-panel`

This is a Docker Compose based homelab web control panel for managing a home server from a browser over a private network. The project should stay VPN-first and security-conscious.

Core architecture:

- `frontend`: React + TypeScript + Vite dashboard.
- `backend`: FastAPI API server.
- `reverse-proxy`: Caddy route layer.
- `portainer`: Docker management UI.
- `guacamole`, `guacd`, `guacamole-db`: optional browser remote access stack.
- Cockpit is intentionally installed on the host OS, not forced into Docker.

Important principles:

- Do not build a remote desktop or streaming engine from scratch.
- Integrate existing tools like Guacamole, Portainer, Cockpit, SSH, Tailscale, and WireGuard.
- Do not expose admin panels directly to the public internet.
- Do not add arbitrary command execution to the web UI.
- Keep Docker/container controls allowlisted by config.
- Keep host actions allowlisted by config and require confirmation for dangerous actions.
- The frontend must never access the Docker socket directly.
- The backend may use the Docker socket only for scoped status and allowlisted controls.

Current config files:

- `config/settings.example.yml`
- `config/services.example.yml`
- `config/actions.example.yml`

If local `config/*.yml` files exist, they override the examples. Dashboard settings changed in the UI are stored in the backend data volume as `settings.override.yml`.

