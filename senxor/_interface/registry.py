# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from senxor._interface.serial_ import SerialInterface, SerialPort

if TYPE_CHECKING:
    from collections.abc import Sequence

    from senxor._interface.protocol import IDevice, ISenxorInterface


class InterfaceRegistry:
    _registry: ClassVar[dict[str, tuple[type[IDevice], type[ISenxorInterface]]]] = {
        "serial": (SerialPort, SerialInterface),
    }

    @classmethod
    def register(cls, name: str, device_class: type[IDevice], interface_class: type[ISenxorInterface]) -> None:
        cls._registry[name] = (device_class, interface_class)

    @classmethod
    def get(cls, name: str) -> tuple[type[IDevice], type[ISenxorInterface]]:
        if name not in cls._registry:
            raise KeyError(f"Unknown interface type: {name}")
        return cls._registry[name]

    @classmethod
    def list_devices(cls, interface_name: str) -> Sequence[IDevice]:
        _, interface_class = cls.get(interface_name)
        return interface_class.list_devices()

    @classmethod
    def create_interface(cls, device: IDevice) -> ISenxorInterface:
        for device_class, interface_class in cls._registry.values():
            if isinstance(device, device_class):
                return interface_class(device)
        raise ValueError(f"Unsupported device type: {type(device)}")
