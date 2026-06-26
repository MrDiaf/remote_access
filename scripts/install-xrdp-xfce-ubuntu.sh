#!/usr/bin/env sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  printf "Run with sudo: sudo %s\n" "$0" >&2
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies xrdp xorgxrdp dbus-x11

adduser xrdp ssl-cert >/dev/null 2>&1 || true
printf "startxfce4\n" > /etc/skel/.xsession

if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  user_home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
  if [ -n "$user_home" ] && [ -d "$user_home" ]; then
    printf "startxfce4\n" > "$user_home/.xsession"
    chown "$SUDO_USER:$SUDO_USER" "$user_home/.xsession"
  fi
fi

systemctl enable --now xrdp

printf "xrdp is installed and listening on TCP 3389 when active.\n"
printf "Create or choose a Linux user with a strong password for Guacamole RDP login.\n"
printf "For existing users, create ~/.xsession containing: startxfce4\n"
printf "Keep TCP 3389 private to your LAN/VPN firewall scope.\n"
