"""Tests for boundary conditions in regmap modules.

This module tests boundary conditions including value limits, data type boundaries,
collection edge cases, and invalid input handling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .fixtures import EnhancedMockInterface, TestDataGenerator

if TYPE_CHECKING:
    from senxor.regmap._regmap import _RegMap


class TestValueBoundaries:
    """Test value boundary conditions."""

    def test_register_value_boundaries(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test register value boundaries."""
        test_addr = 0xCA

        # Test minimum valid value
        regmap.write_reg(test_addr, 0)
        assert regmap._regs_cache[test_addr] == 0

        # Test maximum valid value
        regmap.write_reg(test_addr, 255)
        assert regmap._regs_cache[test_addr] == 255

        # Test boundary values
        boundary_values = [0, 1, 127, 128, 254, 255]
        for value in boundary_values:
            regmap.write_reg(test_addr, value)
            assert regmap._regs_cache[test_addr] == value

        # Test invalid values
        invalid_values = [-1, 256, 300, 1000, -100]
        for value in invalid_values:
            with pytest.raises(ValueError):
                regmap.write_reg(test_addr, value)

    def test_address_boundaries(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test address boundary conditions."""
        # Test minimum valid address
        min_addr = min(regmap.regs.__addr_list__)
        mock_interface.set_register_value(min_addr, 100)
        value = regmap.read_reg(min_addr)
        assert value == 100

        # Test maximum valid address
        max_addr = max(regmap.regs.__addr_list__)
        mock_interface.set_register_value(max_addr, 150)
        value = regmap.read_reg(max_addr)
        assert value == 150

        # Test invalid addresses
        invalid_addrs = [-1, 0x1000, 0xFFFF, 0x999]
        for addr in invalid_addrs:
            with pytest.raises((KeyError, ValueError, TypeError)):
                regmap.read_reg(addr)

            with pytest.raises((KeyError, ValueError, TypeError)):
                regmap.write_reg(addr, 100)

    def test_bit_position_boundaries(self, regmap: _RegMap) -> None:
        """Test bit position boundaries in fields."""
        # This would test bit field boundaries
        # For now, test with SW_RESET field (bit field)

        # Test valid bit values
        valid_bit_values = [0, 1]
        for value in valid_bit_values:
            regmap.fields.set_field("SW_RESET", value)
            assert regmap._fields_cache["SW_RESET"] == value

        # Test invalid bit values
        invalid_bit_values = [-1, 2, 10, 255]
        for value in invalid_bit_values:
            with pytest.raises((ValueError, AttributeError)):
                regmap.fields.set_field("SW_RESET", value)


class TestDataTypeBoundaries:
    """Test data type boundary conditions."""

    def test_bool_boundaries(self, regmap: _RegMap) -> None:
        """Test boolean validator function boundaries."""
        from senxor.regmap._fields import _validator_bool

        bool_boundaries = {
            "valid": [0, 1],
            "invalid": [-1, 2, 3, 10, 255, 256],
        }

        # Test _validator_bool function directly
        # Valid boolean values (0, 1)
        for value in bool_boundaries["valid"]:
            assert _validator_bool(value, regmap.fields) is True

        # Invalid boolean values
        for value in bool_boundaries["invalid"]:
            assert _validator_bool(value, regmap.fields) is False

    def test_validator_uintx_comprehensive(self, regmap: _RegMap) -> None:
        """Test _validator_uintx function comprehensively for different bit widths."""
        from senxor.regmap._fields import _validator_uintx

        # Test different bit widths
        test_cases = [
            (1, 0, 1),  # 1-bit: 0-1
            (2, 0, 3),  # 2-bit: 0-3
            (3, 0, 7),  # 3-bit: 0-7
            (4, 0, 15),  # 4-bit: 0-15
            (5, 0, 31),  # 5-bit: 0-31
            (8, 0, 255),  # 8-bit: 0-255
        ]

        for bit_width, min_val, max_val in test_cases:
            # Test valid boundary values
            assert _validator_uintx(bit_width, min_val, regmap.fields) is True
            assert _validator_uintx(bit_width, max_val, regmap.fields) is True

            # Test invalid values
            assert _validator_uintx(bit_width, min_val - 1, regmap.fields) is False
            assert _validator_uintx(bit_width, max_val + 1, regmap.fields) is False

            # Test middle value
            mid_val = (min_val + max_val) // 2
            assert _validator_uintx(bit_width, mid_val, regmap.fields) is True


class TestCollectionBoundaries:
    """Test collection boundary conditions."""

    def test_empty_register_list(self, regmap: _RegMap) -> None:
        """Test operations with empty register lists."""
        # Test empty read
        result = regmap.read_regs([])
        assert result == {}

        # Test empty write
        regmap.write_regs({})
        # Should not raise any errors

    def test_empty_field_list(self, regmap: _RegMap) -> None:
        """Test operations with empty field lists."""
        # Test empty field read
        result = regmap.fields.get_fields([])
        assert result == {}

        # Test empty field write
        regmap.fields.set_fields({})
        # Should not raise any errors

    def test_single_item_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test operations with single items."""
        # Single register operations
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Single read
        result = regmap.read_regs([test_addr])
        assert result == {test_addr: test_value}

        # Single write
        regmap.write_regs({test_addr: 85})
        assert regmap._regs_cache[test_addr] == 85

        # Single field operations
        result = regmap.fields.get_fields(["EMISSIVITY"])
        assert "EMISSIVITY" in result

        regmap.fields.set_fields({"EMISSIVITY": 90})
        assert regmap._fields_cache["EMISSIVITY"] == 90

    def test_maximum_batch_size(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test operations with maximum batch sizes."""
        # Test with all available registers for reading
        all_addrs = regmap.regs.__addr_list__
        test_data = {addr: addr % 256 for addr in all_addrs}

        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Maximum batch read
        result = regmap.read_regs(all_addrs)
        assert len(result) == len(all_addrs)

        # Maximum batch write (exclude read-only registers)
        writable_data = {
            addr: value for addr, value in test_data.items() if addr not in TestDataGenerator.READ_ONLY_ADDRESSES
        }
        regmap.write_regs(writable_data)
        for addr, value in writable_data.items():
            assert regmap._regs_cache[addr] == value

    def test_duplicate_items_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test handling of duplicate items in collections."""
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Duplicate addresses in read
        result = regmap.read_regs([test_addr, test_addr, test_addr])
        assert result == {test_addr: test_value}

        # Duplicate fields in read
        result = regmap.fields.get_fields(["EMISSIVITY", "EMISSIVITY"])
        assert len(result) == 1
        assert "EMISSIVITY" in result


class TestEdgeCaseScenarios:
    """Test edge case scenarios."""

    def test_concurrent_read_write(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent read and write operations."""
        test_addr = 0xCA

        # Setup initial value
        mock_interface.set_register_value(test_addr, 80)

        # Rapid read-write sequence
        for i in range(10):
            regmap.write_reg(test_addr, i * 10)
            value = regmap.read_reg(test_addr)
            assert value == i * 10

    def test_rapid_successive_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test rapid successive operations."""
        test_addr = 0xCA

        # Rapid writes
        for i in range(100):
            regmap.write_reg(test_addr, i % 256)

        # Final value should be correct
        assert regmap._regs_cache[test_addr] == 99

        # Rapid reads
        for _ in range(100):
            value = regmap.regs.get_reg(test_addr)
            assert value == 99

    def test_interleaved_reg_field_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test interleaved register and field operations."""
        test_addr = 0xCA

        # Interleaved operations
        regmap.write_reg(test_addr, 80)
        regmap.fields.set_field("EMISSIVITY", 85)
        value = regmap.read_reg(test_addr)
        assert value == 85

        regmap.fields.set_field("EMISSIVITY", 90)
        value = regmap.regs.get_reg(test_addr)
        assert value == 90


class TestInvalidInputHandling:
    """Test invalid input handling."""

    def test_invalid_register_names(self, regmap: _RegMap) -> None:
        """Test handling of invalid register names."""
        invalid_names = [
            "INVALID_REGISTER",
            "",
            "123",
            "register_with_spaces",
            "VERY_LONG_REGISTER_NAME_THAT_DOES_NOT_EXIST",
            None,
            123,
            [],
            {},
        ]

        for name in invalid_names:
            with pytest.raises((KeyError, AttributeError, TypeError)):
                regmap.regs[name]  # type: ignore

    def test_invalid_field_names(self, regmap: _RegMap) -> None:
        """Test handling of invalid field names."""
        invalid_names = [
            "INVALID_FIELD",
            "",
            "123",
            "field_with_spaces",
            "VERY_LONG_FIELD_NAME_THAT_DOES_NOT_EXIST",
            None,
            123,
            [],
            {},
        ]

        for name in invalid_names:
            with pytest.raises((KeyError, AttributeError, TypeError)):
                regmap.fields[name]  # type: ignore

    def test_invalid_addresses(self, regmap: _RegMap) -> None:
        """Test handling of invalid addresses."""
        invalid_addresses = [
            -1,
            0x1000,
            0xFFFF,
            0x999,
            "0xCA",
            None,
            [],
            {},
            1.5,
        ]

        for addr in invalid_addresses:
            with pytest.raises((KeyError, TypeError, ValueError)):
                regmap.read_reg(addr)  # type: ignore

            with pytest.raises((KeyError, TypeError, ValueError)):
                regmap.write_reg(addr, 100)  # type: ignore

    def test_invalid_value_types(self, regmap: _RegMap) -> None:
        """Test handling of invalid value types."""
        test_addr = 0xCA

        invalid_values = [
            "80",
            None,
            [],
            {},
            1.5,
            complex(1, 2),
            object(),
        ]

        for value in invalid_values:
            with pytest.raises((TypeError, ValueError)):
                regmap.write_reg(test_addr, value)  # type: ignore

    def test_malformed_parameters(self, regmap: _RegMap) -> None:
        """Test handling of malformed parameters."""
        # Test malformed register lists
        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.read_regs("not_a_list")  # type: ignore

        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.read_regs([0xCA, "invalid"])  # type: ignore

        # Test malformed register dictionaries
        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.write_regs("not_a_dict")  # type: ignore

        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.write_regs({0xCA: 80, "invalid": 100})  # type: ignore

        # Test malformed field lists
        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.fields.get_fields("not_a_list")  # type: ignore

        with pytest.raises((TypeError, ValueError, AttributeError)):
            regmap.fields.get_fields(["EMISSIVITY", 123])  # type: ignore


class TestExtremeValueScenarios:
    """Test extreme value scenarios."""

    def test_extreme_register_values(self, regmap: _RegMap) -> None:
        """Test extreme register values."""
        test_addr = 0xCA

        # Test with extreme valid values
        extreme_values = [0, 255]
        for value in extreme_values:
            regmap.write_reg(test_addr, value)
            assert regmap._regs_cache[test_addr] == value

        # Test with extreme invalid values
        extreme_invalid = [-1000, 1000, 65535, -65535]
        for value in extreme_invalid:
            with pytest.raises(ValueError):
                regmap.write_reg(test_addr, value)

    def test_extreme_collection_sizes(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test extreme collection sizes."""
        # Test with maximum possible collection size
        max_addrs = regmap.regs.__addr_list__
        test_data = {addr: addr % 256 for addr in max_addrs}

        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Should handle maximum collection size
        result = regmap.read_regs(max_addrs)
        assert len(result) == len(max_addrs)

        # Should handle maximum write collection (exclude read-only registers)
        writable_data = {
            addr: value for addr, value in test_data.items() if addr not in TestDataGenerator.READ_ONLY_ADDRESSES
        }
        regmap.write_regs(writable_data)
        for addr, value in writable_data.items():
            assert regmap._regs_cache[addr] == value


class TestCornerCaseIntegration:
    """Test corner case integration scenarios."""

    def test_mixed_boundary_conditions(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test mixed boundary conditions."""
        # Mix of boundary values
        test_data = {
            0xCA: 0,  # Minimum value
            0xB4: 255,  # Maximum value
            0xB7: 128,  # Mid-range value
        }

        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Should handle mixed boundary values
        result = regmap.read_regs(list(test_data.keys()))
        assert result == test_data

    def test_boundary_error_recovery(self, regmap: _RegMap) -> None:
        """Test recovery from boundary errors."""
        test_addr = 0xCA

        # Cause boundary error
        with pytest.raises(ValueError):
            regmap.write_reg(test_addr, 256)

        # Should be able to recover with valid value
        regmap.write_reg(test_addr, 80)
        assert regmap._regs_cache[test_addr] == 80

    def test_cascading_boundary_effects(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cascading effects of boundary conditions."""
        # Test that boundary conditions in one area don't affect others
        test_addr = 0xCA

        # Set valid value
        regmap.write_reg(test_addr, 80)
        assert regmap._regs_cache[test_addr] == 80

        # Cause error in different register
        with pytest.raises(ValueError):
            regmap.write_reg(0xB4, 256)

        # Original register should be unaffected
        assert regmap._regs_cache[test_addr] == 80

        # Should be able to continue operations
        regmap.write_reg(0xB4, 100)
        assert regmap._regs_cache[0xB4] == 100


class TestBoundaryDocumentation:
    """Test boundary condition documentation and error messages."""

    def test_boundary_error_messages(self, regmap: _RegMap) -> None:
        """Test that boundary error messages are informative."""
        test_addr = 0xCA

        # Test value out of range error message
        with pytest.raises(ValueError) as exc_info:
            regmap.write_reg(test_addr, 256)

        error_msg = str(exc_info.value)
        assert "256" in error_msg
        assert "255" in error_msg or "0" in error_msg  # Range information

        # Test negative value error message
        with pytest.raises(ValueError) as exc_info:
            regmap.write_reg(test_addr, -1)

        error_msg = str(exc_info.value)
        assert "-1" in error_msg

    def test_boundary_help_information(self, regmap: _RegMap) -> None:
        """Test availability of boundary help information."""
        # Test that field boundaries are documented
        for field_name in regmap.fields.__field_defs__:
            field_def = regmap.fields.__field_defs__[field_name]

            # Should have type information
            assert hasattr(field_def, "type")
            assert isinstance(field_def.type, str)

            # Should have help information
            assert hasattr(field_def, "help")
            assert isinstance(field_def.help, str)

    def test_boundary_validation_consistency(self, regmap: _RegMap) -> None:
        """Test consistency of boundary validation."""
        # Test that validation is consistent across different access methods
        test_addr = 0xCA

        # Direct register access
        with pytest.raises(ValueError):
            regmap.write_reg(test_addr, 256)

        # Register object access
        with pytest.raises(ValueError):
            regmap.regs.write_reg(test_addr, 256)

        # Both should fail consistently
        # This ensures validation is applied consistently across all access paths
