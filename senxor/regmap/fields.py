# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

# ruff: noqa: E501
from typing import ClassVar

from senxor.consts import MCU_TYPE as MCU_TYPE_MAP
from senxor.consts import MODULE_TYPE as MODULE_TYPE_MAP
from senxor.consts import SENXOR_TYPE as SENXOR_TYPE_MAP
from senxor.regmap.base import Field, FieldDescriptor, describe_field
from senxor.regmap.registers import Registers


class Fields:
    """The definition of the fields for the senxor.

    You can use this class to get the field definitions statically, without connecting to a device.

    Attributes
    ----------
    __fields__ : list[type[Field]]
        The list of field definitions.
    __reg2fields__ : dict[int, list[str]]
        The dictionary of register addresses to field names.

    Examples
    --------
    >>> from senxor.regmap import Fields
    >>> Fields.__fields__
    ['SW_RESET', ...]
    >>> Fields.__reg2fields__
    {0x00: ['SW_RESET'], 0x01: ['DMA_TIMEOUT_ENABLE', 'TIMEOUT_PERIOD', 'STOP_HOST_XFER'], ...}
    >>> Fields.SW_RESET.name
    'SW_RESET'


    """

    __fields__: ClassVar[list[type[Field]]] = []
    __reg2fields__: ClassVar[dict[int, list[str]]] = {}

    def __init__(self):
        raise RuntimeError("Do not instantiate this class directly.")

    @describe_field
    class SW_RESET(Field):
        name = "SW_RESET"
        description = "Software reset"
        help = """
        Set this bit to 1 to reset the MI48.
        This bit is cleared automatically after the reset is complete.
        """
        address = 0x00
        bits_range = (0, 1)
        writable = True
        readable = False
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class DMA_TIMEOUT_ENABLE(Field):
        name = "DMA_TIMEOUT_ENABLE"
        description = "DMA timeout enable"
        help = """
        For SPI interface only. Enable DMA timeout monitoring for the SPI transfer.
        The value of timeout is determined by the TIMEOUT_PERIOD below.
        """
        address = 0x01
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class TIMEOUT_PERIOD(Field):
        name = "TIMEOUT_PERIOD"
        description = "Select timeout period for DMA"
        help = """
        The value selects the timeout period as follows, in conjunction when bit 0 is set to 1:
        - 0: 500 ms
        - 1: 1000 ms
        - 2: 2000 ms
        - 3: 100 ms (default)
        """
        address = 0x01
        bits_range = (1, 3)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "500 ms",
            1: "1000 ms",
            2: "2000 ms",
            3: "100 ms",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class STOP_HOST_XFER(Field):
        name = "STOP_HOST_XFER"
        description = "Reset SPI transfer between host and MI48"
        help = """
        For SPI interface only. For the host to reset the SPI transfer between the host and the MI48.
        Stop and reset host SPI DMA by setting to 1. This bit is self-cleared when the reset is complete.
        """
        address = 0x01
        bits_range = (3, 4)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class REQ_RETRANSMIT(Field):
        name = "REQ_RETRANSMIT"
        description = "Request retransmission from MI48"
        help = """
        Set this bit to 1 to request a retransmission from MI48
        This bit is cleared automatically after the changes are applied.
        """
        address = 0x19
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class AUTO_RETRANSMIT(Field):
        name = "AUTO_RETRANSMIT"
        description = "Enable automatic retransmission on SPI timeout"
        help = """
        Set this bit to 1 to enable automatic retransmission when SPI timeout is detected
        """
        address = 0x19
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class GET_SINGLE_FRAME(Field):
        name = "GET_SINGLE_FRAME"
        description = "Acquire a single frame"
        help = """
        Setting this bit to 1 leads to the acquisition of a single frame.
        This bit is automatically reset to 0 after the acquisition of one frame.
        Note that writing 1 to this bit prior to it being auto-reset and prior to DATA_READY going high will restart the frame acquisition.
        DATA_READY will remain low until the data from the restarted acquisition is available in the output buffer.
        """
        address = 0xB1
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class CONTINUOUS_STREAM(Field):
        name = "CONTINUOUS_STREAM"
        description = "Enable continuous capture mode"
        help = """
        Setting this bit to 1 instructs the MI48xx to operate in Continuous Capture Mode, whereby it continuously acquires data from the camera module and updates the readout buffer accessible through the SPI interface.
        Resetting this bit to 0 instructs the MI48xx to stop continuous data acquisition. This also resets to 0 the DATA_READY pin and the corresponding bit 4 of the STATUS register.
        """
        address = 0xB1
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class READOUT_MODE(Field):
        name = "READOUT_MODE"
        description = "Configure the readout mode"
        help = """
        Configure the readout mode of the output frame buffer, accessible through the SPI interface.
        Currently only Full-Frame Readout Mode is implemented, where the host controller can read out the frame only when it is captured and processed in its entirety.

        Values:
        - 0: Full-Frame Readout Mode (default)
        - 1 to 7: Reserved.
        """
        address = 0xB1
        bits_range = (2, 5)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "Full-Frame Readout Mode",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class NO_HEADER(Field):
        name = "NO_HEADER"
        description = "Eliminate header from thermal data frame"
        help = """
        Setting this bit to 1 eliminates the HEADER from the Thermal Data Frame transferred through the SPI interface.
        Resetting this bit to 0 includes the HEADER in the Thermal Data Frame.
        """
        address = 0xB1
        bits_range = (5, 6)
        writable = True
        readable = True
        self_reset = False
        enabled = False
        disabled_reason = "Enable no header mode may cause compatibility issues in some devices."

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class ADC_ENABLE(Field):
        name = "ADC_ENABLE"
        description = "Output raw ADC data"
        help = """
        Setting this bit to 1 enables the output of raw ADC data.
        """
        address = 0xB1
        bits_range = (7, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class FW_VERSION_MAJOR(Field):
        name = "FW_VERSION_MAJOR"
        description = "Major firmware version number"
        help = """
        Major firmware version number
        """
        address = 0xB2
        bits_range = (4, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class FW_VERSION_MINOR(Field):
        name = "FW_VERSION_MINOR"
        description = "Minor firmware version number"
        help = """
        Minor firmware version number
        """
        address = 0xB2
        bits_range = (0, 4)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class FW_VERSION_BUILD(Field):
        name = "FW_VERSION_BUILD"
        description = "Firmware build number"
        help = """
        Firmware build number
        """
        address = 0xB3
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class FRAME_RATE_DIVIDER(Field):
        name = "FRAME_RATE_DIVIDER"
        description = "Frame rate divider"
        help = """
        The value of these bits establishes the rate at which the host controller can read out thermal data frame from the Output Frame Buffer through the SPI interface.
        The value must be an unsigned integer representing the frame rate divisor of the maximum frame rate, FPS_MAX, of the attached camera module: FPS = FPS_MAX / FRAME_RATE_DIVIDER.
        Exception is FRAME_RATE = 0, which yields FPS_MAX.

        Values:
        - 0: MAX FPS
        - 1 to 127: 1/value MAX FPS
        """
        address = 0xB4
        bits_range = (0, 7)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            if value == 0:
                return "MAX FPS"
            else:
                return f"1/{value} MAX FPS"

    @describe_field
    class SLEEP_PERIOD(Field):
        name = "SLEEP_PERIOD"
        description = "Sleep period duration"
        help = """
        The length of time during which the MI48xx and the attached SenXorTM camera module stay in low power mode (sleep mode) after every frame that has been read out through the SPI interface.
        The value represents time in units of 10 milliseconds, or time in units of 1 s if PERIOD_X100 (bit 6) is set.
        Values:
        - 0 to 63: value * 10 ms or value * 1 s
        """
        address = 0xB5
        bits_range = (0, 6)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            period_x100 = self.fieldmap.PERIOD_X100.get()
            if period_x100 == 1:
                return f"{value} s"
            else:
                return f"{value * 10} ms"

    @describe_field
    class PERIOD_X100(Field):
        name = "PERIOD_X100"
        description = "Set sleep period units to seconds"
        help = """
        When this bit is set, the value of SLEEP_PERIOD is in units of 1 second.
        """
        address = 0xB5
        bits_range = (6, 7)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "1 s" if value == 1 else "10 ms"

    @describe_field
    class SLEEP(Field):
        name = "SLEEP"
        description = "Enter low power sleep mode"
        help = """
        When this bit is set to 1 the MI48xx will power down the SenXorTM Camera Module and will enter low power sleep mode itself immediately after.
        The bit is automatically reset to 0 if MI48xx is addressed via the I2C interface, upon which the chip exits sleep mode and powers up the camera module.

        In SPI/I2C mode the chip supports host-control and automatic sleep modes.
        Host-control: set this bit to 1 to enter sleep; any I2C access exits sleep and clears the bit. Wait 50 ms before capture.
        Automatic: set a non-zero SLEEP_PERIOD; the chip sleeps after each frame and waits 50 ms on wake-up.
        Do not use in USB mode.

        """
        address = 0xB5
        bits_range = (7, 8)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class READOUT_TOO_SLOW(Field):
        name = "READOUT_TOO_SLOW"
        description = "Last frame readout was too slow"
        help = """
        Reads 1 if the last frame was not readout within the time-period reciprocal to the maximum frame rate of the attached camera module.
        Relevant only in Continuous Capture Mode (see bit 1, CONTINUOUS_STREAM, of register FRAME_MODE, 0xB1).
        Reads 0 otherwise.
        Auto-reset upon read.
        Supported only in SPI/I2C mode.
        """
        address = 0xB6
        bits_range = (1, 2)
        writable = False
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class SENXOR_IF_ERROR(Field):
        name = "SENXOR_IF_ERROR"
        description = "Error detected during power-up"
        help = """
        Reads 1 if an error was detected on the SenXor interface during power-up of the MI48xx.
        """
        address = 0xB6
        bits_range = (2, 3)
        writable = False
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class CAPTURE_ERROR(Field):
        name = "CAPTURE_ERROR"
        description = "Communication error during data capture"
        help = """
        Communication error on the SenXor interface during thermal data capture.
        """
        address = 0xB6
        bits_range = (3, 4)
        writable = False
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class DATA_READY(Field):
        name = "DATA_READY"
        description = "Data ready status flag"
        help = """
        This bit reflects the state of the DATA_READY pin and is intended to be polled by a system that cannot have a hardware connection to the DATA_READY pin.
        Note however, that when this bit is polled continuously without delay it might cause a drop in the data frame rate.
        Therefore, it is recommended to introduce a few milliseconds delay between successive polls.
        """
        address = 0xB6
        bits_range = (4, 5)
        writable = False
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class BOOTING_UP(Field):
        name = "BOOTING_UP"
        description = "MI48xx boot status"
        help = """
        Reads 1 if the MI48xx is still booting up. Reads 0 after the MI48xx completes its boot up process.
        Once it reads zero, write to other registers is allowed, and frame capture can start.
        """
        address = 0xB6
        bits_range = (5, 6)
        writable = False
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class CLK_SLOW_DOWN(Field):
        name = "CLK_SLOW_DOWN"
        description = "Reduce internal clock speed"
        help = """
        Setting this bit to 0 reduces the internal clock speed of the MI48xx by a half, and leads to a reduction of its dynamic power by approximately the same factor.
        """
        address = 0xB7
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class MODULE_GAIN(Field):
        name = "MODULE_GAIN"
        description = "SenXor array signal amplification"
        help = """
        These bits define the common amplification of the signal generated by each pixel in the SenXor array.
        The increased amplification improves signal to noise ratio but limits the range of scene temperatures that can be reported.

        Values:
        - 0: 1.0 (default, maximum gain)
        - 1: auto (automatic gain selection: 1.0, 0.5, or 0.25 based on input signal)
        - 2: 0.25 (quarter gain)
        - 3: 0.5 (half gain)
        - 4: 1.0 (maximum gain)
        - 5-15: Reserved
        """
        address = 0xB9
        bits_range = (0, 4)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "1.0",
            1: "auto",
            2: "0.25",
            3: "0.5",
            4: "1.0",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class SENXOR_TYPE(Field):
        name = "SENXOR_TYPE"
        description = "SenXor chip type identifier"
        help = """
        As per the SenXor chip in the attached module
        """
        address = 0xBA
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return SENXOR_TYPE_MAP.get(value, f"Unknown: {value}")

    @describe_field
    class MODULE_TYPE(Field):
        name = "MODULE_TYPE"
        description = "Camera module type identifier"
        help = """
        Module type, defined by the combination of SenXor chip type and specific lens.
        The value of this register is typically pre-set during factory calibration of the module.
        However, for self-calibrated modules, the user must write the correct value before initiating the self-calibration process.
        """
        address = 0xBB
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return MODULE_TYPE_MAP.get(value, f"Unknown: {value}")

    @describe_field
    class MCU_TYPE(Field):
        name = "MCU_TYPE"
        description = "MCU type identifier"
        help = """
        The MCU_TYPE register indicates the model of the MIxx series chip used in the module.
        """
        address = 0x33
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return MCU_TYPE_MAP.get(value, f"Unknown: {value}")

    @describe_field
    class LUT_SOURCE(Field):
        name = "LUT_SOURCE"
        description = "Select LUT source"
        help = """
        Select LUT Source.

        Values:
        - 0: Module flash (default)
        - 1: Firmware
        """
        address = 0xBC
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "Module flash",
            1: "Firmware",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class LUT_SELECTOR(Field):
        name = "LUT_SELECTOR"
        description = "Select specific LUT"
        help = """
        Interpretation depends on the 'LUT_SOURCE' as follows:

        `LUT_SOURCE` is `0`:
        - 0: lens-specific
        - 1-7: reserved

        `LUT_SOURCE` is `1`:
        - 0: not lens-specific
        - 1: reserved
        - 2: extended LUT, for MI0802-M5S, supporting an extended scene range
        - 4: LUT V10, for MI0802-M7G
        - 5-7: reserved
        """
        address = 0xBC
        bits_range = (1, 3)
        writable = True
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class LUT_VERSION(Field):
        name = "LUT_VERSION"
        description = "Look-up-table version"
        help = """
        Read-only field indicating the version of the currently selected look-up-table.
        """
        address = 0xBC
        bits_range = (4, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class CORR_FACTOR(Field):
        name = "CORR_FACTOR"
        description = "Temperature readout correction factor"
        help = """
        Multiplicative factor to the temperature readout of every pixel, allowing correction of the sensitivity.
        e.g. when a protective filter is placed in front of the thermal camera lens.

        Formula: corrected_factor = CORR_FACTOR * 0.01.
        e.g. value 100 means corrected_factor = 1.0.
        """
        address = 0xC2
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> float:
            return round(value * 0.01, 2)

    @describe_field
    class START_COLOFFS_CALIB(Field):
        name = "START_COLOFFS_CALIB"
        description = "Start column offsets calibration"
        help = """
        Start column offsets calibration.
        The bit is automatically set during power up and upon a change in MODULE_GAIN (either manual or automatic).
        """
        address = 0xC5
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class COLOFFS_CALIB_ON(Field):
        name = "COLOFFS_CALIB_ON"
        description = "Column offsets calibration status"
        help = """
        After setting START_COLOFFS_CALIB to 1, COLOFFS_CALIB_ON bit reads 1 throughout the process of column offsets calibration.
        Once the process is complete, this bit returns to 0.
        """
        address = 0xC5
        bits_range = (2, 3)
        writable = False
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class USE_SELF_CALIB(Field):
        name = "USE_SELF_CALIB"
        description = "Use self-calibration data"
        help = """
        If set to 1, the module will not use module-specific calibration data. It will use instead the data obtained during column offset calibration, and predefined generic data for the given chip and lens combination.
        NOTE: the user must write the correct value of MODULE_TYPE to register 0xBB, in order to achieve a reliable self-calibration operation. In any case, the use of self-calibration cannot be as good as the factory calibration, which is done for each individual module.
        """
        address = 0xC5
        bits_range = (4, 5)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "True" if value == 1 else "False"

    @describe_field
    class CALIB_SAMPLE_SIZE(Field):
        name = "CALIB_SAMPLE_SIZE"
        description = "Number of calibration frames"
        help = """
        These bits define the number of frames acquired during column calibration.
        According to the formula: (SAMPLE_SIZE + 1) x 100.
        """
        address = 0xC5
        bits_range = (5, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return f"{(value + 1) * 100}"

    @describe_field
    class EMISSIVITY(Field):
        name = "EMISSIVITY"
        description = "Target object emissivity value (percent)"
        help = """
        Emissivity value (percent) to be used in the conversion of raw data captured from SenXor to the temperature data that is readout through the SPI interface.
        The reset value reflects the emissivity of the black body source used for factory calibration of the camera module.
        If the target object is known to have a different emissivity, programming the correct value will lead to an accurate readout of the absolute temperature.

        Formula: emissivity = EMISSIVITY * 0.01.
        e.g. value 100 means emissivity = 1.0.
        """
        address = 0xCA
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> float:
            return round(value * 0.01, 2)

    @describe_field
    class OFFSET(Field):
        name = "OFFSET"
        description = "Temperature offset correction"
        help = """
        This field specifies a temperature offset applied to every pixel in the data frame.

        - Representation: 8-bit signed integer (two's complement)
        - Units: 0.1 K (or 0.1°C)
        - Range: -12.8 K to +12.7 K
        - Enables precise adjustment of the temperature readout to correct for bias

        For example, to correct a bias of +0.7 K, set the offset to -0.7 K. Compute the register value: `-0.7 x 10 = -7`, since -7 is negative, encode as unsigned: `256 + (-7) = 249`.
        And for an offset of +0.75 K: Compute the register value: `0.75 x 10 = 7.5`, rounded to `8`,
        """
        address = 0xCB
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> float:
            uint8 = value
            int8 = uint8 if uint8 < 128 else uint8 - 256
            return round(int8 * 0.1, 1)

    @describe_field
    class OTF(Field):
        name = "OTF"
        description = "Object temperature correction factor"
        help = """
        A multiplicative factor applied to each pixel's value before the frame is output.
        This is used to correct for size-of-source optical phenomena.

        - Representation: 8-bit signed integer (two's complement).
        - Resolution: 0.01.
        - Range: -1.28 to +1.27.
        - It is a unitless factor.
        - Formula: `Corrected_Temp = Raw_Temp * (1 + uint8_to_int8(OTF) * 0.01)`

        For example,
        If the factor is 1.01, the field value should be `(1.01 - 1) * 100 = 1`.
        If the filed value is 1, the factor should be `1 + 1 * 0.01 = 1.01`.
        If the factor is 0.99, the field value should be `(0.99 - 1) * 100 = -1, -1 < 0, so 256 + (-1) = 255`.
        """
        address = 0xCD
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> float:
            uint8 = value
            int8 = uint8 if uint8 < 128 else uint8 - 256
            return round(1 + int8 * 0.01, 2)

    @describe_field
    class PRODUCTION_YEAR(Field):
        name = "PRODUCTION_YEAR"
        description = "Production year"
        help = """
        The year of production, stored as an offset from year 2000.

        - Valid range: 19-99
        """
        address = 0xE0
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> int:
            return value + 2000

    @describe_field
    class PRODUCTION_WEEK(Field):
        name = "PRODUCTION_WEEK"
        description = "Production week"
        help = """
        The week number in which the module was produced.
        """
        address = 0xE1
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class MANUF_LOCATION(Field):
        name = "MANUF_LOCATION"
        description = "Manufacturing location"
        help = """
        A code identifying the manufacturing location.
        """
        address = 0xE2
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class SERIAL_NUMBER_0(Field):
        name = "SERIAL_NUMBER_0"
        description = "Serial number 0"
        help = """
        Serial number 0.
        """
        address = 0xE3
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class SERIAL_NUMBER_1(Field):
        name = "SERIAL_NUMBER_1"
        description = "Serial number 1"
        help = """
        Serial number 1.
        """
        address = 0xE4
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class SERIAL_NUMBER_2(Field):
        name = "SERIAL_NUMBER_2"
        description = "Serial number 2"
        help = """
        Serial number 2.
        """
        address = 0xE5
        bits_range = (0, 8)
        writable = False
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class USER_FLASH_ENABLE(Field):
        name = "USER_FLASH_ENABLE"
        description = "Enable host access to User Flash"
        help = """
        When set to `1`, this bit enables host access to the 128-byte User Flash memory area (addresses `0x00` to `0x7F`).

        - Access is via register-like byte access through the host interface (USB or I2C).
        - This bit must be cleared to `0` to regain access to the standard registers.
        - For firmware version 4.5.10 and newer, this area can store up to 63 register address/value pairs for pre-set
        """
        address = 0xD8
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class TEMP_UNITS(Field):
        name = "TEMP_UNITS"
        description = "Temperature units selection"
        help = """
        These 3 bits select the temperature units for the frame output and the temperature items in the frame header. The
        representation of the values can be an unsigned integer, two's complement, or half-precision 16-bit floating point,
        depending on the unit.

        | Value      | Unit         | 16-bit Representation        | Resolution |
        | ---------- | ------------ | ---------------------------- | ---------- |
        | 0(default) | deci-Kelvin  | Fixed point unsigned integer | 1 dK       |
        | 1          | deci-Celsius | Fixed point two's complement | 0.1°C      |
        | 2          | deci-Fahr.   | Fixed point two's complement | 0.1°F      |
        | 4          | Kelvin       | Half-precision float         | 1 K        |
        | 5          | Celsius      | Half-precision float         | 1°C        |
        | 6          | Fahrenheit   | Half-precision float         | 1°F        |
        """
        address = 0x31
        bits_range = (0, 3)
        writable = True
        readable = True
        self_reset = False
        enabled = False
        disabled_reason = "This field is not supported in some firmware versions. Don't use it."

        value_map: ClassVar[dict[int, str]] = {
            0: "dK",
            1: "dC",
            2: "dF",
            4: "K",
            5: "C",
            6: "F",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class STARK_ENABLE(Field):
        name = "STARK_ENABLE"
        description = "Enable STARK denoising filter"
        help = """
        Enable STARK denoising filter (Spatio-temporal advanced rolling kernel).
        Preserves features without significant historical artefacts. Optimal filter for quasi-static scenes.
        However, for dynamic scenes, the changing parts of the scene will have noise penetration (which perceptually may be confused with motion blur/ghosting).
        """
        address = 0x20
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class STARK_TYPE(Field):
        name = "STARK_TYPE"
        description = "STARK filter type selection"
        help = """
        Select the STARK filter type:

        - 0: quick-stark (lowest processing overhead)
        - 1: stark-v1 (auto)
        - 2: stark-v2
        - 3: stark-v1 (background smooth)
        - 4: full-stark (higher processing overhead)
        - 5-7: quick-stark
        """
        address = 0x20
        bits_range = (1, 4)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "quick-stark",
            1: "stark-v1",
            2: "stark-v2",
            3: "stark-v1-background-smooth",
            4: "full-stark",
            5: "quick-stark",
            6: "quick-stark",
            7: "quick-stark",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class SPATIAL_KERNEL(Field):
        name = "SPATIAL_KERNEL"
        description = "Kernel size for spatial operations"
        help = """
        Select the kernel size for spatial filtering operations:

        Values:
        - 0: 3x3 kernel (default)
        - 1: 5x5 kernel (lower noise, but there is some feature erosion and FPS drops for small FPS_DIVISOR of 1 to 3), significantly
        """
        address = 0x20
        bits_range = (4, 5)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "3x3 kernel",
            1: "5x5 kernel",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class STARK_CUTOFF(Field):
        name = "STARK_CUTOFF"
        description = "Noise suppression cutoff value"
        help = """
        Noise suppression cutoff in units of dK
        The higher the value, the better the noise suppression, except during scene change.
        """
        address = 0x21
        bits_range = (0, 7)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return f"{value / 10} K"

    @describe_field
    class STARK_GRADIENT(Field):
        name = "STARK_GRADIENT"
        description = "Filter output transition steepness"
        help = """
        Unitless value that influences the steepness of filter output transition upon scene change.
        A higher value leads to more rapid transition, but also lowers the noise immunity of the output from the filter.
        """
        address = 0x22
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class STARK_SCALE(Field):
        name = "STARK_SCALE"
        description = "Maximum allowed output change percentage"
        help = """
        Percentage of the input change that is ever allowed to reach the output during change.
        """
        address = 0x23
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return f"{value / 100} %"

    @describe_field
    class MMS_KXMS(Field):
        name = "MMS_KXMS"
        description = "Enable k-extrema median stabilization"
        help = """
        KXMS is short for k-extrema median stabilization, which is turned ON when this flag is set to 1 (default).
        It operates on a per-frame basis, and thus has an instantaneous response to a dynamic scene.
        However, it is computationally more expensive and may lead to noticeable FPS drop for small values of FPS_DIVISOR.
        Disabled if this bit is cleared.
        """
        address = 0x25
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class MMS_RA(Field):
        name = "MMS_RA"
        description = "Enable rolling average min/max stabilization"
        help = """
        Min/Max stabilization based on a rolling average of FPS_DIVISOR-dependent depth, providing ~500 ms response time upon a change in scene range, is enabled if this bit is set to 1.
        Cleared (disabled) by default.
        """
        address = 0x25
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class MEDIAN_ENABLE(Field):
        name = "MEDIAN_ENABLE"
        description = "Enable Median denoising filter"
        help = """
        Enable Midian denoising filter operating in the spatial domain.
        This is a standard image processing filter, on a per-frame basis.
        It is great at removing very localised noise at the expense of computational cost (FPS drop) and erosion of small image features.
        """
        address = 0x30
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class MEDIAN_KERNEL_SIZE(Field):
        name = "MEDIAN_KERNEL_SIZE"
        description = "Sets median filter kernel size"
        help = """
        Select the size of the median filter kernel:

        Values:
        - 0: 3x3 kernel (default)
        - 1: 5x5 kernel
        """
        address = 0x30
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        value_map: ClassVar[dict[int, str]] = {
            0: "3x3 kernel",
            1: "5x5 kernel",
        }

        def get_display(self, value: int) -> str:
            return self.value_map.get(value, f"Invalid value: {value}")

    @describe_field
    class TEMPORAL_ENABLE(Field):
        name = "TEMPORAL_ENABLE"
        description = "Enable temporal domain filtering"
        help = """
        Enable data filtering in the temporal domain when set to 1.
        The effect of this filter is determined by the value of register FILTER_SETTING_1 (0xD1 - 0xD2).
        The higher the value, the more stable the readout temperature, but also the more noticeable trailing artefacts in a dynamical scene.
        Note that the use of the temporal filter in conjunction with bit 0 of CLK_SPEED register, CLK_SLOW_DOWN, leads to a reduction in the data frame rate.
        """
        address = 0xD0
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = False
        enabled = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class TEMPORAL_INIT(Field):
        name = "TEMPORAL_INIT"
        description = "Initialize temporal filter"
        help = """
        Initialize temporal filter, when set to 1.
        This bit must be set to one whenever a new value is written to register FILTER_SETTING_1 (0xD1 - 0xD2), in order for the new setting to take effect.
        The bit will be automatically reset to 0 after the initialization is complete.
        """
        address = 0xD0
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = True
        enabled = True

        def get_display(self, value: int) -> str:
            return "Active" if value == 1 else "Idle"

    @describe_field
    class TEMPORAL_LSB(Field):
        name = "TEMPORAL_LSB"
        description = "Temporal filter strength low byte"
        help = """
        The lower 8 bits of the temporal filter strength value.
        """
        address = 0xD1
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True

    @describe_field
    class TEMPORAL_MSB(Field):
        name = "TEMPORAL_MSB"
        description = "Temporal filter strength high byte"
        help = """
        The upper 8 bits of the temporal filter strength value.
        """
        address = 0xD2
        bits_range = (0, 8)
        writable = True
        readable = True
        self_reset = False
        enabled = True


Fields.__fields__ = [v.cls for v in Fields.__dict__.values() if isinstance(v, FieldDescriptor)]
Fields.__reg2fields__ = {addr: [] for addr in Registers.__addrs__}
for field in Fields.__fields__:
    Fields.__reg2fields__[field.address].append(field.name)

if __name__ == "__main__":
    print(Fields.__reg2fields__)
