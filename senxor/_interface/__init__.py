from typing import Literal

from .protocol import SenxorInterfaceProtocol
from .usb_serial import SENXOR_PRODUCT_ID, SENXOR_VENDER_ID, SenxorInterfaceSerial, is_senxor_usb, list_senxor_usb

__all__ = [
    "SENXOR_CONNECTION_TYPES",
    "SENXOR_PRODUCT_ID",
    "SENXOR_VENDER_ID",
    "SenxorInterfaceProtocol",
    "SenxorInterfaceSerial",
    "is_senxor_usb",
    "list_senxor_usb",
    "register_senxor_connection_type",
]

SENXOR_CONNECTION_TYPES: dict[str, type[SenxorInterfaceProtocol]] = {
    "serial": SenxorInterfaceSerial,
    # TODO: "tcp": SenxorInterfaceTCP,
    # TODO:"gpio": SenxorInterfaceGPIO,
}


def register_senxor_connection_type(type_: Literal["serial"], interface_class: type[SenxorInterfaceProtocol]) -> None:
    """Register a new connection type for Senxor devices.

    Parameters
    ----------
    type_ : Literal["serial"]
        The type of connection to register.
    interface_class : type[SenxorInterfaceProtocol]
        The class to use for the connection. Must be a subclass of SenxorInterfaceProtocol.

    """
    if type_ in SENXOR_CONNECTION_TYPES:
        msg = f"Connection type {type_} already registered"
        raise ValueError(msg)
    SENXOR_CONNECTION_TYPES[type_] = interface_class
