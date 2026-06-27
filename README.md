# server-control-panel

A browser-based remote control portal for an Ubuntu home server PC.

The main point of this project is simple:

```text
Any computer / phone / tablet with a browser
  -> open the dashboard
  -> click Remote Desktop
  -> open Guacamole
  -> control the Ubuntu server desktop
```

You do **not** need Windows. In tutorial videos, Windows is often just the RDP client. Here, **Guacamole is the RDP client**, and your browser views Guacamole.

## What Runs Where

Run this project on the **Ubuntu server PC** you want to control.

Your daily computer only needs a browser.

```text
Daily computer browser
  -> http://server-ip:8080
  -> Guacamole web UI
  -> guacd container
  -> Ubuntu server's remote desktop service
  -> Ubuntu desktop screen/session
```

## Recommended Setup

If the server has a real GNOME desktop and monitor, use:

```text
GNOME Remote Desktop over RDP
```

This is the path for controlling the actual logged-in Ubuntu desktop session.

Use xrdp/XFCE only if you want a separate server-management desktop session.

## Security

This is a private LAN/Tailscale/WireGuard tool.

The custom dashboard has no login for the MVP. Anyone who can reach it on your private network can open it. Guacamole, Portainer, and Cockpit keep their own logins.

Do not expose these ports directly to the public internet:

- Dashboard `8080`
- Guacamole `8081`
- RDP `3389`
- VNC `5900`
- Portainer `9443`
- Cockpit `9090`

## Fresh Setup After Git Pull

Run these commands on the Ubuntu server PC.

1. Go to the project:

   ```sh
   cd /path/to/remote_access
   ```

2. Create `.env` if it does not exist:

   ```sh
   cp .env.example .env
   ```

3. Edit `.env` and change at least:

   ```env
   POSTGRES_PASSWORD=replace-with-a-strong-guacamole-db-password
   GUACAMOLE_VERSION=1.6.0
   ```

4. Start the dashboard:

   ```sh
   make up
   ```

5. Start Guacamole:

   ```sh
   make remote-up
   ```

6. Enable sharing of the physical GNOME screen:

   ```sh
   make enable-physical-screen
   ```

   It asks for a remote desktop username and password. Remember them. You will enter them in Guacamole.

7. Check the whole remote desktop path:

   ```sh
   make check-remote
   ```

   You want to see:

   ```text
   ok: scp-guacamole is running
   ok: scp-guacd is running
   ok: scp-guacamole-db is running
   ok: host.docker.internal resolves inside guacd
   ok: host.docker.internal:3389 reachable from guacd container
   ok: host is listening on TCP 3389
   ```

8. Open the dashboard from another computer:

   ```text
   http://server-ip:8080
   ```

9. Click **Remote Desktop**.

## First Guacamole Login

Open:

```text
http://server-ip:8080/guacamole/
```

Default login is usually:

```text
username: guacadmin
password: guacadmin
```

Change that password immediately.

## Create The Physical Ubuntu Desktop Connection

In Guacamole:

1. Top-right `guacadmin`
2. `Settings`
3. `Connections`
4. `New Connection`

Use these values.

Top section:

```text
Name: Ubuntu Physical Desktop
Location: ROOT
Protocol: RDP
```

Guacamole Proxy Parameters (GUACD):

```text
Hostname: guacd
Port: 4822
Encryption: blank / none
```

Parameters -> Network:

```text
Hostname: host.docker.internal
Port: 3389
```

Parameters -> Authentication:

```text
Username: the username from make enable-physical-screen
Password: the password from make enable-physical-screen
Domain: blank
Security mode: Any
Disable authentication: unchecked
Ignore server certificate: checked
```

Parameters -> Input:

```text
Keyboard layout / server-layout: en-us-qwerty by default, or the Remote keyboard value from dashboard Settings
```

Changing the dashboard's Remote keyboard setting now applies that value to Guacamole's RDP `server-layout` parameter. Reconnect any open Guacamole session before testing keys again.

On phones and other touch devices, the embedded Remote Desktop page sets Guacamole's native browser preferences before loading the iframe:

```text
emulateAbsoluteMouse: false
inputMethod: text
```

This makes Guacamole use Touchpad mode by default, where dragging moves the remote pointer instead of clicking the exact point touched on the phone screen. Use the Touchpad/Touchscreen button on the Remote Desktop page to switch modes; the embedded Guacamole frame reloads after the change.

Mobile browsers need a local input field before they will show the phone keyboard. After placing the remote cursor in a text field, tap the Keyboard button overlaid on the remote frame. The dashboard opens a local phone-keyboard input and forwards typed text/backspace into Guacamole's native text input field.

If the dashboard still shows old code after `git pull`, run:

```sh
make refresh
```

If Guacamole connects and immediately drops with a security-type error, try:

```text
Security mode: TLS
```

Remote Desktop Gateway:

```text
leave everything blank
```

Save it.

Go back to Guacamole Home and click:

```text
Ubuntu Physical Desktop
```

That should open the Ubuntu server desktop in the browser.

## If You Already Had The Stack Running Before Git Pull

After pulling new changes, run:

```sh
git pull
make up
make remote-up
docker compose pull guacd guacamole
docker compose --profile remote up -d --force-recreate guacd guacamole
make check-remote
```

The force-recreate step matters if `guacd` was already running before the Docker Compose host mapping or Guacamole version was changed.

## Troubleshooting

### Guacamole Says Disconnected Immediately

Run on the server:

```sh
docker logs --tail=80 scp-guacd
```

If you see:

```text
DNS lookup failed (incorrect hostname?)
```

then `guacd` cannot resolve `host.docker.internal`.

Fix:

```sh
git pull
docker compose --profile remote up -d --force-recreate guacd
make check-remote
```

You need:

```text
ok: host.docker.internal resolves inside guacd
ok: host.docker.internal:3389 reachable from guacd container
```

If you see this in `journalctl --user -u gnome-remote-desktop`:

```text
Client did not advertise support for the Graphics Pipeline
```

then `guacd` is too old for GNOME's physical-screen RDP server.
Use Guacamole/guacd `1.6.0` or newer, then recreate the containers:

```sh
git pull
docker compose pull guacd guacamole
docker compose --profile remote up -d --force-recreate guacd guacamole
make check-remote
```

You want `make check-remote` to show:

```text
info: scp-guacd image is guacamole/guacd:1.6.0
ok: host.docker.internal:3389 reachable from guacd container
ok: host is listening on TCP 3389
```

### `make check-remote` Says RDP Is Not Reachable

Run:

```sh
make enable-physical-screen
make check-remote
```

Also make sure the Ubuntu server is logged into GNOME on the physical screen.

### Guacamole Logs Mention VNC

You created the wrong type of connection.

For this setup, use:

```text
Protocol: RDP
```

Do not use VNC unless you intentionally set up a VNC server.

### Wrong Username Or Password

The Guacamole connection username/password must match what you entered when running:

```sh
make enable-physical-screen
```

It does not have to be your Ubuntu login username unless you chose the same one.

## Separate xrdp/XFCE Session

If you want a separate desktop session instead of the physical monitor session:

```sh
make install-host-remote-desktop
make check-remote
```

Then create an RDP connection in Guacamole to:

```text
Hostname: host.docker.internal
Port: 3389
Username: your Ubuntu Linux username
Password: your Ubuntu Linux password
```

xrdp/XFCE is useful for headless management, but it usually does not show the exact physical monitor session.

## Make Commands

Main commands:

- `make up` starts the dashboard stack.
- `make remote-up` starts Guacamole, guacd, and PostgreSQL.
- `make refresh` rebuilds/recreates the dashboard, starts the remote stack, and reapplies the saved remote keyboard setting to Guacamole.
- `make shutdown` gracefully stops the dashboard and Guacamole stacks for maintenance or updates.
- `make enable-physical-screen` enables GNOME physical monitor sharing over RDP.
- `make check-remote` checks the Guacamole-to-RDP path.
- `make down` stops the default stack.
- `make remote-down` stops the Guacamole stack.
- `make apply-remote-input` reapplies the saved remote keyboard setting to Guacamole RDP connections.

Other commands:

- `make build`
- `make restart`
- `make logs`
- `make ps`
- `make guacamole-init`
- `make install-host-remote-desktop`
- `make backup`
- `make restore`

## Development Without Host npm

Frontend production builds already run inside Docker using the frontend Dockerfile's `node:22-alpine` build stage. You do not need Node/npm installed on the host for normal rebuilds; use `make build`, `make refresh`, or `docker compose build frontend`.

A dedicated Docker-based dev workflow is still a TODO. Future development should add `docker-compose.dev.yaml` plus Make wrappers such as `make dev` or `make frontend-dev-shell`, instead of requiring host npm.

## Ports

Browser/client connects to:

- Dashboard: `http://server-ip:8080`
- Guacamole direct: `http://server-ip:8081/guacamole/`
- Guacamole through dashboard: `http://server-ip:8080/guacamole/`

Guacamole connects internally to:

- `host.docker.internal:3389`

Optional:

- Portainer: `https://server-ip:9443`
- Cockpit: `https://server-ip:9090`
- VNC alternative: `5900`
