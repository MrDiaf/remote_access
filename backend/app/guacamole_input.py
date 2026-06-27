from __future__ import annotations

from docker.errors import DockerException, NotFound
from fastapi import HTTPException, status

from .docker_control import get_client
from .models import RemoteInputApplyResult, RemoteInputSettings


APPLY_KEYBOARD_SQL = """\
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
"""


def _last_output_line(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def apply_guacamole_input_settings(remote_input: RemoteInputSettings) -> RemoteInputApplyResult:
    layout = remote_input.remote_keyboard_layout
    client = get_client()

    try:
        container = client.containers.get("scp-guacamole-db")
        container.reload()
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guacamole database container is missing") from exc
    except DockerException as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Docker is unavailable") from exc

    if container.attrs.get("State", {}).get("Status") != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Guacamole database container is not running")

    command = (
        "psql -q -t -A -v ON_ERROR_STOP=1 "
        '-v layout="$REMOTE_KEYBOARD_LAYOUT" '
        '-U "$POSTGRES_USER" -d "$POSTGRES_DB" <<\'SQL\'\n'
        f"{APPLY_KEYBOARD_SQL}"
        "SQL"
    )

    try:
        result = container.exec_run(["sh", "-c", command], environment={"REMOTE_KEYBOARD_LAYOUT": layout})
    except DockerException as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update Guacamole") from exc

    output = result.output.decode("utf-8", errors="replace")
    if result.exit_code != 0:
        detail = _last_output_line(output) or "Unable to apply keyboard layout to Guacamole"
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

    try:
        updated_connections = int(_last_output_line(output))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Guacamole returned an unexpected keyboard update result",
        ) from exc

    if updated_connections == 0:
        message = "No Guacamole RDP connections were found to update"
    else:
        message = f"Applied {layout} to {updated_connections} Guacamole RDP connection(s); reconnect open sessions"

    return RemoteInputApplyResult(
        success=updated_connections > 0,
        keyboard_layout=layout,
        updated_connections=updated_connections,
        message=message,
    )
