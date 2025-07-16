"""The core class for Senxor devices."""

from __future__ import annotations

import contextlib
import time
from typing import Any, Literal

import numpy as np
from structlog import get_logger

from senxor._error import SenxorNotConnectedError, SenxorReadTimeoutError
from senxor._interface import SENXOR_CONNECTION_TYPES
from senxor.consts import SENXOR_TYPE2FRAME_SHAPE
from senxor.proc import dk_to_celsius, raw_to_frame
from senxor.regmap import Register, Registers

logger = get_logger("senxor")


class Senxor:
    def __init__(
        self,
        address: Any,
        interface_type: Literal["serial"] | None = None,
        auto_open: bool = True,
        stop_stream_on_connect: bool = True,
        get_status_on_connect: bool = True,
        **kwargs,
    ):
        """Initialize the senxor.

        Parameters
        ----------
        address : Any
            The address of the senxor.
        interface_type : Literal["serial"] | None, optional
            The type of the interface, by default None.
        auto_open : bool, optional
            Whether to open the senxor automatically, by default True.
        stop_stream_on_connect : bool, optional
            Whether to stop the stream automatically on connect, by default True.
        get_status_on_connect : bool, optional
            Whether to get the status of the senxor automatically on connect, by default True.
        kwargs : Any
            The extra keyword arguments for the interface.

        Raises
        ------
        ValueError
            If the address is not valid for any of the supported types.

        """
        logger.info(
            "init Senxor",
            address=address,
            type=interface_type,
            auto_open=auto_open,
            stop_stream=stop_stream_on_connect,
            get_status=get_status_on_connect,
            **kwargs,
        )

        if interface_type is None:
            possible_types = []
            for t, interface_class in SENXOR_CONNECTION_TYPES.items():
                if interface_class.is_valid_address(address):
                    possible_types.append(t)
            if len(possible_types) == 1:
                interface_type = possible_types[0]
            elif len(possible_types) == 0:
                raise ValueError(f"{address} is not a valid address for any of the supported types.")
            else:
                raise ValueError(
                    f"{address} could be one of the following types: {possible_types}, please specify the type.",
                )

        self.type = interface_type
        self.interface = SENXOR_CONNECTION_TYPES[interface_type](address, **kwargs)  # type: ignore[call-arg]
        self.get_status_on_connect = get_status_on_connect
        self.stop_stream_on_connect = stop_stream_on_connect

        self.regs: Registers = Registers(self)

        if auto_open:
            self.open()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def open(self):
        """Open the senxor. If the senxor is already connected, do nothing."""
        if self.is_connected:
            return

        time_start = time.time()
        self.interface.open()
        self._logger = get_logger("senxor").bind(address=self.address)

        if self.stop_stream_on_connect:
            self.stop_stream()

        if self.get_status_on_connect:
            self.regs.read_all()

        time_cost = int((time.time() - time_start) * 1000)
        self._logger.info("open senxor success", address=self.address, type=self.type, startup_time=f"{time_cost}ms")

    def close(self):
        """Close the senxor. If the senxor is not connected, do nothing."""
        if not self.is_connected:
            return
        with contextlib.suppress(SenxorNotConnectedError):
            self.stop_stream()

        self._logger.info("closing senxor")
        self.interface.close()
        self._logger.info("close senxor success")

    @property
    def is_streaming(self) -> bool:
        # TODO: Replace the implementation with senxor.fields
        frame_mode = self.regs.FRAME_MODE.get()
        res = (frame_mode & 0b00000010) == 0b00000010
        return res

    @property
    def is_connected(self) -> bool:
        is_connected = self.interface.is_connected
        if is_connected is None:
            # We assume the device is connected if the connection cannot be checked.
            return True
        else:
            return is_connected

    @property
    def address(self) -> Any:
        return self.interface.address

    def start_stream(self):
        """Start the stream mode."""
        # TODO: Replace the implementation with senxor.fields
        self.regs.FRAME_MODE.set(0b00000010)
        self._logger.info("start stream")

    def stop_stream(self):
        """Stop the stream mode."""
        # TODO: Replace the implementation with senxor.fields
        if self.is_connected:
            self.regs.FRAME_MODE.set(0b00000000)
        self._logger.info("stop stream")

    def read(
        self,
        block: bool = True,
        *,
        raw: bool = False,
        celsius: bool = True,
    ) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """Read the frame data from the senxor, return (header: np.ndarray[uint16], frame: np.ndarray).

        The header is a 1D numpy array of uint16, check documentation for more details.
        The frame depends on the `raw` and `celsius` parameters.
        By default, the frame is a numpy array with shape (height, width), dtype is float32, each element means the
        temperature in Celsius.

        Parameters
        ----------
        block : bool, optional
            Whether to block the read operation until a frame is available.
            If False, if no frame is available, return None immediately.
        raw : bool, optional
            Whether to return the raw data or the frame data.
            Raw data is a flat numpy array of uint16.
            Frame data is reshaped to a 2D numpy array of uint16.
            In the most cases, frame data is open to use.
        celsius : bool, optional
            Whether to convert the frame data to Celsius.
            If True, the frame data will be converted to Celsius, float32.
            If False, the frame data will be returned in 1/10 Kelvin, uint16.

        Returns
        -------
        tuple[np.ndarray, np.ndarray] | tuple[None, None]
            The frame data, as a tuple of two numpy arrays.
            The first array is the header data, the second array is the frame data.

            If `block=False` and no frame is available, return (None, None).

        Raises
        ------
        SenxorNotConnectedError
            If the senxor is not connected.
        RuntimeError
            If the senxor is not in the stream mode or single capture mode.
        SenxorReadTimeoutError
            If the read operation timeout due to other reasons.

        """
        if not self.is_connected:
            raise SenxorNotConnectedError
        try:
            resp = self.interface.read(block)
        except SenxorReadTimeoutError as e:
            if not self.is_streaming:
                raise RuntimeError("Senxor is not in the stream mode or single capture mode") from None
            else:
                raise e
        if resp is None:
            return None, None
        else:
            header, data = resp
            if celsius:
                data = dk_to_celsius(data)
            if not raw:
                data = raw_to_frame(data)
            return header, data

    def read_reg(self, reg: int | str | Register) -> int:
        """Read the value from a register.

        Notes
        -----
        - You need to know the register name or address to use this method.
        - For a more modern and editor-friendly approach, use `senxor.regs.REG_NAME` to benefit from autocompletion.
        - If you want to read multiple registers at once, `read_regs` is more efficient as it only communicates with the device once.

        Parameters
        ----------
        reg : int | str | Register
            The register to read from, specified as a Register instance, a register name, or an integer address.

        Returns
        -------
        int
            The value read from the register.

        Raises
        ------
        ValueError
            If the register is not readable.

        Examples
        --------
        >>> senxor.read_reg(senxor.regs.EMISSIVITY)
        95
        >>> senxor.read_reg("EMISSIVITY")
        95
        >>> senxor.read_reg(0xCA)
        95
        >>> senxor.read_reg(202)
        95

        """
        if not self.is_connected:
            raise SenxorNotConnectedError
        addr = self.regs.get_addr(reg)
        return self.regs.read_reg(addr)

    def read_regs(self, regs: list[str | int | Register]) -> dict[int, int]:
        """Read the values from multiple registers at once.

        Note: This method takes the almost same time as reading one register.

        Parameters
        ----------
        regs : list[str | int | Register]
            The list of registers to read from, specified as a list of register names, integer addresses, or Register instances.

        Returns
        -------
        dict[int, int]
            The dictionary of register addresses and their values.

        Raises
        ------
        ValueError
            If a register is not readable.

        Examples
        --------
        >>> senxor.regs_read([0xB1, 0xB2, 0xB3, 0xB4])
        {177: 0, 178: 0, 179: 0, 180: 0}

        """
        if not self.is_connected:
            raise SenxorNotConnectedError
        regs_addrs = [self.regs.get_addr(reg) for reg in regs]
        regs_values = self.regs.read_regs(regs_addrs)
        return regs_values

    def write_reg(self, reg: str | int | Register, value: int):
        """Write a value to a register.

        Parameters
        ----------
        reg : str | int | Register
            The register to write to, specified as a register name, integer address, or Register instance.
        value : int
            The value to write to the register (0-0xFF).

        Returns
        -------
        Any
            The result of the write operation, as returned by the interface.

        Raises
        ------
        ValueError
            If the register is not writable or the value is out of range.

        Examples
        --------
        >>> senxor.write_reg("EMISSIVITY", 0x5F)
        >>> senxor.write_reg(0xCA, 0x5F)
        >>> senxor.write_reg(senxor.regs.EMISSIVITY, 0x5F)

        """
        if not self.is_connected:
            raise SenxorNotConnectedError
        if value < 0 or value > 0xFF:
            raise ValueError(f"Value must be between 0 and 0xFF, got {value}")
        addr = self.regs.get_addr(reg)
        self.regs.write_reg(addr, value)

    def get_shape(self) -> tuple[int, int]:
        """Get the frame shape(height, width) of the senxor.

        Returns
        -------
        tuple[int, int]
            The frame shape(height, width) of the senxor.

        """
        # Although the frame shape depends on the senxor type, but the internal implementation of `read` method
        # do not rely on this method.

        senxor_type = self.regs.SENXOR_TYPE.get()
        frame_shape = SENXOR_TYPE2FRAME_SHAPE[senxor_type]
        return frame_shape

    def __repr__(self):
        return f"Senxor(address={self.address}, type={self.type})"
