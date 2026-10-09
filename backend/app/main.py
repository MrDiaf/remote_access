from __future__ import annotations

from fastapi import FastAPI, HTTPException, status

from .actions import list_actions, run_action
from .config import (
    load_actions_config,
    load_dashboard_settings,
    load_remote_desktop_config,
    load_services_config,
    save_dashboard_settings,
)
from .disk_usage import scan as scan_disk_usage
from .docker_control import control_container, list_containers
from .guacamole_input import apply_guacamole_input_settings
from .models import (
    ActionRunRequest,
    ActionRunResult,
    ActionSummary,
    DashboardSettings,
    DashboardSettingsUpdate,
    DiskUsageResult,
    DockerContainerInfo,
    HealthResponse,
    RemoteInputApplyResult,
    RemoteDesktopStatus,
    ServiceStatus,
    SteamStatus,
    SystemInfo,
)
from .remote_status import get_remote_desktop_status
from .services import list_service_status
from .steam_control import control_steam, get_steam_status
from .system_info import get_system_info


app = FastAPI(title="server-control-panel API", version="0.1.0")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="server-control-panel", auth="none-lan-vpn")


@app.get("/api/settings", response_model=DashboardSettings)
def get_settings() -> DashboardSettings:
    return load_dashboard_settings()


@app.put("/api/settings", response_model=DashboardSettings)
def update_settings(update: DashboardSettingsUpdate) -> DashboardSettings:
    return save_dashboard_settings(update)


@app.get("/api/system", response_model=SystemInfo)
def system() -> SystemInfo:
    settings = load_dashboard_settings()
    return get_system_info(settings.server_name)


@app.get("/api/disk-usage", response_model=DiskUsageResult)
def disk_usage(path: str = "/", refresh: bool = False) -> DiskUsageResult:
    return scan_disk_usage(path, refresh)


@app.get("/api/docker/containers", response_model=list[DockerContainerInfo])
def docker_containers() -> list[DockerContainerInfo]:
    settings = load_dashboard_settings()
    return list_containers(settings.allowed_containers)


@app.post("/api/docker/containers/{name}/start", response_model=DockerContainerInfo)
def start_container(name: str) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "start", settings.allowed_containers)


@app.post("/api/docker/containers/{name}/stop", response_model=DockerContainerInfo)
def stop_container(name: str) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "stop", settings.allowed_containers)


@app.post("/api/docker/containers/{name}/restart", response_model=DockerContainerInfo)
def restart_container(name: str) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "restart", settings.allowed_containers)


@app.get("/api/services", response_model=list[ServiceStatus])
def services() -> list[ServiceStatus]:
    return list_service_status(load_services_config())


@app.get("/api/remote/status", response_model=RemoteDesktopStatus)
def remote_status() -> RemoteDesktopStatus:
    return get_remote_desktop_status(load_remote_desktop_config())


@app.post("/api/remote/input/apply", response_model=RemoteInputApplyResult)
def apply_remote_input() -> RemoteInputApplyResult:
    settings = load_dashboard_settings()
    return apply_guacamole_input_settings(settings.remote_input)


@app.get("/api/actions", response_model=list[ActionSummary])
def actions() -> list[ActionSummary]:
    return list_actions(load_actions_config())


@app.post("/api/actions/{action_id}/run", response_model=ActionRunResult)
def run_named_action(
    action_id: str,
    request: ActionRunRequest,
) -> ActionRunResult:
    settings = load_dashboard_settings()
    return run_action(action_id, load_actions_config(), settings.allowed_containers, request.confirmed)


@app.get("/api/steam", response_model=SteamStatus)
def steam_status() -> SteamStatus:
    return get_steam_status()


@app.post("/api/steam/start", response_model=SteamStatus)
def start_steam() -> SteamStatus:
    return control_steam("start")


@app.post("/api/steam/bigpicture", response_model=SteamStatus)
def steam_big_picture() -> SteamStatus:
    # Starts Steam in Big Picture, or switches a running Steam to it.
    return control_steam("bigpicture")


@app.post("/api/steam/stop", response_model=SteamStatus)
def stop_steam(request: ActionRunRequest) -> SteamStatus:
    # Quitting Steam can interrupt a running game.
    if not request.confirmed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmation required")
    return control_steam("stop")
