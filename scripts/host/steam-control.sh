#!/usr/bin/env sh
# Forced command for the dashboard's Steam key (see enable-steam-control.sh).
# sshd runs this instead of whatever the client asked for and puts the
# requested word in SSH_ORIGINAL_COMMAND. Only status, start, and stop are
# accepted; anything else exits 2 without doing anything.
set -eu

# apt/.deb installs to /usr/games; the snap to /snap/bin.
STEAM=${STEAM_BIN:-}
if [ -z "$STEAM" ]; then
  STEAM=/usr/games/steam
  [ -x "$STEAM" ] || [ ! -x /snap/bin/steam ] || STEAM=/snap/bin/steam
fi

case "${SSH_ORIGINAL_COMMAND:-}" in
  status | start | stop) verb=$SSH_ORIGINAL_COMMAND ;;
  *)
    printf "refused: only status, start, and stop are allowed\n"
    exit 2
    ;;
esac

# An SSH login has no desktop environment of its own; talk to the user's
# systemd manager, which GNOME fills with DISPLAY/WAYLAND_DISPLAY at login.
uid=$(id -u)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$uid}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

running() {
  pgrep -u "$uid" -x steam >/dev/null 2>&1
}

case "$verb" in
  status)
    if running; then printf "running\n"; else printf "stopped\n"; fi
    ;;

  start)
    if running; then
      printf "running\n"
      exit 0
    fi
    if [ ! -x "$STEAM" ]; then
      printf "missing: %s is not installed\n" "$STEAM"
      exit 4
    fi
    if ! systemctl --user show-environment 2>/dev/null | grep -Eq '^(DISPLAY|WAYLAND_DISPLAY)='; then
      printf "no-session: nobody is logged in to the desktop\n"
      exit 3
    fi
    # A transient unit runs Steam in the desktop session and outlives this call.
    systemctl --user reset-failed scp-steam.service >/dev/null 2>&1 || true
    systemd-run --user --quiet --collect --unit=scp-steam "$STEAM" >/dev/null
    printf "starting\n"
    ;;

  stop)
    if ! running; then
      printf "stopped\n"
      exit 0
    fi
    # Ask Steam to quit cleanly. Never kill it: a game may still be saving.
    "$STEAM" -shutdown >/dev/null 2>&1 || true
    waited=0
    while running && [ "$waited" -lt 30 ]; do
      sleep 1
      waited=$((waited + 1))
    done
    if running; then printf "stopping\n"; else printf "stopped\n"; fi
    ;;
esac
