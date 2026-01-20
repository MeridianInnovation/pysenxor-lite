# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import functools
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from serial import Serial, SerialException
from serial.tools import list_ports

from senxor.consts import SENXOR_PRODUCT_ID, SENXOR_VENDER_ID
from senxor.error import (
    SenxorLostConnectionError,
    SenxorNoModuleError,
    SenxorNotConnectedError,
    SenxorResponseTimeoutError,
)
from senxor.interface.event import SenxorInterfaceEvent
from senxor.interface.protocol import IDevice, ISenxorInterface
from senxor.interface.serial_port._parser import SenxorCmdEncoder
from senxor.interface.serial_port._reader import SenxorSerialReader
from senxor.log import get_logger

if TYPE_CHECKING:
    from collections import deque

    from serial.tools.list_ports_common import ListPortInfo


def is_serial_port_senxor(port: ListPortInfo) -> bool:
    """Check if the serial port is a senxor device."""
    return (port.vid == SENXOR_VENDER_ID) and (port.pid in SENXOR_PRODUCT_ID)


def list_senxor_serial_ports(exclude_open_ports: bool = True) -> list[SerialPort]:
    """List all the senxor serial ports.

    Parameters
    ----------
    exclude_open_ports : bool, optional
        If True, exclude the ports that are currently open (in use).
        Default is True.

    """
    ports = list_ports.comports()
    senxor_ports = []
    for port in ports:
        if not is_serial_port_senxor(port):
            continue
        if exclude_open_ports:
            try:
                s = Serial(port.device, exclusive=True)
                s.close()
            except SerialException:
                continue
        senxor_ports.append(SerialPort(port))
    return senxor_ports


class SerialPort(IDevice):
    def __init__(self, port: ListPortInfo):
        self.port = port

    @property
    def name(self) -> str:
        return self.port.name

    @property
    def device(self) -> str:
        return self.port.device

    @property
    def vid(self) -> int:
        return self.port.vid

    @property
    def pid(self) -> int:
        return self.port.pid

    def __repr__(self) -> str:
        return f"SerialPort(port={self.port})"

    def __str__(self) -> str:
        return f"SerialPort {self.name}"


def _op_wrapper(func: Callable) -> Callable:
    def operation(self: SerialInterface, *args, **kwargs) -> Any:
        self.receiver.raise_if_error()
        if not self.is_connected:
            self.close()
            raise SenxorNotConnectedError
        return func(self, *args, **kwargs)

    def handle_error(self: SerialInterface, error: Exception, try_count: int) -> None:
        if isinstance(error, (SenxorNotConnectedError, SenxorLostConnectionError)):
            raise error
        if try_count == 0:
            self.logger.error("op_failed", error=error, func_name=func.__name__)
            time.sleep(self.OP_RETRY_INTERVAL)
        elif try_count < self.OP_RETRY_TIMES:
            self.logger.error("retry_failed", retry_count=try_count, error=error, func_name=func.__name__)
            time.sleep(self.OP_RETRY_INTERVAL)
        else:
            self.logger.exception("last_retry_failed", retry_count=try_count, error=error, func_name=func.__name__)
            self.close()
            raise error

    @functools.wraps(func)
    def retry_wrapper(self: SerialInterface, *args, **kwargs) -> Any:
        for try_count in range(self.OP_RETRY_TIMES + 1):
            try:
                op_result = operation(self, *args, **kwargs)
                return op_result
            except Exception as e:  # noqa: PERF203
                handle_error(self, e, try_count)

    return retry_wrapper


class SerialInterface(ISenxorInterface[SerialPort]):
    # The parameters for the serial port, should not be changed.
    SENXOR_SERIAL_PARAMS: ClassVar[dict[str, Any]] = {
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "xonxoff": False,
        "rtscts": False,
        "dsrdtr": False,
        "timeout": 0,
        "write_timeout": 0.2,
        "exclusive": True,
    }

    READ_TIMEOUT: ClassVar[float] = 1.5
    OP_TIMEOUT: ClassVar[float] = 3
    OP_RETRY_TIMES: ClassVar[int] = 1
    OP_RETRY_INTERVAL: ClassVar[float] = 0.1

    def __init__(self, device: SerialPort):
        self.device = device
        if not is_serial_port_senxor(device.port):
            raise ValueError(f"The serial port {device.device} is not a senxor device.")
        self.logger = get_logger().bind(name=device.name)
        self.ser: Serial = Serial()
        self.events = SenxorInterfaceEvent(self.logger)
        self.receiver = SenxorSerialReader(
            self.ser,
            self.logger,
            self.events,
        )
        self._op_lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self.ser.is_open

    @classmethod
    def list_devices(cls) -> list[SerialPort]:
        return list_senxor_serial_ports()

    def open(self) -> None:
        try:
            self.ser.port = self.device.device
            self.ser.apply_settings(self.SENXOR_SERIAL_PARAMS)
            if not self.is_connected:
                self.ser.open()
            self.receiver.start()
            self.events.open.emit()
        except Exception as e:
            self.logger.exception("open_failed", error=e)
            raise

    def close(self):
        self.receiver.stop()
        self.events.close.emit()

    @_op_wrapper
    def read(self, block: bool = True) -> tuple[bytes | None, bytes | None]:
        if self.receiver.gfra_queue:
            return self.receiver.gfra_queue.popleft()
        elif self.receiver.no_module_event.is_set():
            raise SenxorNoModuleError
        elif block:
            data = self._wait_for_ack("GFRA", self.receiver.gfra_queue, self.receiver.gfra_ready, self.READ_TIMEOUT)
            return data
        else:
            return None, None

    @_op_wrapper
    def read_reg(self, reg: int) -> int:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rreg(reg)
            self.receiver.write(cmd)
            data = self._wait_for_ack("RREG", self.receiver.rreg_queue, self.receiver.rreg_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def write_reg(self, reg: int, value: int) -> None:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_wreg(reg, value)
            self.receiver.write(cmd)
            data = self._wait_for_ack("WREG", self.receiver.wreg_queue, self.receiver.wreg_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def read_regs(self, regs: list[int]) -> dict[int, int]:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rrse(regs)
            self.receiver.write(cmd)
            data = self._wait_for_ack("RRSE", self.receiver.rrse_queue, self.receiver.rrse_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def write_regs(self, regs: dict[int, int]) -> None:
        for reg, value in regs.items():
            self.write_reg(reg, value)

    def _wait_for_ack(self, cmd: str, queue: deque, ready: threading.Condition, timeout: float) -> Any:
        start_time = time.time()
        with ready:
            while not queue:
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    self.receiver.raise_if_error()
                    raise SenxorResponseTimeoutError(f"Timeout waiting for {cmd} response")
                ready.wait(remaining)
            return queue.popleft()
