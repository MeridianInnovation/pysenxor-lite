# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Register definitions for Senxor devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from senxor.log import get_logger
from senxor.regmap._reg import Register, _RegisterDef, _RegisterDescriptor

if TYPE_CHECKING:
    from collections.abc import Iterator

    from senxor.regmap._regmap import _RegMap


class Registers:
    MCU_RESET = _RegisterDescriptor(
        _RegisterDef(
            name="MCU_RESET",
            addr=0x00,
            readable=False,
            writable=True,
            desc="Software Reset of the MI48",
            auto_reset=True,
        ),
    )

    HOST_XFER_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="HOST_XFER_CTRL",
            addr=0x01,
            readable=True,
            writable=True,
            desc="Host DMA transfer control",
            auto_reset=True,
        ),
    )

    SPI_RTY = _RegisterDescriptor(
        _RegisterDef(
            name="SPI_RTY",
            addr=0x19,
            readable=True,
            writable=True,
            desc="SPI retransmission control",
            auto_reset=True,
        ),
    )

    FRAME_MODE = _RegisterDescriptor(
        _RegisterDef(
            name="FRAME_MODE",
            addr=0xB1,
            readable=True,
            writable=True,
            desc="Control capture and readout of thermal data",
            auto_reset=True,
        ),
    )

    FW_VERSION_1 = _RegisterDescriptor(
        _RegisterDef(
            name="FW_VERSION_1",
            addr=0xB2,
            readable=True,
            writable=False,
            desc="Firmware Version (Major, Minor)",
        ),
    )

    FW_VERSION_2 = _RegisterDescriptor(
        _RegisterDef(
            name="FW_VERSION_2",
            addr=0xB3,
            readable=True,
            writable=False,
            desc="Firmware Version (Build)",
        ),
    )

    FRAME_RATE = _RegisterDescriptor(
        _RegisterDef(
            name="FRAME_RATE",
            addr=0xB4,
            readable=True,
            writable=True,
            desc="Frame rate",
        ),
    )

    SLEEP_MODE = _RegisterDescriptor(
        _RegisterDef(
            name="SLEEP_MODE",
            addr=0xB5,
            readable=True,
            writable=True,
            desc="Control of low power state",
            auto_reset=True,
        ),
    )

    STATUS = _RegisterDescriptor(
        _RegisterDef(
            name="STATUS",
            addr=0xB6,
            readable=True,
            writable=False,
            desc="MI48 and SenXor Status",
            auto_reset=True,
        ),
    )

    CLK_SPEED = _RegisterDescriptor(
        _RegisterDef(
            name="CLK_SPEED",
            addr=0xB7,
            readable=True,
            writable=True,
            desc="Control of internal clock parameters",
        ),
    )

    SENXOR_GAIN = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_GAIN",
            addr=0xB9,
            readable=True,
            writable=True,
            desc="Module ADC gain control",
        ),
    )

    SENXOR_TYPE = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_TYPE",
            addr=0xBA,
            readable=True,
            writable=False,
            desc="SenXor chip type",
        ),
    )

    MODULE_TYPE = _RegisterDescriptor(
        _RegisterDef(
            name="MODULE_TYPE",
            addr=0xBB,
            readable=True,
            writable=False,
            desc="Module type (chip-lens combination)",
        ),
    )

    MCU_TYPE = _RegisterDescriptor(
        _RegisterDef(
            name="MCU_TYPE",
            addr=0x33,
            readable=True,
            writable=False,
            desc="MCU type",
        ),
    )

    TEMP_CONVERT_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="TEMP_CONVERT_CTRL",
            addr=0xBC,
            readable=True,
            writable=True,
            desc="Temperature Conversion Control",
        ),
    )

    SENSITIVITY_FACTOR = _RegisterDescriptor(
        _RegisterDef(
            name="SENSITIVITY_FACTOR",
            addr=0xC2,
            readable=True,
            writable=True,
            desc="Sensitivity correction factor",
        ),
    )

    SELF_CALIBRATION = _RegisterDescriptor(
        _RegisterDef(
            name="SELF_CALIBRATION",
            addr=0xC5,
            readable=True,
            writable=True,
            desc="Self-Calibration of column offset",
            auto_reset=True,
        ),
    )

    EMISSIVITY = _RegisterDescriptor(
        _RegisterDef(
            name="EMISSIVITY",
            addr=0xCA,
            readable=True,
            writable=True,
            desc="Emissivity value for temperature conversion",
        ),
    )

    OFFSET_CORR = _RegisterDescriptor(
        _RegisterDef(
            name="OFFSET_CORR",
            addr=0xCB,
            readable=True,
            writable=True,
            desc="Offset correction to the entire frame",
        ),
    )

    OBJECT_TEMP_FACTOR = _RegisterDescriptor(
        _RegisterDef(
            name="OBJECT_TEMP_FACTOR",
            addr=0xCD,
            readable=True,
            writable=True,
            desc="Object temperature factor",
        ),
    )

    SENXOR_ID_0 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_0",
            addr=0xE0,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 0",
        ),
    )

    SENXOR_ID_1 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_1",
            addr=0xE1,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 1",
        ),
    )

    SENXOR_ID_2 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_2",
            addr=0xE2,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 2",
        ),
    )

    SENXOR_ID_3 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_3",
            addr=0xE3,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 3",
        ),
    )

    SENXOR_ID_4 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_4",
            addr=0xE4,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 4",
        ),
    )

    SENXOR_ID_5 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_5",
            addr=0xE5,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 5",
        ),
    )

    SENXOR_ID_6 = _RegisterDescriptor(
        _RegisterDef(
            name="SENXOR_ID_6",
            addr=0xE6,
            readable=True,
            writable=False,
            desc="Serial number of the attached camera module byte 6",
        ),
    )

    USER_FLASH_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="USER_FLASH_CTRL",
            addr=0xD8,
            readable=True,
            writable=True,
            desc="Enable/Disable host access to User Flash",
        ),
    )

    FRAME_FORMAT = _RegisterDescriptor(
        _RegisterDef(
            name="FRAME_FORMAT",
            addr=0x31,
            readable=True,
            writable=True,
            desc="Temperature units of output frame",
        ),
    )

    STARK_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="STARK_CTRL",
            addr=0x20,
            readable=True,
            writable=True,
            desc="STARK denoising filter control",
        ),
    )

    STARK_CUTOFF = _RegisterDescriptor(
        _RegisterDef(
            name="STARK_CUTOFF",
            addr=0x21,
            readable=True,
            writable=True,
            desc="STARK filter cutoff",
        ),
    )

    STARK_GRAD = _RegisterDescriptor(
        _RegisterDef(
            name="STARK_GRAD",
            addr=0x22,
            readable=True,
            writable=True,
            desc="STARK filter gradient",
        ),
    )

    STARK_SCALE = _RegisterDescriptor(
        _RegisterDef(
            name="STARK_SCALE",
            addr=0x23,
            readable=True,
            writable=True,
            desc="STARK filter scale",
        ),
    )

    MMS_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="MMS_CTRL",
            addr=0x25,
            readable=True,
            writable=True,
            desc="Min/Max Stabilization control",
        ),
    )

    MEDIAN_CTRL = _RegisterDescriptor(
        _RegisterDef(
            name="MEDIAN_CTRL",
            addr=0x30,
            readable=True,
            writable=True,
            desc="Median denoising filter control",
        ),
    )

    FILTER_CONTROL = _RegisterDescriptor(
        _RegisterDef(
            name="FILTER_CONTROL",
            addr=0xD0,
            readable=True,
            writable=True,
            desc="Temporal domain denoising filter control",
            auto_reset=True,
        ),
    )

    FILTER_SETTING_1_0 = _RegisterDescriptor(
        _RegisterDef(
            name="FILTER_SETTING_1_0",
            addr=0xD1,
            readable=True,
            writable=True,
            desc="Parameters for the temporal filter Low Byte",
        ),
    )

    FILTER_SETTING_1_1 = _RegisterDescriptor(
        _RegisterDef(
            name="FILTER_SETTING_1_1",
            addr=0xD2,
            readable=True,
            writable=True,
            desc="Parameters for the temporal filter High Byte",
        ),
    )

    REG_0x00 = MCU_RESET
    REG_0x01 = HOST_XFER_CTRL
    REG_0x19 = SPI_RTY
    REG_0xB1 = FRAME_MODE
    REG_0xB2 = FW_VERSION_1
    REG_0xB3 = FW_VERSION_2
    REG_0xB4 = FRAME_RATE
    REG_0xB5 = SLEEP_MODE
    REG_0xB6 = STATUS
    REG_0xB7 = CLK_SPEED
    REG_0xB9 = SENXOR_GAIN
    REG_0xBA = SENXOR_TYPE
    REG_0xBB = MODULE_TYPE
    REG_0x33 = MCU_TYPE
    REG_0xBC = TEMP_CONVERT_CTRL
    REG_0xC2 = SENSITIVITY_FACTOR
    REG_0xC5 = SELF_CALIBRATION
    REG_0xCA = EMISSIVITY
    REG_0xCB = OFFSET_CORR
    REG_0xCD = OBJECT_TEMP_FACTOR
    REG_0xE0 = SENXOR_ID_0
    REG_0xE1 = SENXOR_ID_1
    REG_0xE2 = SENXOR_ID_2
    REG_0xE3 = SENXOR_ID_3
    REG_0xE4 = SENXOR_ID_4
    REG_0xE5 = SENXOR_ID_5
    REG_0xE6 = SENXOR_ID_6
    REG_0xD8 = USER_FLASH_CTRL
    REG_0x31 = FRAME_FORMAT

    REG_0x20 = STARK_CTRL
    REG_0x21 = STARK_CUTOFF
    REG_0x22 = STARK_GRAD
    REG_0x23 = STARK_SCALE
    REG_0x25 = MMS_CTRL
    REG_0x30 = MEDIAN_CTRL
    REG_0xD0 = FILTER_CONTROL
    REG_0xD1 = FILTER_SETTING_1_0
    REG_0xD2 = FILTER_SETTING_1_1

    __reg_defs__: ClassVar[dict[str, _RegisterDef]] = {
        k: v._register_def
        for k, v in locals().items()
        if isinstance(v, _RegisterDescriptor) and not k.startswith("REG_")
    }

    __alter2name__: ClassVar[dict[str, str]] = {
        k: v._register_def.name
        for k, v in locals().items()
        if isinstance(v, _RegisterDescriptor) and k.startswith("REG_")
    }
    __addr2name__: ClassVar[dict[int, str]] = {v.addr: k for k, v in __reg_defs__.items()}
    __name2addr__: ClassVar[dict[str, int]] = {v: k for k, v in __addr2name__.items()}
    __name_list__: ClassVar[list[str]] = list(__reg_defs__.keys())
    __alter_list__: ClassVar[list[str]] = list(__alter2name__.keys())
    __addr_list__: ClassVar[list[int]] = list(__addr2name__.keys())
    __readable_list__: ClassVar[list[str]] = [k for k, v in __reg_defs__.items() if v.readable]
    __writable_list__: ClassVar[list[str]] = [k for k, v in __reg_defs__.items() if v.writable]
    __auto_reset_list__: ClassVar[list[str]] = [k for k, v in __reg_defs__.items() if v.auto_reset]

    def __init__(self, regmap: _RegMap):
        self._regmap = regmap
        self._log = get_logger(address=regmap.address)

        self._regs: dict[str, Register] = {k: getattr(self, k) for k in self.__name_list__}

    # ------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------

    @property
    def _regs_cache(self) -> dict[int, int]:
        return self._regmap._regs_cache

    @property
    def writable_regs(self) -> list[str]:
        """Return a set of all writable register names."""
        return self.__writable_list__.copy()

    @property
    def readable_regs(self) -> list[str]:
        """Return a set of all readable register names."""
        return self.__readable_list__.copy()

    @property
    def status(self) -> dict[int, int]:
        """Return a dictionary of all register values after last operation.

        Note: Due to some registers can be auto-reset, this may not reflect the current device state.

        Returns
        -------
        dict[int, int]
            The dictionary of register addresses and their values.

        """
        return self._regs_cache.copy()

    @property
    def regs(self) -> dict[str, Register]:
        """Return a dictionary of all register instances."""
        return self._regs

    # ------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------

    def get_addr(self, key: str | int | Register) -> int:
        """Get the address of a register.

        Parameters
        ----------
        key : str | int | Register
            The key of the register.

        Returns
        -------
        int
            The address of the register.

        """
        if isinstance(key, Register):
            return key.addr
        elif isinstance(key, str):
            return self[key].addr
        elif isinstance(key, int):
            return key
        else:
            raise TypeError(f"Invalid key type: {type(key)}")

    def read_all(self) -> dict[int, int]:
        """Read all registers from the device."""
        return self.read_regs(list(self.__addr_list__))

    def read_reg(self, addr: int) -> int:
        """Read a single register from the device."""
        value = self._regmap.read_reg(addr)
        return value

    def read_regs(self, addrs: list[int]) -> dict[int, int]:
        """Read multiple registers from the device."""
        values_dict = self._regmap.read_regs(addrs)
        return values_dict

    def get_reg(self, addr: int) -> int:
        """Get a register value by address.

        This method try to use the cached value instead of reading from the device if possible.
        """
        # The addr validation is done in __getitem__
        if self.__addr2name__[addr] in self.__auto_reset_list__ or addr not in self._regs_cache:
            self.read_reg(addr)
        return self._regs_cache[addr]

    def get_regs(self, addrs: list[int]) -> dict[int, int]:
        """Get multiple register values by addresses.

        This method try to use the cached value instead of reading from the device if possible.
        """
        need_read = [
            addr
            for addr in addrs
            if self.__addr2name__[addr] in self.__auto_reset_list__ or addr not in self._regs_cache
        ]
        if need_read:
            self.read_regs(need_read)
        return {addr: self._regs_cache[addr] for addr in addrs}

    def write_reg(self, addr: int, value: int):
        """Write a single register to the device."""
        if value < 0 or value > 255:
            raise ValueError(f"Register value must be in [0, 0xFF], got {value}")

        register_name = self.__addr2name__.get(addr, None)

        if register_name is not None and register_name not in self.__writable_list__:
            self._log.error("write protection violation", name=register_name, addr=addr, value=value)
            raise AttributeError(f"Register {register_name} (0x{addr:02X}) is read-only")

        self._regmap.write_reg(addr, value)

    def write_regs(self, values_dict: dict[int, int]):
        """Write multiple registers to the device."""
        for addr, value in values_dict.items():
            self.write_reg(addr, value)

    # ------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------

    def __getitem__(self, key: str | int) -> Register:
        if isinstance(key, str):
            if key in self.__name_list__:
                name = key
            elif key in self.__alter_list__:
                name = self.__alter2name__[key]
            else:
                raise KeyError(f"Invalid register name: {key}")
        elif isinstance(key, int):
            if key in self.__addr_list__:
                name = self.__addr2name__[key]
            else:
                raise KeyError(f"Invalid register address: {key}")
        else:
            raise KeyError(f"Invalid key type: {type(key)}")

        return getattr(self, name)

    def __setitem__(self, _, __):
        raise AttributeError("Direct assignment to Registers is not allowed.")

    def __iter__(self) -> Iterator[Register]:
        return iter(self._regs.values())

    def __repr__(self):
        return f"Registers(regmap={self._regmap})"
