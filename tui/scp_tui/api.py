"""Blocking client for the server-control-panel backend API.

Mirrors frontend/src/api/client.ts. The app calls it from worker threads.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Api:
    def __init__(self, base_url: str, timeout: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Any = None, timeout: float | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            message = exc.reason or f"HTTP {exc.code}"
            try:
                detail = json.loads(exc.read()).get("detail")
                if detail:
                    message = detail if isinstance(detail, str) else json.dumps(detail)
            except (ValueError, AttributeError):
                pass
            raise ApiError(exc.code, str(message)) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ApiError(0, f"Cannot reach {self.base_url}: {reason}") from exc
        return json.loads(raw) if raw else None

    def settings(self) -> dict:
        return self._request("GET", "/api/settings")

    def update_settings(self, settings: dict) -> dict:
        body = {key: settings[key] for key in ("server_name", "links", "allowed_containers", "remote_input")}
        return self._request("PUT", "/api/settings", body)

    def system(self) -> dict:
        return self._request("GET", "/api/system")

    def disk_usage(self, path: str, refresh: bool = False) -> dict:
        query = urllib.parse.urlencode({"path": path, **({"refresh": "true"} if refresh else {})})
        # Large folders can take minutes; the backend gives up after 5.
        return self._request("GET", f"/api/disk-usage?{query}", timeout=330)

    def containers(self) -> list[dict]:
        return self._request("GET", "/api/docker/containers")

    def container_action(self, name: str, action: str) -> dict:
        return self._request("POST", f"/api/docker/containers/{urllib.parse.quote(name, safe='')}/{action}")

    def services(self) -> list[dict]:
        return self._request("GET", "/api/services")

    def remote_status(self) -> dict:
        return self._request("GET", "/api/remote/status")

    def apply_remote_input(self) -> dict:
        return self._request("POST", "/api/remote/input/apply")

    def actions(self) -> list[dict]:
        return self._request("GET", "/api/actions")

    def run_action(self, action_id: str, confirmed: bool) -> dict:
        return self._request(
            "POST",
            f"/api/actions/{urllib.parse.quote(action_id, safe='')}/run",
            {"confirmed": confirmed},
            timeout=120,
        )
