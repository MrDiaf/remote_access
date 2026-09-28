from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import psutil

from .models import DiskStats, GpuStats, MemoryStats, NetworkAddress, NetworkStats, SystemInfo


def _disk_stats(name: str, mount: str, host_path: str | None) -> DiskStats:
    usage = psutil.disk_usage(mount)
    return DiskStats(
        name=name,
        mount=mount,
        host_path=host_path,
        total=usage.total,
        used=usage.used,
        free=usage.free,
        percent=usage.percent,
    )


def _directories(path: Path) -> list[Path]:
    try:
        return sorted(
            (entry for entry in path.iterdir() if entry.is_dir()),
            key=lambda entry: entry.name.casefold(),
        )
    except OSError:
        return []


def _mounted_media_disks(roots: str, host_roots: str) -> list[DiskStats]:
    """Find mounts one or two directories below each container-visible root.

    Ubuntu normally puts removable media at /run/media/<user>/<label>, while
    persistent data disks are commonly mounted at /mnt/<label>. The Compose
    service exposes both parent directories read-only. host_roots lists the
    matching host directories in the same order so the disk usage view can
    open each drive by its host path.
    """
    disks: list[DiskStats] = []
    seen_devices: set[int] = set()
    host_root_list = [value.strip() for value in host_roots.split(os.pathsep)] if host_roots else []

    for index, root in enumerate(value.strip() for value in roots.split(os.pathsep)):
        if not root:
            continue
        host_root = host_root_list[index] if index < len(host_root_list) else ""

        for entry in _directories(Path(root)):
            candidates = [entry]
            try:
                if not entry.is_mount():
                    candidates = _directories(entry)
            except OSError:
                continue

            for candidate in candidates:
                try:
                    if not candidate.is_mount():
                        continue
                    device = candidate.stat().st_dev
                    if device in seen_devices:
                        continue
                    seen_devices.add(device)
                    host_path = None
                    if host_root:
                        host_path = str(Path(host_root) / candidate.relative_to(root))
                    disks.append(_disk_stats(candidate.name, str(candidate), host_path))
                except OSError:
                    continue

    return disks


def _parse_nvidia_smi(output: str) -> list[GpuStats]:
    """Parse `nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total
    --format=csv,noheader,nounits`. Memory values are MiB."""
    gpus: list[GpuStats] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.rsplit(",", 3)]
        if len(parts) != 4:
            continue
        name, utilization, used_mib, total_mib = parts
        try:
            used = int(float(used_mib)) * 1024 * 1024
            total = int(float(total_mib)) * 1024 * 1024
            percent = float(utilization)
        except ValueError:
            # "[N/A]" on GPUs that do not report a value.
            continue
        gpus.append(
            GpuStats(
                name=name,
                percent=percent,
                memory=MemoryStats(total=total, used=used, percent=round(used / total * 100, 1) if total else 0.0),
            )
        )
    return gpus


def _gpu_stats() -> list[GpuStats]:
    """NVIDIA GPUs only. nvidia-smi exists in the container only when Compose
    grants the GPU (docker-compose.gpu.yml, added by the Makefile when Docker
    has the NVIDIA runtime). Without it the Status page shows no GPU card."""
    if not shutil.which("nvidia-smi"):
        return []
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return _parse_nvidia_smi(result.stdout)


def get_system_info(server_name: str) -> SystemInfo:
    memory = psutil.virtual_memory()
    main_disk = _disk_stats("Main drive", "/", "/")
    media_roots = os.environ.get("HOST_MEDIA_ROOTS", os.environ.get("HOST_MEDIA_ROOT", ""))
    host_media_roots = os.environ.get("HOST_MEDIA_HOST_ROOTS", "")
    disks = [main_disk, *_mounted_media_disks(media_roots, host_media_roots)]
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
        gpus=_gpu_stats(),
        uptime_seconds=int(time.time() - psutil.boot_time()),
        load_average=load_average,
        network=NetworkStats(
            hostname=socket.gethostname(),
            addresses=addresses,
            bytes_sent=net.bytes_sent,
            bytes_recv=net.bytes_recv,
        ),
    )
