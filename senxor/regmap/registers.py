# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from senxor.regmap.base import Register, RegisterDescriptor, describe

if TYPE_CHECKING:
    from senxor.regmap.types import RegisterName


class Registers:
    """The definition of the registers for the senxor.

    You can use this class to get the register definitions statically, without connecting to a device.

    Attributes
    ----------
    __regs__ : list[type[Register]]
        The list of register definitions.
    __addrs__ : dict[int, RegisterName]
        The dictionary of register addresses to register names.

    Examples
    --------
    >>> from senxor.regmap import Registers
    >>> Registers.__regs__
    ['MCU_RESET', ...]
    >>> Registers.MCU_RESET.name
    'MCU_RESET'
    >>> Registers.MCU_RESET.address
    0x00
    >>> Registers.MCU_RESET.description
    'Software Reset of the MI48'
    >>> Registers.MCU_RESET.writable
    True
    >>> Registers.MCU_RESET.readable
    True
    >>> Registers.MCU_RESET.self_reset
    True

    self_reset: Whether the register value can be modified by the senxor itself.

    """

    __regs__: ClassVar[list[type[Register]]] = []
    __addrs__: ClassVar[dict[int, RegisterName]] = {}

    def __init__(self):
        raise RuntimeError("Do not instantiate this class directly.")

    @describe
    class MCU_RESET(Register):
        name = "MCU_RESET"
        description = "Software Reset of the MI48"
        address = 0x00
        writable = True
        readable = True

        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class HOST_XFER_CTRL(Register):
        name = "HOST_XFER_CTRL"
        description = "Host DMA transfer control"
        address = 0x01
        writable = True
        readable = True

        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class SPI_RTY(Register):
        name = "SPI_RTY"
        description = "SPI retransmission control"
        address = 0x19
        writable = True
        readable = True

        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class FRAME_MODE(Register):
        name = "FRAME_MODE"
        description = "Control capture and readout of thermal data"
        address = 0xB1
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class FW_VERSION_1(Register):
        name = "FW_VERSION_1"
        description = "Firmware Version (Major, Minor)"
        address = 0xB2
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class FW_VERSION_2(Register):
        name = "FW_VERSION_2"
        description = "Firmware Version (Build)"
        address = 0xB3
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class FRAME_RATE(Register):
        name = "FRAME_RATE"
        description = "Frame rate"
        address = 0xB4
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SLEEP_MODE(Register):
        name = "SLEEP_MODE"
        description = "Control of low power state"
        address = 0xB5
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class STATUS(Register):
        name = "STATUS"
        description = "MI48 and SenXor Status"
        address = 0xB6
        writable = False
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class CLK_SPEED(Register):
        name = "CLK_SPEED"
        description = "Control of internal clock parameters"
        address = 0xB7
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SENXOR_GAIN(Register):
        name = "SENXOR_GAIN"
        description = "Module ADC gain control"
        address = 0xB9
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SENXOR_TYPE(Register):
        name = "SENXOR_TYPE"
        description = "SenXor chip type"
        address = 0xBA
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class MODULE_TYPE(Register):
        name = "MODULE_TYPE"
        description = "Module type (chip-lens combination)"
        address = 0xBB
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class MCU_TYPE(Register):
        name = "MCU_TYPE"
        description = "MCU type"
        address = 0x33
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class TEMP_CONVERT_CTRL(Register):
        name = "TEMP_CONVERT_CTRL"
        description = "Temperature Conversion Control"
        address = 0xBC
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SENSITIVITY_FACTOR(Register):
        name = "SENSITIVITY_FACTOR"
        description = "Sensitivity correction factor"
        address = 0xC2
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SELF_CALIBRATION(Register):
        name = "SELF_CALIBRATION"
        description = "Self-Calibration of column offset"
        address = 0xC5
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class EMISSIVITY(Register):
        name = "EMISSIVITY"
        description = "Emissivity value for temperature conversion"
        address = 0xCA
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class OFFSET_CORR(Register):
        name = "OFFSET_CORR"
        description = "Offset correction to the entire frame"
        address = 0xCB
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class OBJECT_TEMP_FACTOR(Register):
        name = "OBJECT_TEMP_FACTOR"
        description = "Object temperature factor"
        address = 0xCD
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class SENXOR_ID_0(Register):
        name = "SENXOR_ID_0"
        description = "SenXor ID (0)"
        address = 0xE0
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_1(Register):
        name = "SENXOR_ID_1"
        description = "Serial number of the attached camera module byte 1"
        address = 0xE1
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_2(Register):
        name = "SENXOR_ID_2"
        description = "Serial number of the attached camera module byte 2"
        address = 0xE2
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_3(Register):
        name = "SENXOR_ID_3"
        description = "Serial number of the attached camera module byte 3"
        address = 0xE3
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_4(Register):
        name = "SENXOR_ID_4"
        description = "Serial number of the attached camera module byte 4"
        address = 0xE4
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_5(Register):
        name = "SENXOR_ID_5"
        description = "Serial number of the attached camera module byte 5"
        address = 0xE5
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class SENXOR_ID_6(Register):
        name = "SENXOR_ID_6"
        description = "Serial number of the attached camera module byte 6"
        address = 0xE6
        writable = False
        readable = True
        self_reset = False
        enabled = True
        default_value = None

    @describe
    class USER_FLASH_CTRL(Register):
        name = "USER_FLASH_CTRL"
        description = "Enable/Disable host access to User Flash"
        address = 0xD8
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class FRAME_FORMAT(Register):
        name = "FRAME_FORMAT"
        description = "Temperature units of output frame"
        address = 0x31
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class STARK_CTRL(Register):
        name = "STARK_CTRL"
        description = "STARK denoising filter control"
        address = 0x20
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class STARK_CUTOFF(Register):
        name = "STARK_CUTOFF"
        description = "STARK filter cutoff"
        address = 0x21
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class STARK_GRAD(Register):
        name = "STARK_GRAD"
        description = "STARK filter gradient"
        address = 0x22
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class STARK_SCALE(Register):
        name = "STARK_SCALE"
        description = "STARK filter scale"
        address = 0x23
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class MMS_CTRL(Register):
        name = "MMS_CTRL"
        description = "Min/Max Stabilization control"
        address = 0x25
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class MEDIAN_CTRL(Register):
        name = "MEDIAN_CTRL"
        description = "Median denoising filter control"
        address = 0x30
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class FILTER_CONTROL(Register):
        name = "FILTER_CONTROL"
        description = "Temporal domain denoising filter control"
        address = 0xD0
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = 0x00

    @describe
    class FILTER_SETTING_1_0(Register):
        name = "FILTER_SETTING_1_0"
        description = "Parameters for the temporal filter Low Byte"
        address = 0xD1
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00

    @describe
    class FILTER_SETTING_1_1(Register):
        name = "FILTER_SETTING_1_1"
        description = "Parameters for the temporal filter High Byte"
        address = 0xD2
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x00


Registers.__regs__ = [v.cls for v in Registers.__dict__.values() if isinstance(v, RegisterDescriptor)]
Registers.__addrs__ = {register.address: register.name for register in Registers.__regs__}
