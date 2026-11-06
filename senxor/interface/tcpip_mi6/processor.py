# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Command reply and image frame processing for MI6 devices."""

from __future__ import annotations

import threading
from collections import deque
from typing import TYPE_CHECKING

from senxor.interface.serial_port.processor import AckProcessorState, SerialAckProcessor
from senxor.interface.tcpip_mi6.parser import MI6AckParser

if TYPE_CHECKING:
    from senxor.interface.serial_port.base import SerialTransportBase
    from senxor.log import SenxorLogger

_IMAGE_LENGTHS = {"GRGB": 640 * 360 * 3 // 2, "GFUC": 480 * 360 * 3 // 2, "GFUS": 480 * 360}
_REGULAR_COMMANDS = {"GFRA", "RREG", "WREG", "WRGE", "RRSE", "SERR"}


class MI6AckProcessor(SerialAckProcessor):
    """Process MI6 command replies and image frames."""

    def __init__(self, transport: SerialTransportBase, logger: SenxorLogger):
        """Initialize the MI6 reply processor.

        Parameters
        ----------
        transport : SerialTransportBase
            The transport used to read data and send commands.
        logger : SenxorLogger
            The logger for protocol and connection events.

        """
        super().__init__(transport, logger)
        self._parser = MI6AckParser(logger)

    def _init_ack_pipe(self) -> None:
        """Initialize command reply, thermal, RGB, and fusion queues."""
        super()._init_ack_pipe()
        self.rgb_queue: deque[bytes] = deque(maxlen=1)
        self.rgb_ready = threading.Condition()
        self.fusion_queue: deque[tuple[str, bytes]] = deque(maxlen=1)
        self.fusion_ready = threading.Condition()

    def _on_reader_started(self) -> None:
        """Clear buffered data and reply state before receiving a new stream."""
        self._buffer.discard(len(self._buffer))
        for queue in (
            self.gfra_queue,
            self.rreg_queue,
            self.wreg_queue,
            self.rrse_queue,
            self.rgb_queue,
            self.fusion_queue,
        ):
            queue.clear()
        self.no_module_event.clear()
        self._fatal_error = None
        super()._on_reader_started()

    def _on_invalid_ack(self) -> None:
        """Discard a complete invalid image packet or use regular reply recovery."""
        buffer = self._buffer.buf
        cmd = bytes(buffer[self._parser.ACK_CMD_IDX]).decode("ascii", errors="replace")
        expected = _IMAGE_LENGTHS.get(cmd)
        if expected is not None:
            length = int.from_bytes(buffer[self._parser.ACK_LENGTH_IDX], byteorder="little")
            total = self._parser.ACK_LENGTH_IDX.stop + length
            if length == expected + 8 and len(buffer) >= total:
                self._buffer.discard(total)
                self.state = AckProcessorState.MISALIGNED
                self.logger.info("discard_invalid_frame", cmd=cmd, ack_len=total)
                return
        super()._on_invalid_ack()

    def _on_ack_parsed(self, cmd: str, data: bytes | bytearray) -> None:
        """Dispatch a parsed reply or image frame to its queue.

        Parameters
        ----------
        cmd : str
            The parsed message tag.
        data : bytes | bytearray
            The payload after checksum validation.

        """
        expected = _IMAGE_LENGTHS.get(cmd)
        if expected is not None:
            if len(data) != expected:
                self.logger.warning("invalid_frame_size", cmd=cmd, expected=expected, actual=len(data))
                return
            if cmd == "GRGB":
                with self.rgb_ready:
                    self.rgb_queue.append(bytes(data))
                    self.rgb_ready.notify_all()
            else:
                with self.fusion_ready:
                    self.fusion_queue.append((cmd, bytes(data)))
                    self.fusion_ready.notify_all()
        elif cmd in _REGULAR_COMMANDS:
            super()._on_ack_parsed(cmd, data)
        else:
            self.logger.warning("unknown_ack_type", cmd=cmd, ack_len=len(data))
