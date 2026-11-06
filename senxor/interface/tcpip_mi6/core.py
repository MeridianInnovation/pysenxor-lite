# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""TCP/IP transport and frame reads for MI6 devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from senxor.error import SenxorLostConnectionError, SenxorNotConnectedError, SenxorResponseTimeoutError
from senxor.interface.serial_port.base import _op_wrapper
from senxor.interface.tcpip_mi6.processor import MI6AckProcessor
from senxor.interface.tcpip_serial.core import TCPIPInterface, TCPIPPort, TCPIPTransport

if TYPE_CHECKING:
    import threading
    from collections import deque

_RECV_SIZE = 65536


class TCPIPMI6Transport(TCPIPTransport):
    """TCP/IP transport for MI6 command replies and image streams."""

    def read(self) -> bytes:
        """Read available data from the TCP connection.

        Returns
        -------
        bytes
            Up to 65536 bytes from the connection.
            Returns empty bytes if the socket read times out.

        Raises
        ------
        SenxorNotConnectedError
            If the connection is not open.
        SenxorLostConnectionError
            If the connection is closed by the device or a socket error occurs.

        """
        sock = self._sock
        if sock is None:
            raise SenxorNotConnectedError
        try:
            data = sock.recv(_RECV_SIZE)
        except TimeoutError:
            return b""
        except OSError as error:
            raise self._map_os_error(error) from error
        if data == b"":
            raise SenxorLostConnectionError
        return data


class TCPIPMI6Interface(TCPIPInterface):
    """TCP/IP interface for MI6 devices.

    Attributes
    ----------
    transport : TCPIPMI6Transport
        The TCP/IP transport used to communicate with the device.
    processor : MI6AckProcessor
        The processor for command replies and thermal, RGB, and fusion frames.

    """

    TRANSPORT_CLASS = TCPIPMI6Transport

    def __init__(self, device: TCPIPPort, *, timeout: float = 3.0) -> None:
        """Initialize the MI6 interface.

        Parameters
        ----------
        device : TCPIPPort
            The hostname and TCP port of the MI6 device.
        timeout : float, optional
            The command reply timeout in seconds, by default 3.0.
            Frame read timeouts are supplied to the read methods separately.

        Raises
        ------
        ValueError
            If `timeout` is not greater than zero.

        """
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        super().__init__(device)
        self.processor = MI6AckProcessor(self.transport, self.logger)
        self._command_timeout = timeout

    @property
    def data_ready(self) -> bool:
        """Whether a thermal frame is available.

        Returns
        -------
        bool
            Whether the thermal frame queue contains a frame.

        """
        return bool(self.processor.gfra_queue)

    def hard_reset(self) -> None:
        """Reset the device through the interface.

        Raises
        ------
        NotImplementedError
            Hard reset is not supported by this interface.

        """
        raise NotImplementedError("Hard reset is not supported by the MI6 TCP interface")

    def open(self) -> None:
        """Open the connection and start the reply processor."""
        if self.is_connected:
            return
        self.processor.stop()
        super().open()

    def _wait_for_ack(
        self,
        cmd: str,
        queue: deque,
        ready: threading.Condition,
        timeout: float | None,
    ) -> Any:
        """Wait for a reply, applying the configured timeout to commands."""
        if cmd != "GFRA":
            timeout = self._command_timeout
        return super()._wait_for_ack(cmd, queue, ready, timeout)

    def _wait_for_image(
        self,
        cmd: str,
        queue: deque,
        ready: threading.Condition,
        timeout: float | None,
    ) -> Any:
        """Wait for an image without closing the connection on a read timeout."""
        try:
            return super()._wait_for_ack("GFRA", queue, ready, timeout)
        except SenxorResponseTimeoutError as error:
            raise SenxorResponseTimeoutError(f"Timeout waiting for {cmd} response") from error

    @_op_wrapper
    def read_rgb(self, timeout: float | None = None) -> bytes | None:
        """Read the latest RGB frame payload.

        Parameters
        ----------
        timeout : float | None, optional
            The maximum time to wait in seconds. None waits until a frame
            is available. Zero returns immediately, by default None.

        Returns
        -------
        bytes | None
            The raw GRGB payload in NV12 format, with resolution 640x360.
            Returns None if `timeout=0` and no frame is available.

        Raises
        ------
        SenxorResponseTimeoutError
            If no frame arrives before the timeout expires.
        SenxorNotConnectedError
            If the device is not connected.

        """
        if self.processor.rgb_queue:
            return self.processor.rgb_queue.popleft()
        if timeout == 0:
            return None
        return self._wait_for_image("GRGB", self.processor.rgb_queue, self.processor.rgb_ready, timeout)

    @_op_wrapper
    def read_fusion(self, timeout: float | None = None) -> tuple[str, bytes] | None:
        """Read the latest fusion frame tag and payload.

        Parameters
        ----------
        timeout : float | None, optional
            The maximum time to wait in seconds. None waits until a frame
            is available. Zero returns immediately, by default None.

        Returns
        -------
        tuple[str, bytes] | None
            The message tag and raw payload. GFUC contains a 480x360 NV12
            image; GFUS contains 480x360 uint8 palette indices.
            Returns None if `timeout=0` and no frame is available.

        Raises
        ------
        SenxorResponseTimeoutError
            If no frame arrives before the timeout expires.
        SenxorNotConnectedError
            If the device is not connected.

        """
        if self.processor.fusion_queue:
            return self.processor.fusion_queue.popleft()
        if timeout == 0:
            return None
        return self._wait_for_image("fusion", self.processor.fusion_queue, self.processor.fusion_ready, timeout)
