#!/usr/bin/env sh
# One-time host setup, run by `make up` after the containers are healthy.
# Every step checks first and does nothing when it is already done, so this is
# safe on every `make up`. Missing steps are asked about one by one; answering
# "n" is remembered in data/host-setup.skip until `make setup-host` asks again.
# Without a terminal (CI, `ssh host make up`) nothing is asked, only listed.
set -u

cd "$(dirname "$0")/.."
COMPOSE_CMD=${COMPOSE_CMD:-docker compose}
SKIP_FILE=data/host-setup.skip
ASK_ALL=${SETUP_HOST_ASK_ALL:-0}

# Over SSH there is no desktop environment; reach the user's session manager.
uid=$(id -u)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$uid}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

rdp_user=""
rdp_pass=""

trap 'stty echo 2>/dev/null' EXIT INT TERM

# ask STEP QUESTION: 0 when the user agrees now.
ask() {
  if [ "$ASK_ALL" != 1 ] && grep -qx "$1" "$SKIP_FILE" 2>/dev/null; then
    printf "skipped: %s (make setup-host asks again)\n" "$2"
    return 1
  fi
  if [ ! -t 0 ]; then
    printf "todo: %s (run make setup-host in a terminal)\n" "$2"
    return 1
  fi
  printf "%s? [Y/n] " "$2"
  read -r answer || answer=n
  case "$answer" in
    [Nn]*)
      grep -qx "$1" "$SKIP_FILE" 2>/dev/null || printf "%s\n" "$1" >> "$SKIP_FILE"
      printf "  Skipped. Run make setup-host to be asked again.\n"
      return 1
      ;;
  esac
  if [ -f "$SKIP_FILE" ]; then
    grep -vx "$1" "$SKIP_FILE" > "$SKIP_FILE.tmp" || true
    mv "$SKIP_FILE.tmp" "$SKIP_FILE"
  fi
  return 0
}

read_secret() {
  stty -echo 2>/dev/null
  printf "%s: " "$1"
  read -r secret || secret=""
  stty echo 2>/dev/null
  printf "\n"
}

# psql in the Guacamole database; SQL comes from stdin. Extra args are
# `docker compose exec` options such as `-e NAME` (value taken from this env,
# so secrets never appear on a command line).
guac_sql() {
  out=$($COMPOSE_CMD exec -T "$@" guacamole-db \
    sh -c 'psql -q -t -A -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"') || return 1
  printf "%s\n" "$out" | tr -d '\r' | sed '/^$/d' | tail -n 1
}

guac_db_running() {
  [ "$(docker inspect -f '{{.State.Status}}' scp-guacamole-db 2>/dev/null)" = "running" ]
}

printf "\n== Host setup ==\n"

# 1. Docker must start on boot, or nothing comes back after a reboot.
if ! command -v systemctl >/dev/null 2>&1 || [ "$(systemctl is-enabled docker 2>/dev/null)" = "enabled" ]; then
  printf "ok: Docker starts on boot\n"
elif ask docker-boot "Start Docker on boot (sudo systemctl enable docker)"; then
  sudo systemctl enable docker && printf "ok: Docker starts on boot\n"
fi

# 2. The Terminal page and Steam control log in to the host over SSH.
ssh_port=$(sed -n 's/^TERMINAL_SSH_PORT=//p' .env 2>/dev/null | tail -n 1)
ssh_port=${ssh_port:-22}
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]$ssh_port\$"; then
  printf "ok: SSH server is listening on port %s\n" "$ssh_port"
elif ask ssh-server "Install and start the SSH server for the Terminal page (sudo apt install openssh-server)"; then
  sudo apt-get install -y openssh-server && sudo systemctl enable --now ssh && printf "ok: SSH server installed\n"
fi

# 3. Share the logged-in GNOME screen over RDP.
screen_enabled() {
  grdctl status 2>/dev/null | awk '/^RDP:/ {rdp = 1; next} /^[^\t ]/ {rdp = 0} rdp && $1 == "Status:" {print $2; exit}' | grep -qx enabled
}
if ! command -v grdctl >/dev/null 2>&1; then
  printf "todo: install GNOME Remote Desktop for the physical screen: sudo apt install gnome-remote-desktop\n"
elif screen_enabled; then
  printf "ok: the physical screen is shared over RDP\n"
elif ask physical-screen "Share this desktop's screen over RDP (asks for a new remote desktop login)"; then
  printf "Pick a username and password for remote desktop. Guacamole will use them.\n"
  printf "Remote desktop username: "
  read -r rdp_user || rdp_user=""
  read_secret "Remote desktop password"
  rdp_pass=$secret
  if [ -n "$rdp_user" ] && [ -n "$rdp_pass" ]; then
    RDP_USERNAME=$rdp_user RDP_PASSWORD=$rdp_pass ./scripts/enable-gnome-physical-rdp.sh >/dev/null \
      && printf "ok: the physical screen is shared over RDP\n" \
      || { printf "fail: make enable-physical-screen failed; run it from the desktop to see why\n"; rdp_user=""; rdp_pass=""; }
  else
    printf "  A username and password are both required; skipped.\n"
  fi
fi

# 4. Guacamole needs one RDP connection pointing at that screen.
if ! guac_db_running; then
  printf "todo: the Guacamole database is not running; run make up\n"
else
  rdp_connections=$(printf "SELECT count(*) FROM guacamole_connection WHERE lower(protocol) = 'rdp';\n" | guac_sql)
  if [ "${rdp_connections:-0}" -gt 0 ] 2>/dev/null; then
    printf "ok: Guacamole has a remote desktop connection\n"
  elif ask guacamole-connection "Create the Guacamole connection to this desktop"; then
    if [ -z "$rdp_user" ]; then
      printf "Use the remote desktop login from make enable-physical-screen.\n"
      printf "Remote desktop username: "
      read -r rdp_user || rdp_user=""
      read_secret "Remote desktop password"
      rdp_pass=$secret
    fi
    if [ -n "$rdp_user" ] && [ -n "$rdp_pass" ]; then
      export RDP_USERNAME="$rdp_user" RDP_PASSWORD="$rdp_pass"
      guac_sql -e RDP_USERNAME -e RDP_PASSWORD <<'SQL' >/dev/null && printf "ok: created the Guacamole connection \"Ubuntu Physical Desktop\"\n" || printf "fail: could not create the Guacamole connection\n"
\getenv rdp_user RDP_USERNAME
\getenv rdp_pass RDP_PASSWORD
WITH conn AS (
    INSERT INTO guacamole_connection (connection_name, protocol)
    VALUES ('Ubuntu Physical Desktop', 'rdp')
    RETURNING connection_id
), params AS (
    INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value)
    SELECT connection_id, p.name, p.value
    FROM conn, (VALUES
        ('hostname', 'host.docker.internal'),
        ('port', '3389'),
        ('username', :'rdp_user'),
        ('password', :'rdp_pass'),
        ('security', 'any'),
        ('ignore-cert', 'true')
    ) AS p(name, value)
)
INSERT INTO guacamole_connection_permission (entity_id, connection_id, permission)
SELECT e.entity_id, conn.connection_id, perm::guacamole_object_permission_type
FROM conn, guacamole_entity e, unnest(ARRAY['READ', 'UPDATE', 'DELETE', 'ADMINISTER']) AS perm
WHERE e.name = 'guacadmin' AND e.type = 'USER';
SQL
      unset RDP_USERNAME RDP_PASSWORD
    else
      printf "  A username and password are both required; skipped.\n"
    fi
  fi

  # 5. Guacamole ships with guacadmin/guacadmin. Guacamole stores
  #    SHA-256(password + uppercase hex salt); compare without reading it out.
  default_admin=$(guac_sql <<'SQL'
SELECT count(*) FROM guacamole_user u JOIN guacamole_entity e USING (entity_id)
WHERE e.name = 'guacadmin' AND e.type = 'USER'
  AND u.password_hash = sha256(convert_to('guacadmin' || upper(encode(u.password_salt, 'hex')), 'UTF8'));
SQL
)
  if [ "${default_admin:-0}" = 0 ]; then
    printf "ok: Guacamole's guacadmin password has been changed\n"
  elif ask guacamole-password "Change Guacamole's default guacadmin/guacadmin password"; then
    read_secret "New guacadmin password"
    first=$secret
    read_secret "Repeat it"
    if [ -z "$first" ] || [ "$first" != "$secret" ]; then
      printf "  The passwords were empty or did not match; unchanged.\n"
    else
      export GUAC_ADMIN_PASSWORD="$first"
      guac_sql -e GUAC_ADMIN_PASSWORD <<'SQL' >/dev/null && printf "ok: guacadmin password changed\n" || printf "fail: could not change the guacadmin password\n"
\getenv new_pass GUAC_ADMIN_PASSWORD
UPDATE guacamole_user u
SET password_salt = s.salt,
    password_hash = sha256(convert_to(:'new_pass' || upper(encode(s.salt, 'hex')), 'UTF8')),
    password_date = now()
FROM guacamole_entity e,
     (SELECT sha256(convert_to(gen_random_uuid()::text || gen_random_uuid()::text, 'UTF8')) AS salt) s
WHERE u.entity_id = e.entity_id AND e.name = 'guacadmin' AND e.type = 'USER';
SQL
      unset GUAC_ADMIN_PASSWORD
    fi
  fi
fi

# 6. Steam control is optional and only offered when Steam is installed.
if [ -x /usr/games/steam ] || [ -x /snap/bin/steam ]; then
  if [ -f data/steam-control/id_ed25519 ] && grep -q " scp-steam-control\$" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    printf "ok: the dashboard can start and quit Steam\n"
  elif ask steam-control "Let the dashboard start and quit Steam"; then
    ./scripts/enable-steam-control.sh >/dev/null && printf "ok: the dashboard can start and quit Steam\n" \
      || printf "fail: make enable-steam-control failed; run it to see why\n"
  fi
fi

# 7. After a reboot the physical screen needs someone logged in. That is a GDM
#    setting with a security trade-off, so it is only pointed out here.
gdm_conf=""
for candidate in /etc/gdm3/custom.conf /etc/gdm/custom.conf; do
  [ -f "$candidate" ] && gdm_conf=$candidate && break
done
if [ -n "$gdm_conf" ] && ! grep -Eiq '^[[:space:]]*AutomaticLoginEnable[[:space:]]*=[[:space:]]*true' "$gdm_conf"; then
  printf "info: after a reboot, log in at the monitor once, or turn on automatic\n"
  printf "      login in Settings > System > Users so the remote desktop comes back by itself.\n"
fi
