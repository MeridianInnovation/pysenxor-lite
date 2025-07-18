"""Tests for auto-reset behavior in regmap modules.

This module tests comprehensive auto-reset behavior including identification,
cache handling, hardware interaction, and complex scenarios.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from senxor._error import SenxorNotConnectedError

from .fixtures import EnhancedMockInterface, TestDataGenerator

if TYPE_CHECKING:
    from senxor.regmap._regmap import _RegMap


class TestAutoResetIdentification:
    """Test auto-reset register and field identification."""

    def test_auto_reset_register_detection(self, regmap: _RegMap) -> None:
        """Test detection of auto-reset registers."""
        # Get auto-reset register list
        auto_reset_regs = regmap.regs.__auto_reset_list__

        # Should contain known auto-reset registers
        expected_auto_reset = TestDataGenerator.AUTO_RESET_ADDRESSES
        for addr in expected_auto_reset:
            # Find register name for this address
            if addr in regmap.regs.__addr2name__:
                reg_name = regmap.regs.__addr2name__[addr]
                assert reg_name in auto_reset_regs

        # Verify register instances have correct auto_reset property
        for reg_name in auto_reset_regs:
            reg_instance = regmap.regs[reg_name]
            assert reg_instance.auto_reset is True

    def test_auto_reset_field_detection(self, regmap: _RegMap) -> None:
        """Test detection of auto-reset fields."""
        # Check fields that should be auto-reset
        auto_reset_fields = []
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset:
                auto_reset_fields.append(field_name)

        # Verify field instances have correct auto_reset property
        for field_name in auto_reset_fields:
            field_instance = regmap.fields[field_name]
            assert field_instance.auto_reset is True

        # Verify non-auto-reset fields
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if not field_def.auto_reset:
                field_instance = regmap.fields[field_name]
                assert field_instance.auto_reset is False

    def test_auto_reset_inheritance(self, regmap: _RegMap) -> None:
        """Test auto-reset inheritance from register to field."""
        # For each auto-reset register, at least one of its fields should be auto-reset.
        for reg_name in regmap.regs.__auto_reset_list__:
            reg_instance = regmap.regs[reg_name]
            reg_addr = reg_instance.addr
            auto_reset_field_found = False
            for field_name, field_def in regmap.fields.__field_defs__.items():
                if reg_addr in field_def.addr_map:
                    field_instance = regmap.fields[field_name]
                    if field_instance.auto_reset:
                        auto_reset_field_found = True
                        break
            assert auto_reset_field_found, f"No auto-reset field found for auto-reset register {reg_name}"

    def test_auto_reset_metadata_consistency(self, regmap: _RegMap) -> None:
        """Test consistency of auto-reset metadata."""
        # Register metadata should be consistent
        for reg_name in regmap.regs.__auto_reset_list__:
            reg_def = regmap.regs.__reg_defs__[reg_name]
            assert reg_def.auto_reset is True

        # Field metadata should be consistent
        for field_name, field_def in regmap.fields.__field_defs__.items():
            field_instance = regmap.fields[field_name]
            assert field_instance.auto_reset == field_def.auto_reset


class TestAutoResetCacheBehavior:
    """Test auto-reset cache behavior."""

    def test_auto_reset_cache_bypass(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that auto-reset registers bypass cache."""
        # Get an auto-reset register
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]  # SW_RESET
        test_value = 1
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # First read
        value1 = regmap.read_reg(auto_reset_addr)
        assert value1 == test_value

        # Clear call history
        mock_interface.reset_call_history()

        # Second read should always hit hardware (bypass cache)
        value2 = regmap.read_reg(auto_reset_addr)

        # Should have made hardware call
        assert auto_reset_addr in mock_interface.read_calls

        # Value should be 0 (auto-reset)
        assert value2 == 0

    def test_auto_reset_cache_invalidation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset cache invalidation."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Write to auto-reset register
        regmap.write_reg(auto_reset_addr, test_value)

        # Cache should be updated with written value
        assert regmap._regs_cache[auto_reset_addr] == test_value

        # But hardware should auto-reset
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Next read should get 0 and update cache
        value = regmap.read_reg(auto_reset_addr)
        assert value == 0
        assert regmap._regs_cache[auto_reset_addr] == 0

    def test_auto_reset_cache_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset cache updates."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Write value
        regmap.write_reg(auto_reset_addr, test_value)

        # Immediately after write, cache should have written value
        assert regmap._regs_cache[auto_reset_addr] == test_value

        # But hardware should be auto-reset
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Read should update cache to reflect hardware state
        value = regmap.read_reg(auto_reset_addr)
        assert value == 0
        assert regmap._regs_cache[auto_reset_addr] == 0

    def test_auto_reset_cache_consistency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache consistency for auto-reset registers."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Write through different access methods
        regmap.write_reg(auto_reset_addr, test_value)
        regmap.regs.write_reg(auto_reset_addr, test_value)

        # Cache should be consistent
        assert regmap._regs_cache[auto_reset_addr] == test_value

        # Read should always get current hardware state
        value = regmap.read_reg(auto_reset_addr)
        assert value == 0  # Auto-reset value

        # Cache should be updated
        assert regmap._regs_cache[auto_reset_addr] == 0


class TestAutoResetHardwareInteraction:
    """Test auto-reset hardware interaction."""

    def test_auto_reset_read_behavior(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset read behavior."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Set hardware value
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # Read should return value and trigger auto-reset
        value = regmap.read_reg(auto_reset_addr)
        assert value == test_value

        # Hardware should be auto-reset
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Next read should get 0
        value2 = regmap.read_reg(auto_reset_addr)
        assert value2 == 0

    def test_auto_reset_write_behavior(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset write behavior."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Write to auto-reset register
        regmap.write_reg(auto_reset_addr, test_value)

        # Write should succeed
        assert (auto_reset_addr, test_value) in mock_interface.write_calls

        # Hardware should auto-reset after write
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Cache should initially have written value
        assert regmap._regs_cache[auto_reset_addr] == test_value

    def test_auto_reset_hardware_state_changes(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test hardware state changes for auto-reset registers."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Initial state
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Write value
        regmap.write_reg(auto_reset_addr, test_value)

        # Hardware should auto-reset
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Set value again
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # Read should trigger auto-reset
        regmap.read_reg(auto_reset_addr)
        assert mock_interface.get_register_value(auto_reset_addr) == 0

    def test_auto_reset_timing_requirements(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test timing requirements for auto-reset."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        test_value = 1

        # Rapid write-read sequence
        regmap.write_reg(auto_reset_addr, test_value)
        value = regmap.read_reg(auto_reset_addr)

        # Should handle rapid sequence correctly
        assert value == 0  # Auto-reset should have occurred

        # Multiple rapid operations
        for _i in range(10):
            regmap.write_reg(auto_reset_addr, 1)
            value = regmap.read_reg(auto_reset_addr)
            assert value == 0


class TestAutoResetCrossRegisterFields:
    """Test auto-reset behavior with cross-register fields."""

    def test_multi_register_auto_reset_field(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test multi-register field with auto-reset."""
        # This would test fields that span multiple registers where some are auto-reset
        # For now, test single-register auto-reset fields

        # Find an auto-reset field
        auto_reset_field = None
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset:
                auto_reset_field = field_name
                break

        if auto_reset_field:
            # Test field behavior
            test_value = 1
            regmap.fields.set_field(auto_reset_field, test_value)

            # Field cache should be updated
            assert regmap._fields_cache[auto_reset_field] == test_value

            # Read should get auto-reset value
            value = regmap.fields.get_field(auto_reset_field)
            assert value == 0  # Auto-reset

    def test_partial_auto_reset_in_multi_reg_field(
        self,
        regmap: _RegMap,
        mock_interface: EnhancedMockInterface,
    ) -> None:
        """Test partial auto-reset in multi-register field."""
        # This would test fields spanning both auto-reset and normal registers
        # For now, test conceptually

        # Find fields that might span multiple registers
        for field_def in regmap.fields.__field_defs__.values():
            if len(field_def.addr_map) > 1:
                # Check if some registers are auto-reset
                has_auto_reset = False
                has_normal = False

                for reg_addr in field_def.addr_map:
                    if reg_addr in regmap.regs.__addr2name__:
                        reg_name = regmap.regs.__addr2name__[reg_addr]
                        if reg_name in regmap.regs.__auto_reset_list__:
                            has_auto_reset = True
                        else:
                            has_normal = True

                if has_auto_reset and has_normal:
                    # This field spans both auto-reset and normal registers
                    # Test behavior would be complex
                    pass

    def test_auto_reset_field_synchronization(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test synchronization of auto-reset fields."""
        # Find auto-reset field
        auto_reset_field = None
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset and field_def.writable:
                auto_reset_field = field_name
                break

        if auto_reset_field:
            test_value = 1

            # Write through field
            regmap.fields.set_field(auto_reset_field, test_value)

            # Both caches should be synchronized
            assert regmap._fields_cache[auto_reset_field] == test_value

            # Find corresponding register
            field_def = regmap.fields.__field_defs__[auto_reset_field]
            for reg_addr in field_def.addr_map:
                if reg_addr in regmap._regs_cache:
                    # Register cache should reflect field write
                    assert regmap._regs_cache[reg_addr] == test_value
                    break

    def test_cross_register_cache_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache updates across registers for auto-reset fields."""
        # This would test complex scenarios with multi-register fields
        # For now, test single-register auto-reset fields

        auto_reset_field = None
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset and field_def.writable:
                auto_reset_field = field_name
                break

        if auto_reset_field:
            test_value = 1

            # Write field
            regmap.fields.set_field(auto_reset_field, test_value)

            # Read field (should get auto-reset value)
            value = regmap.fields.get_field(auto_reset_field)
            assert value == 0

            # Cache should be updated
            assert regmap._fields_cache[auto_reset_field] == 0


class TestAutoResetMixedOperations:
    """Test auto-reset behavior in mixed operations."""

    def test_mixed_auto_reset_normal_registers(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test mixed auto-reset and normal register operations."""
        # Get auto-reset and normal registers
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA  # EMISSIVITY (normal register)

        # Setup values
        mock_interface.set_register_value(auto_reset_addr, 1)
        mock_interface.set_register_value(normal_addr, 80)

        # Read both
        auto_value = regmap.read_reg(auto_reset_addr)
        normal_value = regmap.read_reg(normal_addr)

        assert auto_value == 1
        assert normal_value == 80

        # Auto-reset should be reset, normal should remain
        assert mock_interface.get_register_value(auto_reset_addr) == 0
        assert mock_interface.get_register_value(normal_addr) == 80

        # Second read
        auto_value2 = regmap.read_reg(auto_reset_addr)
        normal_value2 = regmap.regs.get_reg(normal_addr)  # Use cache

        assert auto_value2 == 0
        assert normal_value2 == 80

    def test_mixed_auto_reset_normal_fields(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test mixed auto-reset and normal field operations."""
        # Find auto-reset and normal fields
        auto_reset_field = None
        normal_field = "EMISSIVITY"  # Known normal field

        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset and field_def.writable:
                auto_reset_field = field_name
                break

        if auto_reset_field:
            # Set values
            regmap.fields.set_field(auto_reset_field, 1)
            regmap.fields.set_field(normal_field, 80)

            # Read both
            auto_value = regmap.fields.get_field(auto_reset_field)
            normal_value = regmap.fields.get_field(normal_field)

            assert auto_value == 0  # Auto-reset
            assert normal_value == 80  # Normal

    def test_bulk_operations_with_auto_reset(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test bulk operations with auto-reset registers."""
        # Mix of auto-reset and normal registers
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA

        test_data = {
            auto_reset_addr: 1,
            normal_addr: 80,
        }

        # Setup hardware
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Bulk read
        result = regmap.read_regs(list(test_data.keys()))

        # Should get correct values
        assert result[auto_reset_addr] == 1
        assert result[normal_addr] == 80

        # Auto-reset should be reset
        assert mock_interface.get_register_value(auto_reset_addr) == 0
        assert mock_interface.get_register_value(normal_addr) == 80

    def test_auto_reset_in_batch_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset behavior in batch operations."""
        # Batch write with auto-reset registers
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA

        test_data = {
            auto_reset_addr: 1,
            normal_addr: 80,
        }

        # Batch write
        regmap.write_regs(test_data)

        # Auto-reset should be reset after write
        assert mock_interface.get_register_value(auto_reset_addr) == 0
        assert mock_interface.get_register_value(normal_addr) == 80

        # Cache should reflect written values initially
        assert regmap._regs_cache[auto_reset_addr] == 1
        assert regmap._regs_cache[normal_addr] == 80


class TestAutoResetErrorScenarios:
    """Test auto-reset behavior in error scenarios."""

    def test_auto_reset_with_connection_errors(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset behavior with connection errors."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]

        # Setup initial state
        regmap.write_reg(auto_reset_addr, 1)
        assert regmap._regs_cache[auto_reset_addr] == 1

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Operations should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(auto_reset_addr)

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(auto_reset_addr, 1)

        # Cache should remain in last known state
        assert regmap._regs_cache[auto_reset_addr] == 1

        # Restore connection
        mock_interface.restore_connection()

        # Should be able to continue operations
        value = regmap.read_reg(auto_reset_addr)
        assert value == 0  # Auto-reset should have occurred

    def test_auto_reset_with_partial_failures(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset behavior with partial failures."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA

        # Setup for partial failure
        mock_interface.simulate_partial_write_failure(fail_after=1)

        test_data = {
            auto_reset_addr: 1,
            normal_addr: 80,
        }

        # Attempt batch write that will partially fail
        try:
            regmap.write_regs(test_data)
        except SenxorNotConnectedError:
            pass  # Expected

        # Check partial success
        successful_writes = len(mock_interface.write_calls)
        assert successful_writes == 1

        # Auto-reset behavior should still work for successful writes
        if (auto_reset_addr, 1) in mock_interface.write_calls:
            assert mock_interface.get_register_value(auto_reset_addr) == 0

    def test_auto_reset_recovery_scenarios(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset recovery scenarios."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]

        # Normal operation
        regmap.write_reg(auto_reset_addr, 1)
        assert regmap._regs_cache[auto_reset_addr] == 1

        # Simulate error
        mock_interface.simulate_connection_loss()

        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(auto_reset_addr)

        # Restore connection
        mock_interface.restore_connection()

        # Recovery should work normally
        value = regmap.read_reg(auto_reset_addr)
        assert value == 0  # Auto-reset
        assert regmap._regs_cache[auto_reset_addr] == 0

    def test_auto_reset_error_consistency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset error consistency."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]

        # Setup state
        regmap.write_reg(auto_reset_addr, 1)

        # Simulate error during read
        mock_interface.simulate_connection_loss()

        # Error should be consistent across access methods
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(auto_reset_addr)

        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.read_reg(auto_reset_addr)

        # Cache should remain consistent
        assert regmap._regs_cache[auto_reset_addr] == 1

        # Restore and verify consistency
        mock_interface.restore_connection()

        # All access methods should work consistently
        value1 = regmap.read_reg(auto_reset_addr)
        mock_interface.set_register_value(auto_reset_addr, 1)
        value2 = regmap.regs.read_reg(auto_reset_addr)

        assert value1 == 0
        assert value2 == 1


class TestAutoResetComplexScenarios:
    """Test complex auto-reset scenarios."""

    def test_auto_reset_sequence_validation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset sequence validation."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]

        # Complex sequence
        regmap.write_reg(auto_reset_addr, 1)  # Write
        value1 = regmap.read_reg(auto_reset_addr)  # Read (should be 0)
        regmap.write_reg(auto_reset_addr, 1)  # Write again
        value2 = regmap.regs.get_reg(auto_reset_addr)  # Always reads hardware for auto-reset
        value3 = regmap.read_reg(auto_reset_addr)  # Hardware read

        assert value1 == 0  # Auto-reset after first write
        assert value2 == 0  # Auto-reset register always bypasses cache in get_reg
        assert value3 == 0  # Auto-reset after second write

    def test_get_reg_cache_behavior_comparison(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test get_reg cache behavior difference between auto-reset and normal registers."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA  # EMISSIVITY (normal register)

        # Setup initial values
        regmap.write_reg(auto_reset_addr, 1)  # Will auto-reset to 0
        regmap.write_reg(normal_addr, 80)  # Will stay 80

        # Clear call history to track hardware calls
        mock_interface.reset_call_history()

        # Call get_reg on both registers
        auto_value = regmap.regs.get_reg(auto_reset_addr)  # Should read hardware (bypass cache)
        normal_value = regmap.regs.get_reg(normal_addr)  # Should use cache

        # Verify values
        assert auto_value == 0  # Auto-reset value
        assert normal_value == 80  # Cached value

        # Verify hardware call behavior
        # Auto-reset register should have triggered a hardware read
        assert auto_reset_addr in mock_interface.read_calls
        # Normal register should NOT have triggered a hardware read (uses cache)
        assert normal_addr not in mock_interface.read_calls

    def test_auto_reset_field_register_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset synchronization between fields and registers."""
        # Find auto-reset field and its register
        auto_reset_field = None
        auto_reset_addr = None

        for field_name, field_def in regmap.fields.__field_defs__.items():
            if field_def.auto_reset and field_def.writable:
                auto_reset_field = field_name
                auto_reset_addr = next(iter(field_def.addr_map.keys()))
                break

        if auto_reset_field and auto_reset_addr:
            # Write through field
            regmap.fields.set_field(auto_reset_field, 1)

            # Register cache should be updated
            assert regmap._regs_cache[auto_reset_addr] == 1

            # Read through register
            reg_value = regmap.read_reg(auto_reset_addr)
            assert reg_value == 0  # Auto-reset

            # Field cache should be updated
            field_value = regmap.fields.get_field(auto_reset_field)
            assert field_value == 0

    def test_auto_reset_performance_impact(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test performance impact of auto-reset behavior."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]
        normal_addr = 0xCA

        # Setup values
        mock_interface.set_register_value(auto_reset_addr, 1)
        mock_interface.set_register_value(normal_addr, 80)

        # Multiple reads of auto-reset register
        mock_interface.reset_call_history()
        for _ in range(10):
            regmap.read_reg(auto_reset_addr)

        auto_reset_calls = len(mock_interface.read_calls)

        # Multiple reads of normal register
        mock_interface.reset_call_history()
        for _ in range(10):
            regmap.regs.get_reg(normal_addr)

        normal_calls = len(mock_interface.read_calls)

        # Auto-reset should make more hardware calls (no caching)
        assert auto_reset_calls > normal_calls

    def test_auto_reset_state_machine(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset state machine behavior."""
        auto_reset_addr = TestDataGenerator.AUTO_RESET_ADDRESSES[0]

        # State transitions
        states = []

        # Initial state
        states.append(mock_interface.get_register_value(auto_reset_addr))

        # Write -> Auto-reset
        regmap.write_reg(auto_reset_addr, 1)
        states.append(mock_interface.get_register_value(auto_reset_addr))

        # Read -> Auto-reset
        mock_interface.set_register_value(auto_reset_addr, 1)
        regmap.read_reg(auto_reset_addr)
        states.append(mock_interface.get_register_value(auto_reset_addr))

        # Expected state sequence
        expected_states = [0, 0, 0]  # Always auto-reset to 0
        assert states == expected_states


class TestAutoResetDocumentation:
    """Test auto-reset documentation and metadata."""

    def test_auto_reset_metadata_completeness(self, regmap: _RegMap) -> None:
        """Test completeness of auto-reset metadata."""
        # All auto-reset registers should have complete metadata
        for reg_name in regmap.regs.__auto_reset_list__:
            reg_def = regmap.regs.__reg_defs__[reg_name]

            # Should have all required attributes
            assert hasattr(reg_def, "auto_reset")
            assert hasattr(reg_def, "addr")
            assert hasattr(reg_def, "readable")
            assert hasattr(reg_def, "writable")
            assert hasattr(reg_def, "desc")

            # Auto-reset should be True
            assert reg_def.auto_reset is True

    def test_auto_reset_behavior_consistency(self, regmap: _RegMap) -> None:
        """Test consistency of auto-reset behavior documentation."""
        # Auto-reset behavior should be consistent across all instances
        for reg_name in regmap.regs.__auto_reset_list__:
            reg_instance = regmap.regs[reg_name]
            reg_def = regmap.regs.__reg_defs__[reg_name]

            # Instance and definition should agree
            assert reg_instance.auto_reset == reg_def.auto_reset
            assert reg_instance.auto_reset is True

        # Same for fields
        for field_name, field_def in regmap.fields.__field_defs__.items():
            field_instance = regmap.fields[field_name]

            # Instance and definition should agree
            assert field_instance.auto_reset == field_def.auto_reset
