# Copyright (c) 2025 Meridian Innovation. All rights reserved.

import queue
import threading
import time
from collections import deque
from collections.abc import Callable
from enum import Enum, auto
from itertools import count
from typing import Literal

from serial import PortNotOpenError, Serial, SerialException

from senxor._interface._serial_parser import SenxorAckDecoder, SenxorAckParser
from senxor.error import SenxorAckInvalidError, SenxorLostConnectionError, SenxorNotConnectedError


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


class SenxorSerialReader:
    def __init__(self, ser: Serial, logger, read_interval: float = 0.005):
        self.ser = ser

        self.logger = logger
        self.read_interval = read_interval

        self._buffer = ByteFIFO()
        self._parser = SenxorAckParser(logger)
        self._init_ack_pipe()

        self._write_queue: queue.Queue[bytes] = queue.Queue()

        self.state: SenxorSerialState = SenxorSerialState.CLOSED
        self.worker_thread: threading.Thread | None = None

        self.stop_event = threading.Event()
        self.error_event = threading.Event()
        self.error_queue: queue.Queue[tuple[str, Exception]] = queue.Queue(1)
        self.no_module_event = threading.Event()

    def start(self) -> None:
        """Start the receiver thread."""
        if not self.ser.is_open:
            raise RuntimeError("Serial port not open", self.ser.port)
        if self.ser.timeout != 0:
            raise ValueError("Serial read timeout must be 0")
        self._reset_statis()
        self.stop_event.clear()
        self.state = SenxorSerialState.UNKNOWN
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self) -> None:
        """Stop the receiver thread."""
        self.stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=3)
            if self.worker_thread.is_alive():
                self.logger.warning("serial_receiver_thread_stopped_timeout", thread=self.worker_thread.name)
                self._clean_up()
                self.logger.info("forced_clean_up")
            self.worker_thread = None

    def raise_if_error(self) -> None:
        if self.error_event.is_set():
            self.error_event.clear()
            msg, error = self.error_queue.get()
            self.logger.exception(msg, error=error)
            self.stop()
            raise error

    def write(self, data: bytes) -> None:
        # Raise error if the queue is full.
        self._write_queue.put_nowait(data)

    def _init_ack_pipe(self) -> None:
        """Initialize the ACK pipe."""
        self.gfra_queue: deque[tuple[bytearray | None, bytearray]] = deque(maxlen=5)
        self.gfra_ready = threading.Condition()

        self.rreg_queue: deque[int] = deque(maxlen=1)
        self.rreg_ready = threading.Condition()

        self.wreg_queue: deque[bool] = deque(maxlen=1)
        self.wreg_ready = threading.Condition()

        self.rrse_queue: deque[dict[int, int]] = deque(maxlen=1)
        self.rrse_ready = threading.Condition()

    def _reset_statis(self) -> None:
        self._ack_error_count = 0
        self._misaligned_count = 0

        self._max_ack_error_count = 4
        self._max_misaligned_count = 4

    def _set_error(self, error: Exception, msg: str) -> None:
        self.error_queue.put((msg, error))
        self.error_event.set()

    def _worker_loop(self) -> None:
        try:
            while not self.stop_event.is_set():
                self._read_data()
                self._write_data()
                time.sleep(self.read_interval)
        except PortNotOpenError as e:
            e_ = SenxorNotConnectedError()
            self._set_error(e, "serial_port_not_open")
        except SerialException:
            e_ = SenxorLostConnectionError()
            self._set_error(e_, "serial_lost_connection")
        except Exception as e:
            self._set_error(e, "serial_unexpected_error")
        finally:
            self._clean_up()
            self.state = SenxorSerialState.CLOSED

    def _clean_up(self) -> None:
        """Clean up the receiver."""
        try:
            self.ser.close()
            self.logger.debug("serial_closed")
        except Exception as e:
            self.logger.warning("close_serial_failed", error=e)

    def _read_data(self) -> None:
        """Read data from the serial port. Called in the worker thread."""
        chunk = self.ser.read(self.ser.in_waiting)
        if chunk:
            self._buffer.put(chunk)
            self._on_data_received()

    def _write_data(self) -> None:
        """Write data to the serial port. Called in the worker thread."""
        try:
            data = self._write_queue.get_nowait()
        except queue.Empty:
            return
        self.ser.write(data)
        self.logger.debug("serial_write", data=data)
        self._write_queue.task_done()

    def _on_data_received(self) -> None:
        """On data received from the serial port."""
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
            self._misaligned_count += 1
            if self._misaligned_count >= self._max_misaligned_count:
                self._set_error(
                    SenxorAckInvalidError("Can not recover from misaligned buffer"),
                    "serial_misaligned_count_exceeded",
                )
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
            discarded = len(self._buffer)
            self._buffer.buf.clear()
            self.logger.debug("realign_buffer", state="no_prefix", discarded=discarded)
        elif prefix_idx == 0:
            # Should only happen when first communication.
            discarded = 0
            self.logger.debug("realign_buffer", state="already_aligned", discarded=0)
        else:
            discarded = prefix_idx
            self._buffer.discard(discarded)
            self.logger.debug("realign_buffer", state="aligned", discarded=discarded)
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
                self.gfra_queue.append((header, temp_data))
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
            self.no_module_event.set()
        else:
            self.logger.warning("unknown_ack_type", cmd=cmd, data=data)
