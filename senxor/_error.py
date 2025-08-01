# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Senxor error codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Policy:
    """Error policy for the senxor."""

    callback: Callable[[Exception], Any] | None = None
    """The callback to handle the error."""
    retry_times: int = 1
    """The number of times to retry the operation. 0 means no retry."""
    retry_interval: float = 0.01
    """The interval between retries."""


class InvalidAckHeaderError(Exception):
    """Exception raised when the message header is not valid."""

    def __init__(self, header: bytes, *args: Any) -> None:
        self.header = header
        super().__init__(f"Invalid message header: {header}", *args)


class InvalidAckBodyError(Exception):
    """Exception raised when the message body is not valid."""

    def __init__(self, *args: Any) -> None:
        super().__init__("Invalid message body", *args)


class ChecksumError(Exception):
    """Exception raised when a checksum validation fails."""

    def __init__(self, expected_checksum: bytes, message_checksum: bytes, *args: Any) -> None:
        self.expected_checksum = expected_checksum
        self.message_checksum = message_checksum
        super().__init__(f"Checksum mismatch, expected: {expected_checksum}, message: {message_checksum}", *args)


class SenxorReadTimeoutError(TimeoutError):
    """Exception raised when the read operation timeout."""

    def __init__(self, *args: Any) -> None:
        super().__init__("Serial read timeout", *args)


class SenxorNotConnectedError(Exception):
    """Exception raised when the device is not connected."""

    def __init__(self, *args: Any) -> None:
        super().__init__("Not Connected", *args)
