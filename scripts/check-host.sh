#!/usr/bin/env sh
# Checks that the stack will come back after a reboot and that the web
# terminal can reach the host's SSH server. Read-only: it changes nothing.
set -u

section() {
  printf "\n== %s ==\n" "$1"
}

section "Start on boot"
if command -v systemctl >/dev/null 2>&1; then
  if [ "$(systemctl is-enabled docker 2>/dev/null)" = "enabled" ]; then
    printf "ok: Docker starts on boot\n"
  else
    printf "warn: Docker is not enabled on boot; fix with: sudo systemctl enable docker\n"
  fi
else
  printf "info: systemctl not found; cannot check boot services\n"
fi

if ! docker info >/dev/null 2>&1; then
  printf "fail: Docker daemon is not reachable\n"
  exit 1
fi

section "Containers"
for name in scp-proxy scp-frontend scp-backend scp-terminal scp-portainer scp-guacamole scp-guacd scp-guacamole-db; do
  if ! docker inspect "$name" >/dev/null 2>&1; then
    printf "warn: %s is missing; run make up\n" "$name"
    continue
  fi
  state=$(docker inspect -f '{{.State.Status}}' "$name")
  policy=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' "$name")
  if [ "$state" = "running" ] && [ "$policy" = "unless-stopped" ]; then
    printf "ok: %s is running and restarts after reboot\n" "$name"
  else
    printf "warn: %s is %s (restart policy: %s); run make up\n" "$name" "$state" "$policy"
  fi
done

section "Web terminal (SSH)"
if command -v ss >/dev/null 2>&1 && ss -ltn | awk '{print $4}' | grep -Eq "[:.]22$"; then
  printf "ok: host is listening on TCP 22\n"
else
  printf "warn: host is not listening on TCP 22; install/start it: sudo apt install openssh-server\n"
fi
if [ "$(docker inspect -f '{{.State.Status}}' scp-terminal 2>/dev/null)" != "running" ]; then
  printf "info: scp-terminal is not running; skipped the SSH reachability check\n"
elif docker exec scp-terminal sh -c 'nc -z -w 4 "${TERMINAL_SSH_HOST}" "${TERMINAL_SSH_PORT}"' >/dev/null 2>&1; then
  printf "ok: terminal container reaches the host SSH server\n"
else
  printf "warn: terminal container cannot reach the host SSH server (check sshd and firewall rules for the Docker network)\n"
fi

section "Physical screen after reboot"
# GNOME Remote Desktop shares the logged-in desktop, so after a reboot someone
# must be logged in at the monitor, or GDM must log in automatically.
gdm_conf=""
for candidate in /etc/gdm3/custom.conf /etc/gdm/custom.conf; do
  [ -f "$candidate" ] && gdm_conf="$candidate" && break
done
if [ -n "$gdm_conf" ] && grep -Eiq '^[[:space:]]*AutomaticLoginEnable[[:space:]]*=[[:space:]]*true' "$gdm_conf"; then
  printf "ok: GNOME automatic login is enabled (%s)\n" "$gdm_conf"
else
  printf "info: GNOME automatic login is off. After a reboot, log in at the monitor once\n"
  printf "      before the physical screen is available, or enable automatic login in\n"
  printf "      Settings > System > Users. See README: After A Reboot.\n"
fi
if command -v systemctl >/dev/null 2>&1; then
  if [ "$(systemctl --user is-enabled gnome-remote-desktop.service 2>/dev/null)" = "enabled" ]; then
    printf "ok: gnome-remote-desktop starts with your GNOME session\n"
  else
    printf "info: gnome-remote-desktop is not enabled for this user; run make enable-physical-screen\n"
  fi
fi

section "Steam control (optional)"
if [ ! -x /usr/games/steam ] && [ ! -x /snap/bin/steam ]; then
  printf "info: Steam is not installed; the dashboard Steam card stays disabled\n"
elif [ ! -f data/steam-control/id_ed25519 ] || ! grep -q " scp-steam-control\$" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
  printf "info: Steam control is not set up; run make enable-steam-control\n"
else
  printf "ok: the dashboard key may start and quit Steam\n"
  if systemctl --user show-environment 2>/dev/null | grep -Eq '^(DISPLAY|WAYLAND_DISPLAY)='; then
    printf "ok: a desktop session is running, so Steam has a screen to open on\n"
  else
    printf "info: no desktop session right now; Steam can start only after someone logs in\n"
  fi
fi
