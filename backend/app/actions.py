from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from .docker_control import control_container
from .models import ActionRunResult, ActionSummary


OUTPUT_LIMIT = 4000


def list_actions(action_defs: list[dict[str, Any]]) -> list[ActionSummary]:
    summaries: list[ActionSummary] = []
    for item in action_defs:
        if not isinstance(item, dict):
            continue
        action_id = str(item.get("id", "")).strip()
        name = str(item.get("name", action_id)).strip() or action_id
        action_type = str(item.get("type", "script")).strip()
        if not action_id:
            continue
        summaries.append(
            ActionSummary(
                id=action_id,
                name=name,
                description=item.get("description"),
                type=action_type,
                requires_confirmation=bool(item.get("requires_confirmation", False)),
                dangerous=bool(item.get("dangerous", False)),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return summaries


def _find_action(action_id: str, action_defs: list[dict[str, Any]]) -> dict[str, Any]:
    for item in action_defs:
        if isinstance(item, dict) and str(item.get("id", "")).strip() == action_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found")


def _require_confirmation(action: dict[str, Any], confirmed: bool) -> None:
    if bool(action.get("requires_confirmation", False)) or bool(action.get("dangerous", False)):
        if not confirmed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmation required")


def _run_script(action_id: str, action: dict[str, Any]) -> ActionRunResult:
    command = action.get("command", [])
    if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid script command")

    executable = Path(command[0])
    scripts_root = Path("/scripts").resolve()
    try:
        executable.resolve().relative_to(scripts_root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Script must be mounted from /scripts") from exc

    if not executable.is_absolute():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Script must be mounted from /scripts")

    timeout = int(action.get("timeout_seconds", 30))
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            shell=False,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found") from exc
    except subprocess.TimeoutExpired as exc:
        return ActionRunResult(id=action_id, success=False, message="Action timed out", output=str(exc))

    output = (completed.stdout + completed.stderr).strip()
    if len(output) > OUTPUT_LIMIT:
        output = output[:OUTPUT_LIMIT] + "\n... output truncated ..."

    return ActionRunResult(
        id=action_id,
        success=completed.returncode == 0,
        message="Action completed" if completed.returncode == 0 else "Action failed",
        exit_code=completed.returncode,
        output=output,
    )


def _run_docker_restart(action_id: str, action: dict[str, Any], allowed_containers: list[str]) -> ActionRunResult:
    containers = action.get("containers", [])
    if not isinstance(containers, list) or not all(isinstance(name, str) for name in containers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid container list")
    if not containers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No containers configured")

    restarted: list[str] = []
    for container in containers:
        control_container(container, "restart", allowed_containers)
        restarted.append(container)

    return ActionRunResult(
        id=action_id,
        success=True,
        message=f"Restarted {len(restarted)} container(s)",
        output="\n".join(restarted),
    )


def run_action(
    action_id: str,
    action_defs: list[dict[str, Any]],
    allowed_containers: list[str],
    confirmed: bool,
) -> ActionRunResult:
    action = _find_action(action_id, action_defs)
    if not bool(action.get("enabled", True)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action is disabled")

    _require_confirmation(action, confirmed)

    action_type = str(action.get("type", "script")).strip()
    if action_type == "script":
        return _run_script(action_id, action)
    if action_type == "docker_restart":
        return _run_docker_restart(action_id, action, allowed_containers)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action type")
