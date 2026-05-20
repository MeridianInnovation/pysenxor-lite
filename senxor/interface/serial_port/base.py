# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import functools
import threading
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from senxor.error import (
    SenxorLostConnectionError,
    SenxorNoModuleError,
    SenxorNotConnectedError,
    SenxorResponseTimeoutError,
)
from senxor.interface.protocol import IDevice, ISenxorInterface
from senxor.interface.serial_port.parser import SenxorCmdEncoder
from senxor.interface.serial_port.processor import SerialAckProcessor
from senxor.log import get_logger

if TYPE_CHECKING:
    from collections import deque


class SerialTransportBase(ABC):
    """Abstract transport interface for serial port."""

    def __init__(self, device: IDevice):
        self.device = device

    @abstractmethod
    def read(self) -> bytes: ...

    @abstractmethod
    def write(self, data: bytes) -> None: ...

    @abstractmethod
    def cancel_read(self) -> None: ...

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


def _op_wrapper(func: Callable) -> Callable:
    def operation(self: SerialInterfaceBase, *args, **kwargs) -> Any:
        self.processor.raise_if_error()
        if not self.is_connected:
            self.close()
            raise SenxorNotConnectedError
        return func(self, *args, **kwargs)

    def handle_error(self: SerialInterfaceBase, error: Exception, try_count: int) -> None:
        if isinstance(error, (SenxorNotConnectedError, SenxorLostConnectionError, SenxorResponseTimeoutError)):
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
    def retry_wrapper(self: SerialInterfaceBase, *args, **kwargs) -> Any:
        for try_count in range(self.OP_RETRY_TIMES + 1):
            try:
                op_result = operation(self, *args, **kwargs)
                return op_result
            except Exception as e:  # noqa: PERF203
                handle_error(self, e, try_count)

    return retry_wrapper


class SerialInterfaceBase(ISenxorInterface):
    OP_TIMEOUT: ClassVar[float] = 3
    OP_RETRY_TIMES: ClassVar[int] = 1
    OP_RETRY_INTERVAL: ClassVar[float] = 0.1

    TRANSPORT_CLASS: ClassVar[type[SerialTransportBase]]

    def __init__(self, device: IDevice) -> None:
        self._device = device
        self.logger = get_logger().bind(name=device.name)
        self.transport = self.TRANSPORT_CLASS(device)
        self.processor = SerialAckProcessor(self.transport, self.logger)
        self._op_lock = threading.Lock()

    def open(self) -> None:
        try:
            self.transport.open()
            self.processor.start()
        except Exception as e:
            self.logger.exception("open_failed", error=e)
            raise

    @property
    def device(self) -> IDevice:
        return self._device

    @property
    def is_connected(self) -> bool:
        return self.transport.is_open

    def close(self) -> None:
        self.processor.stop()
        self.transport.close()

    @_op_wrapper
    def read(self, timeout: float | None = None) -> tuple[bytes | None, bytes | None]:
        if self.processor.gfra_queue:
            return self.processor.gfra_queue.popleft()
        if self.processor.no_module_event.is_set():
            raise SenxorNoModuleError
        if timeout == 0:
            return None, None
        return self._wait_for_ack("GFRA", self.processor.gfra_queue, self.processor.gfra_ready, timeout)

    @_op_wrapper
    def read_reg(self, reg: int) -> int:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rreg(reg)
            self.processor.write(cmd)
            data = self._wait_for_ack("RREG", self.processor.rreg_queue, self.processor.rreg_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def write_reg(self, reg: int, value: int) -> None:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_wreg(reg, value)
            self.processor.write(cmd)
            data = self._wait_for_ack("WREG", self.processor.wreg_queue, self.processor.wreg_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def read_regs(self, regs: list[int]) -> dict[int, int]:
        with self._op_lock:
            cmd = SenxorCmdEncoder.encode_ack_rrse(regs)
            self.processor.write(cmd)
            data = self._wait_for_ack("RRSE", self.processor.rrse_queue, self.processor.rrse_ready, self.OP_TIMEOUT)
            return data

    @_op_wrapper
    def write_regs(self, regs: dict[int, int]) -> None:
        for reg, value in regs.items():
            self.write_reg(reg, value)

    def _wait_for_ack(
        self,
        cmd: str,
        queue: deque,
        ready: threading.Condition,
        timeout: float | None,
    ) -> Any:
        start_time = time.time()
        while True:
            self.processor.raise_if_error()
            with ready:
                if queue:
                    return queue.popleft()
                if timeout is not None:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        break
                    ready.wait(remaining)
                else:
                    ready.wait()
        self.processor.raise_if_error()
        raise SenxorResponseTimeoutError(f"Timeout waiting for {cmd} response")
