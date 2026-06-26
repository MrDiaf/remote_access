# Host Setup Notes

Use the dashboard over a private network first. Tailscale is the simplest starting point for many homelabs:

```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

## Remote Desktop MVP

The recommended first remote desktop setup is GNOME Remote Desktop on the host, with Guacamole in Docker connecting over RDP. This shares the physical logged-in GNOME screen.

Install on Ubuntu/Debian:

```sh
./scripts/enable-gnome-physical-rdp.sh
```

Check it:

```sh
./scripts/check-remote-desktop.sh
```

Guacamole RDP connection defaults:

- Protocol: RDP
- Hostname: `host.docker.internal`
- Port: `3389`
- Username/password: the credentials entered in `enable-gnome-physical-rdp.sh`

Use xrdp/XFCE only if you want a separate management desktop session instead of the physical monitor session:

```sh
sudo ./scripts/install-xrdp-xfce-ubuntu.sh
```

Keep RDP private to your LAN or VPN firewall scope.

## Cockpit

Install Cockpit directly on Ubuntu/Debian:

```sh
sudo ./scripts/install-cockpit-ubuntu.sh
```

Recommended firewall stance:

- Allow SSH only from your LAN or VPN.
- Allow the dashboard only from your LAN or VPN.
- Keep Portainer, Guacamole, Cockpit, RDP, VNC, and Docker private.
- Do not expose `/var/run/docker.sock` over TCP.

For HTTPS, terminate TLS through a trusted reverse proxy, Tailscale Serve/Funnel for private use, or a local certificate flow you control.
