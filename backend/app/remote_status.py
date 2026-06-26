from __future__ import annotations

import socket

from .docker_control import get_container_state
from .models import RemoteDesktopConfig, RemoteDesktopStatus


def _check_tcp(host: str, port: int) -> tuple[bool, str | None]:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True, f"{host}:{port} reachable"
    except OSError as exc:
        return False, str(exc)


def get_remote_desktop_status(config: RemoteDesktopConfig) -> RemoteDesktopStatus:
    rdp_reachable, rdp_detail = _check_tcp(config.rdp_host, config.rdp_port)
    return RemoteDesktopStatus(
        protocol=config.protocol,
        guacamole_url=config.guacamole_url,
        rdp_host=config.rdp_host,
        rdp_port=config.rdp_port,
        rdp_reachable=rdp_reachable,
        rdp_detail=rdp_detail,
        guacamole_container=get_container_state("scp-guacamole"),
        guacd_container=get_container_state("scp-guacd"),
        database_container=get_container_state("scp-guacamole-db"),
        connection_hint=f"{config.protocol} to {config.rdp_host}:{config.rdp_port}",
    )
