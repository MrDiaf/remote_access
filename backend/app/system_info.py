from __future__ import annotations

import os
import socket
import time
from pathlib import Path

import psutil

from .models import DiskStats, MemoryStats, NetworkAddress, NetworkStats, SystemInfo


def _disk_stats(name: str, mount: str) -> DiskStats:
    usage = psutil.disk_usage(mount)
    return DiskStats(
        name=name,
        mount=mount,
        total=usage.total,
        used=usage.used,
        free=usage.free,
        percent=usage.percent,
    )


def _mounted_media_disks(root: str) -> list[DiskStats]:
    if not root:
        return []

    media_root = Path(root)
    try:
        owner_directories = sorted(
            (entry for entry in media_root.iterdir() if entry.is_dir()),
            key=lambda entry: entry.name.casefold(),
        )
    except OSError:
        return []

    disks: list[DiskStats] = []
    for owner_directory in owner_directories:
        try:
            candidates = sorted(
                (entry for entry in owner_directory.iterdir() if entry.is_dir()),
                key=lambda entry: entry.name.casefold(),
            )
        except OSError:
            continue

        for candidate in candidates:
            try:
                if candidate.is_mount():
                    disks.append(_disk_stats(candidate.name, str(candidate)))
            except OSError:
                continue

    return disks


def get_system_info(server_name: str) -> SystemInfo:
    memory = psutil.virtual_memory()
    main_disk = _disk_stats("Main drive", "/")
    disks = [main_disk, *_mounted_media_disks(os.environ.get("HOST_MEDIA_ROOT", ""))]
    net = psutil.net_io_counters()

    addresses: list[NetworkAddress] = []
    for interface, values in psutil.net_if_addrs().items():
        for value in values:
            if value.family == socket.AF_INET and not value.address.startswith("127."):
                addresses.append(NetworkAddress(interface=interface, address=value.address))

    try:
        load_average = [round(value, 2) for value in os.getloadavg()]
    except OSError:
        load_average = []

    return SystemInfo(
        server_name=server_name,
        online=True,
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory=MemoryStats(total=memory.total, used=memory.used, percent=memory.percent),
        disk=main_disk,
        disks=disks,
        uptime_seconds=int(time.time() - psutil.boot_time()),
        load_average=load_average,
        network=NetworkStats(
            hostname=socket.gethostname(),
            addresses=addresses,
            bytes_sent=net.bytes_sent,
            bytes_recv=net.bytes_recv,
        ),
    )
