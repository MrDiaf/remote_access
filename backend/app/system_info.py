from __future__ import annotations

import os
import socket
import time

import psutil

from .models import DiskStats, MemoryStats, NetworkAddress, NetworkStats, SystemInfo


def get_system_info(server_name: str) -> SystemInfo:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
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
        disk=DiskStats(mount="/", total=disk.total, used=disk.used, free=disk.free, percent=disk.percent),
        uptime_seconds=int(time.time() - psutil.boot_time()),
        load_average=load_average,
        network=NetworkStats(
            hostname=socket.gethostname(),
            addresses=addresses,
            bytes_sent=net.bytes_sent,
            bytes_recv=net.bytes_recv,
        ),
    )

