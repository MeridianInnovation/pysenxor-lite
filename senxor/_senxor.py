# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""The core class for Senxor devices."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from senxor._interface import SENXOR_INTERFACES
from senxor.consts import SENXOR_TYPE2FRAME_SHAPE
from senxor.error import SenxorResponseTimeoutError
from senxor.log import get_logger
from senxor.proc import dk_to_celsius, raw_to_frame
from senxor.regmap import Register
from senxor.regmap._regmap import _RegMap

if TYPE_CHECKING:
    from senxor.regmap import Register


class Senxor:
    def __init__(
        self,
        address: Any,
        interface_type: Literal["serial"] | None = None,
        auto_open: bool = True,
        stop_stream_on_connect: bool | None = None,
        get_status_on_connect: bool | None = None,
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
            Whether to stop the stream automatically on connect, by default None.
        get_status_on_connect : bool, optional
            Whether to get the status of the senxor automatically on connect, by default None.
        kwargs : Any
            The extra keyword arguments for the interface.

        Raises
        ------
        ValueError
            If the address is not valid for any of the supported types.

        """
        logger = get_logger()
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
            for t, interface_class in SENXOR_INTERFACES.items():
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

        if get_status_on_connect is not None:
            logger.warning(
                "deprecated_param",
                msg="The `get_status_on_connect` parameter is deprecated and will be removed in future versions.",
            )
        if stop_stream_on_connect is not None:
            logger.warning(
                "deprecated_param",
                msg="The `stop_stream_on_connect` parameter is deprecated and will be removed in future versions.",
            )

        self.type = interface_type
        self.interface = SENXOR_INTERFACES[interface_type](address, **kwargs)  # type: ignore[call-arg]

        self._regmap = _RegMap(self)
        self.regs = self._regmap.regs
        self.fields = self._regmap.fields

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
        self._logger = get_logger(address=self.address)

        self.refresh_regmap()

        time_cost = int((time.time() - time_start) * 1000)
        self._logger.info("open senxor success", address=self.address, type=self.type, startup_time=f"{time_cost}ms")

    def close(self):
        """Close the senxor. If the senxor is not connected, do nothing."""
        if not self.is_connected:
            return

        self._logger.info("closing senxor")
        self.interface.close()
        self._logger.info("close senxor success")

    @property
    def is_streaming(self) -> bool:
        if self.is_connected:
            return bool(self.fields.CONTINUOUS_STREAM.get())
        else:
            return False

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
        self.fields.CONTINUOUS_STREAM.set(1)
        self._logger.info("start stream")

    def stop_stream(self):
        """Stop the stream mode."""
        self.fields.CONTINUOUS_STREAM.set(0)
        self._logger.info("stop stream")

    def refresh_regmap(self):
        """Refresh the regmap cache. This method will read all registers and update all fields.

        Then use `self.regs.status` and `self.fields.status` to get the status you want.

        Examples
        --------
        >>> senxor.refresh_regmap()
        >>> senxor.regs.status
        {177: 0, 0: 0, 1: 0, ...}
        >>> senxor.fields.status
        {"SW_RESET": 0, "DMA_TIMEOUT_ENABLE": 0, ...}

        """
        self._regmap.read_all()

    def read(
        self,
        block: bool = True,
        *,
        raw: bool = False,
        celsius: bool = True,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
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
        tuple[np.ndarray | None, np.ndarray | None]
            The frame data, as a tuple of two numpy arrays.
            The first array is the header data, the second array is the frame data.

            If `block=False` and no frame is available, return (None, None).

        Raises
        ------
        RuntimeError
            If the senxor is not in the stream mode or single capture mode.
        SenxorAckTimeoutError
            If the read operation timeout due to other reasons.

        """
        try:
            resp = self.interface.read(block)
        except SenxorResponseTimeoutError as e:
            if not self.is_streaming:
                raise RuntimeError("Senxor is not in the stream mode or single capture mode") from None
            else:
                raise e
        if resp is None:
            return None, None
        else:
            header, data_bytes = resp
            header = np.frombuffer(header, dtype=np.uint16) if header is not None else None
            data = np.frombuffer(data_bytes, dtype=np.uint16)
            if celsius and not self.fields.ADC_ENABLE.get():
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
        - If you want to read multiple registers at once, `read_regs` is more efficient as it only communicates with the
        device once.

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
        addr = self.regs.get_addr(reg)
        return self.regs.read_reg(addr)

    def read_regs(self, regs: list[str | int | Register]) -> dict[int, int]:
        """Read the values from multiple registers at once.

        Note: This method takes the almost same time as reading one register.

        Parameters
        ----------
        regs : list[str | int | Register]
            The list of registers to read from, specified as a list of register names, integer addresses, or Register
            instances.

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

        senxor_type = self.fields.SENXOR_TYPE.get()
        frame_shape = SENXOR_TYPE2FRAME_SHAPE[senxor_type]
        return frame_shape

    def get_production_year(self) -> int:
        """Get the production year.

        Returns
        -------
        int
            The production year.

        """
        production_year = self.fields.PRODUCTION_YEAR.get() + 2000
        return production_year

    def get_senxor_id_hex(self) -> str:
        """Get the senxor id(SN code) string in hex format.

        The senxor id is a hex string of 12 characters, the format is:
        `YYWWLLSSSSSS`, where:
        - `YY` is the production year (from 2000 to 2099).
        - `WW` is the production week.
        - `LL` is the manufacturing location.
        - `SSSSSS` is the serial number (from 000000 to 999999).

        Returns
        -------
        str
            The senxor id.

        """
        production_year = self.fields.PRODUCTION_YEAR.get()
        production_week = self.fields.PRODUCTION_WEEK.get()
        manuf_location = self.fields.MANUF_LOCATION.get()
        serial_number = self.fields.SERIAL_NUMBER.get()
        return f"{production_year:02X}{production_week:02X}{manuf_location:02X}{serial_number:06X}"

    def get_sn(self) -> str:
        """Get the SN code string. Same as `get_senxor_id_hex`.

        Returns
        -------
        str
            The SN code string.

        """
        return self.get_senxor_id_hex()

    def get_module_type(self) -> str:
        """Get the module type."""
        module_type = self.fields.MODULE_TYPE.display()
        return module_type

    def get_fw_version(self) -> str:
        """Get the firmware version string.

        Returns
        -------
        str
            The firmware version string.

        """
        major = self.fields.FW_VERSION_MAJOR.get()
        minor = self.fields.FW_VERSION_MINOR.get()
        build = self.fields.FW_VERSION_BUILD.get()
        return f"{major}.{minor}.{build}"

    def __repr__(self):
        return f"Senxor(address={self.address}, type={self.type})"

    # ------------------------------------------------------------
    # Backward compatibility code
    # ------------------------------------------------------------

    # These methods are for backward compatibility.
    # Please try to use the new methods instead.

    def regread(self, reg: str | int) -> int:
        return self.read_reg(reg)

    def regwrite(self, reg: str | int, value: int):
        return self.write_reg(reg, value)

    def start(self):
        return self.start_stream()

    def stop(self):
        return self.close()

    def stop_capture(self):
        return self.stop_stream()

    @property
    def fpa_shape(self) -> tuple[int, int]:
        nrows, ncols = self.get_shape()
        return ncols, nrows
