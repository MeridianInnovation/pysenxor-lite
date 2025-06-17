"""All useful constants."""

# --- Physical Constants ---
KELVIN = 273.15

# --- Sensor Constants ---
SENXOR_VENDER_ID = 0x0416
SENXOR_PRODUCT_ID = {
    0xB002: "EVK",
    0xB020: "XPRO",
    0x9393: "XCAM",
}

# Following the numpy format: (height, width)
SENXOR_FRAME_SHAPE = {
    4960: (62, 80),
    19200: (120, 160),
}
