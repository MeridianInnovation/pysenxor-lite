# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, cast

from senxor.interface.protocol import TDevice
from senxor.log import get_logger
from senxor.regmap.fields import Fields
from senxor.regmap.registers import Registers

if TYPE_CHECKING:
    from collections.abc import Iterator

    from senxor.interface.protocol import ISenxorInterface
    from senxor.regmap.base import Field, Register
    from senxor.regmap.types import FieldName, RegisterAddress, RegisterName


class SenxorRegistersManager(Registers, Generic[TDevice]):
    """The register system for the senxor.

    Attributes
    ----------
    interface : ISenxorInterface[TDevice]
        The interface of the senxor.
    registers : dict[int, Register]
        The dictionary of registers instance by address.
    fieldmap : SenxorFieldsManager
        The field system for the senxor.
    cache : dict[int, int | None]
        The cache of the registers values.

    Examples
    --------
    1. Iterate over the registers:
    >>> regs = SenxorRegistersManager(interface)
    >>> for reg in regs:
    ...     print(reg.name, reg.address)

    2. Use subscript notation to get a register instance:
    >>> regs = SenxorRegistersManager(interface)
    >>> regs["MCU_RESET"]
    >>> regs[0x00]

    3. Check if a register exists:
    >>> "MCU_RESET" in regs
    >>> 0x00 in regs

    4. Use the cache to get the cached register value:
    >>> regs.cache
    {0x00: 0x00, 0x01: 0x01, ...}

    5. Refresh the cache of all registers:
    >>> regs.refresh_all()
    >>> regs.cache
    {0x00: 0x00, 0x01: 0x01, ...}

    Notes
    -----
    Each register operation should be performed through this class to ensure logging,
    cache updating and error handling.

    """

    def __init__(self, interface: ISenxorInterface[TDevice]):
        self.interface: ISenxorInterface[TDevice] = interface
        self._log = get_logger(name=self.interface.device.name)
        self.registers: dict[int, Register] = {register.address: register(self) for register in self.__regs__}
        self._registers_by_name: dict[RegisterName, Register] = {
            register.name: register for register in self.registers.values()
        }

        self.fieldmap = SenxorFieldsManager(self)

    def __iter__(self) -> Iterator[Register]:
        return iter(self.registers.values())

    def __getitem__(self, key: RegisterName | RegisterAddress) -> Register:
        return self.get_reg(key)

    def __contains__(self, key: str | int) -> bool:
        return key in self.registers or key in self._registers_by_name

    @property
    def cache(self) -> dict[int, int | None]:
        return {addr: reg._value for addr, reg in self.registers.items()}

    def refresh_all(self) -> None:
        """Refresh the cache of all registers and fields."""
        for reg in self.registers.values():
            reg.read()

    def get_reg(self, name_or_addr: RegisterName | RegisterAddress, /) -> Register:
        """Get a register instance by name or address."""
        if isinstance(name_or_addr, str):
            return self._registers_by_name[name_or_addr]
        elif isinstance(name_or_addr, int):
            return self.registers[name_or_addr]
        else:
            raise TypeError(f"Argument must be a RegisterName or an integer address, got {type(name_or_addr)}")

    def read_reg(self, addr: int) -> int:
        """Read a register value from the senxor."""
        self._check_valid_addr(addr)
        self._warn_unknown_reg(addr, "read")
        try:
            value = self.interface.read_reg(addr)
        except Exception as e:
            self._log.exception("read_reg_failed", op="read", addr=addr, error=e)
            raise e
        else:
            self._update_reg_value(addr, value)
            updated_fields = self.fieldmap._update_field_values({addr: value})
            self._log.info("read_reg_success", op="read", addr=addr, value=value, updated_fields=updated_fields)
            return value

    def write_reg(self, addr: int, value: int) -> None:
        """Write a value to a register."""
        self._check_valid_addr(addr)
        self._check_reg_writable(addr)
        self._warn_unknown_reg(addr, "write")
        try:
            self.interface.write_reg(addr, value)
        except Exception as e:
            self._log.exception("write_reg_failed", op="write", addr=addr, error=e)
            raise e
        else:
            self._update_reg_value(addr, value)
            updated_fields = self.fieldmap._update_field_values({addr: value})
            self._log.info(
                "write_reg_success",
                op="write",
                addr=addr,
                value=value,
                updated_fields=updated_fields,
            )
            self.fieldmap._warn_disabled_fields(updated_fields)

    def read_regs(self, addrs: list[int]) -> dict[int, int]:
        """Read the values from multiple registers at once."""
        for addr in addrs:
            self._check_valid_addr(addr)
            self._warn_unknown_reg(addr, "read_regs")
        try:
            values = self.interface.read_regs(addrs)
        except Exception as e:
            self._log.exception("read_regs_failed", op="read", addrs=addrs, error=e)
            raise e
        else:
            for addr, value in values.items():
                self._update_reg_value(addr, value)
            fields_updated = self.fieldmap._update_field_values(values)
            self._log.info("read_regs_success", op="read", values=values, fields_updated=fields_updated)
            return values

    def write_regs(self, regs: dict[int, int]) -> None:
        """Write the values to multiple registers at once."""
        raise NotImplementedError

    def _update_reg_value(self, addr: int, value: int):
        reg = self.registers.get(addr)
        if reg:
            reg._update_value(value)

    def _check_valid_addr(self, addr: int):
        if not isinstance(addr, int):
            raise TypeError(f"Register address must be an integer, got {type(addr)}")
        if addr < 0 or addr > 0xFF:
            raise ValueError(f"Register address must be in [0, 0xFF], got {addr}")

    def _check_reg_writable(self, addr: int):
        reg = self.registers.get(addr)
        if reg and not reg.writable:
            self._log.critical("write_protection_violation", addr=addr, name=reg.name)
            raise AttributeError(f"Register {reg.name} is read-only")

    def _warn_unknown_reg(self, addr: int, op: str):
        if addr not in Registers.__addrs__:
            self._log.warning("access_unknown_reg", op=op, addr=addr)
            return True
        return False


class SenxorFieldsManager(Fields):
    """The field system for the senxor.

    Attributes
    ----------
    regmap : SenxorRegistersManager
        The register system for the senxor.
    fields : dict[FieldName, Field]
        The dictionary of field instances by name.
    cache : dict[FieldName, int | None]
        The cache of the fields values.
    cache_display : dict[FieldName, str | int | float | None]
        The cache of the fields display values.

    Examples
    --------
    1. Iterate over the fields:
    >>> fieldmap = SenxorFieldsManager(regmap)
    >>> for field in fieldmap:
    ...     print(field.name, field.address)

    2. Use subscript notation to get a field instance:
    >>> fieldmap["MCU_TYPE"]

    3. Check if a field exists:
    >>> "MCU_TYPE" in fieldmap

    4. Use the cache to get the cached field value:
    >>> fieldmap.cache
    {SENXOR_TYPE: 1, MODULE_TYPE: 19, ...}

    5. Use the cache_display to get the cached field display value:
    >>> fieldmap.cache_display
    {SENXOR_TYPE: "MI0801", MODULE_TYPE: "MI0802M5S", ...}

    """

    def __init__(self, regmap: SenxorRegistersManager):
        self._log = regmap._log
        self.regmap: SenxorRegistersManager = regmap
        self.fields: dict[str, Field] = {field.name: field(self) for field in self.__fields__}

    def __iter__(self) -> Iterator[Field]:
        return iter(self.fields.values())

    def __getitem__(self, key: FieldName) -> Field:
        return self.get_field(key)

    def __contains__(self, key: str) -> bool:
        return key in self.fields

    @property
    def cache(self) -> dict[FieldName, int | None]:
        return {field.name: field._value for field in self.fields.values()}  # type: ignore[reportReturnType]

    @property
    def cache_display(self) -> dict[FieldName, str | int | float | None]:
        return {
            field.name: None if field._value is None else field.get_display(field._value)
            for field in self.fields.values()
        }  # type: ignore[reportReturnType]

    def get_field(self, name: FieldName) -> Field:
        """Get a field instance by name."""
        return self.fields[name]

    def get_fields_by_addr(self, addr: RegisterAddress) -> list[Field]:
        """Get the fields by register address."""
        names = self.__reg2fields__[addr]
        return [self.fields[name] for name in names]

    def read_field(self, name: FieldName) -> int:
        """Read a field value from the senxor."""
        field = self.get_field(name)
        reg = self.regmap.get_reg(field.address)
        reg_value = reg.read()
        field_value = self._decode_field_value(reg_value, field.bits_range)
        field._update_value(field_value)
        return field_value

    def set_field(self, name: FieldName, value: int, *, force: bool = False) -> None:
        """Set a field value on the senxor."""
        field = self.get_field(name)
        self._check_field_enabled(field, force)
        self._check_field_writable(field)
        self._check_field_value_range(field, value)
        self._validate_field_value(field, value)
        reg = self.regmap.get_reg(field.address)

        reg_value = reg.get()
        new_reg_value = self._encode_field_value(reg_value, value, field.bits_range)
        self.regmap.write_reg(reg.address, new_reg_value)
        field._update_value(value)
        self._log.info("set_field_success", name=field.name, value=value)

    def _update_field_values(self, regs: dict[int, int]) -> dict[str, int]:
        updated_fields: dict[str, int] = {}
        for addr, reg_value in regs.items():
            if addr not in self.regmap.registers:
                continue
            fields = self.get_fields_by_addr(cast("RegisterAddress", addr))
            for field in fields:
                field_value = self._decode_field_value(reg_value, field.bits_range)
                if field_value != field._value:
                    updated_fields[field.name] = field_value
                    field._update_value(field_value)

        return updated_fields

    def _warn_disabled_fields(self, fields: dict[str, int]) -> None:
        for name, value in fields.items():
            field = self.fields[name]
            if not field.enabled:
                self._log.warning(
                    "set_disabled_field",
                    name=field.name,
                    value=value,
                    reason=field.disabled_reason,
                )

    def _validate_field_value(self, field: Field, value: int) -> None:
        try:
            field.validate_value(value)
        except ValueError as e:
            raise ValueError(f"Invalid field value for {field.name}: {value}, {e}") from None

    def _check_field_value_range(self, field: Field, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError(f"Field value must be an integer, got {type(value)}")
        max_value = field._max_value
        if value < 0 or value > max_value:
            raise ValueError(f"Invalid field value for {field.name}: {value}, expected range: [0, {max_value}]")

    def _check_field_enabled(self, field: Field, force: bool = False) -> None:
        if field.enabled or force:
            return
        self._log.critical("field_disabled_violation", name=field.name, reason=field.disabled_reason)
        raise AttributeError(f"Field {field.name} is disabled, reason: {field.disabled_reason}")

    def _check_field_writable(self, field: Field) -> None:
        if not field.writable:
            self._log.critical("field_read_only_violation", name=field.name)
            raise AttributeError(f"Field {field.name} is read-only")

    @staticmethod
    def _decode_field_value(reg_value: int, bits_range: tuple[int, int]) -> int:
        start, end = bits_range
        length = end - start
        mask = (1 << length) - 1
        result = (reg_value >> start) & mask
        return result

    @staticmethod
    def _encode_field_value(reg_value: int, field_value: int, bits_range: tuple[int, int]) -> int:
        start, end = bits_range
        length = end - start
        max_value = (1 << length) - 1
        mask = max_value << start
        result = (reg_value & ~mask) | ((field_value & max_value) << start)
        return result
