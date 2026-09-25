#!/bin/sh
set -eu

host=${TERMINAL_SSH_HOST:-host.docker.internal}
port=${TERMINAL_SSH_PORT:-22}
user=${TERMINAL_SSH_USER:-}

printf "Server terminal: SSH to %s port %s\n\n" "$host" "$port"

if [ -z "$user" ]; then
  printf "Username: "
  read -r user
fi

# The username goes on the ssh command line; refuse anything that could be
# read as an ssh option or a different host.
case "$user" in
  "" | -* | *[!A-Za-z0-9._-]*)
    printf "Invalid username.\n"
    exit 1
    ;;
esac

exec ssh \
  -o StrictHostKeyChecking=accept-new \
  -o ServerAliveInterval=30 \
  -p "$port" \
  -l "$user" \
  "$host"
