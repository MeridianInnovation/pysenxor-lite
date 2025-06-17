"""Tests for the regs module."""

import pytest

from senxor.regs import REGS, Register


@pytest.fixture
def sample_regs():
    """Sample registers for testing."""
    return {
        "readable": REGS.STATUS,  # Read-only register
        "writable": REGS.MCU_RESET,  # Write-only register
        "rw": REGS.HOST_XFER_CTRL,  # Read-write register
        "multi_byte_low": REGS.COMPPAR_P0_0,  # Low byte of a multi-byte register
        "multi_byte_high": REGS.COMPPAR_P0_1,  # High byte of a multi-byte register
    }


class TestRegister:
    """Test the Register dataclass."""

    def test_register_creation(self):
        """Test Register creation and properties."""
        reg = Register(0x00, True, False, "Test Register")
        assert reg.address == 0x00
        assert reg.readable is True
        assert reg.writable is False
        assert reg.desc == "Test Register"

    def test_register_string_representation(self):
        """Test Register string representation."""
        reg = Register(0x00, True, True, "Test Register")
        assert str(reg) == "0x00 (RW) Test Register"
        reg = Register(0x01, True, False, "Read Only")
        assert str(reg) == "0x01 (R) Read Only"
        reg = Register(0x02, False, True, "Write Only")
        assert str(reg) == "0x02 (W) Write Only"


class TestREGS:
    """Test the REGS enum."""

    def test_reg_properties(self, sample_regs):
        """Test basic properties of registers."""
        # Read-only register
        assert sample_regs["readable"].readable is True
        assert sample_regs["readable"].writable is False

        # Write-only register
        assert sample_regs["writable"].readable is False
        assert sample_regs["writable"].writable is True

        # Read-write register
        assert sample_regs["rw"].readable is True
        assert sample_regs["rw"].writable is True

    def test_reg_address_format(self):
        """Test register address formatting."""
        for reg in REGS:
            if not reg.name.startswith("REG_0x"):
                assert hasattr(REGS, f"REG_0x{reg.address:02X}")
                assert getattr(REGS, f"REG_0x{reg.address:02X}") == reg

    def test_from_addr(self):
        """Test getting register by address."""
        # Valid addresses
        assert REGS.from_addr(0x00) == REGS.MCU_RESET
        assert REGS.from_addr(0xB6) == REGS.STATUS

        # Invalid address
        with pytest.raises(ValueError):
            REGS.from_addr(0xFF)

    def test_list_all_names(self):
        """Test listing all register names."""
        names = REGS.list_all_names()
        assert "MCU_RESET" in names
        assert "STATUS" in names
        assert not any(name.startswith("REG_0x") for name in names)

    def test_list_all_addrs(self):
        """Test listing all register addresses."""
        addresses = REGS.list_all_addrs()
        assert 0x00 in addresses  # MCU_RESET
        assert 0xB6 in addresses  # STATUS
        assert len(addresses) == len(REGS.list_all_names())

    def test_list_readable_regs(self):
        """Test listing readable registers."""
        readable = REGS.list_readable_regs()
        assert REGS.STATUS in readable
        assert REGS.MCU_RESET not in readable
        assert all(reg.readable for reg in readable)

    def test_list_writable_regs(self):
        """Test listing writable registers."""
        writable = REGS.list_writable_regs()
        assert REGS.MCU_RESET in writable
        assert REGS.STATUS not in writable
        assert all(reg.writable for reg in writable)

    def test_register_uniqueness(self):
        """Test that all registers have unique addresses."""
        addresses = [reg.address for reg in REGS if not reg.name.startswith("REG_0x")]
        assert len(addresses) == len(set(addresses)), "Duplicate register addresses found"

    def test_register_naming_convention(self):
        """Test register naming conventions."""
        for reg in REGS:
            if not reg.name.startswith("REG_0x"):
                # Check that register names are uppercase
                assert reg.name.isupper() or "_" in reg.name
                # Check that REG_0x aliases exist and are correct
                addr_name = f"REG_0x{reg.address:02X}"
                assert hasattr(REGS, addr_name)
                assert getattr(REGS, addr_name) == reg

    def test_all_registers_have_address_alias(self):
        """Test that all registers (except address aliases) have corresponding address aliases."""
        non_alias_regs = [reg for reg in REGS if not reg.name.startswith("REG_0x")]
        for reg in non_alias_regs:
            alias_name = f"REG_0x{reg.address:02X}"
            assert hasattr(REGS, alias_name), f"Register {reg.name} missing address alias {alias_name}"
            alias_reg = getattr(REGS, alias_name)
            assert alias_reg == reg, f"Register {reg.name} has incorrect address alias mapping"
            assert alias_reg.address == reg.address, f"Register {reg.name} address mismatch with alias"

    def test_all_address_aliases_have_base_register(self):
        """Test that all address aliases correspond to a valid base register."""
        alias_regs = [reg for reg in REGS if reg.name.startswith("REG_0x")]
        for alias_reg in alias_regs:
            # Find the base register with the same address
            base_regs = [reg for reg in REGS if not reg.name.startswith("REG_0x") and reg.address == alias_reg.address]
            assert len(base_regs) == 1, f"Address alias {alias_reg.name} has no unique base register"
            base_reg = base_regs[0]
            assert alias_reg == base_reg, f"Address alias {alias_reg.name} does not match its base register"

    def test_address_alias_properties(self):
        """Test that address aliases maintain the same properties as their base registers."""
        for reg in REGS:
            if not reg.name.startswith("REG_0x"):
                alias_name = f"REG_0x{reg.address:02X}"
                alias_reg = getattr(REGS, alias_name)
                assert (
                    alias_reg.value.readable == reg.value.readable
                ), f"Register {reg.name} readable property mismatch with alias"
                assert (
                    alias_reg.value.writable == reg.value.writable
                ), f"Register {reg.name} writable property mismatch with alias"
                assert alias_reg.value.desc == reg.value.desc, f"Register {reg.name} description mismatch with alias"
