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

On the server, in the project folder, from a terminal in the logged-in desktop
(or over SSH while someone is logged in to the desktop):

```sh
make up
```

That is the whole setup. `make up`:

1. creates `.env` with a random Guacamole database password if it is missing
   (it never overwrites it);
2. builds and starts every container and waits until they are healthy;
3. goes through the host setup and asks about each step that is not done yet:

   | Step | What you type |
   | --- | --- |
   | Start Docker on boot | your sudo password |
   | Install the SSH server (Terminal page) | your sudo password |
   | Share this desktop's screen over RDP | a new remote desktop username and password |
   | Create the Guacamole connection to it | nothing new; it reuses that login |
   | Change Guacamole's default `guacadmin` password | a new password, twice |
   | Let the dashboard start and quit Steam (only if Steam is installed) | nothing |

4. prints the URLs.

Steps that are already done print `ok` and ask nothing, so `make up` stays
safe to repeat. Answer `n` to skip a step; `make up` remembers that, and
`make setup-host` asks about every step again. Without a terminal (for example
`ssh server make up`), nothing is asked and the missing steps are listed as
`todo`.

Then open `http://server-ip:8080` from another device, and run `make doctor`
for a full check. Look through `.env` for the other settings (ports, drive
folders, terminal SSH user).

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

## Steam

Play the server's games on your phone, TV, or another PC with Steam Remote
Play. The **Actions** page has a Steam card that shows whether Steam is
running and lets you start it, start it in **Big Picture** (best for a
controller or TV), or quit it. In the TUI, press `s` (start/quit) or `b` (Big
Picture) on the Actions tab.

Open **Play on your phone, TV, or another PC** under the card for the pairing
steps. In short: sign in to Steam on the server once through the remote
desktop; install the Steam Link app on the phone or TV and sign in with the
same account; then type the app's 4-digit PIN into Steam on the server. Away
from home, Steam connects through its own servers, so no ports are opened.

If the stream shows a black screen, start the game directly instead of
streaming the desktop or Big Picture. Steam's Remote Play is unreliable on
GNOME Wayland desktops. If streaming at home is slow and `ufw` is on, allow
UDP 27031–27036 and TCP 27036–27037 from your home network. When
Steam is installed, `make up` offers to set this up (or run
`make enable-steam-control` yourself, as the user who logs in to the desktop).

This gives the backend its own SSH key, and `~/.ssh/authorized_keys` limits
that key to one script that accepts only `status`, `start`, and `stop`. Steam
opens on the logged-in desktop, so someone must be logged in. Quitting asks
for confirmation and closes Steam cleanly; it never force-kills a running game.
To revoke access, delete the line ending in `scp-steam-control` from
`~/.ssh/authorized_keys`.

## Low-Latency Stream (Experimental)

An alternative to Guacamole for the physical screen. [Sunshine](https://github.com/LizardByte/Sunshine)
runs on the server, captures the real GNOME screen (KMS), and encodes it on
the GPU. [Moonlight-Web](https://github.com/MrCreativ3001/moonlight-web-stream)
sends it to the browser over WebRTC, with audio. Guacamole keeps working next
to it, so you can compare the two.

Set it up once:

```sh
make install-sunshine   # installs the pinned official package (sudo) and starts it
```

1. On the server, open `https://localhost:47990` (accept the self-signed
   certificate) and create the Sunshine admin login.
2. Run `make stream-up` and open `http://server-ip:8080/stream/`. **The first
   login there creates the Moonlight-Web admin account**, so do it right away.
3. Add a host with address `host.docker.internal`, click it to pair, and
   enter the PIN it shows in Sunshine's web UI (**PIN** tab).
4. Click the host, then **Desktop**.

The dashboard's Remote Desktop page links to it as **Low-latency stream
(beta)**. `make doctor` checks Sunshine, and `make stream-down` stops the
relay.

Limits of the experiment:

- Plain HTTP only, so browsers block Keyboard Lock (Super/Alt-Tab capture)
  and gamepads. These need HTTPS, which is a later step.
- Media goes over UDP 40000–40010 directly to the server's LAN or Tailscale
  address. Moonlight-Web uses host networking so it can offer both. If WebRTC
  cannot connect, it falls back to WebSockets, which is much slower over
  plain HTTP.
- Remove it with `make stream-down` and `sudo apt remove sunshine`.

## Remote Desktop In Detail

Use **GNOME Remote Desktop over RDP** to control the actual logged-in Ubuntu
desktop. Use xrdp/XFCE only if you want a separate management session (see
[Separate xrdp/XFCE Session](#separate-xrdpxfce-session)).

### First Guacamole Login

Open:

```text
http://server-ip:8080/guacamole/
```

Log in as `guacadmin` with the password you chose during `make up`. If you
skipped that step, the password is still `guacadmin`; run `make setup-host`
to change it.

### Create The Physical Ubuntu Desktop Connection

`make up` creates this connection for you ("Ubuntu Physical Desktop") as soon
as Guacamole has no RDP connection. Do it by hand only to add or change one.

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
| `make setup` | Only create `.env` and the Guacamole schema (`make up` does this too) |
| `make up` | Set up and start everything; asks about any host step still missing |
| `make setup-host` | Ask again about every host step, including skipped ones |
| `make down` | Stop everything; keeps volumes and data |
| `make status` | Show container status |
| `make doctor` | Check boot autostart, terminal SSH, and the remote desktop path |
| `make logs` | Follow logs |
| `make tui` | Open the terminal UI |
| `make refresh` | Force-recreate dashboard containers after an update |
| `make enable-physical-screen` | Share the logged-in GNOME monitor over RDP |
| `make enable-steam-control` | Let the dashboard start and quit Steam (Actions page) |
| `make check-remote` | Check only the Guacamole-to-RDP path |
| `make apply-remote-input` | Reapply the saved remote keyboard layout to Guacamole |
| `make test` | Run backend and TUI tests in containers |
| `make install-sunshine` | Experimental: install and start Sunshine on the host (sudo) |
| `make stream-up` / `make stream-down` | Experimental: start/stop Moonlight-Web at `/stream/` |
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
