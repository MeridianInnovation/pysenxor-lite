# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.
from __future__ import annotations

import threading
from collections import deque
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

from serial import PortNotOpenError, Serial, SerialException

from senxor.error import SenxorAckInvalidError, SenxorLostConnectionError, SenxorNoModuleError, SenxorNotConnectedError
from senxor.interface.serial_port._parser import SenxorAckDecoder, SenxorAckParser

if TYPE_CHECKING:
    from senxor.interface.event import SenxorInterfaceEvent


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


class SenxorSerialState(Enum):
    CLOSED = auto()  # The serial port is closed.
    MISALIGNED = auto()  # The buffer is misaligned (not starting with the ACK header).
    UNKNOWN = auto()  # The state is unknown.
    EMPTY = auto()  # The buffer is empty (< 8, can not parse data length).
    PENDING = auto()  # The buffer is pending (> 8, < data_length, waiting for more data).
    ALIGNED = auto()  # The buffer is aligned and has enough data to parse.
    ACK_ERROR = auto()  # There was an ACK error (e.g. lost part of the ACK).


class SerialReaderThread:
    def __init__(
        self,
        ser: Serial,
        logger,
        on_started: Callable[[], None],
        on_data: Callable[[bytes], None],
        on_error: Callable[[Exception], None],
    ):
        self.ser = ser
        self.logger = logger
        self.on_started = on_started
        self.on_data = on_data
        self.on_error = on_error

        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the receiver thread."""
        if not self.ser.is_open:
            raise RuntimeError("Serial port not open", self.ser.port)
        if self.worker_thread:
            raise RuntimeError("Serial reader thread already started")
        self.on_started()
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.ser.is_open:
            self.ser.cancel_read()
        if self.worker_thread:
            self.worker_thread.join(timeout=3)
            if self.worker_thread.is_alive():
                self.logger.warning("serial_receiver_thread_stopped_timeout", thread=self.worker_thread.name)
                self.clean_up()
                self.logger.info("forced_clean_up")
            self.worker_thread = None

    def _worker_loop(self) -> None:
        try:
            while not self.stop_event.is_set():
                chunk = self.ser.read(self.ser.in_waiting or 1)
                if chunk:
                    self.on_data(chunk)
        except Exception as e:
            self.on_error(e)
        finally:
            self.clean_up()

    def clean_up(self) -> None:
        """Clean up the reader."""
        try:
            with self._lock:
                self.ser.close()
            self.logger.debug("serial_closed")
        except Exception as e:
            self.logger.warning("close_serial_failed", error=e)

    def write(self, data: bytes) -> None:
        with self._lock:
            self.ser.write(data)


class SenxorSerialReader:
    def __init__(
        self,
        ser: Serial,
        logger,
        events: SenxorInterfaceEvent,
    ):
        self.ser = ser
        self.logger = logger
        self.events = events

        self._buffer = ByteFIFO()
        self._parser = SenxorAckParser(logger)
        self._init_ack_pipe()

        self.state: SenxorSerialState = SenxorSerialState.CLOSED

        self._fatal_error_lock = threading.Lock()
        self._fatal_error: tuple[str, Exception] | None = None
        self.no_module_event = threading.Event()

        self._reader = SerialReaderThread(
            ser,
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
        self.state = SenxorSerialState.UNKNOWN

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
        """On data received from the serial port."""
        self._buffer.put(data)
        while True:
            if self.state == SenxorSerialState.ACK_ERROR:
                self._on_invalid_ack()
            self._check_state()
            if self.state == SenxorSerialState.ALIGNED:
                self._parse_ack()
            elif self.state == SenxorSerialState.MISALIGNED:
                self._on_buffer_misaligned()
            elif self.state == SenxorSerialState.ACK_ERROR:
                self._on_invalid_ack()
            elif self.state == SenxorSerialState.PENDING or self.state == SenxorSerialState.EMPTY:
                break
            else:
                raise RuntimeError(f"Invalid state: {self.state}")

    def _on_reader_error(self, e: Exception) -> None:
        if isinstance(e, PortNotOpenError):
            error = SenxorNotConnectedError()
            self._set_error(error, "serial_port_not_open")
        elif isinstance(e, SerialException):
            error = SenxorLostConnectionError()
            self._set_error(error, "serial_lost_connection")
        else:
            self._set_error(e, "serial_unexpected_error")

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
        self.events.error.emit(error)

    def _check_state(self) -> None:
        """Check the state of the buffer.

        State transition: UNKNOWN | PENDING | EMPTY -> MISALIGNED | EMPTY | PENDING | ALIGNED.
        """
        if self.state == SenxorSerialState.ACK_ERROR:
            raise RuntimeError("Unexpected state (ACK_ERROR)")
        elif not (
            self.state == SenxorSerialState.UNKNOWN
            or self.state == SenxorSerialState.PENDING
            or self.state == SenxorSerialState.EMPTY
            or self.state == SenxorSerialState.MISALIGNED
        ):
            # For development purpose, this should not happen.
            self.logger.warning(
                "unexpected_state",
                state=self.state,
                msg="this_should_not_happen, please report this issue.",
            )

        if self._parser.is_buffer_empty(self._buffer.buf):
            self.state = SenxorSerialState.EMPTY
        elif self._parser.is_buffer_unaligned(self._buffer.buf):
            self.state = SenxorSerialState.MISALIGNED
        elif self._parser.is_buffer_pending(self._buffer.buf):
            self.state = SenxorSerialState.PENDING
        else:
            self.state = SenxorSerialState.ALIGNED

        # self.logger.debug("check_state", state=self.state)

    def _on_buffer_misaligned(self) -> None:
        """On buffer misaligned.

        State transition: MISALIGNED -> UNKNOWN.
        """
        if self.state != SenxorSerialState.MISALIGNED:
            raise RuntimeError("Unexpected state")

        prefix_idx = self._buffer.buf.find(SenxorAckParser.ACK_HEADER)
        if prefix_idx == -1:
            # Consider there may partial prefix(1-3 bytes) in the buffer, keep the last 3 bytes to avoid losing data.
            bytes_to_keep = self._parser.ACK_HEADER_LENGTH - 1
            buf_len = len(self._buffer)
            discarded = buf_len - bytes_to_keep if buf_len > bytes_to_keep else 0
            self._buffer.discard(discarded)
            self.logger.debug("realign_buffer", state="no_prefix", discarded=discarded)
        elif prefix_idx == 0:
            # Should only happen when first communication.
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
                "serial_misaligned_bytes_exceeded",
            )
        self.state = SenxorSerialState.UNKNOWN

    def _on_invalid_ack(self) -> None:
        """On invalid ACK received.

        State transition: ACK_ERROR -> MISALIGNED.
        """
        if self.state != SenxorSerialState.ACK_ERROR:
            raise RuntimeError(f"Unexpected state ({self.state})")

        if not self._buffer.buf.startswith(SenxorAckParser.ACK_HEADER):
            self.state = SenxorSerialState.MISALIGNED
            self.logger.warning(
                "discard_invalid_ack",
                state="unexpected_prefix",
                msg="this_should_not_happen, please report this issue.",
            )
            return

        discarded = self._parser.ACK_HEADER_IDX.stop
        self._buffer.discard(discarded)
        self.logger.info("discard_invalid_ack", state="discarded_header_and_realign", discarded=discarded)
        self.state = SenxorSerialState.MISALIGNED

    def _parse_ack(self) -> None:
        """Parse the ACK from the buffer.

        State transition: ALIGNED -> UNKNOWN | ACK_ERROR.
        """
        if self.state != SenxorSerialState.ALIGNED:
            raise RuntimeError(f"Unexpected state ({self.state})")

        try:
            cmd, data, total_len = self._parser.parse_ack(self._buffer.buf)
            self._on_ack_parsed(cmd, data)
            self.logger.debug("ack_received", cmd=cmd, ack_len=total_len)
            self._buffer.discard(total_len)
            self.state = SenxorSerialState.UNKNOWN
            self._reset_statis()
        except SenxorAckInvalidError as e:
            self.state = SenxorSerialState.ACK_ERROR
            self.logger.error("parse_ack_failed", state="invalid_ack", error=e)
            self._ack_error_count += 1
            if self._ack_error_count >= self._max_ack_error_count:
                self._set_error(
                    SenxorAckInvalidError("Parse ACK continuously failed, last error: " + str(e)),
                    "parse_ack_failed_too_many_times",
                )
        except Exception as e:
            # Unexpected error, maybe the ack is corrupted or something else.
            # Not sure if this will hang the program.
            self.logger.error("parse_ack_failed", state="unexpected_error", error=e)
            self.state = SenxorSerialState.ACK_ERROR

    def _on_ack_parsed(self, cmd: str, data: bytearray) -> None:
        """On a new ACK parsed."""
        if cmd == "GFRA":
            with self.gfra_ready:
                header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
                header_ = None if header is None else bytes(header)
                temp_data_ = bytes(temp_data)
                self.gfra_queue.append((header_, temp_data_))
                self.gfra_ready.notify_all()
                self.events.data.emit(header_, temp_data_)
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
                # We don't call `_set_error` here because register operations still work without lens module.
                # Only `read` function will raise `SenxorNoModuleError`.
                self.events.error.emit(SenxorNoModuleError())
        else:
            self.logger.warning("unknown_ack_type", cmd=cmd, data=data)
