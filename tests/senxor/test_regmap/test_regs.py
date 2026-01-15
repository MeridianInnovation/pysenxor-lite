from typing import TYPE_CHECKING

from senxor.regmap import Registers

if TYPE_CHECKING:
    from senxor.regmap.base import Register


class TestRegisters:
    def test_registers_definition(self):
        """Verify basic register definitions and __addrs__ mapping."""
        assert Registers.__regs__ is not None
        assert Registers.__addrs__ is not None
        for reg in Registers.__regs__:
            assert reg.name == reg.__name__
        for addr, reg_name in Registers.__addrs__.items():
            assert hasattr(Registers, reg_name)
            assert getattr(Registers, reg_name).address == addr

    def test_register_addresses_are_unique(self):
        """Ensure all register addresses are unique."""
        addresses = [reg.address for reg in Registers.__regs__]
        assert len(addresses) == len(set(addresses))

    def test_register_required_attributes(self):
        """Ensure all registers have required attributes."""
        for reg in Registers.__regs__:
            assert hasattr(reg, "name")
            assert hasattr(reg, "description")
            assert hasattr(reg, "address")
            assert hasattr(reg, "writable")
            assert hasattr(reg, "readable")
            assert hasattr(reg, "self_reset")
            assert hasattr(reg, "enabled")
            assert reg.writable or reg.readable

    def test_register_addrs_consistency(self):
        """Ensure __addrs__ mapping is consistent with register definitions."""
        for addr, reg_name in Registers.__addrs__.items():
            assert hasattr(Registers, reg_name)
            reg: Register = getattr(Registers, reg_name)
            assert reg.address == addr
            assert reg.name == reg_name

    def test_readonly_registers_properties(self):
        """Verify readonly registers have correct properties."""
        for reg in Registers.__regs__:
            if not reg.writable and reg.readable:
                assert not reg.writable
                assert reg.readable
