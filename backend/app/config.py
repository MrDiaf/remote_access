from __future__ import annotations

import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .models import DashboardSettings, DashboardSettingsUpdate, LinkConfig, RemoteDesktopConfig


CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "config"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))
SETTINGS_OVERRIDE = DATA_DIR / "settings.override.yml"
CONTAINER_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def _read_yaml(primary_name: str, fallback_name: str) -> dict[str, Any]:
    primary = CONFIG_DIR / primary_name
    fallback = CONFIG_DIR / fallback_name
    path = primary if primary.exists() else fallback
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _read_settings_override() -> dict[str, Any]:
    if not SETTINGS_OVERRIDE.exists():
        return {}
    with SETTINGS_OVERRIDE.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}


def _sanitize_container_names(names: list[str]) -> list[str]:
    clean: list[str] = []
    for name in names:
        trimmed = name.strip()
        if trimmed and CONTAINER_NAME_RE.match(trimmed) and trimmed not in clean:
            clean.append(trimmed)
    return clean


def load_dashboard_settings() -> DashboardSettings:
    base = _read_yaml("settings.yml", "settings.example.yml")
    merged = _deep_merge(base, _read_settings_override())

    server_name = str(merged.get("server", {}).get("name", "Home Server")).strip() or "Home Server"

    links_raw = merged.get("links", {})
    links: dict[str, LinkConfig] = {}
    if isinstance(links_raw, dict):
        for key, value in links_raw.items():
            if not isinstance(value, dict):
                continue
            label = str(value.get("label", key)).strip() or key
            url = str(value.get("url", "")).strip()
            if url:
                links[str(key)] = LinkConfig(label=label, url=url)

    allowed_raw = merged.get("docker", {}).get("allowed_containers", [])
    allowed = _sanitize_container_names(allowed_raw if isinstance(allowed_raw, list) else [])

    return DashboardSettings(
        server_name=server_name,
        links=links,
        allowed_containers=allowed,
    )


def load_remote_desktop_config() -> RemoteDesktopConfig:
    base = _read_yaml("settings.yml", "settings.example.yml")
    merged = _deep_merge(base, _read_settings_override())

    remote = merged.get("remote_desktop", {})
    if not isinstance(remote, dict):
        remote = {}

    links = merged.get("links", {})
    guacamole_link = ""
    if isinstance(links, dict) and isinstance(links.get("guacamole"), dict):
        guacamole_link = str(links["guacamole"].get("url", "")).strip()

    protocol = str(remote.get("protocol", "RDP")).strip().upper() or "RDP"
    guacamole_url = str(remote.get("guacamole_url", guacamole_link or "/guacamole/")).strip() or "/guacamole/"
    rdp_host = str(remote.get("rdp_host", "host.docker.internal")).strip() or "host.docker.internal"
    rdp_port = int(remote.get("rdp_port", 3389))

    vnc_host_raw = remote.get("vnc_host")
    vnc_port_raw = remote.get("vnc_port")

    return RemoteDesktopConfig(
        protocol=protocol,
        guacamole_url=guacamole_url,
        rdp_host=rdp_host,
        rdp_port=rdp_port,
        vnc_host=str(vnc_host_raw).strip() if vnc_host_raw else None,
        vnc_port=int(vnc_port_raw) if vnc_port_raw else None,
    )


def save_dashboard_settings(update: DashboardSettingsUpdate) -> DashboardSettings:
    current = load_dashboard_settings()
    next_settings = {
        "server": {"name": current.server_name},
        "links": {key: value.model_dump() for key, value in current.links.items()},
        "docker": {"allowed_containers": current.allowed_containers},
    }

    if update.server_name is not None:
        next_settings["server"]["name"] = update.server_name.strip()

    if update.links is not None:
        next_settings["links"] = {
            key.strip(): value.model_dump()
            for key, value in update.links.items()
            if key.strip() and value.url.strip()
        }

    if update.allowed_containers is not None:
        next_settings["docker"]["allowed_containers"] = _sanitize_container_names(update.allowed_containers)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_OVERRIDE.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(next_settings, handle, sort_keys=True)

    return load_dashboard_settings()


def load_services_config() -> list[dict[str, Any]]:
    raw = _read_yaml("services.yml", "services.example.yml")
    services = raw.get("services", [])
    return services if isinstance(services, list) else []


def load_actions_config() -> list[dict[str, Any]]:
    raw = _read_yaml("actions.yml", "actions.example.yml")
    actions = raw.get("actions", [])
    return actions if isinstance(actions, list) else []
