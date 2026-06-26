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

section "Host RDP from guacd network"
if [ "$(container_state scp-guacd)" = "running" ]; then
  if docker compose exec -T guacd sh -c "getent hosts '$RDP_HOST' >/dev/null 2>&1"; then
    resolved=$(docker compose exec -T guacd getent hosts "$RDP_HOST" | awk '{print $1}' | head -n 1)
    printf "ok: %s resolves inside guacd as %s\n" "$RDP_HOST" "$resolved"
  else
    printf "warn: %s does not resolve inside guacd\n" "$RDP_HOST"
    printf "hint: recreate guacd after adding host-gateway mapping: make remote-up\n"
  fi

  if docker compose exec -T guacd sh -c "nc -z -w 4 '$RDP_HOST' '$RDP_PORT'" >/dev/null 2>&1; then
    printf "ok: %s:%s reachable from guacd container\n" "$RDP_HOST" "$RDP_PORT"
  else
    printf "warn: %s:%s not reachable from guacd container\n" "$RDP_HOST" "$RDP_PORT"
    printf "hint: run make enable-physical-screen on the host and make remote-up to recreate guacd\n"
  fi
else
  printf "warn: scp-guacd is not running; run make remote-up before checking RDP from Guacamole\n"
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
