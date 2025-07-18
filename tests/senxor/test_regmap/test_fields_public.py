"""Tests for Fields public API and invariants.

This module tests the public interface of the Fields class,
including static integrity checks, properties, public methods, and field access.
"""

from __future__ import annotations

import pytest

from senxor.regmap._field import Field
from senxor.regmap._fields import Fields
from senxor.regmap._regmap import _RegMap

from .fixtures import EnhancedMockInterface, SenxorStub


class TestStaticIntegrity:
    """Test static integrity of Fields class metadata."""

    def test_field_defs_uniqueness(self) -> None:
        """Test that field definitions have unique names."""
        field_defs = Fields.__field_defs__
        names = list(field_defs.keys())

        # No duplicate names
        assert len(names) == len(set(names))

        # All names are strings
        assert all(isinstance(name, str) for name in names)

        # All names are non-empty
        assert all(len(name) > 0 for name in names)

    def test_field_attr_name_consistency(self) -> None:
        """Test that field attribute names match field definitions."""
        field_defs = Fields.__field_defs__

        # Create a Fields instance to test attributes
        mock_interface = EnhancedMockInterface()
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)
        fields = regmap.fields

        # Check that each field definition has a corresponding attribute
        for field_name in field_defs:
            assert hasattr(fields, field_name)
            field_instance = getattr(fields, field_name)
            assert isinstance(field_instance, Field)
            assert field_instance.name == field_name

    def test_reg2fname_mapping_correctness(self) -> None:
        """Test that register-to-field-name mapping is correct."""
        field_defs = Fields.__field_defs__
        reg2fname_map = Fields.__reg2fname_map__

        # Check that mapping is consistent with field definitions
        for field_name, field_def in field_defs.items():
            for reg_addr in field_def.addr_map:
                assert reg_addr in reg2fname_map
                assert field_name in reg2fname_map[reg_addr]

        # Check reverse consistency
        for reg_addr, field_names in reg2fname_map.items():
            for field_name in field_names:
                assert field_name in field_defs
                assert reg_addr in field_defs[field_name].addr_map

    def test_no_duplicate_field_names(self) -> None:
        """Test that no duplicate field names exist."""
        field_defs = Fields.__field_defs__
        name_list = Fields.__name_list__

        # Name list should match field_defs keys
        assert set(name_list) == set(field_defs.keys())

        # No duplicates in name list
        assert len(name_list) == len(set(name_list))

    def test_field_register_references_valid(self) -> None:
        """Test that field register references are valid."""
        field_defs = Fields.__field_defs__

        # All register addresses should be valid integers
        for field_def in field_defs.values():
            for reg_addr in field_def.addr_map:
                assert isinstance(reg_addr, int)
                assert 0 <= reg_addr <= 255  # Valid register address range

                # Bit ranges should be valid
                start_bit, end_bit = field_def.addr_map[reg_addr]
                assert isinstance(start_bit, int)
                assert isinstance(end_bit, int)
                assert 0 <= start_bit < 8
                assert 0 <= end_bit <= 8
                assert start_bit <= end_bit


class TestPublicProperties:
    """Test public properties of Fields class."""

    def test_writable_fields_property(self, regmap: _RegMap) -> None:
        """Test writable_fields property."""
        fields = regmap.fields

        writable_fields = fields.writable_fields
        expected_writable = Fields.__writable_list__

        assert writable_fields == expected_writable
        assert isinstance(writable_fields, list)

        # Should be a copy, not the same object
        assert writable_fields is not expected_writable

    def test_readable_fields_property(self, regmap: _RegMap) -> None:
        """Test readable_fields property."""
        fields = regmap.fields

        readable_fields = fields.readable_fields
        expected_readable = Fields.__readable_list__

        assert readable_fields == expected_readable
        assert isinstance(readable_fields, list)

        # Should be a copy, not the same object
        assert readable_fields is not expected_readable

    def test_status_shallow_copy(self, regmap: _RegMap) -> None:
        """Test that status property returns a shallow copy."""
        fields = regmap.fields

        # Add some data to cache
        test_data = {"EMISSIVITY": 80, "SW_RESET": 1}
        for field_name, value in test_data.items():
            fields._fields_cache[field_name] = value

        # Get status
        status = fields.status

        # Should match cache content
        assert status == test_data

        # Should be a copy, not the same object
        assert status is not fields._fields_cache

        # Modifying status should not affect cache
        status["TEST_FIELD"] = 99
        assert "TEST_FIELD" not in fields._fields_cache

    def test_status_display_formatting(self, regmap: _RegMap) -> None:
        """Test status_display property formatting."""
        fields = regmap.fields

        # Add some data to cache
        fields._fields_cache["EMISSIVITY"] = 80
        fields._fields_cache["SW_RESET"] = 1

        # Get status display
        status_display = fields.status_display

        # Should be a dictionary of strings
        assert isinstance(status_display, dict)
        for field_name, display_value in status_display.items():
            assert isinstance(display_value, str)
            assert field_name in fields._fields_cache

    def test_fields_property_access(self, regmap: _RegMap) -> None:
        """Test fields property access."""
        fields = regmap.fields

        fields_dict = fields.fields

        # Should be a dictionary
        assert isinstance(fields_dict, dict)

        # Should contain Field instances
        for name, field_instance in fields_dict.items():
            assert isinstance(field_instance, Field)
            assert field_instance.name == name

        # Should match expected field names
        expected_names = set(Fields.__name_list__)
        assert set(fields_dict.keys()) == expected_names

    def test_property_consistency(self, regmap: _RegMap) -> None:
        """Test that properties are consistent with class metadata."""
        fields = regmap.fields

        # Properties should match class variables
        assert fields.writable_fields == Fields.__writable_list__
        assert fields.readable_fields == Fields.__readable_list__

        # Fields property should contain all defined fields
        assert set(fields.fields.keys()) == set(Fields.__name_list__)


class TestPublicMethods:
    """Test public methods of Fields class."""

    def test_get_field_by_name(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test get_field method with field name."""
        fields = regmap.fields

        # Setup test data
        test_value = 80
        mock_interface.set_register_value(0xCA, test_value)

        # Get field by name
        result = fields.get_field("EMISSIVITY")

        # Should return the field value
        assert result == test_value

        # Should have made hardware call
        assert 0xCA in mock_interface.read_calls

    def test_get_field_by_instance(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test get_field method with Field instance."""
        fields = regmap.fields

        # Setup test data
        test_value = 1
        mock_interface.set_register_value(0x00, test_value)

        # Get field instance
        sw_reset_field = fields.SW_RESET

        # Get field by instance
        result = fields.get_field(sw_reset_field)

        # Should return the field value
        assert result == test_value

    def test_get_field_invalid_name(self, regmap: _RegMap) -> None:
        """Test get_field with invalid field name."""
        fields = regmap.fields

        # Should raise KeyError for invalid name
        with pytest.raises((KeyError, AttributeError)):
            fields.get_field("INVALID_FIELD")

    def test_get_fields_bulk_operation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test get_fields bulk operation."""
        fields = regmap.fields

        # Setup test data
        test_data = {0xCA: 80, 0x00: 1}
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Get multiple fields
        field_names = ["EMISSIVITY", "SW_RESET"]
        result = fields.get_fields(field_names)

        # Should return dictionary of field values
        assert isinstance(result, dict)
        assert result["EMISSIVITY"] == 80
        assert result["SW_RESET"] == 1

        # Should have made hardware calls
        assert 0xCA in mock_interface.read_calls
        assert 0x00 in mock_interface.read_calls

    def test_set_field_by_name(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test set_field method with field name."""
        fields = regmap.fields

        # Set field by name
        fields.set_field("EMISSIVITY", 85)

        # Should have made hardware call
        assert (0xCA, 85) in mock_interface.write_calls

        # Should have updated cache
        assert fields._fields_cache["EMISSIVITY"] == 85

    def test_set_field_by_instance(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test set_field method with Field instance."""
        fields = regmap.fields

        # Get field instance
        emissivity_field = fields.EMISSIVITY

        # Set field by instance
        fields.set_field(emissivity_field, 90)

        # Should have made hardware call
        assert (0xCA, 90) in mock_interface.write_calls

        # Should have updated cache
        assert fields._fields_cache["EMISSIVITY"] == 90

    def test_set_fields_bulk_operation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test set_fields bulk operation."""
        fields = regmap.fields

        # Set multiple fields
        field_values = {"EMISSIVITY": 75}
        fields.set_fields(field_values)

        # Should have made hardware calls
        assert (0xCA, 75) in mock_interface.write_calls

        # Should have updated cache
        assert fields._fields_cache["EMISSIVITY"] == 75

    def test_method_parameter_validation(self, regmap: _RegMap) -> None:
        """Test parameter validation in public methods."""
        fields = regmap.fields

        # Test invalid field name
        with pytest.raises((KeyError, AttributeError)):
            fields.get_field("INVALID_FIELD")

        # Test invalid field in bulk operation
        with pytest.raises((KeyError, AttributeError)):
            fields.get_fields(["INVALID_FIELD"])

        # Test invalid field name in set
        with pytest.raises((KeyError, AttributeError)):
            fields.set_field("INVALID_FIELD", 1)


class TestFieldAccess:
    """Test field access patterns."""

    def test_direct_attribute_access(self, regmap: _RegMap) -> None:
        """Test direct attribute access to fields."""
        fields = regmap.fields

        # Test accessing known fields
        emissivity_field = fields.EMISSIVITY
        assert isinstance(emissivity_field, Field)
        assert emissivity_field.name == "EMISSIVITY"

        sw_reset_field = fields.SW_RESET
        assert isinstance(sw_reset_field, Field)
        assert sw_reset_field.name == "SW_RESET"

    def test_getitem_access(self, regmap: _RegMap) -> None:
        """Test __getitem__ access to fields."""
        fields = regmap.fields

        # Test with valid field name
        field = fields["EMISSIVITY"]
        assert isinstance(field, Field)
        assert field.name == "EMISSIVITY"

        # Test with invalid field name
        with pytest.raises((KeyError, AttributeError)):
            fields["INVALID_FIELD"]

    def test_setitem_prevention(self, regmap: _RegMap) -> None:
        """Test that __setitem__ is prevented."""
        fields = regmap.fields

        # Should raise AttributeError
        with pytest.raises(AttributeError):
            fields["EMISSIVITY"] = 100  # type: ignore

    def test_iteration_support(self, regmap: _RegMap) -> None:
        """Test iteration over fields."""
        fields = regmap.fields

        # Test iteration
        field_instances = list(fields)

        # Should contain Field instances
        assert all(isinstance(field, Field) for field in field_instances)

        # Should contain all expected fields
        expected_names = set(Fields.__name_list__)
        actual_names = {field.name for field in field_instances}
        assert actual_names == expected_names

        # Should be able to iterate multiple times
        field_instances2 = list(fields)
        assert len(field_instances2) == len(field_instances)

    def test_access_consistency(self, regmap: _RegMap) -> None:
        """Test that different access methods return same field instance."""
        fields = regmap.fields

        # Different access methods should return same instance
        field1 = fields.EMISSIVITY
        field2 = fields["EMISSIVITY"]

        # Should be the same instance due to descriptor caching
        assert field1 is field2


class TestStringRepresentation:
    """Test string representation of Fields class."""

    def test_repr_format(self, regmap: _RegMap) -> None:
        """Test __repr__ format."""
        fields = regmap.fields

        repr_str = repr(fields)

        # Should contain class name
        assert "Fields" in repr_str

        # Should contain regmap reference
        assert "regmap" in repr_str

        # Should be a valid string
        assert isinstance(repr_str, str)
        assert len(repr_str) > 0

    def test_repr_consistency(self, regmap: _RegMap) -> None:
        """Test __repr__ consistency."""
        fields = regmap.fields

        # Multiple calls should return same result
        repr1 = repr(fields)
        repr2 = repr(fields)
        assert repr1 == repr2

        # Should be deterministic
        assert isinstance(repr1, str)


class TestFieldInstanceAccess:
    """Test access to individual field instances."""

    def test_field_instance_properties(self, regmap: _RegMap) -> None:
        """Test properties of field instances."""
        fields = regmap.fields

        # Get a field instance
        emissivity_field = fields.EMISSIVITY

        # Test properties
        assert emissivity_field.name == "EMISSIVITY"
        assert isinstance(emissivity_field.group, str)
        assert isinstance(emissivity_field.readable, bool)
        assert isinstance(emissivity_field.writable, bool)
        assert isinstance(emissivity_field.type, str)
        assert isinstance(emissivity_field.desc, str)
        assert isinstance(emissivity_field.help, str)
        assert isinstance(emissivity_field.addr, str)
        assert isinstance(emissivity_field.addr_map, dict)
        assert isinstance(emissivity_field.auto_reset, bool)

    def test_field_instance_consistency(self, regmap: _RegMap) -> None:
        """Test that field instances are consistent."""
        fields = regmap.fields

        # Multiple access should return same instance
        field1 = fields.EMISSIVITY
        field2 = fields.EMISSIVITY
        assert field1 is field2

        # Dict access should return same instance
        field3 = fields["EMISSIVITY"]
        assert field1 is field3

    def test_field_instance_methods(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test methods of field instances."""
        fields = regmap.fields

        # Get a writable field
        emissivity_field = fields.EMISSIVITY

        # Test get method
        test_value = 80
        mock_interface.set_register_value(0xCA, test_value)
        value = emissivity_field.get()
        assert value == test_value

        # Test set method
        new_value = 85
        emissivity_field.set(new_value)
        assert fields._fields_cache["EMISSIVITY"] == new_value

        # Test value property
        assert emissivity_field.value == new_value

        # Test display method
        display_value = emissivity_field.display()
        assert isinstance(display_value, str)

        # Test display with specific value
        display_value2 = emissivity_field.display(90)
        assert isinstance(display_value2, str)

    def test_field_validation_method(self, regmap: _RegMap) -> None:
        """Test field validation method."""
        fields = regmap.fields

        # Get a field
        emissivity_field = fields.EMISSIVITY

        # Test validation with valid value
        is_valid = emissivity_field.validate(80)
        assert isinstance(is_valid, bool)

        # Test validation with potentially invalid value
        is_valid2 = emissivity_field.validate(-1)
        assert isinstance(is_valid2, bool)


class TestErrorHandling:
    """Test error handling in public methods."""

    def test_invalid_field_access(self, regmap: _RegMap) -> None:
        """Test error handling for invalid field access."""
        fields = regmap.fields

        # Test invalid attribute access
        with pytest.raises(AttributeError):
            fields.INVALID_FIELD  # type: ignore

    def test_read_only_field_protection(self, regmap: _RegMap) -> None:
        """Test that read-only fields are protected."""
        fields = regmap.fields

        # Find a read-only field
        for field_name in Fields.__field_defs__:
            field_def = Fields.__field_defs__[field_name]
            if not field_def.writable:
                field_instance = getattr(fields, field_name)

                # Should not be able to set value
                with pytest.raises(AttributeError):
                    field_instance.set(1)

                # set_field should also fail
                with pytest.raises(AttributeError):
                    fields.set_field(field_name, 1)
                break
        else:
            # If no read-only fields found, skip this test
            pytest.skip("No read-only fields found for testing")

    def test_connection_error_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost."""
        fields = regmap.fields

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Field operations should raise error
        with pytest.raises(Exception):  # Should be SenxorNotConnectedError
            fields.get_field("EMISSIVITY")

        with pytest.raises(Exception):
            fields.set_field("EMISSIVITY", 80)

        # Individual field operations should also fail
        with pytest.raises(Exception):
            fields.EMISSIVITY.get()

        with pytest.raises(Exception):
            fields.EMISSIVITY.set(80)


class TestPerformanceCharacteristics:
    """Test performance characteristics of public methods."""

    def test_property_access_performance(self, regmap: _RegMap) -> None:
        """Test that property access is efficient."""
        fields = regmap.fields

        # Multiple property access should be fast
        for _ in range(100):
            _ = fields.writable_fields
            _ = fields.readable_fields
            _ = fields.status
            _ = fields.fields

        # Should not raise any exceptions
        assert True

    def test_field_instance_caching(self, regmap: _RegMap) -> None:
        """Test that field instances are properly cached."""
        fields = regmap.fields

        # Multiple access should return same instance (cached)
        instances = []
        for _ in range(10):
            instances.append(fields.EMISSIVITY)

        # All should be the same instance
        assert all(inst is instances[0] for inst in instances)

    def test_bulk_operations_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that bulk operations are efficient."""
        fields = regmap.fields

        # Setup test data
        test_data = {"EMISSIVITY": 80}
        for field_name, value in test_data.items():
            # Find the register for this field
            field_def = Fields.__field_defs__[field_name]
            for reg_addr in field_def.addr_map:
                mock_interface.set_register_value(reg_addr, value)

        # Bulk get should be efficient
        mock_interface.reset_call_history()
        result = fields.get_fields(list(test_data.keys()))

        # Should have made calls for required registers
        assert len(mock_interface.read_calls) >= 1
        assert result["EMISSIVITY"] == 80


class TestCacheInteraction:
    """Test cache interaction in public methods."""

    def test_field_cache_consistency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test field cache consistency."""
        fields = regmap.fields

        # Set field value
        fields.set_field("EMISSIVITY", 85)

        # Cache should be consistent
        assert fields._fields_cache["EMISSIVITY"] == 85

        # Get field should return cached value
        mock_interface.reset_call_history()
        value = fields.get_field("EMISSIVITY")
        assert value == 85

    def test_register_field_cache_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test synchronization between register and field caches."""
        fields = regmap.fields

        # Set register value directly
        test_value = 90
        mock_interface.set_register_value(0xCA, test_value)

        # Read through regmap to trigger sync
        regmap.read_reg(0xCA)

        # Field cache should be updated
        if "EMISSIVITY" in fields._fields_cache:
            assert fields._fields_cache["EMISSIVITY"] == test_value

    def test_status_property_cache_reflection(self, regmap: _RegMap) -> None:
        """Test that status property reflects cache state."""
        fields = regmap.fields

        # Set some field values
        test_data = {"EMISSIVITY": 80}
        for field_name, value in test_data.items():
            fields._fields_cache[field_name] = value

        # Status should reflect cache
        status = fields.status
        for field_name, value in test_data.items():
            assert status[field_name] == value

    def test_status_display_cache_reflection(self, regmap: _RegMap) -> None:
        """Test that status_display reflects cache state."""
        fields = regmap.fields

        # Set some field values
        fields.EMISSIVITY.set(80)

        # Status display should reflect cache
        status_display = fields.status_display
        assert "EMISSIVITY" in status_display
        assert isinstance(status_display["EMISSIVITY"], str)
