#!/usr/bin/env sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  printf "Run with sudo: sudo %s\n" "$0" >&2
  exit 1
fi

apt-get update
apt-get install -y cockpit
systemctl enable --now cockpit.socket

printf "Cockpit is available at https://server-ip:9090\n"

