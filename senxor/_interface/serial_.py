# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

import functools
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from serial import Serial, SerialException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo

from senxor._interface._serial_parser import SenxorCmdEncoder
from senxor._interface._serial_reader import SenxorSerialReader
from senxor._interface.protocol import InterfaceProtocol
from senxor.consts import SENXOR_PRODUCT_ID, SENXOR_VENDER_ID
from senxor.error import (
    SenxorNoModuleError,
    SenxorNotConnectedError,
    SenxorResponseTimeoutError,
)
from senxor.log import get_logger

if TYPE_CHECKING:
    from collections import deque


def is_senxor_usb(port: ListPortInfo | str) -> bool:
    """Check if the port is a senxor port.

    Parameters
    ----------
    port : ListPortInfo | str
        The port to check. Use `list_ports.comports()` to get the list of ports.


    Returns
    -------
    bool
        True if the port is a senxor port, False otherwise.

    Examples
    --------
    >>> ports = list_ports.comports()
    >>> for port in ports:
    >>>     if is_senxor_port(port):
    >>>         print(port.device)

    """
    if isinstance(port, str):
        ports: list[ListPortInfo] = list_ports.comports()
        for p in ports:
            if p.device == port:
                port = p
                break
        else:
            msg = f"Port not found: {port}"
            raise ValueError(msg)

    vid = port.vid
    pid = port.pid

    res = (vid == SENXOR_VENDER_ID) and (pid in SENXOR_PRODUCT_ID)
    return res


def list_senxor_usb(exclude_open_ports: bool = True) -> list[ListPortInfo]:
    """List all the senxor ports.

    Parameters
    ----------
    exclude_open_ports : bool, optional
        If True, exclude the ports that are currently open (in use).
        If False, include the ports that are currently open (in use).
        Default is True.

    Returns
    -------
    list[ListPortInfo]
        The list of senxor ports.

    Examples
    --------
    >>> ports = list_senxor_ports()
    >>> print([port.device for port in ports])
    ['COM5', 'COM6']

    """
    ports = list_ports.comports()
    senxor_ports = []
    for port in ports:
        if is_senxor_usb(port):
            if not exclude_open_ports:
                senxor_ports.append(port)
            else:
                try:
                    # If we provide the port parameter, pyserial will try to open the port automatically.
                    # On Linux, the serial port can be opened by multiple processes, but the senxor does not
                    # support parallel communication.
                    # So, we need to check if the port is in use by other processes.
                    # We assume other programs using senxor properly lock the port.
                    # On Linux, if we set exclusive=True, pyserial will try to lock the port,
                    # so we can detect if the port is already in use.
                    s = Serial(port.device, exclusive=True)
                    s.close()
                    senxor_ports.append(port)
                except SerialException:
                    pass
    return senxor_ports


class SerialInterface(InterfaceProtocol):
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

    def __init__(
        self,
        port: str | ListPortInfo,
        *,
        read_timeout: float = 1.5,
        op_timeout: float = 3,
        op_retry_times: int = 3,
        op_retry_interval: float = 0.1,
    ):
        if isinstance(port, ListPortInfo):
            port = port.device
        self.port = port

        self.read_timeout = read_timeout
        self.op_timeout = op_timeout
        self.op_retry_times = op_retry_times
        self.op_retry_interval = op_retry_interval

        self.logger = get_logger().bind(address=port)
        self.logger.debug("init_serial_interface")

        self.ser: Serial = Serial()
        self.receiver = SenxorSerialReader(self.ser, self.logger)

        self._op_lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self.ser.is_open

    @property
    def address(self) -> str:
        return self.port

    @staticmethod
    def is_valid_address(address: str) -> bool:
        return is_senxor_usb(address)

    @staticmethod
    def discover(exclude_open_ports: bool = True) -> list[ListPortInfo]:
        return list_senxor_usb(exclude_open_ports)

    def open(self) -> None:
        if not self.is_valid_address(self.port):
            raise ValueError(f"Invalid serial port: {self.port}")

        try:
            self.ser.port = self.port
            self.ser.apply_settings(self.SENXOR_SERIAL_PARAMS)
            if not self.is_connected:
                self.ser.open()
            self.receiver.start()
        except Exception as e:
            self.logger.exception("open_failed", error=e)
            raise

    def close(self):
        self.receiver.stop()

    @staticmethod
    def _op_wrapper(func: Callable) -> Callable:
        def operation(self: SerialInterface, *args, **kwargs) -> Any:
            if not self.is_connected:
                self.close()
                raise SenxorNotConnectedError
            self.receiver.raise_if_error()
            return func(self, *args, **kwargs)

        @functools.wraps(func)
        def wrapper(self: SerialInterface, *args, **kwargs) -> Any:
            # first try
            try:
                return operation(self, *args, **kwargs)
            except Exception as e:
                self.logger.error("op_failed", error=e)

            # if first try failed, retry
            for i in range(2, self.op_retry_times):
                try:
                    self.logger.debug("retry_operation", try_count=i, func_name=func.__name__)
                    return operation(self, *args, **kwargs)
                except Exception as e:  # noqa: PERF203
                    if i < self.op_retry_times:
                        self.logger.error("retry_failed", try_count=i, func_name=func.__name__, error=e)
                        time.sleep(self.op_retry_interval)
                    else:
                        self.logger.exception("last_retry_failed", try_count=i, func_name=func.__name__, error=e)
                        self.close()
                        raise e

        return wrapper

    @_op_wrapper
    def read(self, block: bool = True) -> tuple[bytearray | None, bytearray | None]:
        if self.receiver.gfra_queue:
            return self.receiver.gfra_queue.popleft()
        elif self.receiver.no_module_event.is_set():
            raise SenxorNoModuleError
        elif block:
            data = self._wait_for_ack("GFRA", self.receiver.gfra_queue, self.receiver.gfra_ready, self.read_timeout)
            return data
        else:
            return None, None

    @_op_wrapper
    def read_reg(self, reg: int) -> int:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rreg(reg)
            self.receiver.write(cmd)
            data = self._wait_for_ack("RREG", self.receiver.rreg_queue, self.receiver.rreg_ready, self.op_timeout)
            return data

    @_op_wrapper
    def write_reg(self, reg: int, value: int) -> None:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_wreg(reg, value)
            self.receiver.write(cmd)
            data = self._wait_for_ack("WREG", self.receiver.wreg_queue, self.receiver.wreg_ready, self.op_timeout)
            return data

    @_op_wrapper
    def read_regs(self, regs: list[int]) -> dict[int, int]:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rrse(regs)
            self.receiver.write(cmd)
            data = self._wait_for_ack("RRSE", self.receiver.rrse_queue, self.receiver.rrse_ready, self.op_timeout)
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
