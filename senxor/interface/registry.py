# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from senxor.interface.protocol import IDevice, ISenxorInterface


def _load_serial() -> tuple[type[IDevice], type[ISenxorInterface]]:
    from senxor.interface.serial_port.core import SerialInterface, SerialPort  # noqa: PLC0415

    return SerialPort, SerialInterface


def _load_tcpip_serial() -> tuple[type[IDevice], type[ISenxorInterface]]:
    from senxor.interface.tcpip_serial.core import TCPIPInterface, TCPIPPort  # noqa: PLC0415

    return TCPIPPort, TCPIPInterface


class InterfaceRegistry:
    """Registry for the interfaces."""

    _BUILTIN_LOADERS: ClassVar[dict[str, Callable[[], tuple[type[IDevice], type[ISenxorInterface]]]]] = {
        "serial": _load_serial,
        "tcpip_serial": _load_tcpip_serial,
    }

    _registry: ClassVar[dict[str, tuple[type[IDevice], type[ISenxorInterface]]]] = {}

    @classmethod
    def _interface_names(cls) -> list[str]:
        seen: set[str] = set()
        names: list[str] = []
        for name in (*cls._registry, *cls._BUILTIN_LOADERS):
            if name not in seen:
                seen.add(name)
                names.append(name)
        return names

    @classmethod
    def _resolve(cls, name: str) -> tuple[type[IDevice], type[ISenxorInterface]]:
        if name in cls._registry:
            return cls._registry[name]
        loader = cls._BUILTIN_LOADERS.get(name)
        if loader is None:
            raise KeyError(f"Unknown interface type: {name}")
        try:
            entry = loader()
        except ImportError as exc:
            msg = f"Failed to load interface '{name}': missing required dependencies"
            raise ImportError(msg) from exc
        cls._registry[name] = entry
        return entry

    @classmethod
    def register(cls, name: str, device_class: type[IDevice], interface_class: type[ISenxorInterface]) -> None:
        """Register a new interface.

        Parameters
        ----------
        name : str
            The name of the interface.
        device_class : type[IDevice]
            The class of the device.
        interface_class : type[ISenxorInterface]
            The class of the interface.

        Returns
        -------
        None

        """
        cls._registry[name] = (device_class, interface_class)

    @classmethod
    def get(cls, name: str) -> tuple[type[IDevice], type[ISenxorInterface]]:
        """Get the interface class by name."""
        return cls._resolve(name)

    @classmethod
    def list_devices(cls, interface_name: str) -> Sequence[IDevice]:
        _, interface_class = cls.get(interface_name)
        return interface_class.list_devices()

    @classmethod
    def create_interface(cls, device: IDevice) -> ISenxorInterface:
        interface_type = getattr(type(device), "INTERFACE_TYPE", None)
        if interface_type is not None:
            device_class, interface_class = cls.get(interface_type)
            if not isinstance(device, device_class):
                msg = f"Device type {type(device)!r} does not match interface '{interface_type}'"
                raise ValueError(msg)
            return interface_class(device)

        for name in cls._interface_names():
            device_class, interface_class = cls._resolve(name)
            if isinstance(device, device_class):
                return interface_class(device)
        raise ValueError(f"Unsupported device type: {type(device)}")
