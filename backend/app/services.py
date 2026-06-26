from __future__ import annotations

import socket
import urllib.error
import urllib.request
from typing import Any

from .docker_control import docker_available, get_container_state
from .models import ServiceStatus


def _check_tcp(host: str, port: int) -> tuple[str, str | None]:
    try:
        with socket.create_connection((host, port), timeout=2):
            return "online", f"{host}:{port}"
    except OSError as exc:
        return "offline", str(exc)


def _check_http(url: str) -> tuple[str, str | None]:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return "online", f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code < 500:
            return "online", f"HTTP {exc.code}"
        return "offline", f"HTTP {exc.code}"
    except Exception as exc:
        return "offline", str(exc)


def list_service_status(service_defs: list[dict[str, Any]]) -> list[ServiceStatus]:
    statuses: list[ServiceStatus] = []

    for item in service_defs:
        if not isinstance(item, dict):
            continue

        service_id = str(item.get("id", "")).strip()
        name = str(item.get("name", service_id)).strip() or service_id
        kind = str(item.get("kind", "unknown")).strip()
        optional = bool(item.get("optional", False))

        if not service_id:
            continue

        status = "unknown"
        detail: str | None = None

        if kind == "docker_api":
            status = "online" if docker_available() else "offline"
        elif kind == "docker_container":
            container = str(item.get("container", "")).strip()
            state = get_container_state(container) if container else "unknown"
            status = "online" if state == "running" else "offline"
            detail = state
        elif kind == "tcp":
            host = str(item.get("host", "")).strip()
            port = int(item.get("port", 0))
            if host and port:
                status, detail = _check_tcp(host, port)
        elif kind == "http":
            url = str(item.get("url", "")).strip()
            if url:
                status, detail = _check_http(url)

        statuses.append(
            ServiceStatus(
                id=service_id,
                name=name,
                kind=kind,
                status=status,  # type: ignore[arg-type]
                detail=detail,
                optional=optional,
            )
        )

    return statuses

