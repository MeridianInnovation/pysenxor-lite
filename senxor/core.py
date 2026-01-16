# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""The core class for Senxor devices."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Generic, Literal, overload

import numpy as np

from senxor.error import SenxorResponseTimeoutError
from senxor.helper import SenxorHelperMixin
from senxor.interface.protocol import TDevice
from senxor.log import get_logger
from senxor.proc import process_senxor_data
from senxor.regmap import SenxorRegistersManager

if TYPE_CHECKING:
    from senxor.interface import ISenxorInterface
    from senxor.regmap.types import RegisterName


class Senxor(SenxorHelperMixin, Generic[TDevice]):
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
        super().__init__()
        logger = get_logger()
        logger.info(
            "init_senxor_instance",
            name=interface.device.name,
            interface=str(interface),
        )
        self.interface = interface

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
        self._logger = get_logger(name=self.name)
        if self.is_connected:
            self._logger.info("senxor_already_opened")
            return
        self._logger.info("opening_senxor")
        time_start = time.time()
        self.interface.open()

        self.stop_stream()
        # Read readonly registers(device info registers) and cache the values.
        for reg in self.regs:
            if not reg.writable:
                reg.get()

        self._setup_senxor()

        time_cost = int((time.time() - time_start) * 1000)
        self._logger.info(
            "open_senxor_success",
            device=self.device,
            startup_time=f"{time_cost}ms",
            fw_version=self.get_fw_version(),
            module_type=self.get_module_type(),
            sn=self.get_sn(),
        )

    def close(self):
        """Close the senxor. If the senxor is not connected, do nothing."""
        if not self.is_connected:
            return

        self._logger.info("closing_senxor")
        self.interface.close()
        self._logger.info("close_senxor_success")

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
        self._logger.info("start_stream_success")

    def stop_stream(self):
        """Stop the stream mode."""
        self.fields.CONTINUOUS_STREAM.set(0)
        self._logger.info("stop_stream_success")

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
        block: Literal[False],
    ) -> tuple[np.ndarray | None, np.ndarray | None]: ...

    @overload
    def read(
        self,
        *,
        block: Literal[True] = True,
    ) -> tuple[np.ndarray | None, np.ndarray]: ...

    def read(
        self,
        *,
        block: bool = True,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Read a frame from the Senxor and return (header, frame).

        header : np.ndarray[uint16], 1-D
            Frame metadata; see the documentation for layout details.
        frame  : np.ndarray, 2-D, shape (height, width)
            - If ADC_ENABLE = 1 → dtype = uint16, values are raw ADC counts.
            - If ADC_ENABLE = 0 → dtype = float32, values are temperature in °C.

        Parameters
        ----------
        block : bool, optional
            Whether to block the read operation until a frame is available.
            If False, if no frame is available, return None immediately.

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
            is_adc_enabled = self.fields.ADC_ENABLE.get() == 1
            data = process_senxor_data(data_bytes, adc=is_adc_enabled)
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

    def _setup_senxor(self):
        # Ensure the TEMP_UNITS is set to 0
        temp_units = self.fields.TEMP_UNITS.value
        if temp_units != 0:
            self.fields.TEMP_UNITS.set(0, force=True)
            self._logger.warning(
                "reset_temp_units",
                msg="pysenxor internally force set TEMP_UNITS to 0",
                raw_value=temp_units,
            )
        # Ensure the NO_HEADER is set to 0
        no_header = self.fields.NO_HEADER.value
        if no_header != 0:
            self.fields.NO_HEADER.set(0, force=True)
            self._logger.warning(
                "reset_no_header",
                msg="pysenxor internally force set NO_HEADER to 0",
                raw_value=no_header,
            )

        # Read the ADC_ENABLE field and cache it.
        self.fields.ADC_ENABLE.get()

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
