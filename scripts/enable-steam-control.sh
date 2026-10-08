#!/usr/bin/env sh
# Lets the dashboard start and quit Steam on this server's desktop.
#
# The backend container gets its own SSH key. ~/.ssh/authorized_keys pins that
# key to scripts/host/steam-control.sh with `restrict,command=...`, so the key
# can only ask for status, start, or stop: no shell, pty, or forwarding.
# Run it as the user who is logged in to the desktop. Safe to repeat.
set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
steam=/usr/games/steam
[ -x "$steam" ] || [ ! -x /snap/bin/steam ] || steam=/snap/bin/steam
key_dir="$repo/data/steam-control"
key="$key_dir/id_ed25519"
forced="$HOME/.local/bin/scp-steam-control"
auth="$HOME/.ssh/authorized_keys"
tag="scp-steam-control"

if [ "$(id -u)" -eq 0 ]; then
  printf "Run this as your desktop user, not root or sudo.\n" >&2
  exit 1
fi

if [ ! -x "$steam" ]; then
  printf "Steam is not installed at %s. Install it first:\n" "$steam" >&2
  printf "  sudo apt install steam-installer\n" >&2
  exit 1
fi

if ! command -v ssh-keygen >/dev/null 2>&1; then
  printf "ssh-keygen is missing. Install it first:\n  sudo apt install openssh-client\n" >&2
  exit 1
fi

mkdir -p "$(dirname "$forced")"
install -m 755 "$repo/scripts/host/steam-control.sh" "$forced"
printf "Installed %s\n" "$forced"

mkdir -p "$key_dir"
chmod 700 "$key_dir"
if [ ! -f "$key" ]; then
  ssh-keygen -q -t ed25519 -N "" -C "$tag" -f "$key"
  printf "Created %s\n" "$key"
fi
chmod 600 "$key"
id -un > "$key_dir/user"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
touch "$auth"
chmod 600 "$auth"
tmp=$(mktemp "$auth.XXXXXX")
grep -v " $tag\$" "$auth" > "$tmp" || true
printf 'restrict,command="%s" %s\n' "$forced" "$(cut -d' ' -f1,2 "$key.pub") $tag" >> "$tmp"
mv "$tmp" "$auth"
printf "Authorized the dashboard key in %s (Steam control only)\n" "$auth"

printf "\nDone. The Steam card on the dashboard's Actions page works now.\n"
printf "To revoke: delete the line ending in '%s' from %s.\n" "$tag" "$auth"
