# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from senxor.regmap._fields import Fields


def _default_repr(value: Any, _: Fields) -> str:
    if value is None:
        return ""
    return str(value)


@dataclass(frozen=True)
class _FieldDef:
    name: str
    group: str
    readable: bool
    writable: bool
    type: str
    desc: str
    help: str
    addr: str
    addr_map: dict[int, tuple[int, int]]
    auto_reset: bool = False

    def __str__(self):
        return f"{self.group}:{self.name}"

    def __repr__(self):
        return f"<FieldDef {self.__str__()}>"


class Field:
    """Field instance.

    Attributes
    ----------
    name : str
        The name of the field.
    group : str
        The register group that the field belongs to.
    readable : bool
        Whether the field is readable.
    writable : bool
        Whether the field is writable.
    type : str
        The type of the field.
    desc : str
        The description of the field.
    help : str
        The help of the field.
    value : int
        The integer value of the field.
    display : str
        The display value of the field, which is the value formatted for display.

    """

    def __init__(
        self,
        descriptor: _FieldDescriptor,
        instance: Fields,
    ):
        """Initialize the field instance.

        Note: Do not initialize this class directly, this class is designed to be used as a Descriptor Proxy.

        Parameters
        ----------
        descriptor : _FieldDescriptor
            The field descriptor.
        instance : Fields
            The instance of the field.

        """
        self._descriptor = descriptor
        self._instance = instance

        _field_def = descriptor._field_def

        self.name = _field_def.name
        self.group = _field_def.group
        self.readable = _field_def.readable
        self.writable = _field_def.writable
        self.type = _field_def.type
        self.desc = _field_def.desc
        self.help = _field_def.help
        self.addr = _field_def.addr
        self.addr_map = _field_def.addr_map
        self.auto_reset = _field_def.auto_reset

        self._repr_func = self._descriptor._repr_func
        self._validator = self._descriptor._validator

    # ----------------------------------------------------------------
    # Public properties
    # ----------------------------------------------------------------

    @property
    def value(self) -> int:
        """Return the current value of the field (alias of get)."""
        return self.get()

    # ----------------------------------------------------------------
    # Public methods
    # ----------------------------------------------------------------

    def get(self) -> int:
        """Return current integer value of this field."""
        return self._instance._get_field(self)

    def set(self, value: int):
        """Write value to field after validation."""
        self._instance._set_field(self, value)

    def validate(self, value: Any) -> bool:
        """Validate *value* using custom validator if present."""
        if self._validator is None:
            return True
        else:
            return self._validator(value, self._instance)

    def display(self, value: int | None = None) -> str:
        """Return the display value of the field.

        Parameters
        ----------
        value : int | None
            The value to display. If None, will try to get the current value of the field.

        Returns
        -------
        str
            The display value of the field.

        """
        value = value if value is not None else self.get()
        return self._repr_func(value, self._instance)

    # ----------------------------------------------------------------
    # Private methods
    # ----------------------------------------------------------------

    def _parse_field_value(self, regs_values: dict[int, int]) -> int:
        """Parse field value from register bytes."""
        val = 0
        shift = 0
        for addr, (start, end) in self.addr_map.items():
            length = end - start
            mask = (1 << length) - 1
            part = (regs_values[addr] >> start) & mask
            val |= part << shift
            shift += length
        return val

    def _encode_field_value(
        self,
        value: int,
        current_regs: dict[int, int],
    ) -> dict[int, int]:
        """Encode value into register updates dict."""
        if not self.validate(value):
            raise ValueError(f"Value {value} failed validation for field '{self.name}'")

        updates: dict[int, int] = {}
        shift = 0
        for addr, (start, end) in self.addr_map.items():
            length = end - start
            mask_bits = (1 << length) - 1
            part = (value >> shift) & mask_bits
            reg_mask = mask_bits << start
            new_val = (current_regs[addr] & ~reg_mask) | ((part << start) & reg_mask)
            updates[addr] = new_val
            shift += length
        return updates

    def __repr__(self):
        return f"<Field(name={self.name})>"

    def __str__(self):
        return f"{self.name}"


class _FieldDescriptor:
    def __init__(
        self,
        field_def: _FieldDef,
        validator: Callable[[Any, Any], bool] | None = None,
        repr_func: Callable[[Any, Any], str] = _default_repr,
    ):
        self._field_def = field_def
        self._values = weakref.WeakKeyDictionary()
        self._repr_func = repr_func
        self._validator = validator

    def __get__(self, instance: Fields | None, owner: type[Fields]) -> Field:
        if instance is None:
            return self  # type: ignore[return-value]
        elif instance not in self._values:
            instance_proxy = Field(self, instance)
            self._values[instance] = instance_proxy
            return instance_proxy
        else:
            return self._values[instance]

    def __set__(self, instance: Fields, value: Any):
        raise AttributeError("Use '.set()' to set the value of a field")

    def __repr__(self):
        return f"_FieldDescriptor(field_def={self._field_def})"
