# server-control-panel

A browser-based remote control portal for a home server PC.

The main feature is browser-based remote desktop access to the server GUI, using Guacamole as the web gateway and xrdp/XFCE or VNC on the host. SSH already handles terminal control; this project is for visually controlling the server desktop from another computer with only a browser.

The dashboard is intentionally a thin LAN/Tailscale/VPN portal. It does not require its own login for the MVP. Guacamole, Portainer, and Cockpit keep their own logins.

## First Working Path

The MVP path is:

```text
Browser -> Dashboard :8080 -> Remote Desktop -> Guacamole -> guacd -> host.docker.internal:3389 -> xrdp -> XFCE
```

Result: you can open the dashboard, click **Remote Desktop**, and control a Linux GUI session in the browser.

xrdp usually gives a separate desktop session. That is good for server management. If you want to control the exact physical monitor session later, add a VNC/x11vnc/wayvnc option on port `5900`.

## Security Model

Use LAN, Tailscale, WireGuard, or another VPN first.

The custom dashboard has no login by default. Anyone who can reach it on your private network can open the dashboard and click the Guacamole entry point. Do not expose the dashboard, Guacamole, Portainer, Cockpit, RDP, VNC, or Docker access directly to the public internet.

Before real use:

- Change every placeholder in `.env`.
- Change the Guacamole default admin password immediately.
- Use strong host Linux passwords for RDP.
- Keep RDP `3389` and VNC `5900` private to host/LAN/VPN scope.
- Use HTTPS and stronger access controls before any public exposure.

## Ports

Browser/client connects to:

- Dashboard: `http://server-ip:8080`
- Guacamole direct: `http://server-ip:8081/guacamole/`
- Guacamole through dashboard proxy: `http://server-ip:8080/guacamole/`

Guacamole connects internally to:

- RDP on host: `host.docker.internal:3389`

Optional tools:

- Portainer: `https://server-ip:9443`
- Cockpit: `https://server-ip:9090`
- VNC alternative: `5900`

## Quick Start

1. Create and edit the environment file:

   ```sh
   cp .env.example .env
   ```

2. Start the dashboard stack:

   ```sh
   make up
   ```

3. Install the host remote desktop service:

   ```sh
   make install-host-remote-desktop
   ```

4. Start Guacamole:

   ```sh
   make remote-up
   ```

5. Check the remote desktop path:

   ```sh
   make check-remote
   ```

6. Open:

   ```text
   http://server-ip:8080
   ```

7. Click **Remote Desktop**.

## First-Time Guacamole Setup

`make remote-up` runs `make guacamole-init` first if needed. That creates `data/guacamole/initdb.sql`, starts PostgreSQL, starts `guacd`, then starts Guacamole.

Open Guacamole:

```text
http://server-ip:8080/guacamole/
```

or:

```text
http://server-ip:8081/guacamole/
```

Initial Guacamole login is typically:

```text
username: guacadmin
password: guacadmin
```

Change that password immediately.

## Create The RDP Connection

Inside Guacamole, create a new connection:

- Name: `Home Server Desktop`
- Protocol: `RDP`
- Hostname: `host.docker.internal`
- Port: `3389`
- Username: your Linux host username
- Password: your Linux host password
- Security mode: `Any` or `NLA`
- Ignore server certificate: enabled for a private lab with self-signed xrdp certificates

Save it, then launch the connection. You should see the XFCE desktop session in the browser.

If `host.docker.internal` does not work on your Linux Docker setup, use the host LAN IP or Tailscale IP.

## Host xrdp/XFCE Install

The host-side installer is:

```sh
scripts/install-xrdp-xfce-ubuntu.sh
```

The Make target is:

```sh
make install-host-remote-desktop
```

It installs:

- `xfce4`
- `xfce4-goodies`
- `xrdp`
- `xorgxrdp`
- `dbus-x11`

It enables and starts xrdp. RDP listens on TCP `3389`.

For existing users, make sure `~/.xsession` contains:

```sh
startxfce4
```

## Remote Desktop Status API

The backend exposes:

```text
GET /api/remote/status
```

It reports:

- Guacamole container status
- guacd container status
- PostgreSQL container status
- configured Guacamole URL
- configured RDP host and port
- whether the RDP target is reachable from the backend/container network

The frontend Remote Desktop page uses this endpoint.

## Make Commands

Required workflow:

- `make up` starts dashboard, backend, proxy, and Portainer.
- `make remote-up` starts Guacamole, guacd, and PostgreSQL.
- `make check-remote` checks the remote desktop path.
- `make install-host-remote-desktop` installs xrdp + XFCE on Ubuntu/Debian.

Other commands:

- `make down`
- `make restart`
- `make logs`
- `make ps`
- `make remote-down`
- `make guacamole-init`
- `make build`
- `make backup`
- `make restore`

## Configuration

Dashboard and remote desktop defaults live in:

```text
config/settings.example.yml
```

Important defaults:

```yaml
remote_desktop:
  protocol: RDP
  guacamole_url: /guacamole/
  rdp_host: host.docker.internal
  rdp_port: 3389
```

Copy the examples if you want local overrides:

```sh
cp config/settings.example.yml config/settings.yml
cp config/services.example.yml config/services.yml
cp config/actions.example.yml config/actions.yml
```

## Optional Tools

Portainer is included for Docker management:

```text
https://server-ip:9443
```

Cockpit should be installed on the host:

```sh
sudo ./scripts/install-cockpit-ubuntu.sh
```

Then open:

```text
https://server-ip:9090
```

Keep both private to LAN/VPN.

