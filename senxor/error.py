# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Senxor error codes."""

from __future__ import annotations


class SenxorUnexpectedAckError(Exception):
    def __init__(self, *args):
        msg = "Unexpected ACK received from device."
        super().__init__(*args, msg)


class SenxorNotConnectedError(Exception):
    def __init__(self, *args):
        msg = "Device is not connected."
        super().__init__(*args, msg)


class SenxorLostConnectionError(Exception):
    def __init__(self, *args):
        msg = "Device lost connection."
        super().__init__(*args, msg)


class SenxorAckInvalidError(Exception):
    def __init__(self, *args):
        msg = "Invalid ACK received from device."
        super().__init__(*args, msg)


class SenxorResponseTimeoutError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class SenxorNoModuleError(Exception):
    def __init__(self, *args):
        msg = "MI48XX chip has no senxor module installed."
        super().__init__(*args, msg)
