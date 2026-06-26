#!/usr/bin/env sh
set -eu

if ! command -v grdctl >/dev/null 2>&1; then
  printf "gnome-remote-desktop/grdctl is missing. Install it first:\n"
  printf "  sudo apt-get install gnome-remote-desktop\n"
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  printf "openssl is missing. Install it first:\n"
  printf "  sudo apt-get install openssl\n"
  exit 1
fi

printf "This configures GNOME Remote Desktop for the CURRENT logged-in user.\n"
printf "It mirrors the physical GNOME screen over RDP on TCP 3389.\n\n"

read -r -p "Remote desktop username: " remote_user
if [ -z "$remote_user" ]; then
  printf "Username is required.\n" >&2
  exit 1
fi

stty -echo
printf "Remote desktop password: "
read -r remote_pass
printf "\n"
stty echo

if [ -z "$remote_pass" ]; then
  printf "Password is required.\n" >&2
  exit 1
fi

cert_dir="${HOME}/.local/share/gnome-remote-desktop"
cert_path="${cert_dir}/rdp-tls.crt"
key_path="${cert_dir}/rdp-tls.key"

mkdir -p "$cert_dir"
chmod 700 "$cert_dir"

if [ ! -f "$cert_path" ] || [ ! -f "$key_path" ]; then
  openssl req \
    -new \
    -newkey rsa:4096 \
    -days 3650 \
    -nodes \
    -x509 \
    -subj "/CN=$(hostname)" \
    -keyout "$key_path" \
    -out "$cert_path"
  chmod 600 "$key_path"
  chmod 644 "$cert_path"
fi

grdctl rdp set-port 3389
grdctl rdp disable-port-negotiation
grdctl rdp set-auth-methods credentials
grdctl rdp set-tls-cert "$cert_path"
grdctl rdp set-tls-key "$key_path"
grdctl rdp set-credentials "$remote_user" "$remote_pass"
grdctl rdp disable-view-only
grdctl rdp enable

systemctl --user enable --now gnome-remote-desktop.service >/dev/null 2>&1 || \
  systemctl --user start gnome-remote-desktop.service

printf "\nGNOME physical desktop sharing is enabled.\n"
printf "Use this in Guacamole:\n"
printf "  Protocol: RDP\n"
printf "  Hostname: host.docker.internal\n"
printf "  Port: 3389\n"
printf "  Username: %s\n" "$remote_user"
printf "  Password: the password you just entered\n"
printf "  Ignore server certificate: enabled\n"
printf "\nKeep TCP 3389 reachable only from LAN/VPN/Docker, never the public internet.\n"

