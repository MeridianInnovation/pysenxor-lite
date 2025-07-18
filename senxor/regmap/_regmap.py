from threading import Lock
from typing import TYPE_CHECKING

from structlog import get_logger

from senxor.regmap._fields import Fields
from senxor.regmap._regs import Registers

if TYPE_CHECKING:
    from senxor._senxor import Senxor

logger = get_logger("senxor.regmap")


class _RegMap:
    """The private class for the regmap of the senxor."""

    def __init__(self, senxor: "Senxor"):
        self.senxor = senxor

        self._log = logger.bind(address=self.address)

        self._regs_cache: dict[int, int] = {}
        self._fields_cache: dict[str, int] = {}

        self.regs = Registers(self)
        self.fields = Fields(self)

        # This lock is different from the lock in the senxor.interface.
        # It is used to protect the cache of the regmap.
        # ensures that the cache is consistent and that the cache is updated correctly.
        self._cache_lock = Lock()

    @property
    def address(self):
        return self.senxor.address

    @property
    def interface(self):
        return self.senxor.interface

    def read_reg(self, addr: int) -> int:
        self._validate_addr(addr)
        with self._cache_lock:
            value = self.interface.read_reg(addr)
            self._regs_cache[addr] = value
            self._log.info("register read", addr=addr, value=value)
            self._fresh_fields_cache_by_read({addr: value})
            return value

    def write_reg(self, addr: int, value: int):
        self._validate_addr(addr)
        with self._cache_lock:
            self.interface.write_reg(addr, value)
            self._log.info("register write", addr=addr, value=value)
            self._regs_cache[addr] = value
            self._fresh_fields_cache_by_write({addr: value})

    def read_regs(self, addrs: list[int]) -> dict[int, int]:
        for addr in addrs:
            self._validate_addr(addr)
        with self._cache_lock:
            values_dict = self.interface.read_regs(addrs)
            self._regs_cache.update(values_dict)
            self._log.info("registers read", addrs=addrs, values=values_dict)
            self._fresh_fields_cache_by_read(values_dict)
            return values_dict

    def write_regs(self, updates: dict[int, int]):
        for addr in updates:
            self._validate_addr(addr)
        with self._cache_lock:
            success = {}
            try:
                for addr, value in updates.items():
                    self.interface.write_reg(addr, value)
                    success[addr] = value
                    self._regs_cache[addr] = value
            finally:
                self._log.info("registers write", updates=success)
                self._fresh_fields_cache_by_write(success)

    def read_all(self):
        self.regs.read_all()

    def _get_regs(self, addrs: list[int]) -> dict[int, int]:
        """The private API for fields to get register values."""
        # No cache lock here!
        return self.regs.get_regs(addrs)

    def _fresh_fields_cache_by_read(self, regs_values: dict[int, int]):
        """Refresh the cache by reading the registers."""
        f_need_fresh = set(fname for reg in regs_values for fname in self.fields.__reg2fname_map__[reg])

        updates = {}

        for fname in f_need_fresh:
            field = self.fields[fname]
            try:
                value = field._parse_field_value(self._regs_cache)
            except KeyError:
                # The field requires more than one register, but the register is not in the cache.
                # This means that the field is not yet initialized.
                value = None
            if self._fields_cache.get(fname, None) != value:
                updates[fname] = value
        if updates:
            self._fields_cache.update(updates)
            self._log.info("refresh fields by reg-read", fields=updates)
        else:
            self._log.debug("no fields changed by reg-read")

    def _fresh_fields_cache_by_write(self, regs_updates: dict[int, int]):
        """Refresh the cache by writing the registers."""
        f_need_fresh = set(fname for reg in regs_updates for fname in self.fields.__reg2fname_map__[reg])
        updates = {}
        for fname in f_need_fresh:
            field = self.fields[fname]
            try:
                value = field._parse_field_value(self._regs_cache)
            except KeyError:
                value = None
            if self._fields_cache.get(fname, None) != value:
                updates[fname] = value
        if updates:
            self._fields_cache.update(updates)
            self._log.info("refresh fields by reg-write", fields=updates)
        else:
            self._log.debug("no fields changed by reg-write")

    @staticmethod
    def _validate_addr(addr: int):
        if not isinstance(addr, int):
            raise TypeError(f"Register address must be an integer, got {type(addr)}")
        if addr < 0 or addr > 0xFF:
            raise ValueError(f"Register address must be in [0, 0xFF], got {addr}")

    def __repr__(self) -> str:
        return f"RegMap(senxor={self.senxor})"
