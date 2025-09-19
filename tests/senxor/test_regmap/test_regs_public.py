"""Tests for Registers public API and invariants.

This module tests the public interface of the Registers class,
including static integrity checks, properties, public methods, and dict-like access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from senxor.regmap._reg import Register
from senxor.regmap._regs import Registers

from .fixtures import EnhancedMockInterface, TestDataGenerator

if TYPE_CHECKING:
    from senxor.regmap._regmap import _RegMap


class TestStaticIntegrity:
    """Test static integrity of Registers class metadata."""

    def test_reg_defs_uniqueness(self) -> None:
        """Test that register definitions have unique names."""
        reg_defs = Registers.__reg_defs__
        names = list(reg_defs.keys())

        # No duplicate names
        assert len(names) == len(set(names))

        # All names are strings
        assert all(isinstance(name, str) for name in names)

        # All names are non-empty
        assert all(len(name) > 0 for name in names)

    def test_addr_name_mapping_consistency(self) -> None:
        """Test that address-name mappings are consistent."""
        reg_defs = Registers.__reg_defs__
        addr2name = Registers.__addr2name__
        name2addr = Registers.__name2addr__

        # All addresses in reg_defs should be in addr2name
        for name, reg_def in reg_defs.items():
            assert reg_def.addr in addr2name
            assert addr2name[reg_def.addr] == name

        # All names in reg_defs should be in name2addr
        for name, reg_def in reg_defs.items():
            assert name in name2addr
            assert name2addr[name] == reg_def.addr

        # Bidirectional mapping consistency
        for addr, name in addr2name.items():
            assert name2addr[name] == addr

        for name, addr in name2addr.items():
            assert addr2name[addr] == name

    def test_list_alignment_verification(self) -> None:
        """Test that all lists are aligned with main definitions."""
        reg_defs = Registers.__reg_defs__
        name_list = Registers.__name_list__
        addr_list = Registers.__addr_list__
        readable_list = Registers.__readable_list__
        writable_list = Registers.__writable_list__
        auto_reset_list = Registers.__auto_reset_list__

        # Name list should match reg_defs keys
        assert set(name_list) == set(reg_defs.keys())

        # Address list should match reg_defs addresses
        expected_addrs = {reg_def.addr for reg_def in reg_defs.values()}
        assert set(addr_list) == expected_addrs

        # Readable list should match readable registers
        expected_readable = {name for name, reg_def in reg_defs.items() if reg_def.readable}
        assert set(readable_list) == expected_readable

        # Writable list should match writable registers
        expected_writable = {name for name, reg_def in reg_defs.items() if reg_def.writable}
        assert set(writable_list) == expected_writable

        # Auto-reset list should match auto-reset registers
        expected_auto_reset = {name for name, reg_def in reg_defs.items() if reg_def.auto_reset}
        assert set(auto_reset_list) == expected_auto_reset

    def test_no_duplicate_addresses(self) -> None:
        """Test that no two registers have the same address."""
        reg_defs = Registers.__reg_defs__
        addresses = [reg_def.addr for reg_def in reg_defs.values()]

        # No duplicate addresses
        assert len(addresses) == len(set(addresses))

        # All addresses are integers
        assert all(isinstance(addr, int) for addr in addresses)

        # All addresses are in valid range (0-255 for 8-bit)
        assert all(0 <= addr <= 255 for addr in addresses)

    def test_class_variables_immutability(self) -> None:
        """Test that class variables are properly structured."""
        # Test that class variables exist and are of correct type
        assert hasattr(Registers, "__reg_defs__")
        assert hasattr(Registers, "__addr2name__")
        assert hasattr(Registers, "__name2addr__")
        assert hasattr(Registers, "__name_list__")
        assert hasattr(Registers, "__addr_list__")
        assert hasattr(Registers, "__readable_list__")
        assert hasattr(Registers, "__writable_list__")
        assert hasattr(Registers, "__auto_reset_list__")

        # Test types
        assert isinstance(Registers.__reg_defs__, dict)
        assert isinstance(Registers.__addr2name__, dict)
        assert isinstance(Registers.__name2addr__, dict)
        assert isinstance(Registers.__name_list__, list)
        assert isinstance(Registers.__addr_list__, list)
        assert isinstance(Registers.__readable_list__, list)
        assert isinstance(Registers.__writable_list__, list)
        assert isinstance(Registers.__auto_reset_list__, list)


class TestPublicProperties:
    """Test public properties of Registers class."""

    def test_writable_regs_property(self, regmap: _RegMap) -> None:
        """Test writable_regs property."""
        registers = regmap.regs

        writable_regs = registers.writable_regs
        expected_writable = Registers.__writable_list__

        assert writable_regs == expected_writable
        assert isinstance(writable_regs, list)

        # Should be a copy, not the same object
        assert writable_regs is not expected_writable

    def test_readable_regs_property(self, regmap: _RegMap) -> None:
        """Test readable_regs property."""
        registers = regmap.regs

        readable_regs = registers.readable_regs
        expected_readable = Registers.__readable_list__

        assert readable_regs == expected_readable
        assert isinstance(readable_regs, list)

        # Should be a copy, not the same object
        assert readable_regs is not expected_readable

    def test_status_shallow_copy(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that status property returns a shallow copy."""
        registers = regmap.regs

        # Add some data to cache
        test_data = {0xB4: 100, 0xB7: 50}
        for addr, value in test_data.items():
            registers._regs_cache[addr] = value

        # Get status
        status = registers.status

        # Should match cache content
        assert status == test_data

        # Should be a copy, not the same object
        assert status is not registers._regs_cache

        # Modifying status should not affect cache
        status[0xCA] = 80
        assert 0xCA not in registers._regs_cache

    def test_regs_property_access(self, regmap: _RegMap) -> None:
        """Test regs property access."""
        registers = regmap.regs

        regs_dict = registers.regs

        # Should be a dictionary
        assert isinstance(regs_dict, dict)

        # Should contain Register instances
        for name, reg_instance in regs_dict.items():
            assert isinstance(reg_instance, Register)
            assert reg_instance.name == name

        # Should match expected register names
        expected_names = set(Registers.__name_list__)
        assert set(regs_dict.keys()) == expected_names

    def test_property_consistency(self, regmap: _RegMap) -> None:
        """Test that properties are consistent with class metadata."""
        registers = regmap.regs

        # Properties should match class variables
        assert registers.writable_regs == Registers.__writable_list__
        assert registers.readable_regs == Registers.__readable_list__

        # Regs property should contain all defined registers
        assert set(registers.regs.keys()) == set(Registers.__name_list__)


class TestPublicMethods:
    """Test public methods of Registers class."""

    def test_get_addr_valid_inputs(self, regmap: _RegMap) -> None:
        """Test get_addr with valid inputs."""
        registers = regmap.regs

        # Test with string name
        addr = registers.get_addr("EMISSIVITY")
        expected_addr = Registers.__name2addr__["EMISSIVITY"]
        assert addr == expected_addr

        # Test with integer address
        addr = registers.get_addr(0xB4)
        assert addr == 0xB4

        # Test with Register instance
        reg_instance = registers.regs["FRAME_RATE"]
        addr = registers.get_addr(reg_instance)
        expected_addr = Registers.__name2addr__["FRAME_RATE"]
        assert addr == expected_addr

    def test_get_addr_invalid_inputs(self, regmap: _RegMap) -> None:
        """Test get_addr with invalid inputs."""
        registers = regmap.regs

        # Test with invalid string name
        with pytest.raises(KeyError):
            registers.get_addr("INVALID_REGISTER")

        # Test with invalid type
        with pytest.raises((KeyError, TypeError)):
            registers.get_addr(1.5)  # type: ignore

    def test_read_all_comprehensive(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test read_all method comprehensively."""
        registers = regmap.regs

        # Setup test data for all addresses
        test_data = {}
        for addr in Registers.__addr_list__:
            test_data[addr] = addr % 256
            mock_interface.set_register_value(addr, test_data[addr])

        # Call read_all
        result = registers.read_all()

        # Should return the values
        assert result == test_data

        # Should update cache
        for addr, value in test_data.items():
            assert registers._regs_cache[addr] == value

    def test_read_all_hardware_interaction(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_all interacts with hardware correctly."""
        registers = regmap.regs

        # Setup some test data
        test_addrs = Registers.__addr_list__[:5]
        for addr in test_addrs:
            mock_interface.set_register_value(addr, addr % 256)

        # Clear call history
        mock_interface.reset_call_history()

        # Call read_all
        registers.read_all()

        # Should have made hardware calls for all addresses
        for addr in Registers.__addr_list__:
            assert addr in mock_interface.read_calls

    def test_read_all_cache_population(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_all populates cache correctly."""
        registers = regmap.regs

        # Ensure cache is initially empty
        assert len(registers._regs_cache) == 0

        # Setup test data
        test_data = {}
        for addr in Registers.__addr_list__:
            test_data[addr] = (addr * 2) % 256
            mock_interface.set_register_value(addr, test_data[addr])

        # Call read_all
        registers.read_all()

        # Cache should be populated
        assert len(registers._regs_cache) == len(Registers.__addr_list__)
        for addr, value in test_data.items():
            assert registers._regs_cache[addr] == value


class TestDictLikeInterface:
    """Test dict-like interface of Registers class."""

    def test_getitem_by_name(self, regmap: _RegMap) -> None:
        """Test __getitem__ access by register name."""
        registers = regmap.regs

        # Test with valid name
        reg = registers["EMISSIVITY"]
        assert isinstance(reg, Register)
        assert reg.name == "EMISSIVITY"

        # Test with another valid name
        reg = registers["FRAME_RATE"]
        assert isinstance(reg, Register)
        assert reg.name == "FRAME_RATE"

    def test_getitem_by_address(self, regmap: _RegMap) -> None:
        """Test __getitem__ access by register address."""
        registers = regmap.regs

        # Test with valid address
        addr = 0xCA  # EMISSIVITY
        reg = registers[addr]
        assert isinstance(reg, Register)
        assert reg.addr == addr

        # Test with another valid address
        addr = 0xB4  # FRAME_RATE
        reg = registers[addr]
        assert isinstance(reg, Register)
        assert reg.addr == addr

    def test_getitem_by_register_instance_raises(self, regmap: _RegMap) -> None:
        """Test __getitem__ with Register instance raises KeyError."""
        registers = regmap.regs

        reg_instance = registers["EMISSIVITY"]

        with pytest.raises(KeyError):
            _ = registers[reg_instance]  # type: ignore

    def test_getitem_invalid_key(self, regmap: _RegMap) -> None:
        """Test __getitem__ with invalid keys."""
        registers = regmap.regs

        # Test with invalid name
        with pytest.raises(KeyError):
            registers["INVALID_REGISTER"]

        # Test with invalid address
        with pytest.raises(KeyError):
            registers[0x999]

        # Test with invalid type
        with pytest.raises(KeyError):
            registers[1.5]  # type: ignore

    def test_setitem_prevention(self, regmap: _RegMap) -> None:
        """Test that __setitem__ is prevented."""
        registers = regmap.regs

        # Should raise AttributeError
        with pytest.raises(AttributeError):
            registers["EMISSIVITY"] = 100  # type: ignore

        with pytest.raises(AttributeError):
            registers[0xCA] = 100  # type: ignore

    def test_iteration_support(self, regmap: _RegMap) -> None:
        """Test iteration over registers."""
        registers = regmap.regs

        # Test iteration
        reg_instances = list(registers)

        # Should contain Register instances
        assert all(isinstance(reg, Register) for reg in reg_instances)

        # Should contain all expected registers
        expected_names = set(Registers.__name_list__)
        actual_names = {reg.name for reg in reg_instances}
        assert actual_names == expected_names

        # Should be able to iterate multiple times
        reg_instances2 = list(registers)
        assert len(reg_instances2) == len(reg_instances)


class TestStringRepresentation:
    """Test string representation of Registers class."""

    def test_repr_format(self, regmap: _RegMap) -> None:
        """Test __repr__ format."""
        registers = regmap.regs

        repr_str = repr(registers)

        # Should contain class name
        assert "Registers" in repr_str

        # Should contain regmap reference
        assert "regmap" in repr_str

        # Should be a valid string
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

    def test_repr_consistency(self, regmap: _RegMap) -> None:
        """Test __repr__ consistency."""
        registers = regmap.regs

        # Multiple calls should return same result
        repr1 = repr(registers)
        repr2 = repr(registers)
        assert repr1 == repr2

        # Should be deterministic
        assert isinstance(repr1, str)


class TestRegisterInstanceAccess:
    """Test access to individual register instances."""

    def test_register_instance_properties(self, regmap: _RegMap) -> None:
        """Test properties of register instances."""
        registers = regmap.regs

        # Get a register instance
        emissivity_reg = registers.EMISSIVITY

        # Test properties
        assert emissivity_reg.name == "EMISSIVITY"
        assert emissivity_reg.addr == Registers.__name2addr__["EMISSIVITY"]
        assert isinstance(emissivity_reg.readable, bool)
        assert isinstance(emissivity_reg.writable, bool)
        assert isinstance(emissivity_reg.auto_reset, bool)
        assert isinstance(emissivity_reg.desc, str)

    def test_register_instance_consistency(self, regmap: _RegMap) -> None:
        """Test that register instances are consistent."""
        registers = regmap.regs

        # Multiple access should return same instance
        reg1 = registers.EMISSIVITY
        reg2 = registers.EMISSIVITY
        assert reg1 is reg2

        # Dict access should return same instance
        reg3 = registers["EMISSIVITY"]
        assert reg1 is reg3

    def test_register_instance_methods(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test methods of register instances."""
        registers = regmap.regs

        # Get a writable register
        frame_rate_reg = registers.FRAME_RATE

        # Test read method
        test_value = 100
        mock_interface.set_register_value(frame_rate_reg.addr, test_value)
        value = frame_rate_reg.read()
        assert value == test_value

        # Test get method
        value = frame_rate_reg.get()
        assert value == test_value

        # Test set method
        new_value = 150
        frame_rate_reg.set(new_value)
        assert registers._regs_cache[frame_rate_reg.addr] == new_value

        # Test value property
        assert frame_rate_reg.value == new_value


class TestErrorHandling:
    """Test error handling in public methods."""

    def test_invalid_register_access(self, regmap: _RegMap) -> None:
        """Test error handling for invalid register access."""
        registers = regmap.regs

        # Test invalid attribute access
        with pytest.raises(AttributeError):
            registers.INVALID_REGISTER  # type: ignore

    def test_read_only_register_protection(self, regmap: _RegMap) -> None:
        """Test that read-only registers are protected."""
        registers = regmap.regs

        # Get a read-only register
        status_reg = registers.STATUS

        # Should not be able to set value
        with pytest.raises(AttributeError):
            status_reg.set(100)

    def test_connection_error_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost."""
        registers = regmap.regs

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # read_all should raise error
        with pytest.raises(Exception):  # Should be SenxorNotConnectedError
            registers.read_all()

        # Individual register operations should also fail
        with pytest.raises(Exception):
            registers.FRAME_RATE.read()

        with pytest.raises(Exception):
            registers.FRAME_RATE.set(100)


class TestPerformanceCharacteristics:
    """Test performance characteristics of public methods."""

    def test_property_access_performance(self, regmap: _RegMap) -> None:
        """Test that property access is efficient."""
        registers = regmap.regs

        # Multiple property access should be fast
        for _ in range(100):
            _ = registers.writable_regs
            _ = registers.readable_regs
            _ = registers.status
            _ = registers.regs

        # Should not raise any exceptions
        assert True

    def test_register_instance_caching(self, regmap: _RegMap) -> None:
        """Test that register instances are properly cached."""
        registers = regmap.regs

        # Multiple access should return same instance (cached)
        instances = []
        for _ in range(10):
            instances.append(registers.EMISSIVITY)

        # All should be the same instance
        assert all(inst is instances[0] for inst in instances)

    def test_bulk_operations_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that bulk operations are efficient."""
        registers = regmap.regs

        # Setup test data
        test_data = TestDataGenerator.generate_register_values(count=20)
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # read_all should be efficient
        mock_interface.reset_call_history()
        registers.read_all()

        # Should have made calls for all addresses
        expected_calls = len(Registers.__addr_list__)
        actual_calls = len(mock_interface.read_calls)
        assert actual_calls == expected_calls
