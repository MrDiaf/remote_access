# Milestone 06 — Experimental low-latency stream (Sunshine + Moonlight-Web)

## Objective

Try a browser remote desktop that holds up better than Guacamole → GNOME
Remote Desktop (RDP) on the physical GNOME Wayland screen. Keep the RDP path
working next to it so the two can be compared.

This is an experiment on the `exp` branch. It does not replace the default
remote desktop path until the user has compared both.

## Evidence that motivated it (2026-10-09, this server)

- `journalctl --user -u gnome-remote-desktop` over 72 h: 46 × "Network or
  intentional disconnect, stopping session", several
  `ERRCONNECT_CONNECT_TRANSPORT_FAILED` transport timeouts, and audio failing
  on every session ("Client protocol version (6) is too old").
- 9 × "Credentials are not set, denying client": after automatic login the
  GNOME keyring is locked, so GNOME Remote Desktop cannot read its RDP
  password.
- guacd: 15 × "Internal RDP client disconnected", 3 × "Server refused
  connection (wrong security type?)".

## Choice

| Candidate | Physical GNOME Wayland screen | Notes |
| --- | --- | --- |
| Guacamole + GNOME RDP (current) | yes | Disconnects, no audio, keyring problem after reboot |
| **Sunshine + Moonlight-Web** | yes (KMS or portal capture) | NVENC on the RTX 3060, Opus audio, uinput input, WebRTC; Moonlight-Web has its own login |
| Selkies 2.0 | no (own X11 or headless Wayland session) | Better for a separate session |
| KasmVNC, Neko | no (own virtual session) | Separate-session tools |
| linckosz/moonlight-web | yes (own capture) | Young (0.2.x), telemetry on by default |

Picked: [Sunshine](https://github.com/LizardByte/Sunshine) v2026.914.233613
(official Ubuntu 26.04 `.deb`, which sets `cap_sys_admin` for KMS capture)
on the host, plus [moonlight-web-stream](https://github.com/MrCreativ3001/moonlight-web-stream)
v2.10.0 (latest stable; v3 is a prerelease) in Docker.

## Scope

- `scripts/install-sunshine-ubuntu.sh` (run by the user with sudo), `make install-sunshine`
- `docker-compose.yml`: `moonlight-web` service in a `stream` profile, `/stream`
  route in Caddy, WebRTC UDP 40000–40010 bound to `DASHBOARD_BIND`
- Makefile: `make stream-up`, `make stream-down`; `make down` also stops it
- Dashboard Remote Desktop page and TUI Remote tab: a link to the stream
- `make doctor`: Sunshine checks
- README, handoff, `.env.example`

Out of scope: replacing Guacamole, a custom streaming protocol, internet
exposure, and HTTPS (Keyboard Lock and gamepads need it; a later step).

## Completion criteria

- [x] `moonlight-web` serves its UI at `/stream/` through Caddy
- [x] `make install-sunshine` installs the pinned Sunshine release and starts its user service
- [ ] Moonlight-Web pairs with Sunshine on `host.docker.internal`
- [ ] The physical GNOME screen streams in a desktop browser with keyboard, mouse and audio
- [ ] The stream works from a phone
- [ ] User compares stability against Guacamole and decides whether to keep it

## Verification

- Release checks: Sunshine v2026.914.233613 is the latest stable (2026-09-15).
  The Ubuntu 26.04 `.deb` checksum matches the GitHub release digest. Its
  `postinst` sets `cap_sys_admin,cap_sys_nice+p` on `/usr/bin/sunshine` (KMS
  capture), installs udev rules, and ships the user unit
  `app-dev.lizardbyte.app.Sunshine.service`. Moonlight-Web v2.10.0 is the
  latest stable tag; data lives in `/moonlight-web/server`.
- Host: `/dev/uinput` already has an ACL for the user (Steam's udev rules),
  `xdg-desktop-portal-gnome` 50 is installed, and the GPU is an RTX 3060 with
  driver 595.
- Isolated network with the real Caddyfile and the pinned image on port
  18080: `/stream` → 308 to `/stream/`; the page, CSS, JS and icon return 200;
  the login page renders; the first login created the admin role (container
  log "Added admin role").
- `docker compose config`, frontend build, and `make test` (backend 14 OK,
  TUI 13 OK).
- 2026-10-09 install on the real server: the user ran the script with sudo,
  and the package installed (`getcap` shows `cap_sys_admin,cap_sys_nice=p`).
  Two bugs were fixed along the way:
  1. The script sourced `/etc/os-release`, whose `VERSION` overwrote the
     pinned version and broke the URL. Now `SUNSHINE_VERSION`; a dry run with
     shims checked the URL and checksum.
  2. `systemctl --user` failed when `make` ran without the session
     environment. The target now refuses root and falls back to
     `XDG_RUNTIME_DIR=/run/user/<uid>`.
- Startup hang: with the default `capture`, Sunshine probed the GNOME
  RemoteDesktop portal and waited for the on-screen "Allow" dialog, so it
  never opened its ports. With `capture = kms` and `encoder = nvenc` it
  starts in about 1 s: "Screencasting with KMS", connector HDMI-1, found
  `h264_nvenc` and `hevc_nvenc`, and listening on 47984, 47989, 47990 and
  48010. `make install-sunshine` now writes that config when no `capture` is
  set.
- Pairing with Sunshine over `host.docker.internal` worked (user, PIN flow).
- First stream test, 2026-10-09: "the delay is atrocious". Logs showed:
  - The WebRTC sessions failed ICE ("pingAllCandidates called with no
    candidate pairs", then "ICE connection state changed: failed").
  - Moonlight-Web then used the WebSocket transport. Over plain HTTP that
    means the slow playback path.
  - The browser connected from Tailscale (`x-forwarded-for: 100.67.52.40`),
    but the relay advertised only `WEBRTC_NAT_1TO1_HOST=192.168.0.170`, which
    is unreachable from Tailscale.
  - The env var accepts one IP only ("invalid IP address syntax" for a list).
  - The Tailscale path to the laptop is direct, 25 ms round trip.
- Fix: `moonlight-web` now uses `network_mode: host`, so WebRTC gathers
  candidates on every host interface. Other changes:
  - The web UI binds to the Docker bridge gateway (`172.17.0.1:8091`), and
    Caddy proxies `/stream` to `host.docker.internal:8091`.
  - The NAT 1:1 setting and the published UDP ports are gone. The persisted
    `nat_1to1` in the volume's `config.json` was reset to `null`.
  - Verified: `/stream/` 200 through Caddy, effective config `nat_1to1: null`,
    `network_types: [udp4]`, `bind_address: 172.17.0.1:8091`.
- Not done yet: a WebRTC stream test from the laptop after the fix.

## Notes

- `first_login_create_admin` is on in Moonlight-Web. Whoever logs in first
  becomes admin, so the user should log in right after `make stream-up`.
- Without HTTPS, Keyboard Lock and gamepads are unavailable in the browser.
