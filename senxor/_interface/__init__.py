# Copyright (c) 2025 Meridian Innovation. All rights reserved.
from typing import Literal, overload

from senxor._interface.protocol import InterfaceProtocol
from senxor._interface.serial_ import (
    SENXOR_PRODUCT_ID,
    SENXOR_VENDER_ID,
    SerialInterface,
    is_senxor_usb,
    list_senxor_usb,
)

__all__ = [
    "SENXOR_PRODUCT_ID",
    "SENXOR_VENDER_ID",
    "InterfaceProtocol",
    "SerialInterface",
    "is_senxor_usb",
    "list_senxor_usb",
    "register_senxor_interface",
]

SENXOR_INTERFACES: dict[str, type[InterfaceProtocol]] = {
    "serial": SerialInterface,
}


def register_senxor_interface(type_: str, interface_class: type[InterfaceProtocol]) -> None:
    """Register a new interface for Senxor devices.

    Parameters
    ----------
    type_ : str
        The type of interface to register.
    interface_class : type[InterfaceProtocol]
        The class to use for the connection. Must be a subclass of InterfaceProtocol.

    """
    if type_ in SENXOR_INTERFACES:
        msg = f"Interface {type_} already registered"
        raise ValueError(msg)
    SENXOR_INTERFACES[type_] = interface_class
