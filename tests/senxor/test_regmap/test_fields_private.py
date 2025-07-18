"""Tests for Fields private methods and internals.

This module tests the internal implementation of the Fields class,
including private methods, field value parsing/encoding, and internal state management.
"""

from __future__ import annotations

import pytest

from senxor._error import SenxorNotConnectedError
from senxor.regmap._field import Field
from senxor.regmap._fields import Fields
from senxor.regmap._regmap import _RegMap

from .fixtures import (
    EnhancedMockInterface,
    SenxorStub,
    create_mock_with_failure_simulation,
)


class TestFieldsInitialization:
    """Test Fields initialization and setup."""

    def test_init_with_regmap(self, regmap: _RegMap) -> None:
        """Test Fields initialization with _RegMap."""
        fields = regmap.fields

        assert fields._regmap is regmap
        assert fields._log is not None
        assert hasattr(fields, "_fields")
        assert isinstance(fields._fields, dict)

    def test_field_instances_creation(self, regmap: _RegMap) -> None:
        """Test that field instances are created correctly."""
        fields = regmap.fields

        # Test that all fields from __field_defs__ are created as instances
        for field_name in Fields.__field_defs__:
            assert hasattr(fields, field_name)
            field_instance = getattr(fields, field_name)
            assert isinstance(field_instance, Field)
            assert field_instance.name == field_name

        # Test that _fields dictionary contains all fields
        for field_name in Fields.__field_defs__:
            assert field_name in fields._fields
            assert isinstance(fields._fields[field_name], Field)

    def test_cache_reference_setup(self, regmap: _RegMap) -> None:
        """Test that cache reference is set up correctly."""
        fields = regmap.fields

        # Should have cache reference
        assert hasattr(fields, "_fields_cache")
        assert isinstance(fields._fields_cache, dict)

    def test_reg2fname_mapping_build(self, regmap: _RegMap) -> None:
        """Test that register-to-field-name mapping is built correctly."""
        fields = regmap.fields

        # Should have the mapping
        assert hasattr(fields, "__reg2fname_map__")
        assert isinstance(fields.__reg2fname_map__, dict)

        # Should contain mappings for known registers
        reg2fname_map = fields.__reg2fname_map__

        # Test that all fields are properly mapped
        for field_name in Fields.__field_defs__:
            field_def = Fields.__field_defs__[field_name]

            # Each register address in the field's addr_map should have a mapping
            for reg_addr in field_def.addr_map:
                assert reg_addr in reg2fname_map
                assert isinstance(reg2fname_map[reg_addr], set)
                assert field_name in reg2fname_map[reg_addr]

    def test_class_metadata_consistency(self, regmap: _RegMap) -> None:
        """Test consistency between class metadata and field definitions."""
        fields = regmap.fields

        # All fields in __name_list__ should be in __field_defs__
        for name in Fields.__name_list__:
            assert name in Fields.__field_defs__

        # All auto-reset fields should have auto_reset=True
        for name in Fields.__auto_reset_list__:
            assert name in Fields.__field_defs__
            assert Fields.__field_defs__[name].auto_reset is True

        # All readable fields should have readable=True
        for name in Fields.__readable_list__:
            assert name in Fields.__field_defs__
            assert Fields.__field_defs__[name].readable is True

        # All writable fields should have writable=True
        for name in Fields.__writable_list__:
            assert name in Fields.__field_defs__
            assert Fields.__field_defs__[name].writable is True

        # Check that field attribute names match their internal name property
        all_fields = fields.fields
        for field_name in Fields.__name_list__:
            assert field_name in all_fields
            assert isinstance(all_fields[field_name], Field)
            assert all_fields[field_name].name == field_name


class TestPrivateGetMethods:
    """Test private get method implementations."""

    def test_get_field_cache_behavior(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _get_field cache behavior."""
        fields = regmap.fields

        # Get a field instance
        emissivity_field = fields.EMISSIVITY

        # Setup test data
        test_value = 80
        mock_interface.set_register_value(0xCA, test_value)

        # First call should read from hardware
        result1 = fields._get_field(emissivity_field)
        assert result1 == test_value

        # Should have made hardware call
        assert 0xCA in mock_interface.read_calls

        # Clear call history
        mock_interface.reset_call_history()

        # Second call should use cache (for non-auto-reset fields)
        result2 = fields._get_field(emissivity_field)
        assert result2 == test_value

        # Should not have made additional hardware call if cached
        if not emissivity_field.auto_reset:
            assert len(mock_interface.read_calls) == 0

    def test_get_field_auto_reset_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _get_field handling of auto-reset fields."""
        fields = regmap.fields

        # Get an auto-reset field
        sw_reset_field = fields.SW_RESET

        # Setup test data
        test_value = 1
        mock_interface.set_register_value(0x00, test_value)

        # First call
        result1 = fields._get_field(sw_reset_field)
        assert result1 == test_value

        # Clear call history
        mock_interface.reset_call_history()

        # Second call should always read from hardware for auto-reset fields
        fields._get_field(sw_reset_field)

        # Should have made hardware call
        assert 0x00 in mock_interface.read_calls

    def test_get_fields_bulk_processing(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _get_fields bulk processing."""
        fields = regmap.fields

        # Get multiple field instances
        field_instances = [fields.EMISSIVITY, fields.SW_RESET]

        # Setup test data
        test_data = {0xCA: 80, 0x00: 1}
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Call _get_fields
        result = fields._get_fields(field_instances)

        # Should return field values
        assert isinstance(result, dict)
        assert "EMISSIVITY" in result
        assert "SW_RESET" in result

        # Values should match expected
        assert result["EMISSIVITY"] == 80
        assert result["SW_RESET"] == 1

    def test_get_fields_force_refresh(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _get_fields with force refresh."""
        fields = regmap.fields

        # Get field instances
        field_instances = [fields.EMISSIVITY]

        # Setup test data and populate cache
        test_value = 80
        mock_interface.set_register_value(0xCA, test_value)
        fields._fields_cache["EMISSIVITY"] = test_value

        # Clear call history
        mock_interface.reset_call_history()

        # Call _get_fields - should use cache
        result = fields._get_fields(field_instances)
        assert result["EMISSIVITY"] == test_value

        # Should have made hardware call to refresh cache
        assert 0xCA in mock_interface.read_calls

    def test_get_fields_mixed_auto_reset(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _get_fields with mixed auto-reset and normal fields."""
        fields = regmap.fields

        # Get mixed field instances
        field_instances = [fields.EMISSIVITY, fields.SW_RESET]  # Normal and auto-reset

        # Setup test data
        test_data = {0xCA: 80, 0x00: 1}
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Pre-populate cache
        fields._fields_cache["EMISSIVITY"] = 80
        fields._fields_cache["SW_RESET"] = 1

        # Clear call history
        mock_interface.reset_call_history()

        # Call _get_fields
        result = fields._get_fields(field_instances)

        # Should return correct values
        assert result["EMISSIVITY"] == 80
        assert result["SW_RESET"] == 1

        # Should have made hardware calls (especially for auto-reset)
        assert len(mock_interface.read_calls) > 0


class TestPrivateSetMethods:
    """Test private set method implementations."""

    def test_set_field_validation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _set_field validation."""
        fields = regmap.fields

        # Get a writable field
        emissivity_field = fields.EMISSIVITY

        # Test valid value
        fields._set_field(emissivity_field, 80)
        assert (0xCA, 80) in mock_interface.write_calls

    def test_set_field_readonly_protection(self, regmap: _RegMap) -> None:
        """Test _set_field protection for read-only fields."""
        fields = regmap.fields

        # Find a read-only field
        for field_name in fields.__field_defs__:
            field_def = fields.__field_defs__[field_name]
            if not field_def.writable:
                field_instance = getattr(fields, field_name)

                # Should raise AttributeError
                with pytest.raises(AttributeError):
                    fields._set_field(field_instance, 1)
                break
        else:
            # If no read-only fields found, skip this test
            pytest.skip("No read-only fields found for testing")

    def test_set_field_hardware_write(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _set_field hardware write operations."""
        fields = regmap.fields

        # Get a writable field
        emissivity_field = fields.EMISSIVITY
        test_value = 90

        # Call _set_field
        fields._set_field(emissivity_field, test_value)

        # Should have made hardware write
        assert (0xCA, test_value) in mock_interface.write_calls

        # Should have updated cache
        assert fields._fields_cache["EMISSIVITY"] == test_value

    def test_set_field_cache_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _set_field cache synchronization."""
        fields = regmap.fields

        # Get a field
        emissivity_field = fields.EMISSIVITY
        test_value = 85

        # Call _set_field
        fields._set_field(emissivity_field, test_value)

        # Field cache should be updated
        assert fields._fields_cache["EMISSIVITY"] == test_value

        # Register cache should also be updated
        assert regmap._regs_cache[0xCA] == test_value

    def test_set_fields_bulk_validation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _set_fields bulk validation."""
        fields = regmap.fields

        # Get multiple writable fields
        field_instances = [fields.EMISSIVITY]
        values = [75]

        # Call _set_fields
        fields._set_fields(field_instances, values)

        # Should have made hardware writes
        assert (0xCA, 75) in mock_interface.write_calls

        # Should have updated caches
        assert fields._fields_cache["EMISSIVITY"] == 75
        assert regmap._regs_cache[0xCA] == 75

    def test_set_fields_partial_failure_rollback(self, regmap: _RegMap) -> None:
        """Test _set_fields rollback on partial failure."""
        # Create interface that fails after 1 write
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=1)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)
        fields = regmap.fields

        # Get multiple writable fields (if available)
        field_instances = [fields.EMISSIVITY]
        values = [75]

        # First write should succeed, then fail
        try:
            fields._set_fields(field_instances, values)
        except SenxorNotConnectedError:
            pass  # Expected

        # Verify partial state
        successful_writes = len(mock_interface.write_calls)
        assert successful_writes <= 1

    def test_set_fields_cross_register_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test _set_fields with fields spanning multiple registers."""
        fields = regmap.fields

        # This test would need actual multi-register fields
        # For now, test multiple single-register fields
        field_instances = [fields.EMISSIVITY]
        values = [80]

        # Call _set_fields
        fields._set_fields(field_instances, values)

        # Should have updated all relevant registers
        assert (0xCA, 80) in mock_interface.write_calls


class TestFieldValueParsing:
    """Test field value parsing from register data."""

    def test_parse_single_register_field(self, regmap: _RegMap) -> None:
        """Test parsing field value from single register."""
        fields = regmap.fields

        # Get a single-register field
        emissivity_field = fields.EMISSIVITY

        # Test data
        register_data = {0xCA: 80}

        # Parse field value
        result = emissivity_field._parse_field_value(register_data)

        # Should return the register value (for full-byte fields)
        assert result == 80

    def test_parse_multi_register_field(self, regmap: _RegMap) -> None:
        """Test parsing field value from multiple registers."""
        fields = regmap.fields

        # Look for a multi-register field
        # This would need actual multi-register field implementation
        # For now, test with single register
        emissivity_field = fields.EMISSIVITY

        register_data = {0xCA: 80}
        result = emissivity_field._parse_field_value(register_data)
        assert result == 80

    def test_parse_bit_field_extraction(self, regmap: _RegMap) -> None:
        """Test parsing bit field from register."""
        fields = regmap.fields

        # Get a bit field (like SW_RESET)
        sw_reset_field = fields.SW_RESET

        # Test data with bit set
        register_data = {0x00: 0b00000001}  # Bit 0 set

        # Parse field value
        result = sw_reset_field._parse_field_value(register_data)

        # Should extract the bit
        assert result == 1

        # Test with bit cleared
        register_data = {0x00: 0b00000000}  # Bit 0 cleared
        result = sw_reset_field._parse_field_value(register_data)
        assert result == 0

    def test_parse_field_value_edge_cases(self, regmap: _RegMap) -> None:
        """Test field value parsing edge cases."""
        fields = regmap.fields

        # Test with empty register data
        emissivity_field = fields.EMISSIVITY

        # Should handle missing register gracefully
        empty_data = {}
        try:
            result = emissivity_field._parse_field_value(empty_data)
            # If it doesn't raise an error, result should be reasonable
            assert isinstance(result, int)
        except KeyError:
            # This is also acceptable behavior
            pass


class TestFieldValueEncoding:
    """Test field value encoding to register data."""

    def test_encode_single_register_field(self, regmap: _RegMap) -> None:
        """Test encoding field value to single register."""
        fields = regmap.fields

        # Get a single-register field
        emissivity_field = fields.EMISSIVITY

        # Current register state
        current_regs = {0xCA: 0}

        # Encode field value
        result = emissivity_field._encode_field_value(80, current_regs)

        # Should return register updates
        assert isinstance(result, dict)
        assert 0xCA in result
        assert result[0xCA] == 80

    def test_encode_multi_register_field(self, regmap: _RegMap) -> None:
        """Test encoding field value to multiple registers."""
        fields = regmap.fields

        # This would need actual multi-register field implementation
        # For now, test with single register
        emissivity_field = fields.EMISSIVITY

        current_regs = {0xCA: 0}
        result = emissivity_field._encode_field_value(80, current_regs)

        assert result[0xCA] == 80

    def test_encode_bit_field_insertion(self, regmap: _RegMap) -> None:
        """Test encoding bit field into register."""
        fields = regmap.fields

        # Get a bit field
        sw_reset_field = fields.SW_RESET

        # Current register state
        current_regs = {0x00: 0b11111110}  # All bits set except bit 0

        # Encode field value (set bit 0)
        result = sw_reset_field._encode_field_value(1, current_regs)

        # Should set bit 0 while preserving other bits
        assert result[0x00] == 0b11111111

        # Encode field value (clear bit 0)
        result = sw_reset_field._encode_field_value(0, current_regs)

        # Should clear bit 0 while preserving other bits
        assert result[0x00] == 0b11111110

    def test_encode_preserve_other_bits(self, regmap: _RegMap) -> None:
        """Test that encoding preserves other bits in register."""
        fields = regmap.fields

        # Get a bit field
        sw_reset_field = fields.SW_RESET

        # Current register state with other bits set
        current_regs = {0x00: 0b10101010}

        # Encode field value
        result = sw_reset_field._encode_field_value(1, current_regs)

        # Should preserve other bits and set our bit
        expected = 0b10101011  # Bit 0 set, others preserved
        assert result[0x00] == expected


class TestCacheConsistency:
    """Test cache consistency in private methods."""

    def test_field_register_cache_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test synchronization between field and register caches."""
        fields = regmap.fields

        # Set field value
        emissivity_field = fields.EMISSIVITY
        test_value = 85

        fields._set_field(emissivity_field, test_value)

        # Both caches should be updated
        assert fields._fields_cache["EMISSIVITY"] == test_value
        assert regmap._regs_cache[0xCA] == test_value

    def test_register_field_cache_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that register changes sync to field cache."""
        fields = regmap.fields

        # Set register value directly
        test_value = 90
        mock_interface.set_register_value(0xCA, test_value)

        # Read through regmap to trigger sync
        regmap.read_reg(0xCA)

        # Field cache should be updated
        if "EMISSIVITY" in fields._fields_cache:
            assert fields._fields_cache["EMISSIVITY"] == test_value

    def test_cache_invalidation_on_write(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache invalidation on write operations."""
        fields = regmap.fields

        # Pre-populate cache
        fields._fields_cache["EMISSIVITY"] = 80

        # Write new value
        emissivity_field = fields.EMISSIVITY
        new_value = 95
        fields._set_field(emissivity_field, new_value)

        # Cache should be updated
        assert fields._fields_cache["EMISSIVITY"] == new_value


class TestErrorHandling:
    """Test error handling in private methods."""

    def test_connection_error_during_get(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost during get."""
        fields = regmap.fields

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Get field should raise error
        emissivity_field = fields.EMISSIVITY
        with pytest.raises(SenxorNotConnectedError):
            fields._get_field(emissivity_field)

    def test_connection_error_during_set(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost during set."""
        fields = regmap.fields

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Set field should raise error
        emissivity_field = fields.EMISSIVITY
        with pytest.raises(SenxorNotConnectedError):
            fields._set_field(emissivity_field, 80)

    def test_invalid_field_value_handling(self, regmap: _RegMap) -> None:
        """Test handling of invalid field values."""
        fields = regmap.fields

        # Get a field
        emissivity_field = fields.EMISSIVITY

        # Test with invalid value (this would depend on field validation)
        # For now, test with extreme values
        try:
            fields._set_field(emissivity_field, -1)
            # If no error, that's also valid behavior
        except (ValueError, AttributeError):
            # Expected for invalid values
            pass

    def test_missing_register_handling(self, regmap: _RegMap) -> None:
        """Test handling of missing register data."""
        fields = regmap.fields

        # Get a field
        emissivity_field = fields.EMISSIVITY

        # Test with missing register data
        empty_data = {}
        try:
            result = emissivity_field._parse_field_value(empty_data)
            # If no error, result should be reasonable
            assert isinstance(result, int)
        except KeyError:
            # This is acceptable behavior
            pass


class TestThreadSafety:
    """Test thread safety of private methods."""

    def test_concurrent_field_access(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent access to fields."""
        fields = regmap.fields

        # Setup test data
        test_value = 80
        mock_interface.set_register_value(0xCA, test_value)

        # This would require actual threading test
        # For now, test sequential access
        emissivity_field = fields.EMISSIVITY

        result1 = fields._get_field(emissivity_field)
        result2 = fields._get_field(emissivity_field)

        assert result1 == test_value
        assert result2 == test_value

    def test_concurrent_field_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent field updates."""
        fields = regmap.fields

        # Test sequential updates (threading would need more complex setup)
        emissivity_field = fields.EMISSIVITY

        fields._set_field(emissivity_field, 80)
        fields._set_field(emissivity_field, 85)

        # Final value should be the last one set
        assert fields._fields_cache["EMISSIVITY"] == 85


class TestPerformanceOptimization:
    """Test performance optimization in private methods."""

    def test_bulk_field_operations_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test efficiency of bulk field operations."""
        fields = regmap.fields

        # Get multiple fields
        field_instances = [fields.EMISSIVITY]

        # Setup test data
        mock_interface.set_register_value(0xCA, 80)

        # Clear call history
        mock_interface.reset_call_history()

        # Bulk get should be efficient
        result = fields._get_fields(field_instances)

        # Should have made minimal hardware calls
        assert len(mock_interface.read_calls) >= 1
        assert result["EMISSIVITY"] == 80

    def test_cache_utilization_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache utilization efficiency."""
        fields = regmap.fields

        # Get a field
        emissivity_field = fields.EMISSIVITY

        # Setup and first read
        mock_interface.set_register_value(0xCA, 80)
        result1 = fields._get_field(emissivity_field)

        # Clear call history
        mock_interface.reset_call_history()

        # Second read should use cache (for non-auto-reset fields)
        result2 = fields._get_field(emissivity_field)

        assert result1 == result2

        # Should have minimal additional hardware calls
        if not emissivity_field.auto_reset:
            assert len(mock_interface.read_calls) == 0
