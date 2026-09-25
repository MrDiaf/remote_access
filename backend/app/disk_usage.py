from __future__ import annotations

import os
import posixpath
import subprocess
import threading
import time
from pathlib import Path

from fastapi import HTTPException, status

from .models import DiskUsageEntry, DiskUsageResult


# The host filesystem is bind-mounted read-only here. Paths in the API are host
# paths ("/var/lib/docker"), translated to "<HOST_ROOT>/var/lib/docker".
HOST_ROOT = Path(os.environ.get("HOST_ROOT", "/host-root"))
CACHE_SECONDS = 600
SCAN_TIMEOUT_SECONDS = 300
MAX_ENTRIES = 200
# Kernel pseudo filesystems: sizes are meaningless and scanning them is slow.
BLOCKED_PATHS = {"/proc", "/sys"}

_cache: dict[str, DiskUsageResult] = {}
# One scan at a time keeps du from hammering the disks when several browser
# tabs ask at once; a waiting request for the same folder then hits the cache.
_scan_lock = threading.Lock()


def normalize_host_path(path: str) -> str:
    if not path.startswith("/") or "\0" in path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path must be absolute")
    normalized = posixpath.normpath(path)
    # normpath keeps a leading "//"; POSIX treats it as "/".
    return "/" + normalized.lstrip("/")


def _container_path(host_path: str) -> Path:
    root = HOST_ROOT.resolve()
    if not root.is_dir():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Host filesystem is not mounted in the backend container",
        )
    target = (root / host_path.lstrip("/")).resolve()
    # Absolute symlinks on the host resolve against the container's root, so
    # anything that lands outside the mount is refused rather than followed.
    if target != root and root not in target.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is a link outside the host filesystem")
    if not target.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return target


def _host_path_of(container_path: str) -> str:
    relative = os.path.relpath(container_path, HOST_ROOT.resolve())
    return "/" if relative == "." else "/" + relative


def _mount_used_bytes(path: str) -> int:
    try:
        stats = os.statvfs(path)
    except OSError:
        return 0
    return (stats.f_blocks - stats.f_bfree) * stats.f_frsize


def _run_du(target: Path) -> tuple[dict[str, int], bool]:
    """Return allocated bytes for target and each direct child on the same filesystem."""
    try:
        result = subprocess.run(
            ["du", "--one-file-system", "--all", "--max-depth=1", "--block-size=1", "--null", "--", str(target)],
            capture_output=True,
            timeout=SCAN_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Scan took longer than {SCAN_TIMEOUT_SECONDS} seconds. Open a smaller folder.",
        ) from exc

    sizes: dict[str, int] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        size, _, path = record.partition(b"\t")
        try:
            sizes[os.fsdecode(path)] = int(size)
        except ValueError:
            continue
    # du exits 1 when some entries were unreadable but still prints the rest.
    return sizes, result.returncode == 0


def scan(path: str, refresh: bool = False) -> DiskUsageResult:
    host_path = normalize_host_path(path)
    if host_path in BLOCKED_PATHS or any(host_path.startswith(blocked + "/") for blocked in BLOCKED_PATHS):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kernel pseudo filesystems are not scanned")

    cached = _cache.get(host_path)
    if cached and not refresh and time.time() - cached.scanned_at < CACHE_SECONDS:
        return cached

    target = _container_path(host_path)
    with _scan_lock:
        cached = _cache.get(host_path)
        if cached and not refresh and time.time() - cached.scanned_at < CACHE_SECONDS:
            return cached

        sizes, complete = _run_du(target)
        target_key = str(target)
        entries: list[DiskUsageEntry] = []
        for child_path, size in sizes.items():
            if child_path == target_key:
                continue
            entry_path = Path(child_path)
            entries.append(
                DiskUsageEntry(
                    name=entry_path.name,
                    path=_host_path_of(child_path),
                    size=size,
                    is_dir=entry_path.is_dir() and not entry_path.is_symlink(),
                )
            )

        # du --one-file-system skips other drives mounted below this folder.
        # List them with their used space so they can be opened separately.
        target_device = target.stat().st_dev
        try:
            children = list(os.scandir(target))
        except OSError:
            children = []
        for child in children:
            try:
                if not child.is_dir(follow_symlinks=False) or child.stat(follow_symlinks=False).st_dev == target_device:
                    continue
            except OSError:
                continue
            child_host_path = _host_path_of(child.path)
            if child_host_path in BLOCKED_PATHS:
                continue
            entries.append(
                DiskUsageEntry(
                    name=child.name,
                    path=child_host_path,
                    size=_mount_used_bytes(child.path),
                    is_dir=True,
                    is_mount=True,
                )
            )

        entries.sort(key=lambda entry: entry.size, reverse=True)
        hidden = entries[MAX_ENTRIES:]
        result = DiskUsageResult(
            path=host_path,
            parent=None if host_path == "/" else posixpath.dirname(host_path),
            size=sizes.get(target_key, 0),
            entries=entries[:MAX_ENTRIES],
            hidden_entries=len(hidden),
            hidden_size=sum(entry.size for entry in hidden),
            scanned_at=time.time(),
            complete=complete,
        )
        _cache[host_path] = result
        return result
