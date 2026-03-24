# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Constants related to Senxor devices."""

# --- Physical Constants ---
KELVIN = 273.15
FAHRENHEIT_OFFSET = 32
CELSIUS_TO_FAHRENHEIT_RATIO = 9 / 5
FAHRENHEIT_TO_CELSIUS_RATIO = 5 / 9

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
    2500: (50, 50),
}


SENXOR_TYPE = {
    0: "MI0801 non-MP",  # non-MP modules
    1: "MI0801",  # MP modules
    4: "MI0802",  # cougar 80x62
    5: "MI0802",  # cougar 80x62
    6: "MI1602",  # panther 120x160
    8: "MI0802",  # cougar 80x62, high sensitivity
    9: "MI0502",  # Cheetah 50x50
}

MCU_TYPE = {
    0: "MI48D4",  # MI48, Cougar
    1: "MI48D5",  # MI48, Panther
    2: "MI48E",  # MI467, Panther
    3: "MI48G",  # GPM4, Panther
    4: "MI49",  # CCore 4201, Cougar, Cheetah
    5: "MI40",  # CCore 4001, Cougar, Cheetah
    255: "MI48D4",  # MI48, Cougar (older FW has 0x33 Reserved, returning 255)
}

MODULE_TYPE = {
    19: "MI0802-M5S",
    20: "MI0802-M6S",
    21: "MI0802-M7G",
    22: "MI0802-50",
    24: "MI0802-M230",  # M230-022
    28: "MI1602-M5S",
    29: "MI1602-M6C",
    40: "MI1602-M5S",  # Panther engineering sample
    41: "MI1602-M6C",  # Panther engineering sample
    50: "MI0502-M230F",  # Cheetah WFOV, FPC
    255: "MI0801",  # Bobcat FW does not have this register; read returns 0xFF
    42: "MI1602-Z6C",  # Panther MP, Zn-Alloy LHA
    00: "MI0505-M240",  # Cheetah, WFOV, FPC
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
    8: (62, 80),
    9: (50, 50),
}
