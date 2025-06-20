from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable, ClassVar

import numpy as np
from serial import Serial, SerialException
from serial.tools import list_ports
from serial.tools.list_ports_common import ListPortInfo
from structlog import get_logger

from senxor._error import (
    ChecksumError,
    InvalidAckBodyError,
    InvalidAckHeaderError,
    Policy,
    SenxorNotConnectedError,
    SenxorReadTimeoutError,
)
from senxor._interface.parser import SenxorMsgParser
from senxor._interface.protocol import SenxorInterfaceProtocol
from senxor.consts import SENXOR_PRODUCT_ID, SENXOR_VENDER_ID

logger = get_logger("senxor.interface.serial")


def is_senxor_usb(port: ListPortInfo | str) -> bool:
    """Check if the port is a senxor port.

    Parameters
    ----------
    port : ListPortInfo
        The port to check. Use `list_ports.comports()` to get the list of ports.

    Example
    -------
    >>> ports = list_ports.comports()
    >>> for port in ports:
    >>>     if is_senxor_port(port):
    >>>         print(port.device)

    Returns
    -------
    bool
        True if the port is a senxor port, False otherwise.

    """
    if isinstance(port, str):
        ports = list_ports.comports()
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

    Example
    -------
    >>> ports = list_senxor_ports()
    >>> print([port.device for port in ports])
    ['COM5', 'COM6']

    Returns
    -------
    list[ListPortInfo]
        The list of senxor ports.

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


def _rw_op_wrapper(func: Callable) -> Callable:
    """Wrap the read/write operation with the lock and error handler."""

    @functools.wraps(func)
    def wrapper(self: SenxorInterfaceSerial, *args, **kwargs) -> Any:
        if not self._is_connected:
            raise RuntimeError("Serial port is not open.")
        with self._rw_lock:
            # All exceptions raised during the read/write operation are redirected to the error handler.
            # This approach helps manage errors resulting from unexpected port closures or communication issues,
            # ensuring that most runtime errors are handled gracefully.
            # However, abrupt process termination (e.g., kill -9) will bypass this mechanism and may leave
            # the resources in an inconsistent state.
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                return self.error_handler(e, func, args, kwargs)

    return wrapper


class SenxorInterfaceSerial(SenxorInterfaceProtocol):
    # The parameters for the serial port, should not be changed.
    SENXOR_SERIAL_PARAMS: ClassVar[dict[str, Any]] = {
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "xonxoff": False,
        "rtscts": False,
        "dsrdtr": False,
        "timeout": 0.2,
        "write_timeout": 0.2,
        "exclusive": True,
    }

    def __init__(
        self,
        port: str | ListPortInfo,
        frame_read_timeout: float = 1.0,
        validate_gfra_checksum: bool = False,
        fail_on_checksum_error: bool = True,
    ):
        """Initialize the serial interface.

        Parameters
        ----------
        port : str | ListPortInfo
            The port of the device to connect to.
        frame_read_timeout : float, optional
            The timeout for the frame read operation.
        validate_gfra_checksum : bool, optional
            Whether to validate the checksum of the GFRA ack.
        fail_on_checksum_error : bool, optional
            Whether to fail on checksum error.

        """
        self._logger = get_logger("senxor.interface.serial")
        self._logger.debug(
            "init serial interface",
            port=port,
            frame_read_timeout=frame_read_timeout,
            validate_gfra_checksum=validate_gfra_checksum,
            fail_on_checksum_error=fail_on_checksum_error,
        )
        self.port = port
        self.ser: Serial = Serial()
        self.name: str | None = None
        self._is_connected: bool = False

        self.frame_read_timeout = frame_read_timeout

        # The flag to validate the checksum of the GFRA ack.
        # The GFRA have another crc check in the frame header.
        self.validate_gfra_checksum = validate_gfra_checksum

        # The flag to fail on checksum error.
        # In default, the gfra checksum is disabled. Only regs operation can
        # occur checksum error. Which means the error is not suggested to be ignored.
        self.fail_on_checksum_error = fail_on_checksum_error

        # The ack parser.
        self.parser = SenxorMsgParser()
        # Lock for the read/write operation.
        # Used to avoid error may occur in the multi-threading.
        self._rw_lock = threading.Lock()

        # The buffer for the read operation.
        self._gfra_buffer: bytes = b""
        self._gfra_buffer_timestamp: float = 0.0

        self._error_msg_clear_flag: bool = False

        self._init_error_policy()

    def open(self) -> None:
        if self._is_connected:
            self._logger.warning("open already opened port", port=self.port)
            return

        port = self.port

        if not self.is_valid_address(port):
            raise ValueError(f"Invalid port: {port}")

        if isinstance(port, ListPortInfo):
            port = port.device

        params = self.SENXOR_SERIAL_PARAMS

        try:
            self.ser = Serial(
                port,
                **params,
            )
            self._is_connected = True

        except Exception as e:
            self._is_connected = False
            self._logger.exception("failed to open serial port", port=port, error=str(e))
            raise e

        self.port = port
        self.name = self.ser.name
        # The timeout for the frame read operation.
        # The frame read waiting time may be much longer than the w/r regs time.
        # So, we expect a different timeout for the two operations.
        self.set_frame_read_timeout(self.frame_read_timeout)
        self._boot_clear()
        self._logger = self._logger.bind(port=self.ser.name)
        self._logger.info("serial port opened")

    def close(self) -> None:
        self._logger.info("closing serial port", port=self.port)
        if self.ser is None or not self._is_connected:
            self._logger.error("attempting to close unopened port")
            raise RuntimeError("Port is not open")

        try:
            self.ser.close()
        except Exception as e:
            self._logger.warning("error closing serial port", error=str(e))

        finally:
            self._is_connected = False
            self.ser = Serial()  # Empty serial object. It's a good practice to reset the serial object.
            self._logger.debug("serial port closed")

    @property
    def is_connected(self) -> bool | None:
        return self._is_connected

    @property
    def address(self) -> Any:
        return self.port

    @staticmethod
    @functools.wraps(list_senxor_usb)
    def discover(exclude_open_ports: bool = True) -> list[ListPortInfo]:
        return list_senxor_usb(exclude_open_ports)

    @staticmethod
    @functools.wraps(is_senxor_usb)
    def is_valid_address(address: str | ListPortInfo) -> bool:
        return is_senxor_usb(address)

    @_rw_op_wrapper
    def read(self, block: bool = True) -> tuple[np.ndarray, np.ndarray] | None:
        self._logger.debug("read gfra request", block=block)
        ack = None

        # In the stream mode, the senxor will send the GFRA ack periodically.

        # Case: in_waiting == 0 but gfra_buffer is not empty.
        # Extract the gfra_buffer if it is not too old.
        if self.ser.in_waiting == 0:
            if self.gfra_buffer != b"":
                # Make sure the gfra buffer is not too old.
                timestamp = time.time()
                if timestamp - self._gfra_buffer_timestamp < self._frame_read_timeout:
                    ack = self.gfra_buffer
                    self._logger.debug("using cached gfra buffer")
                self._gfra_buffer = b""

        # Case: in_waiting != 0
        # There is a GFRA ack in the serial port input buffer.
        # Read the ack from the buffer.
        else:
            # self._logger.debug("read from buffer", in_waiting=self.ser.in_waiting)
            cmd, ack = self._read_next_msg()
            if cmd != SenxorMsgParser.CMD_GFRA:
                self._logger.error("unexpected non gfra ack", cmd=cmd)
                raise RuntimeError("Unexpected Error: Unparsed non-GFRA ack in the buffer")

            # Case: After reading a GFRA ack, the in_waiting is still not 0.
            # This means there are more than one GFRA ack in the buffer.
            # This happens when the data reading is paused for a while.
            # Make sure we get the newest GFRA ack.
            # if self.ser.in_waiting != 0:
            #     self._logger.debug("more than one gfra in waiting", in_waiting=self.ser.in_waiting)
            while self.ser.in_waiting != 0:
                cmd, ack = self._read_next_msg()
                if cmd != SenxorMsgParser.CMD_GFRA:
                    self._logger.error("unexpected non gfra ack", cmd=cmd)
                    raise RuntimeError("Unexpected Error: Unparsed non-GFRA ack in the buffer")

        # If not block, we can return the result now.
        if ack is None:
            if not block:
                self._logger.debug("read gfra request no data")
                return None
        else:
            return self.parser._parse_ack_gfra(ack)

        # If block and we don't have the data, we need to wait for the GFRA ack.
        try:
            cmd, ack = self._read_next_msg(max_try_times=self._frame_read_try_times)
        except SenxorReadTimeoutError:
            # If the senxor is not in the stream mode, the read operation will timeout.
            # In this case, we should raise the error.
            self._logger.error("read gfra request no data")
            raise

        return self.parser._parse_ack_gfra(ack)

    @_rw_op_wrapper
    def read_reg(self, reg: int) -> int:
        _reg_hex = hex(reg)
        self._logger.debug("read reg request", reg=_reg_hex)
        read_cmd = self.parser._get_rreg_cmd(reg)
        self._flush_gfra_buffer()
        self.ser.write(read_cmd)
        cmd, ack = self._read_next_msg()
        if cmd == SenxorMsgParser.CMD_GFRA:
            self.gfra_buffer = ack
            cmd, ack = self._read_next_msg()
        if cmd != SenxorMsgParser.CMD_RREG:
            self._logger.error("unexpected read reg response", reg=_reg_hex, cmd=cmd)
            raise RuntimeError("Unexpected Error: The ack of the read_reg is not expected", cmd)
        reg_value = self.parser._parse_ack_rreg(ack)
        self._logger.debug("read reg success", reg=_reg_hex, value=reg_value)
        return reg_value

    @_rw_op_wrapper
    def read_regs(self, regs: list[int]) -> dict[int, int]:
        if not isinstance(regs, list):
            raise TypeError("regs must be a list of integers", regs=regs)
        _regs_hex = [hex(r) for r in regs]
        self._logger.debug("read multiple regs request")
        read_cmd = self.parser._get_rrse_cmd(regs)
        self._flush_gfra_buffer()
        self.ser.write(read_cmd)
        cmd, ack = self._read_next_msg()
        if cmd == SenxorMsgParser.CMD_GFRA:
            self.gfra_buffer = ack
            cmd, ack = self._read_next_msg()
        if cmd != SenxorMsgParser.CMD_RRSE:
            self._logger.error("unexpected read multiple regs response", cmd=cmd)
            raise RuntimeError("Unexpected Error: The ack of the read_regs is not expected", cmd)
        reg_values = self.parser._parse_ack_rrse(ack)
        self._logger.debug("read multiple regs success", regs=_regs_hex)
        return reg_values

    @_rw_op_wrapper
    def write_reg(self, reg: int, value: int) -> None:
        _reg_hex = hex(reg)
        self._logger.debug("write reg request", reg=_reg_hex, value=value)
        write_cmd = self.parser._get_wreg_cmd(reg, value)
        self._flush_gfra_buffer()
        self.ser.write(write_cmd)
        cmd, ack = self._read_next_msg()
        if cmd == SenxorMsgParser.CMD_GFRA:
            self.gfra_buffer = ack
            cmd, ack = self._read_next_msg()
        if cmd != SenxorMsgParser.CMD_WREG:
            self._logger.error("unexpected write reg response", reg=_reg_hex, value=value, cmd=cmd)
            raise RuntimeError("Unexpected Error: The ack of the write_reg is not expected", cmd)
        self.parser._parse_ack_wreg(ack)
        self._logger.debug("write reg success", reg=_reg_hex, value=value)

    def set_frame_read_timeout(self, timeout: float) -> None:
        self._logger.debug("setting frame read timeout", timeout=timeout)
        self._frame_read_timeout = timeout
        ser_read_timeout = self.ser.timeout
        if ser_read_timeout is None:
            self._frame_read_try_times = 1
        else:
            self._frame_read_try_times = int(self._frame_read_timeout / ser_read_timeout) + 1

    # Do not wrap this function with _rw_op_wrapper.
    # Do not use this function directly.
    # This function should be called by the method with the error handler.
    def _read_next_msg(self, max_try_times: int = 1) -> tuple[bytes, bytes]:
        """Read the next ack from the senxor.

        Parameters
        ----------
        max_try_times : int, optional
            The maximum number of times to try to read the ack.

        Returns
        -------
        tuple[bytes, bytes] | None
            The command and acknowledgement of the ack.
            If there is no ack from the port after the maximum number of tries,
            the function will return None.

        Raises
        ------
        SenxorMsgHeaderError
            The ack header is not valid.
            Which means the input buffer should be realigned.
        ChecksumError
            The checksum check failed.
        Exception
            Any other exception.

        """
        try_times = 0

        while try_times < max_try_times:
            try_times += 1
            if self._error_msg_clear_flag:
                # If the msg is corrupted, we need to read until the next msg header to
                # re-align the buffer. So after re-align, the next msg header only have
                # the msg_length. e.g. "2808"
                msg_header = self.ser.read(SenxorMsgParser.LEN_MSG_LENGTH)
                msg_header = SenxorMsgParser.MSG_PREFIX + msg_header
                self._error_msg_clear_flag = False
            else:
                # e.g. "   #2808"
                msg_header = self.ser.read(SenxorMsgParser.LEN_MSG_HEADER)
            if msg_header != b"":
                break
            if try_times == max_try_times:
                self._logger.error("read next msg timeout", try_times=try_times)
                raise SenxorReadTimeoutError

        if len(msg_header) != SenxorMsgParser.LEN_MSG_HEADER:
            self._logger.error("invalid ack header length", length=len(msg_header))
            raise RuntimeError("Unexpected Error: msg_header length is not expected")
        if not msg_header.startswith(SenxorMsgParser.MSG_PREFIX):
            self._logger.error("invalid ack header", header=str(msg_header))
            raise InvalidAckHeaderError(msg_header)

        msg_length_str = msg_header[SenxorMsgParser.LEN_MSG_PREFIX :]
        msg_length = SenxorMsgParser._parse_msg_length(msg_length_str)
        msg_body = self.ser.read(msg_length)

        if len(msg_body) != msg_length:
            # May happen when the physically read timeout.
            # For now we don't observe this error.
            self._logger.error("ack body length mismatch", expected=msg_length, actual=len(msg_body))
            raise RuntimeError("Unexpected Error: msg_body length is not expected")

        try:
            cmd, ack, checksum = SenxorMsgParser._parse_msg_body(msg_body)
        except InvalidAckBodyError as e:
            self._logger.error("invalid ack body", error=str(e))
            raise

        if cmd != SenxorMsgParser.CMD_GFRA or self.validate_gfra_checksum:
            # Note: The checksum includes the msg_length_str.
            to_check = msg_length_str + msg_body[: -SenxorMsgParser.LEN_BODY_CHECKSUM]
            try:
                self.parser._check_msg_checksum(to_check, checksum)
            except ChecksumError as e:
                self._logger.error(
                    "checksum validation failed",
                    expected=e.expected_checksum,
                    actual=e.message_checksum,
                )
                raise
        # self._logger.debug("read next msg success", cmd=cmd)

        return cmd, ack

    def _flush_gfra_buffer(self) -> None:
        # If there is one or more GFRA ack in the buffer, clear them before write to the port
        #  to avoid the serial error.

        ack = None
        while self.ser.in_waiting > 0:
            cmd, ack = self._read_next_msg()
            self._logger.debug("flush gfra buffer", in_waiting=self.ser.in_waiting)
            if cmd != SenxorMsgParser.CMD_GFRA:
                self._logger.error("unexpected non gfra ack during flush", cmd=cmd)
                raise RuntimeError("Unexpected Error: Unparsed non-GFRA ack in the buffer")
        if ack is not None:
            self.gfra_buffer = ack

    @property
    def gfra_buffer(self) -> bytes:
        return self._gfra_buffer

    @gfra_buffer.setter
    def gfra_buffer(self, value: bytes) -> None:
        self._gfra_buffer = value
        self._gfra_buffer_timestamp = time.time()

    @_rw_op_wrapper
    def _boot_clear(self) -> None:
        stop_stream = False
        if stop_stream:
            STOP_STREAM_CMD = self.parser._get_wreg_cmd(0xB1, 0b00000000)
            STOP_STREAM_ACK = b"   #0008WREG01FD"
            # If the senxor is in streaming mode when the port is opened,
            # the unaligned data will be written to the buffer.
            # Which will occur the error in booting.

            # This function try to clear the buffer and stop the streaming mode.
            self.ser.reset_input_buffer()
            self.ser.write(STOP_STREAM_CMD)
            timeout = self.ser.timeout
            self.ser.timeout = self._frame_read_timeout
            self.ser.read_until(STOP_STREAM_ACK)
            self.ser.timeout = timeout
        else:
            time.sleep(0.01)
            if self.ser.in_waiting > 0:
                self._clear_error_msg()
        self._logger.debug("boot clear successd")

    def _init_error_policy(self) -> None:
        self._error_policy: dict[type[Exception], Policy] = {
            InvalidAckHeaderError: Policy(callback=self._on_ack_error),
            InvalidAckBodyError: Policy(callback=self._on_ack_error, retry_times=10),
            SenxorReadTimeoutError: Policy(callback=None, retry_times=0),
            SerialException: Policy(callback=self._on_lost_connection_error, retry_times=0),
        }

    def error_handler(
        self,
        err: Exception,
        func: Callable,
        func_args: tuple[Any, ...],
        func_kwargs: dict[str, Any],
    ) -> Any:
        policy = self._error_policy.get(type(err), None)

        if policy is None:
            self._logger.error(
                "unhandled error",
                error=str(err),
                func=func.__name__,
                func_args=func_args,
                func_kwargs=func_kwargs,
            )
            raise err
        else:
            if policy.callback is not None:
                policy.callback(err)
            retry_times = policy.retry_times

        for _ in range(retry_times):
            try:
                if hasattr(func, "__self__"):
                    res = func(*func_args, **func_kwargs)
                else:
                    res = func(self, *func_args, **func_kwargs)
                self._logger.debug("retry success", func=func.__name__)
                return res
            except Exception as retry_err:  # noqa: PERF203
                err = retry_err
                time.sleep(0.01)

        raise err

    def _on_ack_error(self, _: Exception) -> None:
        self._clear_error_msg()

    def _on_lost_connection_error(self, _: Exception) -> None:
        self._is_connected = False
        self._logger.error("lost connection")
        raise SenxorNotConnectedError

    def _clear_error_msg(self) -> None:
        """Clear the error ack from the buffer and re-align the buffer to the next msg header."""
        data = self.ser.read_until(self.parser.MSG_PREFIX)
        # Sometimes there is no next ack after the error ack. So we don't need to set the flag.
        if data.endswith(self.parser.MSG_PREFIX):
            self._error_msg_clear_flag = True
        self._logger.debug("clear error msg")
