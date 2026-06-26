from __future__ import annotations

from fastapi import Depends, FastAPI, Response

from .actions import list_actions, run_action
from .auth import authenticate, clear_session, create_session, require_user
from .config import (
    load_actions_config,
    load_dashboard_settings,
    load_services_config,
    save_dashboard_settings,
)
from .docker_control import control_container, list_containers
from .models import (
    ActionRunRequest,
    ActionRunResult,
    ActionSummary,
    AuthUser,
    DashboardSettings,
    DashboardSettingsUpdate,
    DockerContainerInfo,
    HealthResponse,
    LoginRequest,
    ServiceStatus,
    SystemInfo,
)
from .services import list_service_status
from .system_info import get_system_info


app = FastAPI(title="server-control-panel API", version="0.1.0")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, service="server-control-panel", auth="session-cookie")


@app.post("/api/auth/login", response_model=AuthUser)
def login(credentials: LoginRequest, response: Response) -> AuthUser:
    if not authenticate(credentials):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return create_session(response, credentials.username)


@app.post("/api/auth/logout")
def logout(response: Response, _user: AuthUser = Depends(require_user)) -> dict[str, bool]:
    clear_session(response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=AuthUser)
def me(user: AuthUser = Depends(require_user)) -> AuthUser:
    return user


@app.get("/api/settings", response_model=DashboardSettings)
def get_settings(_user: AuthUser = Depends(require_user)) -> DashboardSettings:
    return load_dashboard_settings()


@app.put("/api/settings", response_model=DashboardSettings)
def update_settings(update: DashboardSettingsUpdate, _user: AuthUser = Depends(require_user)) -> DashboardSettings:
    return save_dashboard_settings(update)


@app.get("/api/system", response_model=SystemInfo)
def system(_user: AuthUser = Depends(require_user)) -> SystemInfo:
    settings = load_dashboard_settings()
    return get_system_info(settings.server_name)


@app.get("/api/docker/containers", response_model=list[DockerContainerInfo])
def docker_containers(_user: AuthUser = Depends(require_user)) -> list[DockerContainerInfo]:
    settings = load_dashboard_settings()
    return list_containers(settings.allowed_containers)


@app.post("/api/docker/containers/{name}/start", response_model=DockerContainerInfo)
def start_container(name: str, _user: AuthUser = Depends(require_user)) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "start", settings.allowed_containers)


@app.post("/api/docker/containers/{name}/stop", response_model=DockerContainerInfo)
def stop_container(name: str, _user: AuthUser = Depends(require_user)) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "stop", settings.allowed_containers)


@app.post("/api/docker/containers/{name}/restart", response_model=DockerContainerInfo)
def restart_container(name: str, _user: AuthUser = Depends(require_user)) -> DockerContainerInfo:
    settings = load_dashboard_settings()
    return control_container(name, "restart", settings.allowed_containers)


@app.get("/api/services", response_model=list[ServiceStatus])
def services(_user: AuthUser = Depends(require_user)) -> list[ServiceStatus]:
    return list_service_status(load_services_config())


@app.get("/api/actions", response_model=list[ActionSummary])
def actions(_user: AuthUser = Depends(require_user)) -> list[ActionSummary]:
    return list_actions(load_actions_config())


@app.post("/api/actions/{action_id}/run", response_model=ActionRunResult)
def run_named_action(
    action_id: str,
    request: ActionRunRequest,
    _user: AuthUser = Depends(require_user),
) -> ActionRunResult:
    settings = load_dashboard_settings()
    return run_action(action_id, load_actions_config(), settings.allowed_containers, request.confirmed)

