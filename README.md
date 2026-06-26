# server-control-panel

A self-hosted browser remote control portal for a powerful home server.

The primary feature is browser-based remote desktop access: open one web URL from your daily driver, log in, click **Remote Desktop**, and control the server GUI visually through Apache Guacamole.

This project **does provide browser-based remote desktop access** by integrating existing remote desktop tools. It **does not** attempt to build a custom low-level streaming/video protocol from scratch.

The dashboard/status features are secondary helpers around the remote desktop workflow.

## Primary Goal

1. Open the dashboard from your daily driver browser.
2. Log in.
3. Click **Remote Desktop**.
4. Open Guacamole.
5. Control the server GUI through RDP or VNC.

Recommended MVP path:

- Guacamole, guacd, and PostgreSQL run in Docker Compose.
- xrdp + XFCE run directly on the host.
- Guacamole connects to the host through RDP on TCP `3389`.

## Requirements

- Docker Engine and Docker Compose v2.
- Ubuntu/Debian host recommended.
- A VPN such as Tailscale or WireGuard.
- A host-side remote desktop service, preferably xrdp + XFCE for the MVP.

## Ports

- Dashboard: `8080`
- Guacamole direct fallback: `8081`
- Guacamole same-origin route: `/guacamole/`
- Host RDP service: `3389`
- Host VNC service: `5900`
- Portainer: `9443`
- Cockpit: `9090`

## Security Warning

This is a private homelab control plane. Use it over VPN first.

Do not expose the dashboard, Guacamole, Portainer, Cockpit, RDP, VNC, or Docker access directly to the public internet without HTTPS, strong authentication, IP restrictions, and a clear access-control design.

Before real use:

- Copy `.env.example` to `.env`.
- Replace every placeholder password and secret.
- Keep `DASHBOARD_SECRET_KEY` long and random.
- Change the Guacamole admin password immediately after first login.
- Use HTTPS and set `DASHBOARD_COOKIE_SECURE=true` when served over HTTPS.
- Keep RDP/VNC reachable only from the Docker host, LAN, or VPN scope.

## Quick Start

1. Create the local environment file:

   ```sh
   cp .env.example .env
   ```

2. Edit `.env` and replace every placeholder.

3. Start the dashboard stack:

   ```sh
   make up
   ```

4. Install host-side RDP + desktop environment:

   ```sh
   sudo ./scripts/install-xrdp-xfce-ubuntu.sh
   ```

5. Start Guacamole:

   ```sh
   make remote-up
   ```

6. Open the dashboard:

   ```text
   http://server-ip:8080
   ```

7. Log in and open **Remote Desktop**.

## How Guacamole Works Here

Guacamole is the browser remote desktop gateway. The browser talks to Guacamole over HTTP. Guacamole talks to `guacd`. `guacd` talks to the host remote desktop service using RDP or VNC.

Default MVP connection:

```text
Browser -> Dashboard /guacamole/ -> guacamole -> guacd -> host.docker.internal:3389 -> xrdp -> XFCE desktop
```

The `remote` Compose profile contains:

- `guacamole`
- `guacd`
- `guacamole-db` / PostgreSQL

Run:

```sh
make remote-up
```

This runs `make guacamole-init` first if needed, then starts the Guacamole services.

Open Guacamole through the dashboard route:

```text
http://server-ip:8080/guacamole/
```

Direct fallback, depending on bind settings:

```text
http://server-ip:8081/guacamole/
```

## Install xrdp + XFCE On The Host

For Ubuntu/Debian:

```sh
sudo ./scripts/install-xrdp-xfce-ubuntu.sh
```

This installs:

- `xrdp`
- `xfce4`
- `xfce4-goodies`
- `dbus-x11`

It enables `xrdp` and configures new users to start XFCE sessions.

Create or choose a Linux user with a strong password for the remote desktop session. Guacamole will use that Linux username/password when connecting over RDP.

For an existing Linux user, create `~/.xsession` containing:

```sh
startxfce4
```

Check host readiness:

```sh
./scripts/check-remote-desktop.sh
```

Expected MVP result:

- xrdp installed
- xrdp active
- TCP `3389` listening
- Guacamole containers running after `make remote-up`

## Create The Guacamole RDP Connection

After `make remote-up`, open:

```text
http://server-ip:8080/guacamole/
```

Then create a connection:

- Protocol: `RDP`
- Hostname: `host.docker.internal`
- Port: `3389`
- Username: your host Linux username
- Password: that user's host password
- Security mode: `Any` or `NLA`, depending on your xrdp setup
- Ignore server certificate: enabled for a private lab with self-signed xrdp certs

Save the connection and test it from Guacamole.

If `host.docker.internal` does not work on your system, use the host's LAN IP or Tailscale/WireGuard IP instead.

## VNC Alternative

VNC is useful when you want to control an existing physical desktop session.

Common VNC path:

```text
Browser -> Guacamole -> guacd -> host:5900 -> VNC server
```

Wayland and X11 matter here. Tools such as `x11vnc`, `wayvnc`, noVNC, or KasmVNC can be added later, but xrdp + XFCE is the recommended MVP.

## Dashboard Role

The dashboard is a helper UI around remote desktop access.

Priority order:

1. Remote Desktop
2. Service status
3. Links to Guacamole, Portainer, and Cockpit
4. Docker container status
5. Safe allowlisted actions

It is not meant to replace SSH for command-line work. There is no arbitrary command text box.

## Portainer

Portainer is included and stores data in the `portainer-data` volume. It uses the Docker socket, so treat it as highly privileged.

Open:

```text
https://server-ip:9443
```

Create the first admin user immediately and use a strong password.

## Cockpit On Host

Cockpit belongs on the host OS because it manages the host directly.

For Ubuntu/Debian:

```sh
sudo ./scripts/install-cockpit-ubuntu.sh
```

Open:

```text
https://server-ip:9090
```

Use Cockpit only through VPN or a secure reverse proxy.

## Configuration

Copy examples if you want local overrides:

```sh
cp config/settings.example.yml config/settings.yml
cp config/services.example.yml config/services.yml
cp config/actions.example.yml config/actions.yml
```

Remote desktop status checks are defined in `config/services.example.yml`:

- `guacamole`
- `guacd`
- `guacamole-db`
- `host-rdp`
- `host-vnc`

Dashboard links and allowlisted Docker containers are defined in `config/settings.example.yml`.

## Make Commands

```sh
make help
```

Required commands:

- `make up` starts the main dashboard stack.
- `make down` stops the default stack.
- `make restart` restarts the default stack.
- `make build` rebuilds images.
- `make logs` follows logs.
- `make ps` shows container status.
- `make remote-up` starts Guacamole, guacd, and PostgreSQL.
- `make remote-down` stops the Guacamole remote desktop stack.
- `make guacamole-init` generates the Guacamole PostgreSQL init schema.
- `make backup` archives config and local data.
- `make restore` prints the manual restore flow.

Developer helpers:

- `make backend-shell`
- `make frontend-shell`
- `make db-shell`
- `make clean`

## Backups

Run:

```sh
make backup
```

Backups include config, local data, `.env` if present, and core project files. Restore is intentionally manual to avoid destructive surprises.
