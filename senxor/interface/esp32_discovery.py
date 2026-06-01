# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

SERVICE_TYPE = "_senxor._tcp.local."
DEFAULT_DISCOVER_TIMEOUT = 2.0


@dataclass(frozen=True)
class Esp32DiscoveredDevice:
    service_name: str
    server: str
    ip: str
    port: int


def discover_esp32_devices(*, timeout: float = DEFAULT_DISCOVER_TIMEOUT) -> list[Esp32DiscoveredDevice]:
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf  # noqa: PLC0415
    except ImportError as exc:
        msg = (
            "zeroconf is required for ESP32 device discovery. "
            "Install it with `pip install 'pysenxor-lite[tcpip]'` or `pip install zeroconf`."
        )
        raise ImportError(msg) from exc

    class _SenXorListener(ServiceListener):
        def __init__(self) -> None:
            self.devices: list[Esp32DiscoveredDevice] = []

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name, timeout=3000)
            if not info or not info.server or info.port is None:
                return
            addrs = [socket.inet_ntoa(a) for a in info.addresses if len(a) == 4]
            if not addrs:
                return
            self.devices.append(
                Esp32DiscoveredDevice(
                    service_name=name.rstrip("."),
                    server=info.server.rstrip("."),
                    ip=addrs[0],
                    port=info.port,
                ),
            )

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            pass

    zc = Zeroconf()
    listener = _SenXorListener()
    ServiceBrowser(zc, SERVICE_TYPE, listener)
    time.sleep(timeout)
    zc.close()
    return listener.devices
