# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Core classes for the configuration of the senxor."""

from __future__ import annotations

import inspect
from abc import ABC
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar, cast, overload

if TYPE_CHECKING:
    from senxor.regmap.core import SenxorFieldsManager, SenxorRegistersManager
    from senxor.regmap.types import FieldName, RegisterName


class Register(ABC):
    """Base class for all registers.

    Attributes
    ----------
    name : ClassVar[str]
        The name of the register.
    description : ClassVar[str]
        The description of the register.
    address : ClassVar[int]
        The address of the register.
    writable : ClassVar[bool]
        Whether the register is writable.
    readable : ClassVar[bool]
        Whether the register is readable.
    self_reset : ClassVar[bool]
        Whether the register value can be modified by the senxor itself.

    default_value : int | None
        The default value of the register. Depends on the module type and firmware version.

    """

    name: ClassVar[RegisterName]
    description: ClassVar[str]
    address: ClassVar[int]

    writable: ClassVar[bool]
    readable: ClassVar[bool]

    self_reset: bool

    default_value: int | None

    def __init__(self, regmap: SenxorRegistersManager):
        """Initialize the register instance.

        Parameters
        ----------
        regmap : SenxorRegistersManager
            The registers manager instance.

        """
        self.regmap = regmap
        self._value: int | None = None

    @property
    def value(self) -> int:
        """The value of the register."""
        return self.get()

    def __repr__(self) -> str:
        return f"<Register(name={self.name}, address=0x{self.address:02X})>"

    def __str__(self) -> str:
        value_str = "" if self._value is None else f"= {self.value:02d}"
        return f"{self.name}(0x{self.address:02X}){value_str}"

    def get(self, *, refresh: bool = True) -> int:
        """Get the value of the register.

        Parameters
        ----------
        refresh : bool, optional
            If True and the register supports self-reset, read from device. Default is True.

        Returns
        -------
        int
            The register value.

        """
        if self._value is None or (self.self_reset and refresh):
            self.read()
        return cast("int", self._value)

    def set(self, value: int) -> None:
        """Set the value of the register.

        Parameters
        ----------
        value : int
            The value to set.

        """
        # The regmap will validate the value, handle the error and update self._value.
        self.regmap.write_reg(self.address, value)

    def read(self) -> int:
        """Read the value from the register on the device.

        Returns
        -------
        int
            The register value.

        """
        # The regmap will handle the error and update self._value.
        return self.regmap.read_reg(self.address)

    def reset(self) -> None:
        """Reset the register to its default value."""
        # The regmap will handle the error and update self._value.
        if self.default_value is None:
            raise ValueError("Default value is not set for the register")
        self.set(self.default_value)

    def _update_value(self, value: int) -> None:
        # Called by the regmap to update the value of the register.
        self._value = value


TRegister = TypeVar("TRegister", bound=Register)


class RegisterDescriptor(Generic[TRegister]):
    def __init__(self, cls: type[TRegister]):
        self.cls = cls

    @overload
    @overload
    def __get__(self, instance: None, owner) -> type[TRegister]: ...
    @overload
    def __get__(self, instance: SenxorRegistersManager, owner) -> TRegister: ...
    def __get__(self, instance: SenxorRegistersManager | None, owner):
        if instance is None:
            return self.cls
        try:
            return instance.get_reg(self.cls.name)  # type: ignore[reportArgumentType]
        except KeyError:
            raise AttributeError(f"Register '{self.cls.name}' not found in the register system") from None

    def __set__(self, instance: SenxorRegistersManager, value: int) -> None:
        raise AttributeError("Use '.set()' to set the value of a register")


def describe(cls: type[TRegister]) -> RegisterDescriptor[TRegister]:
    return RegisterDescriptor[TRegister](cls)


class Field(ABC):
    """Base class for all register fields."""

    name: ClassVar[FieldName]
    description: ClassVar[str]
    help: ClassVar[str]

    address: ClassVar[int]
    bits_range: ClassVar[tuple[int, int]]
    writable: ClassVar[bool]
    readable: ClassVar[bool]

    self_reset: bool

    enabled: bool = True
    disabled_reason: str | None = None
    default_value: int | None = None

    def __init__(self, fieldmap: SenxorFieldsManager):
        self.fieldmap = fieldmap
        self._value: int | None = None
        self._max_value = (1 << (self.bits_range[1] - self.bits_range[0])) - 1

    @property
    def value(self) -> int:
        """The value of the field."""
        return self.get()

    @property
    def display(self) -> str | int | float:
        """The display value of the field."""
        return self.get_display(self.value)

    def get(self, *, refresh: bool = True) -> int:
        """Get the value of the field.

        Parameters
        ----------
        refresh : bool, optional
            If True and the field supports self-reset, read from device. Default is True.

        Returns
        -------
        int
            The field value.

        """
        if self._value is None or (self.self_reset and refresh):
            self.read()
        return cast("int", self._value)

    def set(self, value: int, *, force: bool = False) -> None:
        """Set the value of the field.

        Parameters
        ----------
        value : int
            The value to set.
        force : bool, optional
            If True, skip validation. Default is False.

        """
        # The regmap will validate the value, handle the error and update self._value.
        self.fieldmap.set_field(self.name, value, force=force)

    def read(self) -> int:
        """Read the value from the field on the device.

        Returns
        -------
        int
            The field value.

        """
        # The regmap will validate the address, handle the error and update self._value.
        return self.fieldmap.read_field(self.name)

    def reset(self) -> None:
        """Reset the field to its default value."""
        # The regmap will handle the error and update self._value.
        if self.default_value is None:
            raise ValueError("Default value is not set for the field")
        self.set(self.default_value)

    def validate_value(self, value: int) -> None:  # noqa: B027
        """Validate the field value.

        Parameters
        ----------
        value : int
            The value to validate.

        Raises
        ------
        ValueError
            If validation fails.

        """

    def get_display(self, value: int) -> str | int | float:
        """Get the display value of the field.

        Parameters
        ----------
        value : int
            The raw field value.

        Returns
        -------
        str | int | float
            The display value.

        Examples
        --------
        >>> MCU_TYPE.get_display(0)
        "MI48D4"

        """
        return value

    def _update_value(self, value: int) -> None:
        # Called by the regmap to update the value of the field.
        self._value = value

    def __repr__(self) -> str:
        return f"<Field(name={self.name}, address=0x{self.address:02X}, bits_range={self.bits_range})>"

    def __str__(self) -> str:
        value_str = "" if self._value is None else f"= {self.value:02d}"
        return f"{self.name}(0x{self.address:02X}:{self.bits_range[0]}-{self.bits_range[1]}){value_str}"


TField = TypeVar("TField", bound=Field)


class FieldDescriptor(Generic[TField]):
    def __init__(self, cls: type[TField]):
        self.cls = cls

    @overload
    @overload
    def __get__(self, instance: None, owner) -> type[TField]: ...
    @overload
    def __get__(self, instance: SenxorFieldsManager, owner) -> TField: ...
    def __get__(self, instance: SenxorFieldsManager | None, owner):
        if instance is None:
            return self.cls
        try:
            return instance.get_field(self.cls.name)  # type: ignore[reportArgumentType]
        except KeyError:
            raise AttributeError(f"Field '{self.cls.name}' not found in the register system") from None

    def __set__(self, instance: SenxorRegistersManager, value: int) -> None:
        raise AttributeError("Use '.set()' to set the value of a field")


def describe_field(cls: type[TField]) -> FieldDescriptor[TField]:
    cls.help = inspect.cleandoc(cls.help)
    return FieldDescriptor[TField](cls)
