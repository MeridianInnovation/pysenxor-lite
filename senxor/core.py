# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""The core class for Senxor devices."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Generic, Literal, cast, overload

import numpy as np

from senxor.consts import FRAME_SHAPE2MODULE_CATEGORY, SENXOR_TYPE2FRAME_SHAPE
from senxor.error import SenxorResponseTimeoutError
from senxor.interface.protocol import TDevice
from senxor.log import get_logger
from senxor.proc import bytes_to_adc, bytes_to_raw, raw_to_frame, raw_to_temp
from senxor.regmap import SenxorRegistersManager

if TYPE_CHECKING:
    from senxor.interface import ISenxorInterface
    from senxor.regmap.types import RegisterName


class Senxor(Generic[TDevice]):
    def __init__(
        self,
        interface: ISenxorInterface[TDevice],
        *,
        auto_open: bool = True,
    ):
        """Initialize the senxor.

        Parameters
        ----------
        interface : TInterface
            The interface of the senxor.
        auto_open : bool, optional
            Whether to open the senxor automatically, by default True.

        """
        logger = get_logger()
        logger.info(
            "init Senxor",
            name=interface.device.name,
            interface=str(interface),
        )
        self.interface = interface

        self.read_temp_units: Literal["K", "C", "F"] = "C"
        self.regs = SenxorRegistersManager[TDevice](interface)
        self.fields = self.regs.fieldmap

        if auto_open:
            self.open()

    @property
    def device(self) -> TDevice:
        """Get the device instance."""
        return self.interface.device

    @property
    def name(self):
        """Get the name of the device."""
        return self.device.name

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
        self._logger = get_logger(name=self.name)

        self.stop_stream()

        if self.fields.TEMP_UNITS.value != 0:
            self.fields.TEMP_UNITS.set(0, force=True)
        if self.fields.NO_HEADER.value != 0:
            self.fields.NO_HEADER.set(0, force=True)

        time_cost = int((time.time() - time_start) * 1000)
        self._logger.info(
            "open senxor success",
            device=self.device,
            startup_time=f"{time_cost}ms",
        )

    def close(self):
        """Close the senxor. If the senxor is not connected, do nothing."""
        if not self.is_connected:
            return

        self._logger.info("closing senxor")
        self.interface.close()
        self._logger.info("close senxor success")

    @property
    def is_streaming(self) -> bool:
        """Whether the senxor is in the stream mode."""
        if self.is_connected:
            return bool(self.fields.CONTINUOUS_STREAM.get())
        else:
            return False

    @property
    def is_connected(self) -> bool:
        """Whether the senxor is connected."""
        is_connected = self.interface.is_connected
        if is_connected is None:
            # We assume the device is connected if the connection cannot be checked.
            return True
        else:
            return is_connected

    def start_stream(self):
        """Start the stream mode."""
        self.fields.CONTINUOUS_STREAM.set(1)
        self._logger.info("start stream")

    def stop_stream(self):
        """Stop the stream mode."""
        self.fields.CONTINUOUS_STREAM.set(0)
        self._logger.info("stop stream")

    def refresh_all(self):
        """Refresh the all registers and fields. This method will read all registers and update all fields.

        Then use `self.regs.cache` and `self.fields.cache` to get the cached values you want.

        Examples
        --------
        >>> senxor.refresh_all()
        >>> senxor.regs.cache
        {177: 0, 0: 0, 1: 0, ...}
        >>> senxor.fields.cache
        {"SW_RESET": 0, "DMA_TIMEOUT_ENABLE": 0, ...}

        """
        self.regs.refresh_all()

    @overload
    def read(
        self,
        *,
        raw: bool = False,
        celsius: bool | None = None,
    ) -> tuple[np.ndarray | None, np.ndarray]: ...

    @overload
    def read(
        self,
        *,
        block: Literal[False],
        raw: bool = False,
        celsius: bool | None = None,
    ) -> tuple[np.ndarray | None, np.ndarray | None]: ...

    @overload
    def read(
        self,
        *,
        block: Literal[True] = True,
        raw: bool = False,
        celsius: bool | None = None,
    ) -> tuple[np.ndarray | None, np.ndarray]: ...

    def read(
        self,
        *,
        block: bool = True,
        raw: bool = False,
        celsius: bool | None = None,
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
            header_bytes, data_bytes = self.interface.read(block)
        except SenxorResponseTimeoutError as e:
            if not self.is_streaming:
                raise SenxorResponseTimeoutError("Senxor is not in the stream mode or single capture mode") from None
            else:
                raise e

        if data_bytes is None:
            return None, None
        else:
            header = np.frombuffer(header_bytes, dtype=np.uint16) if header_bytes is not None else None
            frame_units = self.get_temp_units()
            if frame_units == "adc":
                data = bytes_to_adc(data_bytes)
            else:
                data = bytes_to_raw(data_bytes, unit=frame_units)
                if celsius:
                    self._logger.warning(
                        "`senxor.read(celsius=True)` will be deprecated, use `senxor.set_read_temp_units` instead.",
                    )
                    data = raw_to_temp(data, in_unit=frame_units, out_unit="C")
                else:
                    data = raw_to_temp(data, in_unit=frame_units, out_unit=self.read_temp_units)

            if not raw:
                data = raw_to_frame(data)

            return header, data

    def read_reg(self, reg: int | RegisterName) -> int:
        """Read the value from a register.

        Notes
        -----
        - You need to know the register name or address to use this method.
        - For a more modern and editor-friendly approach, use `senxor.regs.REG_NAME` to benefit from autocompletion.
        - If you want to read multiple registers at once, `read_regs` is more efficient as it only communicates with the
        device once.

        Parameters
        ----------
        reg : int | RegisterName
            The register to read from, specified as an integer address or a register name.

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
        if isinstance(reg, str):
            addr = self.regs.get_reg(reg).address
        elif isinstance(reg, int):
            addr = reg
        return self.regs.read_reg(addr)

    def read_regs(self, regs: list[int | RegisterName]) -> dict[int, int]:
        """Read the values from multiple registers at once.

        Note: This method takes the almost same time as reading one register.

        Parameters
        ----------
        regs : list[int | RegisterName]
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
        regs_addrs = [self.regs.get_reg(reg).address if isinstance(reg, str) else reg for reg in regs]
        regs_values = self.regs.read_regs(regs_addrs)
        return regs_values

    def write_reg(self, reg: int | RegisterName, value: int):
        """Write a value to a register.

        Parameters
        ----------
        reg : int | RegisterName
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
        if isinstance(reg, str):
            addr = self.regs.get_reg(reg).address
        elif isinstance(reg, int):
            addr = reg
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

    def get_temp_units(self) -> Literal["dK", "adc"]:
        """Get the temperature units configured on the device.

        The temperature units of the frame is determined by 'ADC_ENABLE' field.
        If 'ADC_ENABLE' is set to `1`, the temperature units is `adc`.
        Otherwise, the temperature units is `dK`.

        Returns
        -------
        Literal["dK", "adc"]
            The temperature units of the frame.
            - `dK`: 0.1 K
            - `adc`: ADC data(uint16)

        """
        if self.fields.ADC_ENABLE.get():
            return "adc"
        else:
            return "dK"

    def set_read_temp_units(self, temp_units: Literal["K", "C", "F"]):
        """Set the temperature units to use for the `read` method.

        Parameters
        ----------
        temp_units : Literal["K", "C", "F"]
            The temperature units to use for the `read` method.

        """
        if temp_units not in ["K", "C", "F"]:
            raise ValueError(f"Invalid temperature units: {temp_units}")
        self.read_temp_units = temp_units

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
        serial_number_0 = self.fields.SERIAL_NUMBER_0.get()
        serial_number_1 = self.fields.SERIAL_NUMBER_1.get()
        serial_number_2 = self.fields.SERIAL_NUMBER_2.get()
        serial_number = (serial_number_0 << 16) | (serial_number_1 << 8) | serial_number_2
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
        module_type = cast("str", self.fields.MODULE_TYPE.display)
        return module_type

    def get_module_category(self) -> Literal["Cougar", "Panther"]:
        """Get the module category."""
        frame_shape = self.get_shape()
        module_category = cast("Literal['Cougar', 'Panther']", FRAME_SHAPE2MODULE_CATEGORY.get(frame_shape))
        return module_category

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
        return f"Senxor(interface={self.interface})"

    # ------------------------------------------------------------
    # Backward compatibility code
    # ------------------------------------------------------------

    # These methods are for backward compatibility.
    # Please try to use the new methods instead.

    def regread(self, reg: int | RegisterName) -> int:
        return self.read_reg(reg)

    def regwrite(self, reg: int | RegisterName, value: int):
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
