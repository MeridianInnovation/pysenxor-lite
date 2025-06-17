from __future__ import annotations

import time
from typing import Any, Literal

import numpy as np
from structlog import get_logger

from senxor._error import SenxorReadTimeoutError
from senxor._interface import SENXOR_CONNECTION_TYPES
from senxor.proc import dk_to_celsius, raw_to_frame
from senxor.regs import REGS

logger = get_logger("senxor")


class _RegisterDict(dict):
    def __init__(self, senxor: Senxor):
        super().__init__()
        self.senxor = senxor

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise TypeError(f"Invalid key type: {type(key)}, expected int")
        if key not in self:
            value = self.senxor.reg_read(key)
            self[key] = value
        return super().__getitem__(key)


class Senxor:
    def __init__(
        self,
        address: Any,
        interface_type: Literal["serial"] | None = None,
        auto_open: bool = True,
        read_frame_mode: bool = True,
        stop_stream_on_connect: bool = True,
        get_status_on_connect: bool = True,
        **kwargs,
    ):
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
        self.read_frame_mode = read_frame_mode

        self.registers: dict[int, int] = _RegisterDict(self)

        if auto_open:
            self.open()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def open(self):
        if self.is_connected:
            return

        time_start = time.time()
        self.interface.open()
        self._logger = get_logger("senxor").bind(address=self.address)

        if self.stop_stream_on_connect:
            self.stop_stream()

        if self.get_status_on_connect:
            self.read_all_regs()

        time_cost = int((time.time() - time_start) * 1000)
        self._logger.info("open senxor success", address=self.address, type=self.type, startup_time=f"{time_cost}ms")

    def close(self):
        if not self.is_connected:
            return
        self.stop_stream()
        self._logger.info("closing senxor")
        self.interface.close()
        self._logger.info("close senxor success")

    @property
    def is_streaming(self) -> bool:
        # TODO: Replace the implementation with senxor.fields
        frame_mode = self.registers[REGS.FRAME_MODE.address]
        res = (frame_mode & 0b00000010) == 0b00000010
        return res

    @property
    def is_connected(self) -> bool | None:
        return self.interface.is_connected

    @property
    def address(self) -> Any:
        return self.interface.address

    def start_stream(self):
        # TODO: Replace the implementation with senxor.fields
        self.reg_write(REGS.FRAME_MODE, 0b00000010)
        self._logger.info("start stream")

    def stop_stream(self):
        # TODO: Replace the implementation with senxor.fields
        self.reg_write(REGS.FRAME_MODE, 0b00000000)
        self._logger.info("stop stream")

    def read(
        self,
        block: bool = True,
        *,
        raw: bool = False,
        celsius: bool = True,
    ) -> tuple[np.ndarray, np.ndarray] | None:
        """Read the frame data from the senxor, default unit is 1/10 Kelvin, uint16.

        Note: If the device is not in the stream mode, this method will return None after timeout.

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
        tuple[np.ndarray, np.ndarray] | None
            The frame data, as a tuple of two numpy arrays.
            The first array is the header data, the second array is the frame data.

            If the frame is not available, return None.

        """
        try:
            resp = self.interface.read(block)
        except SenxorReadTimeoutError as e:
            if not self.is_streaming:
                raise RuntimeError("Senxor is not in the stream mode or single capture mode") from None
            else:
                raise e
        if resp is None:
            return None
        else:
            header, data = resp
            if celsius:
                data = dk_to_celsius(data)
            if not raw:
                data = raw_to_frame(data)
            return header, data

    def reg_read(self, reg: REGS | int) -> int:
        """Read the value from a register.

        Note: If you want to read multiple registers at once, `regs_read` is more efficient.
        The `regs_read` only communicates with the device once.

        Parameters
        ----------
        reg : REGS | int
            The register to read from, specified as a REGS enum member or an integer address.

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
        >>> senxor.reg_read(REGS.EMISSIVITY)
        95
        >>> senxor.reg_read(REGS.REG_0xCA)
        95
        >>> senxor.reg_read(0xCA)
        95
        >>> senxor.reg_read(202)
        95

        """
        if not isinstance(reg, REGS):
            reg = REGS.from_addr(reg)
        if not reg.readable:
            raise ValueError(f"Register 0x{reg.address:02X} is not readable")
        try:
            val = self.interface.read_reg(reg.address)
        except Exception as e:
            self._logger.error("read register failed", reg=reg, error=e)

        self._logger.info("read reg success", reg=reg, value=val)
        self.registers[reg.address] = val
        return val

    def regs_read(self, regs: list[REGS] | list[int] | list[REGS | int]) -> dict[int, int]:
        """Read the values from multiple registers at once.

        Note: This method takes the almost same time as reading one register.

        Parameters
        ----------
        regs : list[REGS | int]
            The list of registers to read from, specified as a list of REGS enum members or integer addresses.

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
        regs_int = []
        for reg_ in regs:
            reg = REGS.from_addr(reg_) if not isinstance(reg_, REGS) else reg_
            if not reg.readable:
                raise ValueError(f"Reg 0x{reg.address:02X} is not readable")
            if reg.address in regs_int:
                raise ValueError(f"Reg 0x{reg.address:02X} is duplicated in the list: {regs}")
            regs_int.append(reg.address)
        try:
            regs_values = self.interface.read_regs(regs_int)
        except Exception as e:
            self._logger.error("read multiple registers failed", regs=regs, error=e)

        self._logger.info("read multiple registers success", regs=regs)
        self.registers.update(regs_values)
        return regs_values

    def reg_write(self, reg: REGS | int, value: int):
        """Write a value to a register.

        Parameters
        ----------
        reg : REGS | int
            The register to write to, specified as a REGS enum member or an integer address.
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
        >>> senxor.reg_write(REGS.EMISSIVITY, 0x5F)
        >>> senxor.reg_write(REGS.REG_0xCA, 0x5F)
        >>> senxor.reg_write(0xCA, 0x5F)

        """
        if not isinstance(reg, REGS):
            reg = REGS.from_addr(reg)
        if not reg.writable:
            raise ValueError(f"Register 0x{reg.address:02X} is not writable")

        if value < 0 or value > 0xFF:
            raise ValueError(f"Value must be between 0 and 0xFF, got {value}")

        try:
            self.interface.write_reg(reg.address, value)
        except Exception as e:
            self._logger.error("write register failed", reg=reg, value=value, error=e)

        self._logger.info("write register success", reg=reg, value=value)
        # TODO: Some regs will auto update the value after write.
        # e.g. FRAME_MODE will auto rollback after single frame is captured.
        # We need to handle this case.
        self.registers[reg.address] = value
        return value

    def read_all_regs(self, refresh: bool = False) -> dict[int, int]:
        """Get all registers and their values.

        Parameters
        ----------
        refresh : bool, optional
            Whether to re-read all registers from the device.

        Returns
        -------
        dict[int, int]
            The dictionary of register addresses and their values.

        """
        if not self.is_connected:
            raise ValueError("Device is not connected")

        if self.registers and not refresh:
            return self.registers

        self.registers.clear()
        self.registers.update(self.regs_read(REGS.list_readable_regs()))
        self._logger.info("read all registers success")
        return self.registers


if __name__ == "__main__":
    from senxor.log import setup_console_logger

    setup_console_logger()

    with Senxor("COM5", interface_type="serial") as senxor:
        senxor.start_stream()
        resp = senxor.read(block=True)
        if resp is not None:
            header, frame = resp
            print(frame.mean())

        senxor.reg_write(REGS.FRAME_FORMAT, 0b00000001)
