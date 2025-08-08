# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

from collections import defaultdict
from functools import partial as _partial
from typing import TYPE_CHECKING, ClassVar

from senxor.consts import MCU_TYPE as _map_mcu_type
from senxor.consts import MODULE_TYPE as _map_module_type
from senxor.consts import SENXOR_TYPE as _map_senxor_type
from senxor.log import get_logger
from senxor.regmap._field import Field, _FieldDef, _FieldDescriptor

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from senxor.regmap._regmap import _RegMap


# ----------------------------------------------------------------
# Field value-to-display mapping
# ----------------------------------------------------------------

_map_timeout_period = {
    0: "500 ms",
    1: "1000 ms",
    2: "2000 ms",
    3: "100 ms",
}

_map_readout_mode = {
    0: "Full-Frame Readout Mode",
}

_map_module_gain = {
    0: "maximum: 1.0",
    1: "auto: 1.0, 0.5, or 0.25",
    2: "quarter: 0.25",
    3: "half: 0.5",
    4: "maximum: 1.0",
}

_map_lut_source = {
    0: "Module flash",
    1: "FW",
}

_map_lut_selector_flash = {
    0: "Default LUT",
}

_map_lut_selector_fw = {
    0: "Generic LUT",
    2: "Extended LUT",
}

_map_temp_units = {
    0: "0.1 K",
    1: "0.1 °C",
    2: "0.1 °F",
    4: "1 K",
    5: "1 °C",
    6: "1 °F",
}

_map_stark_type = {
    0: "Quick Stark",
    1: "Stark V1(auto)",
    2: "Stark V2",
    3: "Stark V1(Background Smooth)",
    4: "Full Stark",
    5: "Quick Stark",
    6: "Quick Stark",
    7: "Quick Stark",
}

_map_spatial_kernel = {
    0: "3x3",
    1: "5x5",
}

_map_median_kernel_size = {
    0: "3x3",
    1: "5x5",
}

# ----------------------------------------------------------------
# Field value validator
# ----------------------------------------------------------------


def _validator_bool(value: int, _: Fields) -> bool:
    # Allow 0, 1, True, False
    return value in [0, 1]


def _validator_uintx(x: int, value: int, _: Fields) -> bool:
    return 0 <= value < 2**x


def _validator_value_in_map(map: dict[int, str], value: int, _: Fields) -> bool:
    return value in map


def _repr_frame_rate_divider(value: int, _: Fields) -> str:
    if value == 0 or value == 1:
        return "MAX FPS"
    else:
        return f"1/{value} MAX FPS"


def _repr_sleep_period(value: int, fields: Fields) -> str:
    if fields.PERIOD_X100 == 1:
        return f"{value} s"
    else:
        return f"{value * 10} ms"


def _repr_from_map(map: dict[int, str], value: int, _: Fields) -> str:
    display = map.get(value, "N/A")
    return display


def _repr_lut_selector(value: int, fields: Fields) -> str:
    if fields.LUT_SOURCE == 0:
        return _repr_from_map(_map_lut_selector_flash, value, fields)
    else:
        return _repr_from_map(_map_lut_selector_fw, value, fields)


def _validator_lut_selector(value: int, fields: Fields) -> bool:
    if fields.LUT_SOURCE == 0:
        return value in _map_lut_selector_flash
    else:
        return value in _map_lut_selector_fw


def _repr_calib_sample_size(value: int, _: Fields) -> str:
    n_frames = (1 + value) * 100
    return f"{n_frames} frames"


def _repr_offset(value: int, _: Fields) -> str:
    if value > 127:
        return f"{-(256 - value) / 10} K"
    else:
        return f"{value / 10} K"


def _repr_otf(value: int, _: Fields) -> str:
    if value > 127:
        value = value - 256
    factor = (value / 100) + 1
    return f"{factor:.2f}"


def _repr_bool(value: int, _: Fields) -> str:
    return "True" if value else "False"


# ----------------------------------------------------------------
# Field help text
# ----------------------------------------------------------------


_help_sw_reset = """
Set this bit to 1 to reset the MI48.
This bit is cleared automatically after the reset is complete.
"""

_help_dma_timeout_enable = """
For SPI interface only. Enable DMA timeout monitoring for the SPI transfer.
The value of timeout is determined by the TIMEOUT_PERIOD below.
"""

_help_timeout_period = """
The value selects the timeout period as follows:
- 0: 500 ms
- 1: 1000 ms
- 2: 2000 ms
- 3: 100 ms (default)
"""

_help_stop_host_xfer = """
For SPI interface only. For the host to reset the SPI transfer between the host and the MI48.
Stop and reset host SPI DMA by setting to 1. This bit is self-cleared when the reset is complete.
"""

_help_req_retransmit = """
Set this bit to 1 to request a retransmission from MI48.
This bit is cleared automatically after the changes are applied.
"""

_help_auto_retransmit = """
Set this bit to 1 to enable automatic retransmission when SPI timeout is detected.
"""

_help_get_single_frame = """
Setting this bit to 1 leads to the acquisition of a single frame.

This bit is automatically reset to 0 after the acquisition of one frame.

Note that writing 1 to this bit prior to it being auto-reset and prior to DATA_READY going high will restart the frame
acquisition. DATA_READY will remain low until the data from the restarted acquisition is available in the output buffer.
"""

_help_continuous_stream = """
Setting this bit to 1 instructs the MI48xx to operate in Continuous Capture Mode, whereby it continuously acquires data
from the camera module and updates the readout buffer accessible through the SPI interface.

Resetting this bit to 0 instructs the MI48xx to stop continuous data acquisition. This also resets to 0 the DATA_READY
pin and the corresponding bit 4 of the STATUS register.
"""

_help_readout_mode = """
Configure the readout mode of the output frame buffer, accessible through the SPI interface.

Currently only Full-Frame Readout Mode is implemented, where the host controller can read out the frame only when it is
captured and processed in its entirety.

Values:
- 0: Full-Frame Readout Mode (default)
- 1-7: Reserved
"""

_help_no_header = """
Setting this bit to 1 eliminates the Header from the Thermal Data Frame transferred through the SPI interface.

Resetting this bit to 0 includes the HEADER in the Thermal Data Frame.
"""

_help_frame_rate_divider = """
The value of these bits establishes the rate at which the host controller can read out thermal data frame from the
Output Frame Buffer through the SPI interface.

The value must be an unsigned integer representing the frame rate divisor of the maximum frame rate, FPS_MAX, of the
attached camera module:

FPS = FPS_MAX / FRAME_RATE_DIVIDER

Exception is FRAME_RATE = 0, which yields FPS_MAX.
"""

_help_sleep_period = """
The length of time during which the MI48xx and the attached SenXor camera module stay in low power mode (sleep mode)
after every frame readout.

The value represents time in:

- Units of 10 milliseconds when PERIOD_X100 is 0
- Units of 1 second when PERIOD_X100 is 1
"""

_help_period_x100 = """
When this bit is set, the value of SLEEP_PERIOD is in units of 1 second.
When clear, SLEEP_PERIOD is in units of 10 milliseconds.
"""

_help_sleep = """
When this bit is set to 1:

- The MI48xx will power down the SenXor Camera Module
- Will enter low power sleep mode itself immediately after

The bit is automatically reset to 0 if MI48xx is addressed via the I2C interface, upon which:

- The chip exits sleep mode
- Powers up the camera module

After exiting sleep mode, the host must wait for 50 ms before initiating frame capture.
"""

_help_readout_too_slow = """
Reads 1 if the last frame was not readout within the time-period reciprocal to the maximum frame rate of the attached
camera module.

- Relevant only in Continuous Capture Mode (see CONTINUOUS_STREAM bit of FRAME_MODE register)
- Reads 0 otherwise
- Auto-reset upon read
- Supported only in SPI/I2C mode
"""

_help_senxor_if_error = """
Reads 1 if an error was detected on the SenXor interface during power up of the MI48xx.
"""

_help_capture_error = """
Communication error on the SenXor interface during thermal data capture.
"""

_help_data_ready = """
This bit reflects the state of the DATA_READY pin and is intended to be polled by a system that cannot have a hardware
connection to the DATA_READY pin.

Note: When this bit is polled continuously without delay it might cause a drop in the data frame rate. Therefore, it is
recommended to introduce a few milliseconds delay between successive polls.
"""

_help_booting_up = """
- Reads 1 if the MI48xx is still booting up
- Reads 0 after the MI48xx completes its boot up process
- Once it reads zero, write to other registers is allowed, and frame capture can start
"""

_help_clk_slow_down = """
Setting this bit to 0 reduces the internal clock speed of the MI48xx by a half, and leads to a reduction of its dynamic
power by approximately the same factor.
"""

_help_module_gain = """
These bits define the common amplification of the signal generated by each pixel in the SenXor array. The increased
amplification improves signal to noise ratio but limits the range of scene temperatures that can be reported.

Values:

- 0: Default, maximum gain of 1.0
- 1: AUTO - Automatic gain selection (1.0, 0.5, or 0.25) based on input signal
- 2: Quarter gain of 0.25
- 3: Half gain of 0.5
- 4: Maximum gain of 1.0
- 5-15: Reserved

Note: If MODULE_GAIN is set to AUTO, reading this register will return the currently selected value.
"""

_help_senxor_type = """
Values:

- 1: MI0801-xxx
- 4: MI0802-xxx Revision 1
- 5: MI0802-xxx Revision 2
- 6: MI16XX Revision 1
"""

_help_module_type = """
Module type, defined by the combination of SenXor chip type and specific lens.
The value of this register is typically pre-set during factory calibration of the module.
For self-calibrated modules, the user must write the correct value before initiating the self-calibration process.
"""

_help_mcu_type = """
The MCU_TYPE register indicates the model of the MIxx series chip used in the module.

- 0: MI48D4
- 1: MI48D5
- 2: MI48E
- 3: MI48G
- 4: MI48C
- 255: MI48D4

Note: 0x33 on old FW of MI48D4 is reserved, so read 0xFF.
"""

_help_lut_source = """
Select LUT Source:

- 0: Module flash (default)
- 1: FW
"""

_help_lut_selector = """
The interpretation of this field depends on the `LUT_SOURCE`.

- If LUT Source is Module Flash (0):
  - 0 : Default LUT, which is specific to the module type and lens.
  - Other values are reserved.
- If LUT Source is FW (1):
  - 0: A generic, non-lens-specific LUT.
  - 2: Extended LUT for MI0802-M5S, supporting an extended scene range.
  - Other values are reserved.
"""

_help_lut_version = """
Read-only field indicating the version of the currently selected look-up-table.
"""

_help_corr_factor = """
This is a multiplicative factor applied to the temperature readout of every pixel. It allows for sensitivity correction,
for example, when a protective filter is used. The value is based on the camera module's calibration data.
"""

_help_start_coloffs_calib = """
Writing 1 to this bit starts the column offsets calibration process.
The bit is automatically cleared when calibration is complete.
"""

_help_coloffs_calib_on = """
A read-only status bit that indicates when column offset calibration is in progress.

- `1`: Calibration is in progress.
- `0`: Calibration is complete or not started.
"""

_help_use_self_calib = """
When set to `1`, the module uses data from the self-calibration process instead of factory-calibrated data.

Note:
    For reliable self-calibration, the `MODULE_TYPE` in register 0xBB must be set correctly. Self-calibration results
    may not be as accurate as the per-module factory calibration.
"""

_help_sample_size = """
Defines the number of frames acquired during column calibration. The number of frames is calculated as
`(SAMPLE_SIZE + 1) * 100`.

- `0`: 100 frames
- `1`: 200 frames
- ...
- `7`: 800 frames
"""

_help_emissivity = """
This register holds the emissivity value of the target object in percent.

- Valid range: 1 to 100
- Default value: 100 (perfect black body)
- Values outside the valid range will be clamped

The emissivity value is used to compensate for the fact that real objects do not behave as perfect black bodies.
A lower emissivity value will result in a higher reported temperature to compensate for the reduced thermal radiation.
"""

_help_offset = """
This field specifies a temperature offset applied to every pixel in the data frame.

- Representation: 8-bit signed integer (two's complement)
- Units: 0.1 K (or 0.1°C)
- Range: -12.8 K to +12.7 K
- Enables precise adjustment of the temperature readout to correct for bias

For example, to correct a bias of +0.7 K, set the offset to -0.7 K. Compute the register value: `-0.7 x 10 = -7`,
since -7 is negative, encode as unsigned: `256 + (-7) = 249`.
And for an offset of +0.75 K: Compute the register value: `0.75 x 10 = 7.5`, rounded to `8`,
since 8 is non-negative, use `8` as the register value.
"""

_help_otf = """
A multiplicative factor applied to each pixel's value before the frame is output. This is used to correct for
size-of-source optical phenomena.

- Representation: 8-bit signed integer (two's complement).
- Resolution: 0.01.
- Range: -1.28 to +1.27.
- It is a unitless factor.
- Formula: `Corrected_Temp = Raw_Temp * (1 + uint8_to_int8(OTF) * 0.01)`

For example,
If the factor is 1.01, the field value should be `(1.01 - 1) * 100 = 1`.
If the filed value is 1, the factor should be `1 + 1 * 0.01 = 1.01`.
If the factor is 0.99, the field value should be `(0.99 - 1) * 100 = -1, -1 < 0, so 256 + (-1) = 255`.
If the field value is 255, the factor should be `1 + (-1) * 0.01 = 0.99`.
"""

_help_production_year = """
The year of production, stored as an offset from year 2000:

- Valid range: 19-99
- Example: 23 represents year 2023
"""

_help_production_week = """
The week number in which the module was produced:

- Valid range: 1-52
"""

_help_manuf_location = """
A code identifying the manufacturing location:

- Valid range: 0-99
- Specific values are assigned to different production facilities
"""

_help_serial_number = """
A unique 32-bit serial number assigned to each camera module during production.
This number can be used for traceability and warranty purposes.
"""

_help_user_flash_enable = """
When set to `1`, this bit enables host access to the 128-byte User Flash memory area (addresses `0x00` to `0x7F`).

- Access is via register-like byte access through the host interface (USB or I2C).
- This bit must be cleared to `0` to regain access to the standard registers.
- For firmware version 4.5.10 and newer, this area can store up to 63 register address/value pairs for pre-set
configurations. The first two bytes must store the count of register pairs.
"""

_help_temp_units = """
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
| 3, 7       | Reserved     | -                            | -          |
"""

_help_temporal_enable = """
When set to `1`, enables temporal domain filtering. The strength of the filter is set in `FILTER_SETTING_1`. Higher
filter values result in more stable temperatures but can cause trailing artifacts in dynamic scenes.
"""

_help_temporal_init = """
When set to `1`, this bit initializes (or re-initializes) the temporal filter. This must be done after changing
`FILTER_SETTING_1` for the new setting to take effect. The bit is cleared automatically after initialization.
"""

_help_temporal = """
These two bytes form a 16-bit value that determines the strength of the temporal filter. A higher value leads to more
aggressive filtering, resulting in a more stable temperature readout at the cost of potential trailing artifacts in
dynamic scenes.
"""

_help_stark_enable = """
Enables the STARK (Spatio-Temporal Advanced Rolling Kernel) denoising filter. It is effective for quasi-static scenes
but may show some noise penetration on moving parts of a dynamic scene.
"""

_help_stark_type = """
Selects the STARK filter type:

- `0`: Quick Stark (Lowest processing overhead)
- `1`: StarkV1 (Auto)
- `2`: StarkV2
- `3`: StarkV1 Background Smooth
- `4`: Full Stark (Higher processing overhead)
- `5-7`: Quick Stark
"""

_help_spatial_kernel = """
Selects the kernel size for spatial filtering operations:

- 0: 3x3 kernel (default)
- 1: 5x5 kernel (stronger filtering but more computational load)
"""

_help_stark_cutoff = """
Defines the threshold for noise suppression:

- Lower values result in stronger noise suppression but may affect fine details
- Higher values preserve more detail but allow more noise through
- Recommended range: 16-96
- Default value: 32
"""

_help_stark_gradient = """
Controls how sharply the filter transitions between noise suppression and detail preservation:

- Lower values create smoother transitions but may blur edges
- Higher values create sharper transitions but may cause artifacts
- Recommended range: 1-255
- Default value: 128
"""

_help_stark_scale = """
Limits the maximum change that the filter can apply to any pixel:

- Value represents percentage of input range
- Lower values provide more conservative filtering
- Higher values allow more aggressive noise reduction
- Recommended range: 10-100
- Default value: 50
"""

_help_kxms = """
When set to 1:

- Enables k-extrema median stabilization
- Reduces temporal noise by stabilizing extreme values
- Particularly effective for reducing sporadic noise spikes
- May slightly increase latency in temperature changes
"""

_help_ra = """
When set to 1:

- Enables rolling average min/max stabilization
- Smooths out rapid fluctuations in temperature readings
- Provides more stable min/max temperature values
- May reduce responsiveness to rapid temperature changes
"""

_help_median_enable = """
When set to 1:

- Enables the median denoising filter
- Reduces impulse noise and outliers
- Preserves edges better than mean filtering
- Takes effect immediately
"""

_help_median_kernel_size = """
Selects the size of the median filter kernel:

- 0: 3x3 kernel (default)
  - Less aggressive noise reduction
  - Lower computational load
  - Better preservation of fine details
- 1: 5x5 kernel
  - Stronger noise reduction
  - Higher computational load
  - May blur fine details
"""

# ----------------------------------------------------------------
# Fields
# ----------------------------------------------------------------


class Fields:
    SW_RESET = _FieldDescriptor(
        _FieldDef(
            name="SW_RESET",
            group="MCU_RESET",
            readable=False,
            writable=True,
            type="bool",
            desc="Software Reset",
            help=_help_sw_reset,
            addr="0x00:0-0x00:1",
            addr_map={0x00: (0, 1)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    DMA_TIMEOUT_ENABLE = _FieldDescriptor(
        _FieldDef(
            name="DMA_TIMEOUT_ENABLE",
            group="HOST_XFER_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="DMA Timeout Control",
            help=_help_dma_timeout_enable,
            addr="0x01:0-0x01:1",
            addr_map={0x01: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    TIMEOUT_PERIOD = _FieldDescriptor(
        _FieldDef(
            name="TIMEOUT_PERIOD",
            group="HOST_XFER_CTRL",
            readable=True,
            writable=True,
            type="uint2",
            desc="Select timeout period for DMA",
            help=_help_timeout_period,
            addr="0x01:1-0x01:3",
            addr_map={0x01: (1, 3)},
        ),
        validator=_partial(_validator_value_in_map, _map_timeout_period),
        repr_func=_partial(_repr_from_map, _map_timeout_period),
    )

    STOP_HOST_XFER = _FieldDescriptor(
        _FieldDef(
            name="STOP_HOST_XFER",
            group="HOST_XFER_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Reset SPI transfer between host and MI48",
            help=_help_stop_host_xfer,
            addr="0x01:3-0x01:4",
            addr_map={0x01: (3, 4)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    REQ_RETRANSMIT = _FieldDescriptor(
        _FieldDef(
            name="REQ_RETRANSMIT",
            group="SPI_RTY",
            readable=True,
            writable=True,
            type="bool",
            desc="Request retransmission from MI48",
            help=_help_req_retransmit,
            addr="0x19:0-0x19:1",
            addr_map={0x19: (0, 1)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    AUTO_RETRANSMIT = _FieldDescriptor(
        _FieldDef(
            name="AUTO_RETRANSMIT",
            group="SPI_RTY",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable automatic retransmission on SPI timeout",
            help=_help_auto_retransmit,
            addr="0x19:1-0x19:2",
            addr_map={0x19: (1, 2)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    GET_SINGLE_FRAME = _FieldDescriptor(
        _FieldDef(
            name="GET_SINGLE_FRAME",
            group="FRAME_MODE",
            readable=True,
            writable=True,
            type="bool",
            desc="Acquire a single frame",
            help=_help_get_single_frame,
            addr="0xB1:0-0xB1:1",
            addr_map={0xB1: (0, 1)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    CONTINUOUS_STREAM = _FieldDescriptor(
        _FieldDef(
            name="CONTINUOUS_STREAM",
            group="FRAME_MODE",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable continuous capture mode",
            help=_help_continuous_stream,
            addr="0xB1:1-0xB1:2",
            addr_map={0xB1: (1, 2)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    READOUT_MODE = _FieldDescriptor(
        _FieldDef(
            name="READOUT_MODE",
            group="FRAME_MODE",
            readable=True,
            writable=True,
            type="uint3",
            desc="Configure the readout mode",
            help=_help_readout_mode,
            addr="0xB1:2-0xB1:5",
            addr_map={0xB1: (2, 5)},
        ),
        validator=_partial(_validator_value_in_map, _map_readout_mode),
        repr_func=_partial(_repr_from_map, _map_readout_mode),
    )

    NO_HEADER = _FieldDescriptor(
        _FieldDef(
            name="NO_HEADER",
            group="FRAME_MODE",
            readable=True,
            writable=True,
            type="bool",
            desc="Eliminate header from Thermal Data Frame",
            help=_help_no_header,
            addr="0xB1:5-0xB1:6",
            addr_map={0xB1: (5, 6)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    FW_VERSION_MAJOR = _FieldDescriptor(
        _FieldDef(
            name="FW_VERSION_MAJOR",
            group="FW_VERSION_1",
            readable=True,
            writable=False,
            type="uint4",
            desc="Major Firmware Version Number",
            help="Major firmware version number",
            addr="0xB2:4-0xB2:8",
            addr_map={0xB2: (4, 8)},
        ),
    )

    FW_VERSION_MINOR = _FieldDescriptor(
        _FieldDef(
            name="FW_VERSION_MINOR",
            group="FW_VERSION_1",
            readable=True,
            writable=False,
            type="uint4",
            desc="Minor Firmware Version Number",
            help="Minor firmware version number",
            addr="0xB2:0-0xB2:4",
            addr_map={0xB2: (0, 4)},
        ),
        # Not writable, no validator
    )

    FW_VERSION_BUILD = _FieldDescriptor(
        _FieldDef(
            name="FW_VERSION_BUILD",
            group="FW_VERSION_2",
            readable=True,
            writable=False,
            type="uint8",
            desc="Firmware build number",
            help="Firmware build number",
            addr="0xB3:0-0xB3:8",
            addr_map={0xB3: (0, 8)},
        ),
    )

    FRAME_RATE_DIVIDER = _FieldDescriptor(
        _FieldDef(
            name="FRAME_RATE_DIVIDER",
            group="FRAME_RATE",
            readable=True,
            writable=True,
            type="uint7",
            desc="Frame rate divider value",
            help=_help_frame_rate_divider,
            addr="0xB4:0-0xB4:7",
            addr_map={0xB4: (0, 7)},
        ),
        repr_func=_repr_frame_rate_divider,
        validator=_partial(_validator_uintx, 7),
    )

    SLEEP_PERIOD = _FieldDescriptor(
        _FieldDef(
            name="SLEEP_PERIOD",
            group="SLEEP_MODE",
            readable=True,
            writable=True,
            type="uint6",
            desc="Sleep period duration",
            help=_help_sleep_period,
            addr="0xB5:0-0xB5:6",
            addr_map={0xB5: (0, 6)},
        ),
        repr_func=_repr_sleep_period,
        validator=_partial(_validator_uintx, 6),
    )

    PERIOD_X100 = _FieldDescriptor(
        _FieldDef(
            name="PERIOD_X100",
            group="SLEEP_MODE",
            readable=True,
            writable=True,
            type="bool",
            desc="Set sleep period units to seconds",
            help=_help_period_x100,
            addr="0xB5:6-0xB5:7",
            addr_map={0xB5: (6, 7)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    SLEEP = _FieldDescriptor(
        _FieldDef(
            name="SLEEP",
            group="SLEEP_MODE",
            readable=True,
            writable=True,
            type="bool",
            desc="Enter low power sleep mode",
            help=_help_sleep,
            addr="0xB5:7-0xB5:8",
            addr_map={0xB5: (7, 8)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    READOUT_TOO_SLOW = _FieldDescriptor(
        _FieldDef(
            name="READOUT_TOO_SLOW",
            group="STATUS",
            readable=True,
            writable=False,
            type="bool",
            desc="Last frame readout was too slow",
            help=_help_readout_too_slow,
            addr="0xB6:1-0xB6:2",
            addr_map={0xB6: (1, 2)},
            auto_reset=True,
        ),
        repr_func=_repr_bool,
    )

    SENXOR_IF_ERROR = _FieldDescriptor(
        _FieldDef(
            name="SENXOR_IF_ERROR",
            group="STATUS",
            readable=True,
            writable=False,
            type="bool",
            desc="Error detected on SenXor interface during power up",
            help=_help_senxor_if_error,
            addr="0xB6:2-0xB6:3",
            addr_map={0xB6: (2, 3)},
        ),
        repr_func=_repr_bool,
    )

    CAPTURE_ERROR = _FieldDescriptor(
        _FieldDef(
            name="CAPTURE_ERROR",
            group="STATUS",
            readable=True,
            writable=False,
            type="bool",
            desc="Communication error during thermal data capture",
            help=_help_capture_error,
            addr="0xB6:3-0xB6:4",
            addr_map={0xB6: (3, 4)},
        ),
        repr_func=_repr_bool,
    )

    DATA_READY = _FieldDescriptor(
        _FieldDef(
            name="DATA_READY",
            group="STATUS",
            readable=True,
            writable=False,
            type="bool",
            desc="Data ready status flag",
            help=_help_data_ready,
            addr="0xB6:4-0xB6:5",
            addr_map={0xB6: (4, 5)},
        ),
        repr_func=_repr_bool,
    )

    BOOTING_UP = _FieldDescriptor(
        _FieldDef(
            name="BOOTING_UP",
            group="STATUS",
            readable=True,
            writable=False,
            type="bool",
            desc="MI48xx boot status",
            help=_help_booting_up,
            addr="0xB6:5-0xB6:6",
            addr_map={0xB6: (5, 6)},
        ),
        repr_func=_repr_bool,
    )

    CLK_SLOW_DOWN = _FieldDescriptor(
        _FieldDef(
            name="CLK_SLOW_DOWN",
            group="CLK_SPEED",
            readable=True,
            writable=True,
            type="bool",
            desc="Reduce internal clock speed",
            help=_help_clk_slow_down,
            addr="0xB7:0-0xB7:1",
            addr_map={0xB7: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    MODULE_GAIN = _FieldDescriptor(
        _FieldDef(
            name="MODULE_GAIN",
            group="SENXOR_GAIN",
            readable=True,
            writable=True,
            type="uint4",
            desc="SenXor array signal amplification",
            help=_help_module_gain,
            addr="0xB9:0-0xB9:4",
            addr_map={0xB9: (0, 4)},
        ),
        validator=_partial(_validator_value_in_map, _map_module_gain),
        repr_func=_partial(_repr_from_map, _map_module_gain),
    )

    SENXOR_TYPE = _FieldDescriptor(
        _FieldDef(
            name="SENXOR_TYPE",
            group="SENXOR_TYPE",
            readable=True,
            writable=False,
            type="uint8",
            desc="SenXor chip type identifier",
            help=_help_senxor_type,
            addr="0xBA:0-0xBA:8",
            addr_map={0xBA: (0, 8)},
        ),
        repr_func=_partial(_repr_from_map, _map_senxor_type),
    )

    MODULE_TYPE = _FieldDescriptor(
        _FieldDef(
            name="MODULE_TYPE",
            group="MODULE_TYPE",
            readable=True,
            writable=False,
            type="uint8",
            desc="Camera module type identifier",
            help=_help_module_type,
            addr="0xBB:0-0xBB:8",
            addr_map={0xBB: (0, 8)},
        ),
        repr_func=_partial(_repr_from_map, _map_module_type),
    )

    MCU_TYPE = _FieldDescriptor(
        _FieldDef(
            name="MCU_TYPE",
            group="MCU_TYPE",
            readable=True,
            writable=False,
            type="uint8",
            desc="MCU type identifier",
            help=_help_mcu_type,
            addr="0x33:0-0x33:8",
            addr_map={0x33: (0, 8)},
        ),
        repr_func=_partial(_repr_from_map, _map_mcu_type),
    )

    LUT_SOURCE = _FieldDescriptor(
        _FieldDef(
            name="LUT_SOURCE",
            group="TEMP_CONVERT_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Select LUT source",
            help=_help_lut_source,
            addr="0xBC:0-0xBC:1",
            addr_map={0xBC: (0, 1)},
        ),
        validator=_partial(_validator_value_in_map, _map_lut_source),
        repr_func=_partial(_repr_from_map, _map_lut_source),
    )

    LUT_SELECTOR = _FieldDescriptor(
        _FieldDef(
            name="LUT_SELECTOR",
            group="TEMP_CONVERT_CTRL",
            readable=True,
            writable=True,
            type="uint3",
            desc="Select specific LUT based on source",
            help=_help_lut_selector,
            addr="0xBC:1-0xBC:3",
            addr_map={0xBC: (1, 3)},
        ),
        validator=_validator_lut_selector,
        repr_func=_repr_lut_selector,
    )

    LUT_VERSION = _FieldDescriptor(
        _FieldDef(
            name="LUT_VERSION",
            group="TEMP_CONVERT_CTRL",
            readable=True,
            writable=False,
            type="uint4",
            desc="Look-up-table version",
            help=_help_lut_version,
            addr="0xBC:4-0xBC:8",
            addr_map={0xBC: (4, 8)},
        ),
    )

    CORR_FACTOR = _FieldDescriptor(
        _FieldDef(
            name="CORR_FACTOR",
            group="SENSITIVITY_FACTOR",
            readable=True,
            writable=True,
            type="uint8",
            desc="Temperature readout correction factor",
            help=_help_corr_factor,
            addr="0xC2:0-0xC2:8",
            addr_map={0xC2: (0, 8)},
        ),
        validator=_partial(_validator_uintx, 8),
    )

    START_COLOFFS_CALIB = _FieldDescriptor(
        _FieldDef(
            name="START_COLOFFS_CALIB",
            group="SELF_CALIBRATION",
            readable=True,
            writable=True,
            type="bool",
            desc="Start column offsets calibration",
            help=_help_start_coloffs_calib,
            addr="0xC5:1-0xC5:2",
            addr_map={0xC5: (1, 2)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    COLOFFS_CALIB_ON = _FieldDescriptor(
        _FieldDef(
            name="COLOFFS_CALIB_ON",
            group="SELF_CALIBRATION",
            readable=True,
            writable=False,
            type="bool",
            desc="Column offsets calibration status",
            help=_help_coloffs_calib_on,
            addr="0xC5:2-0xC5:3",
            addr_map={0xC5: (2, 3)},
        ),
    )

    USE_SELF_CALIB = _FieldDescriptor(
        _FieldDef(
            name="USE_SELF_CALIB",
            group="SELF_CALIBRATION",
            readable=True,
            writable=True,
            type="bool",
            desc="Use self-calibration data",
            help=_help_use_self_calib,
            addr="0xC5:4-0xC5:5",
            addr_map={0xC5: (4, 5)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    CALIB_SAMPLE_SIZE = _FieldDescriptor(
        _FieldDef(
            name="CALIB_SAMPLE_SIZE",
            group="SELF_CALIBRATION",
            readable=True,
            writable=True,
            type="uint3",
            desc="Number of calibration frames",
            help=_help_sample_size,
            addr="0xC5:5-0xC5:8",
            addr_map={0xC5: (5, 8)},
        ),
        validator=_partial(_validator_uintx, 3),
        repr_func=_repr_calib_sample_size,
    )

    EMISSIVITY = _FieldDescriptor(
        _FieldDef(
            name="EMISSIVITY",
            group="EMISSIVITY",
            readable=True,
            writable=True,
            type="uint8",
            desc="Target object emissivity value (percent)",
            help=_help_emissivity,
            addr="0xCA:0-0xCA:8",
            addr_map={0xCA: (0, 8)},
        ),
        validator=lambda value, _: 0 <= value <= 100,
        repr_func=lambda value, _: f"{value}%",
    )

    OFFSET = _FieldDescriptor(
        _FieldDef(
            name="OFFSET",
            group="OFFSET_CORR",
            readable=True,
            writable=True,
            type="int8",
            desc="Temperature offset correction",
            help=_help_offset,
            addr="0xCB:0-0xCB:8",
            addr_map={0xCB: (0, 8)},
        ),
        validator=_partial(_validator_uintx, 8),
        repr_func=_repr_offset,
    )

    OTF = _FieldDescriptor(
        _FieldDef(
            name="OTF",
            group="OBJECT_TEMP_FACTOR",
            readable=True,
            writable=True,
            type="int8",
            desc="Object temperature correction factor",
            help=_help_otf,
            addr="0xCD:0-0xCD:8",
            addr_map={0xCD: (0, 8)},
        ),
        validator=_partial(_validator_uintx, 8),
        repr_func=_repr_otf,
    )

    PRODUCTION_YEAR = _FieldDescriptor(
        _FieldDef(
            name="PRODUCTION_YEAR",
            group="SENXOR_ID",
            readable=True,
            writable=False,
            type="uint8",
            desc="Production year (19-99, offset from 2000)",
            help=_help_production_year,
            addr="0xE0:0-0xE0:8",
            addr_map={0xE0: (0, 8)},
        ),
        repr_func=lambda value, _: f"{value + 2000}",
    )

    PRODUCTION_WEEK = _FieldDescriptor(
        _FieldDef(
            name="PRODUCTION_WEEK",
            group="SENXOR_ID",
            readable=True,
            writable=False,
            type="uint8",
            desc="Production week (1-52)",
            help=_help_production_week,
            addr="0xE1:0-0xE1:8",
            addr_map={0xE1: (0, 8)},
        ),
    )

    MANUF_LOCATION = _FieldDescriptor(
        _FieldDef(
            name="MANUF_LOCATION",
            group="SENXOR_ID",
            readable=True,
            writable=False,
            type="uint8",
            desc="Manufacturing location (0-99)",
            help=_help_manuf_location,
            addr="0xE2:0-0xE2:8",
            addr_map={0xE2: (0, 8)},
        ),
    )

    SERIAL_NUMBER = _FieldDescriptor(
        _FieldDef(
            name="SERIAL_NUMBER",
            group="SENXOR_ID",
            readable=True,
            writable=False,
            type="uint32",
            desc="Serial number of the camera module",
            help=_help_serial_number,
            addr="0xE3:0-0xE5:8",
            addr_map={0xE3: (0, 8), 0xE4: (0, 8), 0xE5: (0, 8)},
        ),
    )

    USER_FLASH_ENABLE = _FieldDescriptor(
        _FieldDef(
            name="USER_FLASH_ENABLE",
            group="USER_FLASH_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable host access to User Flash",
            help=_help_user_flash_enable,
            addr="0xD8:0-0xD8:1",
            addr_map={0xD8: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    TEMP_UNITS = _FieldDescriptor(
        _FieldDef(
            name="TEMP_UNITS",
            group="FRAME_FORMAT",
            readable=True,
            writable=True,
            type="uint3",
            desc="Temperature units selection",
            help=_help_temp_units,
            addr="0x31:0-0x31:3",
            addr_map={0x31: (0, 3)},
        ),
        validator=_partial(_validator_value_in_map, _map_temp_units),
        repr_func=_partial(_repr_from_map, _map_temp_units),
    )

    STARK_ENABLE = _FieldDescriptor(
        _FieldDef(
            name="STARK_ENABLE",
            group="STARK_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable STARK denoising filter",
            help=_help_stark_enable,
            addr="0x20:0-0x20:1",
            addr_map={0x20: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    STARK_TYPE = _FieldDescriptor(
        _FieldDef(
            name="STARK_TYPE",
            group="STARK_CTRL",
            readable=True,
            writable=True,
            type="uint3",
            desc="STARK filter type selection",
            help=_help_stark_type,
            addr="0x20:1-0x20:4",
            addr_map={0x20: (1, 4)},
        ),
        repr_func=_partial(_repr_from_map, _map_stark_type),
        validator=_partial(_validator_value_in_map, _map_stark_type),
    )

    SPATIAL_KERNEL = _FieldDescriptor(
        _FieldDef(
            name="SPATIAL_KERNEL",
            group="STARK_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Kernel size for spatial operations",
            help=_help_spatial_kernel,
            addr="0x20:4-0x20:5",
            addr_map={0x20: (4, 5)},
        ),
        validator=_validator_bool,
        repr_func=_partial(_repr_from_map, _map_spatial_kernel),
    )

    STARK_CUTOFF = _FieldDescriptor(
        _FieldDef(
            name="STARK_CUTOFF",
            group="STARK_CUTOFF",
            readable=True,
            writable=True,
            type="uint7",
            desc="Noise suppression cutoff value",
            help=_help_stark_cutoff,
            addr="0x21:0-0x21:7",
            addr_map={0x21: (0, 7)},
        ),
    )

    STARK_GRADIENT = _FieldDescriptor(
        _FieldDef(
            name="STARK_GRADIENT",
            group="STARK_GRAD",
            readable=True,
            writable=True,
            type="uint8",
            desc="Filter output transition steepness",
            help=_help_stark_gradient,
            addr="0x22:0-0x22:8",
            addr_map={0x22: (0, 8)},
        ),
    )

    STARK_SCALE = _FieldDescriptor(
        _FieldDef(
            name="STARK_SCALE",
            group="STARK_SCALE",
            readable=True,
            writable=True,
            type="uint8",
            desc="Maximum allowed output change percentage",
            help=_help_stark_scale,
            addr="0x23:0-0x23:8",
            addr_map={0x23: (0, 8)},
        ),
    )

    MMS_KXMS = _FieldDescriptor(
        _FieldDef(
            name="MMS_KXMS",
            group="MMS_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable k-extrema median stabilization",
            help=_help_kxms,
            addr="0x25:0-0x25:1",
            addr_map={0x25: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    MMS_RA = _FieldDescriptor(
        _FieldDef(
            name="MMS_RA",
            group="MMS_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable rolling average min/max stabilization",
            help=_help_ra,
            addr="0x25:1-0x25:2",
            addr_map={0x25: (1, 2)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    MEDIAN_ENABLE = _FieldDescriptor(
        _FieldDef(
            name="MEDIAN_ENABLE",
            group="MEDIAN_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable Median denoising filter",
            help=_help_median_enable,
            addr="0x30:0-0x30:1",
            addr_map={0x30: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    MEDIAN_KERNEL_SIZE = _FieldDescriptor(
        _FieldDef(
            name="MEDIAN_KERNEL_SIZE",
            group="MEDIAN_CTRL",
            readable=True,
            writable=True,
            type="bool",
            desc="Sets median filter kernel size",
            help=_help_median_kernel_size,
            addr="0x30:1-0x30:2",
            addr_map={0x30: (1, 2)},
        ),
        validator=_validator_bool,
        repr_func=_partial(_repr_from_map, _map_median_kernel_size),
    )

    TEMPORAL_ENABLE = _FieldDescriptor(
        _FieldDef(
            name="TEMPORAL_ENABLE",
            group="FILTER_CONTROL",
            readable=True,
            writable=True,
            type="bool",
            desc="Enable temporal domain filtering",
            help=_help_temporal_enable,
            addr="0xD0:0-0xD0:1",
            addr_map={0xD0: (0, 1)},
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    TEMPORAL_INIT = _FieldDescriptor(
        _FieldDef(
            name="TEMPORAL_INIT",
            group="FILTER_CONTROL",
            readable=True,
            writable=True,
            type="bool",
            desc="Initialize temporal filter",
            help=_help_temporal_init,
            addr="0xD0:1-0xD0:2",
            addr_map={0xD0: (1, 2)},
            auto_reset=True,
        ),
        validator=_validator_bool,
        repr_func=_repr_bool,
    )

    TEMPORAL = _FieldDescriptor(
        _FieldDef(
            name="TEMPORAL",
            group="FILTER_SETTING_1",
            readable=True,
            writable=True,
            type="uint16",
            desc="Temporal filter strength",
            help=_help_temporal,
            addr="0xD1:0-0xD2:8",
            addr_map={0xD1: (0, 8), 0xD2: (0, 8)},
        ),
    )

    __field_defs__: ClassVar[dict[str, _FieldDef]] = {
        k: v._field_def for k, v in locals().items() if isinstance(v, _FieldDescriptor)
    }

    __name_list__: ClassVar[list[str]] = list(__field_defs__.keys())
    __auto_reset_list__: ClassVar[list[str]] = [k for k, v in __field_defs__.items() if v.auto_reset]
    __readable_list__: ClassVar[list[str]] = [k for k, v in __field_defs__.items() if v.readable]
    __writable_list__: ClassVar[list[str]] = [k for k, v in __field_defs__.items() if v.writable]
    __reg2fname_map__: ClassVar[dict[int, set[str]]] = defaultdict(set)

    for f_n, f_def in __field_defs__.items():
        for addr in f_def.addr_map:
            __reg2fname_map__[addr].add(f_n)

    def __init__(self, regmap: _RegMap):
        self._regmap = regmap
        self._log = get_logger(address=regmap.address)

        self._fields: dict[str, Field] = {k: getattr(self, k) for k in self.__name_list__}

    # ------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------

    @property
    def _fields_cache(self) -> dict[str, int]:
        return self._regmap._fields_cache

    @property
    def writable_fields(self) -> list[str]:
        """Return a set of all writable field names."""
        return self.__writable_list__.copy()

    @property
    def readable_fields(self) -> list[str]:
        """Return a set of all readable field names."""
        return self.__readable_list__.copy()

    @property
    def status(self) -> dict[str, int]:
        """Return a dictionary of all field values after last operation.

        Note: Due to some fields can be auto-reset, this may not reflect the current device state.

        Returns
        -------
        dict[str, int]
            The dictionary of field names and their values.

        """
        return self._fields_cache.copy()

    @property
    def fields(self) -> dict[str, Field]:
        """Return a dict of all field instances."""
        return self._fields

    @property
    def status_display(self) -> dict[str, str]:
        """Return a dictionary of all field names and human-readable representations of last status."""
        return {k: self.fields[k].display(v) for k, v in self.status.items()}

    # ------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------

    def get_field(self, field: str | Field) -> int:
        """Return the integer value of a field.

        Parameters
        ----------
        field : str | Field
            Field name (e.g. ``"FRAME_RATE_DIVIDER"``) or Field instance.

        Returns
        -------
        int
            The integer value of the field.

        """
        field = field if isinstance(field, Field) else self[field]
        return self._get_field(field)

    def get_fields(self, fields: Sequence[str]) -> dict[str, int]:
        """Get multiple field values."""
        fields_ = [self[field] for field in fields]
        return self._get_fields(fields_)

    def set_field(self, field: str | Field, value: int):
        """Set a field value."""
        field = field if isinstance(field, Field) else self[field]
        self._set_field(field, value)

    def set_fields(self, fields_values: dict[str, int]):
        """Set multiple field values."""
        fields_ = [self[field] for field in fields_values]
        values = list(fields_values.values())
        self._set_fields(fields_, values)

    # ------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------

    def _get_field(self, field: Field) -> int:
        """Get a field value."""
        regs_values = self._regmap._fetch_regs_values_by_fields([field])
        value = field._parse_field_value(regs_values)
        return value

    def _get_fields(self, fields: list[Field]) -> dict[str, int]:
        """Get multiple field values."""
        regs_values = self._regmap._fetch_regs_values_by_fields(fields)
        fields_values = {field.name: field._parse_field_value(regs_values) for field in fields}
        return fields_values

    def _set_field(self, field: Field, value: int):
        """Set a field value."""
        if not field.writable:
            raise AttributeError(f"Field '{field.name}' is read-only")
        regs_values = self._regmap._fetch_regs_values_by_fields([field])
        update = field._encode_field_value(value, regs_values)
        self._regmap.write_regs(update)

    def _set_fields(self, fields: list[Field], values: list[int]):
        """Set multiple field values."""
        for field in fields:
            if not field.writable:
                raise AttributeError(f"Field '{field.name}' is read-only")

        regs_values = self._regmap._fetch_regs_values_by_fields(fields)
        updates = regs_values
        for field, value in zip(fields, values):
            update = field._encode_field_value(value, updates)
            updates.update(update)
        self._regmap.write_regs(updates)

    def __getitem__(self, key: str) -> Field:
        """Get a field instance by name."""
        return getattr(self, key)

    def __setitem__(self, key: str, field: Field):
        raise AttributeError("Direct assignment to Fields is not allowed.")

    def __iter__(self) -> Iterator[Field]:
        return iter(self._fields.values())

    def __repr__(self):
        return f"Fields(regmap={self._regmap})"
