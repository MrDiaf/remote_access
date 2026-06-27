from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LinkConfig(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=500)


class RemoteInputSettings(BaseModel):
    local_keyboard_layout: str = Field(default="auto", min_length=1, max_length=40)
    remote_keyboard_layout: str = Field(default="en-us-qwerty", min_length=1, max_length=40)
    capture_release_shortcut: str = Field(default="escape", min_length=1, max_length=40)


class RemoteInputApplyResult(BaseModel):
    success: bool
    keyboard_layout: str
    updated_connections: int
    message: str


class DashboardSettings(BaseModel):
    server_name: str
    links: dict[str, LinkConfig]
    allowed_containers: list[str]
    remote_input: RemoteInputSettings


class RemoteDesktopConfig(BaseModel):
    protocol: str
    guacamole_url: str
    rdp_host: str
    rdp_port: int
    vnc_host: str | None = None
    vnc_port: int | None = None


class DashboardSettingsUpdate(BaseModel):
    server_name: str | None = Field(default=None, min_length=1, max_length=80)
    links: dict[str, LinkConfig] | None = None
    allowed_containers: list[str] | None = None
    remote_input: RemoteInputSettings | None = None


class HealthResponse(BaseModel):
    ok: bool
    service: str
    auth: str


class MemoryStats(BaseModel):
    total: int
    used: int
    percent: float


class DiskStats(BaseModel):
    mount: str
    total: int
    used: int
    free: int
    percent: float


class NetworkAddress(BaseModel):
    interface: str
    address: str


class NetworkStats(BaseModel):
    hostname: str
    addresses: list[NetworkAddress]
    bytes_sent: int
    bytes_recv: int


class SystemInfo(BaseModel):
    server_name: str
    online: bool
    cpu_percent: float
    memory: MemoryStats
    disk: DiskStats
    uptime_seconds: int
    load_average: list[float]
    network: NetworkStats


class DockerContainerInfo(BaseModel):
    name: str
    image: str
    status: str
    state: str
    created: str | None = None
    ports: dict[str, Any]
    can_manage: bool


class ServiceStatus(BaseModel):
    id: str
    name: str
    kind: str
    status: Literal["online", "offline", "unknown"]
    detail: str | None = None
    optional: bool = False


class RemoteDesktopStatus(BaseModel):
    protocol: str
    guacamole_url: str
    rdp_host: str
    rdp_port: int
    rdp_reachable: bool
    rdp_detail: str | None = None
    guacamole_container: str
    guacd_container: str
    database_container: str
    connection_hint: str


class ActionSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    type: str
    requires_confirmation: bool
    dangerous: bool = False
    enabled: bool


class ActionRunRequest(BaseModel):
    confirmed: bool = False


class ActionRunResult(BaseModel):
    id: str
    success: bool
    message: str
    exit_code: int | None = None
    output: str | None = None
