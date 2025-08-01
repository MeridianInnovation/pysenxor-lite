# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Constants related to Senxor devices."""

# --- Physical Constants ---
KELVIN = 273.15

# --- Sensor Constants ---
SENXOR_VENDER_ID = 0x0416
SENXOR_PRODUCT_ID = {
    0xB002: "EVK",
    0xB020: "XPRO",
    0x9393: "XCAM",
}

# Format: (height, width)
SENXOR_FRAME_SHAPE = {
    4960: (62, 80),
    19200: (120, 160),
}


SENXOR_TYPE = {
    0: "MI0801-non-MP",
    1: "MI0801",
    2: "MI0802",
    4: "MI0802-Rev1",
    5: "MI0802-Rev2",
    6: "MI16XX-Rev1",
}


MODULE_TYPE = {
    19: "MI0802-M5S",
    20: "MI0802-M6S",
    21: "MI0802-M7G",
    22: "MI0802-50",
    24: "MI0802-M230",
    28: "MI1602-M5S",
    29: "MI1602-M6C",
    40: "MI1602-M5S",
    41: "MI1602-M6C",
    255: "MI0801",
}

# We can get the frame shape from the senxor type.
# Format: (height, width)
SENXOR_TYPE2FRAME_SHAPE = {
    0: (62, 80),
    1: (62, 80),
    3: (62, 80),
    4: (62, 80),
    5: (62, 80),
    6: (120, 160),
}

MCU_TYPE = {
    0: "MI48D4",
    1: "MI48D5",
    2: "MI48E",
    3: "MI48G",
    4: "MI48C",
    255: "MI48D4",
}
