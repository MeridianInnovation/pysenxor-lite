# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from senxor.regmap._regs import Registers


@dataclass(frozen=True)
class _RegisterDef:
    name: str
    addr: int
    readable: bool
    writable: bool
    desc: str
    auto_reset: bool = False

    def __str__(self) -> str:
        r = "R" if self.readable else ""
        w = "W" if self.writable else ""

        access = f"{r}{w}"
        if not access:
            access = "NA"

        return f"0x{self.addr:02X} {self.name} ({access})"

    def __repr__(self):
        return f"<RegisterDef {self.__str__()}>"


class Register:
    def __init__(self, descriptor: _RegisterDescriptor, instance: Registers):
        """Initialize the register instance.

        Note: Do not initialize this class directly, this class is designed to be used as a Descriptor Proxy.

        Parameters
        ----------
        descriptor : _RegisterDescriptor
            The register descriptor.
        instance : Registers
            The instance of the register.

        """
        self._descriptor = descriptor
        self._instance = instance

        _register_def = descriptor._register_def

        self.name = _register_def.name
        self.addr = _register_def.addr
        self.readable = _register_def.readable
        self.writable = _register_def.writable
        self.auto_reset = _register_def.auto_reset
        self.desc = _register_def.desc

    # ------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------

    @property
    def value(self) -> int:
        """The value of the register."""
        return self.get()

    # ------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------

    def get(self) -> int:
        """Get the value of the register."""
        return self._instance.get_reg(self.addr)

    def read(self) -> int:
        """Read the value of the register."""
        return self._instance.read_reg(self.addr)

    def set(self, value: int):
        """Set the value of the register."""
        self._instance.write_reg(self.addr, value)

    def __repr__(self):
        return f"<Register(name={self.name}, addr=0x{self.addr:02X})>"

    def __str__(self):
        return f"{self.name} (0x{self.addr:02X})"


class _RegisterDescriptor:
    """Register descriptor."""

    def __init__(self, register_def: _RegisterDef):
        self._register_def = register_def
        self._values: weakref.WeakKeyDictionary[Registers, Register] = weakref.WeakKeyDictionary()

    def __get__(self, instance: Registers | None, owner: type[Registers]) -> Register:
        if instance is None:
            return self  # type: ignore[return-value]
        elif instance not in self._values:
            instance_proxy = Register(self, instance)
            self._values[instance] = instance_proxy
            return instance_proxy
        else:
            return self._values[instance]

    def __set__(self, instance: Registers, value: int):
        raise AttributeError("Use '.set()' to set the value of a register")

    def __repr__(self):
        return f"_RegisterDescriptor(register_def={self._register_def})"
