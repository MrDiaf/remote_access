#!/usr/bin/env sh
set -eu

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    printf "ok: %s installed\n" "$1"
  else
    printf "missing: %s\n" "$1"
  fi
}

check_service() {
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "$1"; then
    printf "ok: %s active\n" "$1"
  else
    printf "warn: %s is not active or systemctl is unavailable\n" "$1"
  fi
}

check_port() {
  port="$1"
  label="$2"
  if command -v ss >/dev/null 2>&1 && ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"; then
    printf "ok: %s listening on TCP %s\n" "$label" "$port"
  else
    printf "warn: %s not listening on TCP %s\n" "$label" "$port"
  fi
}

check_cmd xrdp
check_cmd startxfce4
check_service xrdp
check_port 3389 "RDP"
check_port 5900 "VNC"

if command -v docker >/dev/null 2>&1; then
  docker compose --profile remote ps 2>/dev/null || true
fi
