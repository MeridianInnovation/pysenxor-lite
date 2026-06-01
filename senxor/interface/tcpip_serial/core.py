# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import contextlib
import socket
from typing import cast

from senxor.error import SenxorLostConnectionError, SenxorNotConnectedError
from senxor.interface.esp32_discovery import discover_esp32_devices
from senxor.interface.protocol import IDevice
from senxor.interface.serial_port.base import SerialInterfaceBase, SerialTransportBase

_RECV_SIZE = 4096
_READ_TIMEOUT = 3.0


class TCPIPPort(IDevice):
    INTERFACE_TYPE = "tcpip_serial"

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    @property
    def name(self) -> str:
        return f"{self.host}:{self.port}"

    def __repr__(self) -> str:
        return f"TCPIPPort(host={self.host!r}, port={self.port})"

    def __str__(self) -> str:
        return f"TCPIPPort {self.name}"


class TCPIPTransport(SerialTransportBase):
    def __init__(self, device: TCPIPPort):
        super().__init__(device)
        self._sock: socket.socket | None = None

    @property
    def is_open(self) -> bool:
        return self._sock is not None

    def open(self) -> None:
        if self._sock is not None:
            return
        device = cast("TCPIPPort", self.device)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(_READ_TIMEOUT)
            sock.connect((device.host, device.port))
        except OSError as e:
            raise RuntimeError(f"Failed to connect to {device.name}") from e
        self._sock = sock

    def close(self) -> None:
        if self._sock is None:
            return
        with contextlib.suppress(OSError):
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        self._sock = None

    def cancel_read(self) -> None:
        if self._sock is None:
            return
        with contextlib.suppress(OSError):
            self._sock.shutdown(socket.SHUT_RD)

    def read(self) -> bytes:
        sock = self._sock
        if sock is None:
            raise SenxorNotConnectedError
        try:
            data = sock.recv(_RECV_SIZE)
        except TimeoutError:
            return b""
        except OSError as e:
            raise self._map_os_error(e) from e
        if data == b"":
            raise SenxorLostConnectionError
        return data

    def write(self, data: bytes) -> None:
        sock = self._sock
        if sock is None:
            raise SenxorNotConnectedError
        try:
            sock.sendall(data)
        except OSError as e:
            raise self._map_os_error(e) from e

    @staticmethod
    def _map_os_error(error: OSError) -> Exception:
        if isinstance(error, ConnectionResetError | BrokenPipeError):
            return SenxorLostConnectionError()
        return SenxorLostConnectionError()


class TCPIPInterface(SerialInterfaceBase):
    TRANSPORT_CLASS = TCPIPTransport

    def __init__(self, device: TCPIPPort):
        super().__init__(device)

    @property
    def device(self) -> TCPIPPort:
        return cast("TCPIPPort", self._device)

    @classmethod
    def list_devices(cls) -> list[TCPIPPort]:
        return [TCPIPPort(d.server, d.port) for d in discover_esp32_devices()]
