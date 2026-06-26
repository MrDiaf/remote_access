from __future__ import annotations

from typing import Any

import docker
from docker.errors import DockerException, NotFound
from fastapi import HTTPException, status

from .models import DockerContainerInfo


def get_client() -> docker.DockerClient:
    try:
        return docker.from_env(timeout=4)
    except DockerException as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Docker is unavailable") from exc


def docker_available() -> bool:
    try:
        client = get_client()
        client.ping()
        return True
    except Exception:
        return False


def _container_info(container: Any, allowed: set[str]) -> DockerContainerInfo:
    attrs = container.attrs
    config = attrs.get("Config", {})
    state = attrs.get("State", {})
    image = config.get("Image") or ", ".join(container.image.tags) or container.short_id
    return DockerContainerInfo(
        name=container.name,
        image=image,
        status=container.status,
        state=state.get("Status", container.status),
        created=attrs.get("Created"),
        ports=attrs.get("NetworkSettings", {}).get("Ports", {}) or {},
        can_manage=container.name in allowed,
    )


def list_containers(allowed_containers: list[str]) -> list[DockerContainerInfo]:
    allowed = set(allowed_containers)
    client = get_client()
    try:
        containers = client.containers.list(all=True)
    except DockerException as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Unable to list containers") from exc
    return sorted((_container_info(container, allowed) for container in containers), key=lambda item: item.name)


def get_container_state(name: str) -> str:
    client = get_client()
    try:
        container = client.containers.get(name)
        container.reload()
        return str(container.attrs.get("State", {}).get("Status", container.status))
    except NotFound:
        return "not_found"
    except DockerException:
        return "unknown"


def control_container(name: str, action: str, allowed_containers: list[str]) -> DockerContainerInfo:
    if name not in set(allowed_containers):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Container is not allowlisted")

    client = get_client()
    try:
        container = client.containers.get(name)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found") from exc

    try:
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop(timeout=10)
        elif action == "restart":
            container.restart(timeout=10)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action")
        container.reload()
    except DockerException as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Docker action failed: {exc}") from exc

    return _container_info(container, set(allowed_containers))

