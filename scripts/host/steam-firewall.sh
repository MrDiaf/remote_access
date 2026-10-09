#!/bin/sh
# Opens and closes Steam Remote Play's ports in ufw. Runs as root.
#
# setup-host.sh installs it as /usr/local/sbin/scp-steam-firewall (owned by
# root) and adds a sudoers rule that lets the desktop user run only
# `status`, `open`, and `close` without a password; the dashboard reaches those
# through the Steam forced command. `open-lan CIDR` is run once by
# setup-host.sh with the user's own sudo password.
#
#   status       prints: firewall=<active|inactive|missing> lan=<cidr|closed> internet=<open|closed>
#   open         allow the ports from anywhere (the internet)
#   close        remove the internet rules
#   open-lan C   allow the ports from the private network C (replaces older LAN rules)
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin

LAN_TAG=scp-remoteplay-lan
NET_TAG=scp-remoteplay-internet

# Remote Play: UDP 27031-27036 and TCP 27036-27037.
allow() { # SOURCE TAG
  ufw allow proto udp from "$1" to any port 27031:27036 comment "$2" >/dev/null
  ufw allow proto tcp from "$1" to any port 27036:27037 comment "$2" >/dev/null
}

remove() { # TAG; delete by number, highest first, so numbers stay valid
  for n in $(ufw status numbered | sed -n "s/^\[ *\([0-9][0-9]*\)\].*# $1\$/\1/p" | sort -rn); do
    ufw --force delete "$n" >/dev/null
  done
}

status() {
  if ! command -v ufw >/dev/null 2>&1; then
    printf "firewall=missing lan=closed internet=closed\n"
    return
  fi
  out=$(ufw status)
  state=$(printf "%s\n" "$out" | sed -n 's/^Status: //p')
  lan=$(printf "%s\n" "$out" | awk -v tag="# $LAN_TAG" 'index($0, tag) && $3 ~ /\// {print $3; exit}')
  if printf "%s\n" "$out" | grep -q "# $NET_TAG\$"; then net=open; else net=closed; fi
  printf "firewall=%s lan=%s internet=%s\n" "${state:-unknown}" "${lan:-closed}" "$net"
}

case "${1:-}" in
  status)
    status
    ;;
  open)
    command -v ufw >/dev/null 2>&1 || { printf "missing: ufw is not installed\n"; exit 4; }
    ufw status | grep -q "# $NET_TAG\$" || allow any "$NET_TAG"
    status
    ;;
  close)
    command -v ufw >/dev/null 2>&1 || { printf "missing: ufw is not installed\n"; exit 4; }
    remove "$NET_TAG"
    status
    ;;
  open-lan)
    cidr=${2:-}
    # Only private IPv4 ranges: this rule is meant for the home network.
    if ! printf "%s\n" "$cidr" | grep -Eqx '(10\.[0-9]{1,3}|172\.(1[6-9]|2[0-9]|3[01])|192\.168)\.[0-9]{1,3}\.[0-9]{1,3}/([89]|[12][0-9]|3[0-2])'; then
      printf "refused: %s is not a private IPv4 network\n" "$cidr"
      exit 2
    fi
    command -v ufw >/dev/null 2>&1 || { printf "missing: ufw is not installed\n"; exit 4; }
    remove "$LAN_TAG"
    allow "$cidr" "$LAN_TAG"
    status
    ;;
  *)
    printf "refused: use status, open, close, or open-lan CIDR\n"
    exit 2
    ;;
esac
