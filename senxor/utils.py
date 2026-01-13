# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Utilities for Senxor devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, overload

import numpy as np

from senxor._senxor import Senxor
from senxor.cam import list_camera
from senxor.interface.registry import InterfaceRegistry

# To compatible with the old version
from senxor.proc import normalize, raw_to_frame

if TYPE_CHECKING:
    from collections.abc import Sequence

    from senxor.interface.protocol import IDevice
    from senxor.interface.serial_port.core import SerialPort

__all__ = [
    "connect",
    "data_to_frame",
    "list_camera",
    "list_senxor",
    "remap",
]


@overload
def list_senxor() -> list[SerialPort]: ...
@overload
def list_senxor(interface: Literal["serial"]) -> list[SerialPort]: ...
def list_senxor(interface: Literal["serial"] = "serial", **kwargs) -> Sequence[IDevice]:
    """List available Senxor devices.

    Parameters
    ----------
    interface : Literal["serial"], optional
        The interface type to list devices for, by default "serial"

    **kwargs
        Additional arguments for backward compatibility.

    Returns
    -------
    Sequence[IDevice]
        A list of available Senxor devices.

    Raises
    ------
    ValueError
        If the interface type is not supported.

    """
    interface = kwargs.pop("type", interface)  # Backward compatibility
    return InterfaceRegistry.list_devices(interface)


@overload
def connect(device: SerialPort, *, auto_open: bool = True) -> Senxor[SerialPort]: ...
@overload
def connect(device: None, *, auto_open: bool = True) -> Senxor[SerialPort]: ...
def connect(device=None, *, auto_open: bool = True, **kwargs) -> Senxor:
    """Connect to a Senxor device.

    Parameters
    ----------
    device : ListPortInfo | None, optional
        The device to connect to, by default None
        If None, the first serial device is connected.
    auto_open : bool, optional
        Whether to automatically open the device, by default True
    **kwargs
        Additional arguments to pass to the Senxor constructor.

    Returns
    -------
    Senxor
        The Senxor device.

    Raises
    ------
    ValueError
        If the device type is not supported.

    Examples
    --------
    >>> from senxor import list_senxor, connect
    >>> devices = list_senxor("serial")
    >>> senxor = connect(devices[0])
    >>> senxor.open()

    """
    device = kwargs.pop("address", device)  # Backward compatibility

    if device is None:
        devices = list_senxor()
        if len(devices) == 0:
            raise ValueError("No devices found")
        device = devices[0]

    interface = InterfaceRegistry.create_interface(device)
    senxor = Senxor(interface, auto_open=auto_open, **kwargs)
    return senxor


def remap(
    image: np.ndarray,
    in_range: tuple | None = None,
    out_range: tuple | None = None,
    dtype: Any = np.uint8,
):
    """Remap image intensity to a desired range and data type using NumPy.

    It's equivalent to `normalize(..., dtype=np.uint8)`.

    Parameters
    ----------
    image : np.ndarray
        The image to remap.
    in_range : tuple | None, optional
        The input range of the image. If `None`, the image's min/max are used.
    out_range : tuple | None, optional
        The output range of the image.
    dtype : Any, optional
        The data type of the image.

    Returns
    -------
    np.ndarray
        The remapped image.

    """
    return normalize(image, in_range, out_range, dtype)


def data_to_frame(data: np.ndarray, array_shape: tuple[int, int] | None = None, *, hflip: bool = False) -> np.ndarray:  # noqa: ARG001
    """Convert raw data to a frame.

    It's used for backward compatibility.

    Parameters
    ----------
    data : np.ndarray
        The raw data.
    array_shape : tuple[int, int] | None
        Not needed, it's for backward compatibility.
    hflip : bool, optional
        Whether to flip the image horizontally.

    Returns
    -------
    np.ndarray
        The frame.

    """
    frame = raw_to_frame(data)
    if hflip:
        frame = np.flip(frame, axis=1)
    return frame
