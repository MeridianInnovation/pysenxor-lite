"""Utilities for Senxor devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from senxor._interface import SENXOR_CONNECTION_TYPES, is_senxor_usb, list_senxor_usb
from senxor._senxor import Senxor
from senxor.cam import LiteCamera, list_camera

# To compatible with the old version
from senxor.proc import remap

if TYPE_CHECKING:
    from serial.tools.list_ports_common import ListPortInfo

__all__ = [
    "LiteCamera",
    "connect_senxor",
    "is_senxor_usb",
    "list_camera",
    "list_senxor",
    "list_senxor_usb",
    "remap",
]


def list_senxor(type: Literal["serial"] | None = None, exclude: list[str] | str | None = None) -> list[Any]:
    """List all Senxor devices available.

    The return value is a list of Senxor devices, use `senxor.connect` to connect to a device.

    Parameters
    ----------
    type : Literal["serial"] | None, optional
        The type of device to list.
        If not provided, all types will be listed.
    exclude : list[str] | str | None, optional
        If `type` is provided, this will be ignored.
        A list of device names to exclude from the list.
        If not provided, all devices will be listed.

    Returns
    -------
    list
        A list of Senxor devices, use `senxor.connect` to connect to a device.

    """
    devices = []
    if exclude is None:
        exclude = []
    if isinstance(exclude, str):
        exclude = [exclude]

    if type is None:
        for t, connection_class in SENXOR_CONNECTION_TYPES.items():
            if t in exclude:
                continue
            devices.extend(connection_class.discover())

    else:
        devices = SENXOR_CONNECTION_TYPES[type].discover()

    return devices


def connect(
    address: str | ListPortInfo | None = None,
    type: Literal["serial"] | None = None,
    *,
    auto_open: bool = True,
    stop_stream: bool = True,
    **kwargs,
) -> Senxor:
    """Connect to a Senxor device.

    Parameters
    ----------
    address : str | ListPortInfo, optional
        The address of the device to connect to.
    type : Literal["serial"], optional
        The type of device to connect to.
        If not provided, will attempt to auto-detect from address.
    auto_open : bool, optional
        Whether to automatically open the device.
    stop_stream : bool, optional
        Whether to stop the stream when the device is opened.
    **kwargs
        Additional arguments passed to the interface constructor.

    Returns
    -------
    Senxor
        The Senxor device.

    Examples
    --------
    Use a context manager to connect to a device:

    >>> from senxor import list_senxor, connect
    >>> addrs = list_senxor("serial")
    >>> with connect(addrs[0]) as dev:
    ...     print(f"Connected to device {dev.address}")
    Connected to device COM3

    Or connect to a device without a context manager:

    >>> dev = connect(addrs[0])
    >>> print(f"Connected to device {dev.address}")
    Connected to device COM3

    It's recommended to use a context manager because it will automatically close the device when the context is exited.

    """
    if address is None:
        addrs = list_senxor(type, **kwargs)
        if len(addrs) == 0:
            raise ValueError("No Senxor device found")
        address = addrs[0]
        type = "serial"

    return Senxor(address, type, auto_open, stop_stream, **kwargs)


def connect_senxor(
    address: str | ListPortInfo | None = None,
    type: Literal["serial"] | None = None,
    *,
    auto_open: bool = True,
    stop_stream: bool = True,
    **kwargs,
) -> Senxor:
    return connect(address, type, auto_open=auto_open, stop_stream=stop_stream, **kwargs)
