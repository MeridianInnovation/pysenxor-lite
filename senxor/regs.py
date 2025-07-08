"""Register definitions for Senxor devices."""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import ClassVar


@dataclass(frozen=True)
class Register:
    """The definition of a register.

    This class is used to define a register of a Senxor device.

    Attributes
    ----------
    address : int
        The address of the register.
    readable : bool
        Whether the register is readable.
    writable : bool
        Whether the register is writable.
    desc : str
        The description of the register.

    """

    # Use __slots__ instead of slots=True to compatible with python 3.9
    __slots__ = ("address", "desc", "readable", "writable")

    address: int
    readable: bool
    writable: bool
    desc: str

    def __str__(self) -> str:
        r = "R" if self.readable else ""
        w = "W" if self.writable else ""

        access = f"{r}{w}"
        if not access:
            access = "NA"

        return f"0x{self.address:02X} ({access}) {self.desc}"

    def __repr__(self) -> str:
        return f"0x{self.address:02X}"


class REGS(Enum):
    """All registers of the SenXor.

    All register definitions for the SenXor device.
    Each register is represented as an enum member with its address, access permissions, and description.

    The enum members are named REG_0x<address> to match the register address.
    The enum members are also aliased to the register name for convenience.

    Examples
    --------
    >>> REGS.REG_0x00
    <REGS.REG_0x00: 0x00 (W) Software Reset of the MI48>

    >>> REGS.MCU_RESET
    <REGS.REG_0x00: 0x00 (W) Software Reset of the MI48>

    >>> REGS.REG_0x00.address
    0x00

    >>> REGS.REG_0x00.readable
    False

    >>> REGS.REG_0x00.writable
    True

    >>> REGS.REG_0x00.description
    "Software Reset of the MI48"

    """

    MCU_RESET = Register(
        0x00,
        False,
        True,
        "Software Reset of the MI48",
    )
    HOST_XFER_CTRL = Register(
        0x01,
        True,
        True,
        "Host DMA transfer control",
    )
    SPI_RTY = Register(
        0x19,
        True,
        True,
        "SPI retransmission control",
    )
    FRAME_MODE = Register(
        0xB1,
        True,
        True,
        "Control capture and readout of thermal data",
    )
    FW_VERSION_1 = Register(
        0xB2,
        True,
        False,
        "Firmware Version (Major, Minor)",
    )
    FW_VERSION_2 = Register(
        0xB3,
        True,
        False,
        "Firmware Version (Build)",
    )
    FRAME_RATE = Register(
        0xB4,
        True,
        True,
        "Frame rate",
    )
    SLEEP_MODE = Register(
        0xB5,
        True,
        True,
        "Control of low power state",
    )
    STATUS = Register(
        0xB6,
        True,
        False,
        "MI48 and SenXor Status",
    )
    CLK_SPEED = Register(
        0xB7,
        True,
        True,
        "Control of internal clock parameters",
    )
    SENXOR_GAIN = Register(
        0xB9,
        True,
        True,
        "Module ADC gain control",
    )
    SENXOR_TYPE = Register(
        0xBA,
        True,
        False,
        "SenXor chip type",
    )
    MODULE_TYPE = Register(
        0xBB,
        True,
        False,
        "Module type (chip-lens combination)",
    )
    TEMP_CONVERT_CTRL = Register(
        0xBC,
        True,
        True,
        "Temperature Conversion Control",
    )
    SENSITIVITY_FACTOR = Register(
        0xC2,
        True,
        True,
        "Sensitivity correction factor",
    )
    SELF_CALIBRATION = Register(
        0xC5,
        True,
        True,
        "Self-Calibration of column offset",
    )
    EMISSIVITY = Register(
        0xCA,
        True,
        True,
        "Emissivity value for temperature conversion",
    )
    OFFSET_CORR = Register(
        0xCB,
        True,
        True,
        "Offset correction to the entire frame",
    )
    OBJECT_TEMP_FACTOR = Register(
        0xCD,
        True,
        True,
        "Object temperature factor",
    )
    SENXOR_ID_0 = Register(
        0xE0,
        True,
        False,
        "Serial number of the attached camera module byte 0",
    )
    SENXOR_ID_1 = Register(
        0xE1,
        True,
        False,
        "Serial number of the attached camera module byte 1",
    )
    SENXOR_ID_2 = Register(
        0xE2,
        True,
        False,
        "Serial number of the attached camera module byte 2",
    )
    SENXOR_ID_3 = Register(
        0xE3,
        True,
        False,
        "Serial number of the attached camera module byte 3",
    )
    SENXOR_ID_4 = Register(
        0xE4,
        True,
        False,
        "Serial number of the attached camera module byte 4",
    )
    SENXOR_ID_5 = Register(
        0xE5,
        True,
        False,
        "Serial number of the attached camera module byte 5",
    )
    SENXOR_ID_6 = Register(
        0xE6,
        True,
        False,
        "Serial number of the attached camera module byte 6",
    )
    USER_FLASH_CTRL = Register(
        0xD8,
        True,
        True,
        "Enable/Disable host access to User Flash",
    )
    FRAME_FORMAT = Register(
        0x31,
        True,
        True,
        "Temperature units of output frame",
    )

    # These registers only support in MI48E4
    STARK_CTRL = Register(
        0x20,
        True,
        True,
        "STARK denoising filter control",
    )
    STARK_CUTOFF = Register(
        0x21,
        True,
        True,
        "STARK filter cutoff",
    )
    STARK_GRAD = Register(
        0x22,
        True,
        True,
        "STARK filter gradient",
    )
    STARK_SCALE = Register(
        0x23,
        True,
        True,
        "STARK filter scale",
    )
    MMS_CTRL = Register(
        0x25,
        True,
        True,
        "Min/Max Stabilization control",
    )
    MEDIAN_CTRL = Register(
        0x30,
        True,
        True,
        "Median denoising filter control",
    )
    FILTER_CONTROL = Register(
        0xD0,
        True,
        True,
        "Temporal domain denoising filter control",
    )
    FILTER_SETTING_1_0 = Register(
        0xD1,
        True,
        True,
        "Parameters for the temporal filter Low Byte",
    )
    FILTER_SETTING_1_1 = Register(
        0xD2,
        True,
        True,
        "Parameters for the temporal filter High Byte",
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

    _ignore_: ClassVar = ["_regs_dict", "_addr_dict", "_name_dict", "_readable_regs", "_writable_regs"]
    _regs_dict: ClassVar = {}  # type: ignore  # noqa: PGH003
    _addr_dict: ClassVar = {}  # type: ignore  # noqa: PGH003
    _name_dict: ClassVar = {}  # type: ignore  # noqa: PGH003
    _readable_regs: ClassVar = []
    _writable_regs: ClassVar = []

    @property
    def address(self) -> int:
        return self.value.address

    @property
    def readable(self) -> bool:
        return self.value.readable

    @property
    def writable(self) -> bool:
        return self.value.writable

    @property
    def description(self) -> str:
        return self.value.desc

    def __repr__(self) -> str:
        return f"REG_0x{self.address:02X}"

    @classmethod
    def from_addr(cls, addr: int) -> "REGS":
        """Get a register by its address.

        Parameters
        ----------
        addr : int
            The register address.

        Returns
        -------
        REGS
            The register with the given address.

        Raises
        ------
        ValueError
            If no register exists with the given address.

        """
        if not isinstance(addr, int):
            raise ValueError(f"Address must be an integer, got {type(addr)}")

        name = f"REG_0x{addr:02X}"
        reg = cls.__members__.get(name, None)
        if reg is None:
            raise ValueError(f"Unsupported register: 0x{addr:02X}")
        return reg

    @classmethod
    def list_all_names(cls) -> list[str]:
        """List all register names."""
        return list(cls._name_dict.keys())

    @classmethod
    def list_all_addrs(cls) -> list[int]:
        """List all register addresses.

        Returns
        -------
        list[int]
            List of all register addresses.

        """
        return list(cls._addr_dict.keys())

    @classmethod
    def list_all_regs(cls) -> list["REGS"]:
        """List all registers."""
        return list(cls._regs_dict.values())

    @classmethod
    @lru_cache(maxsize=1)
    def list_readable_regs(cls) -> list["REGS"]:
        """List all readable registers.

        Returns
        -------
        list[REGS]
            List of all readable registers.

        """
        return cls._readable_regs

    @classmethod
    @lru_cache(maxsize=1)
    def list_writable_regs(cls) -> list["REGS"]:
        """List all writable registers.

        Returns
        -------
        list[REGS]
            List of all writable registers.

        """
        return cls._writable_regs


REGS._regs_dict = {name: reg for name, reg in REGS.__members__.items() if not name.startswith("REG_0x")}
REGS._addr_dict = {reg.address: reg for reg in REGS._regs_dict.values()}
REGS._name_dict = {reg.name: reg for reg in REGS._regs_dict.values()}
REGS._readable_regs = [reg for reg in REGS._regs_dict.values() if reg.readable]
REGS._writable_regs = [reg for reg in REGS._regs_dict.values() if reg.writable]
