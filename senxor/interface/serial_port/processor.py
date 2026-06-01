# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import contextlib
import threading
from collections import deque
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

from senxor.error import (
    SenxorAckInvalidError,
)
from senxor.interface.serial_port.parser import SenxorAckDecoder, SenxorAckParser

if TYPE_CHECKING:
    from senxor.interface.serial_port.base import SerialTransportBase
    from senxor.log import SenxorLogger


class ByteFIFO:
    """High-performance byte FIFO buffer."""

    def __init__(self):
        self._buf = bytearray()

    @property
    def buf(self) -> bytearray:
        return self._buf

    def put(self, data: bytes) -> None:
        self._buf.extend(data)

    def discard(self, size: int) -> None:
        del self._buf[:size]

    def __getitem__(self, index: slice) -> bytearray:
        return self._buf[index]

    def __len__(self) -> int:
        return len(self._buf)


class AckProcessorState(Enum):
    """State machine for ACK processor."""

    CLOSED = auto()
    MISALIGNED = auto()
    UNKNOWN = auto()
    EMPTY = auto()
    PENDING = auto()
    ALIGNED = auto()
    ACK_ERROR = auto()


class SerialTransportReadThread:
    """Generic read thread for serial transport."""

    def __init__(
        self,
        transport: SerialTransportBase,
        logger: SenxorLogger,
        on_started: Callable[[], None],
        on_data: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ):
        self.transport = transport
        self.logger = logger
        self.on_started = on_started
        self.on_data = on_data
        self.on_error = on_error

        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the read thread."""
        if not self.transport.is_open:
            raise RuntimeError("Transport not open")
        if self.worker_thread:
            raise RuntimeError("Read thread already started")
        self.on_started()
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        with contextlib.suppress(Exception):
            self.transport.cancel_read()
        if self.worker_thread:
            self.worker_thread.join(timeout=3)
            if self.worker_thread.is_alive():
                self.logger.warning("read_thread_stopped_timeout", thread=self.worker_thread.name)
                self.clean_up()
                self.logger.info("forced_clean_up")
            self.worker_thread = None

    def _worker_loop(self) -> None:
        try:
            while not self.stop_event.is_set():
                chunk = self.transport.read()
                if chunk:
                    self.on_data(chunk)
        except Exception as e:
            if not self.stop_event.is_set():
                self.on_error(e)
        finally:
            self.clean_up()

    def clean_up(self) -> None:
        """Clean up the read thread."""
        try:
            with self._lock:
                self.transport.close()
            self.logger.debug("stream_closed")
        except Exception as e:
            self.logger.warning("close_stream_failed", error=e)

    def write(self, data: bytes) -> None:
        with self._lock:
            self.transport.write(data)


class SerialAckProcessor:
    """Processor for serial port ACK/GFRA."""

    def __init__(self, transport: SerialTransportBase, logger: SenxorLogger):
        self.transport = transport
        self.logger = logger

        self._buffer = ByteFIFO()
        self._parser = SenxorAckParser(logger)
        self._init_ack_pipe()

        self.state: AckProcessorState = AckProcessorState.CLOSED

        self._fatal_error_lock = threading.Lock()
        self._fatal_error: tuple[str, Exception] | None = None
        self.no_module_event = threading.Event()

        self._reader = SerialTransportReadThread(
            transport,
            logger,
            on_started=self._on_reader_started,
            on_data=self._on_data_received,
            on_error=self._on_reader_error,
        )

    def start(self) -> None:
        """Start the reader."""
        self._reader.start()

    def stop(self) -> None:
        """Stop the reader."""
        self._reader.stop()

    def write(self, data: bytes) -> None:
        self._reader.write(data)

    def raise_if_error(self) -> None:
        with self._fatal_error_lock:
            if self._fatal_error is None:
                return
            msg, e = self._fatal_error
            self._fatal_error = None
        self.logger.exception(msg, error=e)
        self.stop()
        raise e

    def _on_reader_started(self) -> None:
        self._reset_statis()
        self.state = AckProcessorState.UNKNOWN

    def _init_ack_pipe(self) -> None:
        """Initialize the ACK pipe."""
        self.gfra_queue: deque[tuple[bytes | None, bytes]] = deque(maxlen=5)
        self.gfra_ready = threading.Condition()

        self.rreg_queue: deque[int] = deque(maxlen=1)
        self.rreg_ready = threading.Condition()

        self.wreg_queue: deque[bool] = deque(maxlen=1)
        self.wreg_ready = threading.Condition()

        self.rrse_queue: deque[dict[int, int]] = deque(maxlen=1)
        self.rrse_ready = threading.Condition()

    def _on_data_received(self, data: bytes) -> None:
        """On data received from the stream."""
        self._buffer.put(data)
        while True:
            if self.state == AckProcessorState.ACK_ERROR:
                self._on_invalid_ack()
            self._check_state()
            if self.state == AckProcessorState.ALIGNED:
                self._parse_ack()
            elif self.state == AckProcessorState.MISALIGNED:
                self._on_buffer_misaligned()
            elif self.state == AckProcessorState.ACK_ERROR:
                self._on_invalid_ack()
            elif self.state == AckProcessorState.PENDING or self.state == AckProcessorState.EMPTY:
                break
            else:
                raise RuntimeError(f"Invalid state: {self.state}")

    def _on_reader_error(self, e: Exception) -> None:
        """Handle reader thread errors."""
        self._set_error(e, "transport_error")

    def _reset_statis(self) -> None:
        self._ack_error_count = 0
        self._misaligned_bytes = 0

        self._max_ack_error_count = 4
        self._max_misaligned_bytes = 65536

    def _set_error(self, error: Exception, msg: str) -> None:
        with self._fatal_error_lock:
            if self._fatal_error is not None:
                self.logger.warning("fatal_error_suppressed", pending=self._fatal_error[0], msg=msg, error=error)
                return
            self._fatal_error = (msg, error)

    def _check_state(self) -> None:
        """Check the state of the buffer.

        State transition: UNKNOWN | PENDING | EMPTY -> MISALIGNED | EMPTY | PENDING | ALIGNED.
        """
        if self.state == AckProcessorState.ACK_ERROR:
            raise RuntimeError("Unexpected state (ACK_ERROR)")
        elif not (
            self.state == AckProcessorState.UNKNOWN
            or self.state == AckProcessorState.PENDING
            or self.state == AckProcessorState.EMPTY
            or self.state == AckProcessorState.MISALIGNED
        ):
            self.logger.warning(
                "unexpected_state",
                state=self.state,
                msg="this_should_not_happen, please report this issue.",
            )

        if self._parser.is_buffer_empty(self._buffer.buf):
            self.state = AckProcessorState.EMPTY
        elif self._parser.is_buffer_unaligned(self._buffer.buf):
            self.state = AckProcessorState.MISALIGNED
        elif self._parser.is_buffer_pending(self._buffer.buf):
            self.state = AckProcessorState.PENDING
        else:
            self.state = AckProcessorState.ALIGNED

    def _on_buffer_misaligned(self) -> None:
        """On buffer misaligned.

        State transition: MISALIGNED -> UNKNOWN.
        """
        if self.state != AckProcessorState.MISALIGNED:
            raise RuntimeError("Unexpected state")

        prefix_idx = self._buffer.buf.find(SenxorAckParser.ACK_HEADER)
        if prefix_idx == -1:
            bytes_to_keep = self._parser.ACK_HEADER_LENGTH - 1
            buf_len = len(self._buffer)
            discarded = buf_len - bytes_to_keep if buf_len > bytes_to_keep else 0
            self._buffer.discard(discarded)
            self.logger.debug("realign_buffer", state="no_prefix", discarded=discarded)
        elif prefix_idx == 0:
            discarded = 0
            self.logger.debug("realign_buffer", state="already_aligned", discarded=0)
        else:
            discarded = prefix_idx
            self._buffer.discard(discarded)
            self.logger.debug("realign_buffer", state="aligned", discarded=discarded)

        self._misaligned_bytes += discarded
        if self._misaligned_bytes >= self._max_misaligned_bytes:
            self._set_error(
                SenxorAckInvalidError("Can not recover from misaligned buffer"),
                "stream_misaligned_bytes_exceeded",
            )
        self.state = AckProcessorState.UNKNOWN

    def _on_invalid_ack(self) -> None:
        """On invalid ACK received.

        State transition: ACK_ERROR -> MISALIGNED.
        """
        if self.state != AckProcessorState.ACK_ERROR:
            raise RuntimeError(f"Unexpected state ({self.state})")

        if not self._buffer.buf.startswith(SenxorAckParser.ACK_HEADER):
            self.state = AckProcessorState.MISALIGNED
            self.logger.warning(
                "discard_invalid_ack",
                state="unexpected_prefix",
                msg="this_should_not_happen, please report this issue.",
            )
            return

        discarded = self._parser.ACK_HEADER_IDX.stop
        self._buffer.discard(discarded)
        self.logger.info("discard_invalid_ack", state="discarded_header_and_realign", discarded=discarded)
        self.state = AckProcessorState.MISALIGNED

    def _parse_ack(self) -> None:
        """Parse the ACK from the buffer.

        State transition: ALIGNED -> UNKNOWN | ACK_ERROR.
        """
        if self.state != AckProcessorState.ALIGNED:
            raise RuntimeError(f"Unexpected state ({self.state})")

        try:
            cmd, data, total_len = self._parser.parse_ack(self._buffer.buf)
            self._on_ack_parsed(cmd, data)
            self.logger.debug("ack_received", cmd=cmd, ack_len=total_len)
            self._buffer.discard(total_len)
            self.state = AckProcessorState.UNKNOWN
            self._reset_statis()
        except SenxorAckInvalidError as e:
            self.state = AckProcessorState.ACK_ERROR
            self.logger.error("parse_ack_failed", state="invalid_ack", error=e)
            self._ack_error_count += 1
            if self._ack_error_count >= self._max_ack_error_count:
                self._set_error(
                    SenxorAckInvalidError("Parse ACK continuously failed, last error: " + str(e)),
                    "parse_ack_failed_too_many_times",
                )
        except Exception as e:
            self.logger.error("parse_ack_failed", state="unexpected_error", error=e)
            self.state = AckProcessorState.ACK_ERROR

    def _on_ack_parsed(self, cmd: str, data: bytearray) -> None:
        """On a new ACK parsed."""
        if cmd == "GFRA":
            with self.gfra_ready:
                header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
                header_ = None if header is None else bytes(header)
                temp_data_ = bytes(temp_data)
                self.gfra_queue.append((header_, temp_data_))
                self.gfra_ready.notify_all()
        elif cmd == "RREG":
            with self.rreg_ready:
                self.rreg_queue.append(SenxorAckDecoder._parse_ack_rreg(data))
                self.rreg_ready.notify_all()
        elif cmd == "WREG":
            with self.wreg_ready:
                self.wreg_queue.append(SenxorAckDecoder._parse_ack_wreg(data))
                self.wreg_ready.notify_all()
        elif cmd == "RRSE":
            with self.rrse_ready:
                self.rrse_queue.append(SenxorAckDecoder._parse_ack_rrse(data))
                self.rrse_ready.notify_all()
        elif cmd == "SERR":
            if not self.no_module_event.is_set():
                self.no_module_event.set()
        else:
            self.logger.warning("unknown_ack_type", cmd=cmd, data=data)
