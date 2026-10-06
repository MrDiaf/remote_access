# server-control-panel

A private, browser-based control panel for an Ubuntu home server.

Open one URL from any computer, tablet, or phone on your LAN or VPN and you get:

- **Remote Desktop**: control the server's real, logged-in GNOME screen in the
  browser (Apache Guacamole + GNOME Remote Desktop over RDP).
- **Terminal**: an SSH terminal to the server in the browser.
- **Status**: CPU, RAM, uptime, network, every drive's fill level, and a disk
  usage explorer that shows which folders take up the space.
- **Docker, Services, Actions**: container status, service checks, and a few
  allowlisted buttons.

Everything runs in Docker Compose on the server itself. Your daily computer only
needs a browser. Without a browser, `make tui` opens the same features in a
keyboard-driven terminal UI (see [Terminal UI](#terminal-ui)).

```text
Browser -> http://server-ip:8080 (dashboard, Caddy)
             |-- /guacamole/  -> Guacamole -> guacd -> host RDP :3389 -> GNOME desktop
             |-- /terminal/   -> ttyd -> ssh -> host sshd :22
             `-- /api/        -> FastAPI backend (status, disk usage, Docker)
```

## Security

This is a private LAN/Tailscale/WireGuard tool. Never forward its ports to the
public internet.

- The dashboard itself has **no login**. Anyone who can reach it on your
  private network can open it.
- The **Terminal** always asks for an SSH login (your Ubuntu username and
  password, or key) before you get a shell. It is exactly as safe as SSH on
  your LAN.
- Guacamole, Portainer, and Cockpit keep their own logins.
- The disk usage page can list the names and sizes of every folder on the
  server (not file contents). The backend sees the host filesystem read-only.

Keep these ports private: dashboard `8080`, Guacamole `8081`, SSH `22`,
RDP `3389`, VNC `5900`, Portainer `9443`, Cockpit `9090`.

## Prerequisites

On the Ubuntu server:

- Docker Engine with the Compose plugin, and your user in the `docker` group.
- `make` and `git`.
- An SSH server for the web terminal: `sudo apt install openssh-server`.
- For the physical-screen remote desktop: a GNOME desktop session and
  `gnome-remote-desktop` (installed by default on Ubuntu Desktop).

You do not need Node, npm, or Python on the host. Everything builds in Docker.

## First-Time Setup

Run these once, on the server, from the project folder.

1. Create `.env` with a random Guacamole database password:

   ```sh
   make setup
   ```

   `make setup` never overwrites an existing `.env`. Look through `.env` for
   the other settings (ports, drive folders, terminal SSH user).

2. Build and start everything:

   ```sh
   make up
   ```

   This starts the dashboard, the Guacamole stack, the terminal, and
   Portainer, waits until they are healthy, and prints the URLs.

3. Share the physical GNOME screen over RDP (run it in the logged-in desktop
   session, not over SSH):

   ```sh
   make enable-physical-screen
   ```

   It asks for a remote desktop username and password. You will enter them in
   Guacamole next.

4. Create the Guacamole connection once. See
   [Create The Physical Ubuntu Desktop Connection](#create-the-physical-ubuntu-desktop-connection).

5. Check everything:

   ```sh
   make doctor
   ```

6. Open `http://server-ip:8080` from another device.

## Everyday Use

```sh
make up       # start or update everything (safe to run again)
make down     # stop everything; data is kept
make status   # show containers
make doctor   # check boot autostart, terminal SSH, and remote desktop
make tui      # the dashboard as a terminal UI
make help     # all commands
```

After `git pull`, run `make up`. It rebuilds changed images and recreates only
what changed. If the browser still shows old code, run `make refresh` and
hard-refresh the page.

## After A Reboot

You normally do not need to run anything:

- Docker starts on boot, and every container has `restart: unless-stopped`, so
  the whole stack comes back by itself. (Containers you stopped with
  `make down` stay stopped until the next `make up`.)
- GNOME Remote Desktop shares the **logged-in** desktop. After a reboot, the
  physical screen is only available once someone is logged in to GNOME. To have
  it available without touching the server, enable automatic login in
  **Settings > System > Users** (or `AutomaticLoginEnable=true` in
  `/etc/gdm3/custom.conf`).
- The web terminal only needs `sshd`, which starts on boot by default.

Run `make doctor` once after setup, and again if something is missing after a
restart. It checks:

- Docker is enabled at boot.
- Every container is running and restarts after a reboot.
- `sshd` is listening and reachable from the terminal container.
- GNOME automatic login is enabled.
- `gnome-remote-desktop` is enabled.
- Guacamole can reach RDP on port 3389.

If `make doctor` warns that Docker is not enabled at boot:

```sh
sudo systemctl enable docker
```

## Terminal

Open **Terminal** in the dashboard (or `http://server-ip:8080/#terminal`).
Type your Ubuntu username, then your password. You get a normal SSH shell on
the server. **New session** starts a fresh login, and **Open in tab** gives
the terminal a full browser tab.

Settings in `.env`:

```env
TERMINAL_SSH_HOST=host.docker.internal   # the server itself
TERMINAL_SSH_PORT=22
TERMINAL_SSH_USER=                       # set to skip the username prompt
```

The terminal container (ttyd) has no shell of its own. It can only run `ssh`
to the host, so the host's SSH login is the gate. The host key is remembered in
the `terminal-ssh` Docker volume.

## Terminal UI

`make tui` opens the dashboard as a terminal UI. It's useful over SSH or at the
server's own console. Start the stack with `make up` first; the TUI talks to the
same backend API as the browser.

| Key | Does |
| --- | --- |
| `1`–`7` | Remote Desktop, Terminal, Services, Status, Docker, Actions, Settings |
| `r` | Refresh the current tab |
| arrows, `Enter` | Move in tables; open a folder, container, or action |
| `u` / `s` | Disk usage: up one folder / rescan |
| `y` / `n` | Confirm / cancel a dialog |
| `q` | Quit |

Every browser feature is there, with one exception: the **Remote Desktop**
tab can't show the desktop picture in a terminal. It shows the Guacamole and
RDP status, the keyboard settings, a button to apply the keyboard layout, and
the Guacamole URL to open in a browser. The **Terminal** tab pauses the TUI and
opens an SSH login to the host; type `exit` to return.

The TUI runs in a container, so the host needs no Python. It has no Docker
socket and no shell of its own.

## Disk Usage

On the **Status** page, the **Disk usage** panel lists every drive. Click a
drive to see its folders, largest first. Click a folder to go deeper, and use
the path or the up arrow to go back.

- Sizes are the disk space actually used (like `du`).
- A folder that is another mounted drive shows as **separate drive** with that
  drive's used space. Click it to scan that drive.
- Results are cached for 10 minutes. **Rescan** refreshes them.
- The first scan of a big drive can take a while (13 seconds for 70 GB on an
  SSD). Very large folders time out after 5 minutes. Open a smaller folder if
  that happens.

Extra drives are discovered below `/run/media` (removable) and `/mnt`
(persistent). Change `HOST_MEDIA_PATH` or `HOST_MOUNT_PATH` in `.env` if your
server mounts them elsewhere.

## Remote Desktop In Detail

Use **GNOME Remote Desktop over RDP** to control the actual logged-in Ubuntu
desktop. Use xrdp/XFCE only if you want a separate management session (see
[Separate xrdp/XFCE Session](#separate-xrdpxfce-session)).

### First Guacamole Login

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

### Create The Physical Ubuntu Desktop Connection

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

### Terminal Shows `Connection refused` Or Hangs

The host SSH server is not running or not reachable from Docker:

```sh
sudo apt install openssh-server
sudo systemctl enable --now ssh
make doctor
```

If a firewall (ufw) is active, allow SSH from the Docker bridge network as well
as your LAN.

### Terminal Says The Host Key Changed

This happens after reinstalling the server OS. Clear the remembered key:

```sh
make down
docker volume rm server-control-panel_terminal-ssh
make up
```

### Remote Desktop Is Missing After A Reboot

Check that someone is logged in to GNOME on the server, or that automatic login
is enabled (see [After A Reboot](#after-a-reboot)), then run `make doctor`. If
port 3389 is not listening after an automatic login, log in once at the
monitor. Automatic login does not unlock the GNOME keyring, and GNOME Remote
Desktop may keep its RDP credentials there.


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

`make help` prints the full list. The main ones:

| Command | What it does |
| --- | --- |
| `make setup` | First-time: create `.env` with a random DB password and the Guacamole schema |
| `make up` | Build and start everything, wait until healthy, print URLs |
| `make down` | Stop everything; keeps volumes and data |
| `make status` | Show container status |
| `make doctor` | Check boot autostart, terminal SSH, and the remote desktop path |
| `make logs` | Follow logs |
| `make tui` | Open the terminal UI |
| `make refresh` | Force-recreate dashboard containers after an update |
| `make enable-physical-screen` | Share the logged-in GNOME monitor over RDP |
| `make check-remote` | Check only the Guacamole-to-RDP path |
| `make apply-remote-input` | Reapply the saved remote keyboard layout to Guacamole |
| `make test` | Run backend and TUI tests in containers |
| `make backup` | Archive config, data, and `.env` into `backups/` |

`make shutdown` and `make maintenance-stop` are older names for `make down`.

## Development Without Host npm

Frontend production builds run inside Docker, in the frontend Dockerfile's
`node:22-alpine` build stage. Use `make up` or `make build` to rebuild. A
live-reload development container is not set up yet.

## Ports

Browser/client connects to:

- Dashboard: `http://server-ip:8080`
- Terminal through dashboard: `http://server-ip:8080/terminal/`
- Guacamole through dashboard: `http://server-ip:8080/guacamole/`
- Guacamole direct: `http://127.0.0.1:8081/guacamole/` (localhost only by default)

The containers connect to the host at:

- `host.docker.internal:3389` (RDP, from guacd)
- `host.docker.internal:22` (SSH, from the terminal)

Optional:

- Portainer: `https://127.0.0.1:9443` (localhost only by default)
- Cockpit: `https://server-ip:9090`

## Project Planning And Agent Handoff

- [`PLAN.md`](PLAN.md) is the milestone status registry.
- Each file under [`guidelines/milestones/`](guidelines/milestones/) is one
  self-contained milestone.
- [`handoff.md`](handoff.md) is the current product and operational context.
- [`AGENTS.md`](AGENTS.md) and [`guidelines/`](guidelines/) define the agent
  workflow and project rules.
