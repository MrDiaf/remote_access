# server-control-panel

A self-hosted web control panel for managing a powerful home server from a browser. It is designed for VPN-first access with tools like Tailscale or WireGuard, and it intentionally avoids building a remote desktop or video streaming engine from scratch.

The panel gives you one place to see host status, inspect Docker containers, run safe allowlisted actions, and jump into existing admin tools such as Portainer, Guacamole, and Cockpit.

## What This Is Not

- Not a public internet admin panel.
- Not a replacement for Cockpit, Portainer, Guacamole, or SSH.
- Not an arbitrary command runner.
- Not a custom remote desktop/video streaming system.

## Requirements

- Docker Engine and Docker Compose v2.
- A Linux home server, preferably Ubuntu or Debian.
- VPN access strongly recommended before exposing any service.
- Optional: Tailscale, WireGuard, Cockpit, SSH, Guacamole, Portainer.

## Quick Start

1. Copy the environment template and change every placeholder secret:

   ```sh
   cp .env.example .env
   ```

2. Start the dashboard stack:

   ```sh
   make up
   ```

3. Open the dashboard:

   ```text
   http://server-ip:8080
   ```

4. Sign in with `DASHBOARD_ADMIN_USERNAME` and `DASHBOARD_ADMIN_PASSWORD` from `.env`.

## First-Time Setup

Copy the example config files if you want to customize them:

```sh
cp config/settings.example.yml config/settings.yml
cp config/services.example.yml config/services.yml
cp config/actions.example.yml config/actions.yml
```

Then edit the copied files for your server name, links, allowed Docker containers, visible services, and allowlisted actions.

The dashboard also has a Settings page for the display name, external links, and allowed container list. Service and script/action definitions stay file-based by design.

## VPN Recommended Setup

Use a private network first. With Tailscale, install it on the server and your daily driver, then access the panel through the server's Tailscale IP or MagicDNS name:

```text
http://server-tailnet-name:8080
```

Do not expose this stack directly to the public internet without HTTPS, hardened authentication, IP restrictions, and a clear reason.

## Access URLs

Defaults are configurable in `.env` and `config/settings.yml`.

- Dashboard: `http://server-ip:8080`
- Portainer: `https://server-ip:9443`
- Guacamole: `http://server-ip:8081/guacamole/`
- Cockpit: `https://server-ip:9090`

Portainer and Guacamole are bound to `127.0.0.1` by default in `.env.example`. Their ports are controlled by `PORTAINER_HTTPS_PORT` and `GUACAMOLE_HTTP_PORT`. For VPN access from another machine, set their bind addresses to the server's VPN interface IP or `0.0.0.0` only on a trusted private network.

## Portainer

Portainer is included in `docker-compose.yml` and stores data in the `portainer-data` named volume. It uses the host Docker socket, so treat it as a highly privileged admin tool.

Open:

```text
https://server-ip:9443
```

Create the first admin user immediately and use a strong password.

## Guacamole

Guacamole is included behind the `remote` Compose profile because PostgreSQL must be initialized before first use.

Generate the initial schema:

```sh
mkdir -p data/guacamole
docker run --rm guacamole/guacamole:1.5.5 /opt/guacamole/bin/initdb.sh --postgresql > data/guacamole/initdb.sql
```

Start the database once so it imports the schema:

```sh
docker compose --profile remote up -d guacamole-db
```

Then start the remote access stack:

```sh
docker compose --profile remote up -d guacd guacamole
```

Open:

```text
http://server-ip:8081/guacamole/
```

Change all default Guacamole credentials immediately after first login.

## Cockpit On Host

Cockpit usually belongs on the host OS because it manages the host directly.

For Ubuntu/Debian:

```sh
sudo ./scripts/install-cockpit-ubuntu.sh
```

Then open:

```text
https://server-ip:9090
```

Use Cockpit only through VPN or a secure reverse proxy.

## Adding Services

Edit `config/services.yml`:

```yaml
services:
  - id: ssh
    name: SSH
    kind: tcp
    host: host.docker.internal
    port: 22
```

Supported service checks:

- `docker_api`
- `docker_container`
- `tcp`
- `http`

## Adding Actions

Edit `config/actions.yml`. Actions are allowlisted and never built from user input.

Supported action types:

- `script`: runs a predefined command array with `shell=False`.
- `docker_restart`: restarts a fixed list of allowed container names through the Docker API.

Example:

```yaml
actions:
  - id: restart_portainer
    name: Restart Portainer
    type: docker_restart
    containers:
      - scp-portainer
    requires_confirmation: true
    enabled: true
```

Avoid mounting writeable host paths or adding broad host commands unless you understand the risk.

## Security Notes

- VPN-only access is the first target.
- Change every value in `.env` before running this on a real server.
- Keep `DASHBOARD_SECRET_KEY` long and random.
- Use HTTPS and set `DASHBOARD_COOKIE_SECURE=true` when the dashboard is served over HTTPS.
- Do not expose Docker, Portainer, Guacamole, Cockpit, or this dashboard directly to the public internet without proper access control.
- The backend mounts `/var/run/docker.sock` so it can inspect and control allowlisted containers. This is powerful. Keep the backend private and locked down.
- The frontend never receives Docker socket access.
- There is no arbitrary shell command box. Script actions must be defined in config first.

## Make Commands

Run:

```sh
make help
```

Common commands:

- `make up`
- `make down`
- `make restart`
- `make build`
- `make logs`
- `make ps`
- `make backend-shell`
- `make frontend-shell`
- `make db-shell`
- `make backup`
- `make restore`
