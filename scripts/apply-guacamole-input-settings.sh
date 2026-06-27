#!/usr/bin/env sh
set -eu

COMPOSE_CMD=${COMPOSE_CMD:-docker compose}

layout=${REMOTE_KEYBOARD_LAYOUT:-}
if [ -z "$layout" ]; then
  layout=$($COMPOSE_CMD exec -T backend python -c "from app.config import load_dashboard_settings; print(load_dashboard_settings().remote_input.remote_keyboard_layout)")
fi
layout=$(printf "%s" "$layout" | tr -d "\r" | tr "[:upper:]" "[:lower:]")

case "$layout" in
  en-us-qwerty|en-gb-qwerty|sv-se-qwerty|da-dk-qwerty|no-no-qwerty|fi-fi-qwerty|de-de-qwertz|de-ch-qwertz|fr-fr-azerty|fr-be-azerty|fr-ch-qwertz|es-es-qwerty|es-latam-qwerty|it-it-qwerty|pt-br-qwerty|hu-hu-qwertz|ja-jp-qwerty|tr-tr-qwerty|failsafe) ;;
  *)
    printf "Unsupported Guacamole keyboard layout: %s\n" "$layout" >&2
    exit 1
    ;;
esac

if ! docker inspect scp-guacamole-db >/dev/null 2>&1; then
  printf "Guacamole database container is missing. Run make remote-up first.\n" >&2
  exit 1
fi

if [ "$(docker inspect -f '{{.State.Status}}' scp-guacamole-db 2>/dev/null)" != "running" ]; then
  printf "Guacamole database container is not running. Run make remote-up first.\n" >&2
  exit 1
fi

updated=$($COMPOSE_CMD exec -T -e REMOTE_KEYBOARD_LAYOUT="$layout" guacamole-db sh -c 'psql -q -t -A -v ON_ERROR_STOP=1 -v layout="$REMOTE_KEYBOARD_LAYOUT" -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
WITH rdp_connections AS (
    SELECT connection_id
    FROM guacamole_connection
    WHERE lower(protocol) = 'rdp'
),
upserted AS (
    INSERT INTO guacamole_connection_parameter (connection_id, parameter_name, parameter_value)
    SELECT connection_id, 'server-layout', :'layout'
    FROM rdp_connections
    ON CONFLICT (connection_id, parameter_name)
    DO UPDATE SET parameter_value = EXCLUDED.parameter_value
    RETURNING 1
)
SELECT count(*) FROM upserted;
SQL
)

updated=$(printf "%s\n" "$updated" | tr -d "\r" | awk 'NF { line = $0 } END { gsub(/^[ \t]+|[ \t]+$/, "", line); print line }')
printf "Applied remote keyboard layout %s to %s Guacamole RDP connection(s).\n" "$layout" "$updated"
printf "Reconnect any open Guacamole session before testing the keyboard again.\n"
