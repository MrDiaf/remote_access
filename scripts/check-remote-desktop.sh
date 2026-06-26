#!/usr/bin/env sh
set -eu

env_value() {
  key="$1"
  fallback="$2"
  if [ -f .env ]; then
    value=$(sed -n "s/^${key}=//p" .env | tail -n 1)
    if [ -n "$value" ]; then
      printf "%s" "$value"
      return
    fi
  fi
  printf "%s" "$fallback"
}

GUACAMOLE_PORT=$(env_value GUACAMOLE_HTTP_PORT 8081)
GUACAMOLE_URL="http://127.0.0.1:${GUACAMOLE_PORT}/guacamole/"
RDP_HOST="${REMOTE_RDP_HOST:-host.docker.internal}"
RDP_PORT="${REMOTE_RDP_PORT:-3389}"
DASHBOARD_PORT=$(env_value DASHBOARD_HTTP_PORT 8080)

section() {
  printf "\n== %s ==\n" "$1"
}

container_state() {
  name="$1"
  if docker inspect "$name" >/dev/null 2>&1; then
    docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || printf "unknown"
  else
    printf "missing"
  fi
}

check_url() {
  url="$1"
  label="$2"
  if command -v python3 >/dev/null 2>&1; then
    if python3 - "$url" <<'PY'
import sys
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=4) as response:
        print(f"ok: HTTP {response.status}")
except Exception as exc:
    print(f"warn: {exc}")
    sys.exit(1)
PY
    then
      printf "ok: %s reachable at %s\n" "$label" "$url"
    else
      printf "warn: %s is not reachable at %s\n" "$label" "$url"
    fi
  else
    printf "warn: python3 not found; cannot check %s\n" "$label"
  fi
}

section "Docker"
if docker info >/dev/null 2>&1; then
  printf "ok: Docker daemon is running\n"
else
  printf "fail: Docker daemon is not reachable\n"
  exit 1
fi

section "Guacamole containers"
for name in scp-guacamole scp-guacd scp-guacamole-db; do
  state=$(container_state "$name")
  case "$state" in
    running) printf "ok: %s is running\n" "$name" ;;
    missing) printf "warn: %s is missing; run make remote-up\n" "$name" ;;
    *) printf "warn: %s state is %s\n" "$name" "$state" ;;
  esac
done

section "Guacamole HTTP"
check_url "$GUACAMOLE_URL" "Guacamole"
check_url "http://127.0.0.1:${DASHBOARD_PORT}/guacamole/" "Dashboard proxied Guacamole"

section "Host RDP from backend network"
if [ "$(container_state scp-backend)" = "running" ]; then
  if docker compose exec -T backend python - "$RDP_HOST" "$RDP_PORT" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
try:
    with socket.create_connection((host, port), timeout=4):
        print(f"ok: {host}:{port} reachable from backend container")
except Exception as exc:
    print(f"warn: {host}:{port} not reachable from backend container: {exc}")
    sys.exit(1)
PY
  then
    :
  else
    printf "hint: install/start xrdp on the host with make install-host-remote-desktop\n"
  fi
else
  printf "warn: scp-backend is not running; run make up before checking container-network RDP\n"
fi

section "Host local services"
if command -v grdctl >/dev/null 2>&1; then
  printf "GNOME Remote Desktop status:\n"
  grdctl status 2>&1 | sed 's/^/  /' || true
else
  printf "info: grdctl not found; GNOME physical screen sharing is not configured\n"
fi

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet xrdp; then
  printf "ok: xrdp service is active on host\n"
else
  printf "warn: xrdp service is not active on host or systemctl is unavailable\n"
fi

if command -v ss >/dev/null 2>&1 && ss -ltn | awk '{print $4}' | grep -Eq "[:.]3389$"; then
  printf "ok: host is listening on TCP 3389\n"
else
  printf "warn: host is not listening on TCP 3389\n"
fi
