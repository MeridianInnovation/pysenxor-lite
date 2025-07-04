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


# The type of the senxor.
SENXOR_TYPE = {
    0: "MI0801-non-MP",
    1: "MI0801",
    2: "MI0802",
    4: "MI0802-1",
    5: "MI0802-2",
    6: "MI1603",
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
