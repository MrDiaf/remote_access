#!/usr/bin/env sh
# Forced command for the dashboard's Steam key (see enable-steam-control.sh).
# sshd runs this instead of whatever the client asked for and puts the
# requested word in SSH_ORIGINAL_COMMAND. Only status, start, bigpicture, stop,
# and ports-status/ports-open/ports-close are accepted; anything else exits 2
# without doing anything.
set -eu

# apt/.deb installs to /usr/games; the snap to /snap/bin.
STEAM=${STEAM_BIN:-}
if [ -z "$STEAM" ]; then
  STEAM=/usr/games/steam
  [ -x "$STEAM" ] || [ ! -x /snap/bin/steam ] || STEAM=/snap/bin/steam
fi

case "${SSH_ORIGINAL_COMMAND:-}" in
  status | start | bigpicture | stop | ports-status | ports-open | ports-close) verb=$SSH_ORIGINAL_COMMAND ;;
  *)
    printf "refused: only status, start, bigpicture, stop, and ports-* are allowed\n"
    exit 2
    ;;
esac

# An SSH login has no desktop environment of its own; talk to the user's
# systemd manager, which GNOME fills with DISPLAY/WAYLAND_DISPLAY at login.
uid=$(id -u)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$uid}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

# The real Steam client is .../ubuntu12_32/steam. The /usr/games/steam
# launcher script and its first-run dialogs are not a running Steam.
client_path() {
  pgrep -u "$uid" -a -f '/ubuntu12_32/steam( |$)' 2>/dev/null | awk '$2 ~ /\/ubuntu12_32\/steam$/ {print $2; exit}'
}

running() {
  [ -n "$(client_path)" ]
}

# Launched by this script but the client is not up yet (downloading, or the
# apt package's one-time "Install" dialog is waiting on the desktop).
launching() {
  systemctl --user is-active --quiet scp-steam.service
}

# The apt package installs the client on first launch, after the user clicks
# Install on the desktop.
needs_setup() {
  [ "$STEAM" = /usr/games/steam ] && [ ! -x "$HOME/.steam/debian-installation/ubuntu12_32/steam" ]
}

launching_state() {
  if needs_setup; then
    printf "setup-needed: finish Steam's first-time install on the server's desktop\n"
  else
    printf "starting\n"
  fi
}

# The launcher of whichever Steam (apt or snap) is running, so -shutdown and
# steam:// URLs reach that one.
running_steam() {
  case "$(client_path)" in
    */snap/steam/*) printf "/snap/bin/steam\n" ;;
    *) printf "%s\n" "$STEAM" ;;
  esac
}

# Run Steam with ARGS inside the desktop session. A transient systemd unit gets
# the session's DISPLAY/WAYLAND_DISPLAY and outlives this SSH call.
launch() {
  if [ ! -x "$STEAM" ]; then
    printf "missing: %s is not installed\n" "$STEAM"
    exit 4
  fi
  if ! systemctl --user show-environment 2>/dev/null | grep -Eq '^(DISPLAY|WAYLAND_DISPLAY)='; then
    printf "no-session: nobody is logged in to the desktop\n"
    exit 3
  fi
  systemd-run --user --quiet --collect "$@" >/dev/null
}

case "$verb" in
  ports-*)
    # Remote Play firewall rules: a root-owned helper that sudoers lets this
    # user run with exactly these arguments (see setup-host.sh).
    helper=/usr/local/sbin/scp-steam-firewall
    if [ ! -x "$helper" ]; then
      printf "ports-not-set-up: run make up on the server\n"
      exit 5
    fi
    exec sudo -n "$helper" "${verb#ports-}"
    ;;

  status)
    if running; then
      printf "running\n"
    elif launching; then
      launching_state
    else
      printf "stopped\n"
    fi
    ;;

  start | bigpicture)
    # Big Picture is the controller/TV interface, the usual Remote Play view.
    if running; then
      if [ "$verb" = bigpicture ]; then
        # Hands the URL to the running Steam, which switches to Big Picture.
        launch "$(running_steam)" steam://open/bigpicture
      fi
      printf "running\n"
    elif launching; then
      # Never stack a second launch (and a second install dialog) on the first.
      launching_state
    else
      systemctl --user reset-failed scp-steam.service >/dev/null 2>&1 || true
      if [ "$verb" = bigpicture ]; then
        launch --unit=scp-steam "$STEAM" -gamepadui
      else
        launch --unit=scp-steam "$STEAM"
      fi
      launching_state
    fi
    ;;

  stop)
    if ! running; then
      # Nothing to save yet: cancel a launch that has not reached the client.
      systemctl --user stop scp-steam.service >/dev/null 2>&1 || true
      printf "stopped\n"
      exit 0
    fi
    # Ask Steam to quit cleanly. Never kill it: a game may still be saving.
    "$(running_steam)" -shutdown >/dev/null 2>&1 || true
    waited=0
    while running && [ "$waited" -lt 30 ]; do
      sleep 1
      waited=$((waited + 1))
    done
    if running; then printf "stopping\n"; else printf "stopped\n"; fi
    ;;
esac
