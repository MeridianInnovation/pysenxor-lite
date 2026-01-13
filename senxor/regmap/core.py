# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING

from senxor.log import get_logger
from senxor.regmap.registers import Registers

if TYPE_CHECKING:
    from senxor.interface.protocol import IDevice, ISenxorInterface
    from senxor.regmap.base import Register
    from senxor.regmap.types import RegisterName


class SenxorRegistersManager(Registers):
    """The register system for the senxor.

    Attributes
    ----------
    interface : ISenxorInterface[IDevice]
        The interface of the senxor.
    registers : dict[int, Register]
        The dictionary of registers instance by address.

    Notes
    -----
    Each register operation should be performed through this class to ensure logging,
    cache updating and error handling.

    """

    def __init__(self, interface: ISenxorInterface[IDevice]):
        self.interface: ISenxorInterface[IDevice] = interface
        self._log = get_logger(name=self.interface.device.name)
        self.registers: dict[int, Register] = {register.address: register(self) for register in self.__regs__}
        self._registers_by_name: dict[RegisterName, Register] = {
            register.name: register for register in self.registers.values()
        }

    def get_reg(self, name_or_addr: RegisterName | int, /) -> Register:
        if isinstance(name_or_addr, str):
            return self._registers_by_name[name_or_addr]
        elif isinstance(name_or_addr, int):
            return self.registers[name_or_addr]
        else:
            raise TypeError(f"Argument must be a RegisterName or an integer address, got {type(name_or_addr)}")

    def read_reg(self, addr: int) -> int:
        """The unified method to read a register value from the senxor."""
        self._check_valid_addr(addr)
        self._warn_unknown_reg(addr, "read")
        try:
            value = self.interface.read_reg(addr)
        except Exception as e:
            self._log.exception("read_reg_failed", op="read", addr=addr, error=e)
            raise e
        else:
            self._update_reg_value(addr, value)
            self._log.info("read_reg_success", addr=addr, value=value)
            return value

    def write_reg(self, addr: int, value: int) -> None:
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
            self._log.info("write_reg_success", addr=addr, value=value)

    def read_regs(self, addrs: list[int]) -> dict[int, int]:
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
            self._log.info("read_regs_success", values=values, count=len(values))
            return values

    def write_regs(self, regs: dict[int, int]) -> None:
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
