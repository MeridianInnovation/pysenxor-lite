# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Senxor error codes."""

from __future__ import annotations


class SenxorUnexpectedAckError(Exception):
    """Unexpected ACK received from device."""

    def __init__(self, *args):
        msg = "Unexpected ACK received from device."
        super().__init__(*args, msg)


class SenxorNotConnectedError(Exception):
    """Device is not connected."""

    def __init__(self, *args):
        msg = "Device is not connected."
        super().__init__(*args, msg)


class SenxorLostConnectionError(Exception):
    """Device lost connection."""

    def __init__(self, *args):
        msg = "Device lost connection."
        super().__init__(*args, msg)


class SenxorAckInvalidError(Exception):
    """Invalid ACK received from device."""

    def __init__(self, *args):
        msg = "Invalid ACK received from device."
        super().__init__(*args, msg)


class SenxorResponseTimeoutError(Exception):
    """Response timeout."""

    def __init__(self, *args):
        super().__init__(*args)


class SenxorNoModuleError(Exception):
    """MI48XX chip has no senxor module installed."""

    def __init__(self, *args):
        msg = "MI48XX chip has no senxor module installed."
        super().__init__(*args, msg)
