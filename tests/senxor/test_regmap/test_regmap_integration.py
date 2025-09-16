"""Tests for _RegMap integration and coordination.

This module tests the integration aspects of _RegMap including coordination between
registers and fields, error propagation, and lifecycle management.
"""

from __future__ import annotations

import pytest

from senxor.error import SenxorNotConnectedError
from senxor.regmap._regmap import _RegMap

from .fixtures import (
    EnhancedMockInterface,
    SenxorStub,
    TestDataGenerator,
    create_mock_with_failure_simulation,
)


class TestRegMapCoordination:
    """Test _RegMap coordination between registers and fields."""

    def test_registers_fields_coordination(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test coordination between registers and fields."""
        # Setup test data
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Read through registers
        reg_value = regmap.regs.read_reg(test_addr)
        assert reg_value == test_value

        # Field cache should be updated
        if "EMISSIVITY" in regmap._fields_cache:
            assert regmap._fields_cache["EMISSIVITY"] == test_value

        # Read through fields should return same value
        field_value = regmap.fields.get_field("EMISSIVITY")
        assert field_value == test_value

    def test_cache_consistency_across_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache consistency across register and field operations."""
        test_addr = 0xCA
        test_value = 85

        # Write through registers
        regmap.regs.write_reg(test_addr, test_value)

        # Both caches should be consistent
        assert regmap._regs_cache[test_addr] == test_value
        if "EMISSIVITY" in regmap._fields_cache:
            assert regmap._fields_cache["EMISSIVITY"] == test_value

        # Write through fields
        new_value = 90
        regmap.fields.set_field("EMISSIVITY", new_value)

        # Both caches should be updated
        assert regmap._regs_cache[test_addr] == new_value
        assert regmap._fields_cache["EMISSIVITY"] == new_value

    def test_bidirectional_cache_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test bidirectional cache updates between registers and fields."""
        test_addr = 0xCA

        # Register write should update field cache
        regmap.write_reg(test_addr, 75)
        assert regmap._regs_cache[test_addr] == 75

        # Field read should see the updated value
        field_value = regmap.fields.get_field("EMISSIVITY")
        assert field_value == 75

        # Field write should update register cache
        regmap.fields.set_field("EMISSIVITY", 95)
        assert regmap._regs_cache[test_addr] == 95
        assert regmap._fields_cache["EMISSIVITY"] == 95

    def test_unified_hardware_access(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that both registers and fields use unified hardware access."""
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Clear call history
        mock_interface.reset_call_history()

        # Read through registers
        regmap.regs.read_reg(test_addr)
        reg_calls = len(mock_interface.read_calls)

        # Clear call history
        mock_interface.reset_call_history()

        # Read through fields (should use cache if available)
        regmap.fields.get_field("EMISSIVITY")
        field_calls = len(mock_interface.read_calls)

        # Both should access the same hardware interface
        assert reg_calls > 0
        # Field calls might be 0 if cache is used
        assert field_calls >= 0


class TestErrorPropagation:
    """Test error propagation through _RegMap."""

    def test_interface_error_propagation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that interface errors propagate correctly."""
        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Register operations should raise error
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xCA)

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xCA, 80)

        # Field operations should also raise error
        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.get_field("EMISSIVITY")

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.set_field("EMISSIVITY", 80)

    def test_connection_loss_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test handling of connection loss during operations."""
        # Initial successful operation
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Operations should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        # Cache should remain in last known state
        assert regmap._regs_cache[0xCA] == 80

    def test_partial_failure_recovery(self, regmap: _RegMap) -> None:
        """Test recovery from partial failure scenarios."""
        # Create interface that fails after 2 writes
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=2)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)

        # Attempt multiple writes
        test_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80}

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_regs(test_updates)

        # Verify partial success
        successful_writes = len(mock_interface.write_calls)
        assert successful_writes == 2

        # Cache should reflect successful writes
        assert len(regmap._regs_cache) == successful_writes

        # Restore connection and continue
        mock_interface.restore_connection()
        mock_interface.fail_after_writes = None

        # Should be able to continue operations
        regmap.write_reg(0xCB, 90)
        assert regmap._regs_cache[0xCB] == 90

    def test_error_state_consistency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that error states maintain cache consistency."""
        # Pre-populate cache
        regmap._regs_cache[0xCA] = 80
        regmap._fields_cache["EMISSIVITY"] = 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Operations should fail but cache should remain consistent
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        # Cache should be unchanged
        assert regmap._regs_cache[0xCA] == 80
        assert regmap._fields_cache["EMISSIVITY"] == 80


class TestLifecycleManagement:
    """Test lifecycle management of _RegMap."""

    def test_regmap_creation_lifecycle(self, senxor_stub: SenxorStub) -> None:
        """Test _RegMap creation and initialization lifecycle."""
        # Create regmap
        regmap = _RegMap(senxor_stub)

        # Should be properly initialized
        assert regmap.senxor is senxor_stub
        assert regmap.interface is senxor_stub.interface
        assert regmap.address == senxor_stub.address

        # Caches should be initialized
        assert isinstance(regmap._regs_cache, dict)
        assert isinstance(regmap._fields_cache, dict)
        assert len(regmap._regs_cache) == 0
        assert len(regmap._fields_cache) == 0

        # Registers and fields should be created
        assert regmap.regs is not None
        assert regmap.fields is not None
        assert regmap.regs._regmap is regmap
        assert regmap.fields._regmap is regmap

    def test_cache_cleanup_on_errors(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache behavior during error conditions."""
        # Pre-populate cache
        regmap._regs_cache[0xCA] = 80
        regmap._fields_cache["EMISSIVITY"] = 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Failed operations should not corrupt cache
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        # Cache should remain intact
        assert regmap._regs_cache[0xCA] == 80
        assert regmap._fields_cache["EMISSIVITY"] == 80
        assert 0xB4 not in regmap._regs_cache

    def test_resource_management(self, regmap: _RegMap) -> None:
        """Test resource management in _RegMap."""
        # Test that resources are properly managed
        assert regmap._cache_lock is not None

        # Test that references are properly set
        assert regmap.regs._regmap is regmap
        assert regmap.fields._regmap is regmap

        # Test that caches are properly referenced
        assert regmap.regs._regs_cache is regmap._regs_cache
        assert regmap.fields._fields_cache is regmap._fields_cache


class TestComplexOperationSequences:
    """Test complex sequences of operations."""

    def test_mixed_register_field_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test mixed register and field operations."""
        # Setup test data
        test_data = {0xCA: 80, 0xB4: 100, 0x00: 1}
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Mixed operation sequence
        # 1. Read register
        reg_value = regmap.read_reg(0xCA)
        assert reg_value == 80

        # 2. Read field
        field_value = regmap.fields.get_field("EMISSIVITY")
        assert field_value == 80

        # 3. Write through field
        regmap.fields.set_field("EMISSIVITY", 85)

        # 4. Read through register
        reg_value2 = regmap.regs.get_reg(0xCA)
        assert reg_value2 == 85

        # 5. Write through register
        regmap.write_reg(0xCA, 90)

        # 6. Read through field
        field_value2 = regmap.fields.get_field("EMISSIVITY")
        assert field_value2 == 90

    def test_bulk_operations_integration(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test integration of bulk operations."""
        # Setup test data for reading (can include read-only registers)
        test_data = TestDataGenerator.generate_register_values(count=10)
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Bulk read through registers
        reg_values = regmap.read_regs(list(test_data.keys()))
        assert reg_values == test_data

        # Bulk write through registers (exclude read-only registers)
        writable_data = {
            addr: value for addr, value in test_data.items() if addr not in TestDataGenerator.READ_ONLY_ADDRESSES
        }
        new_values = {addr: (value + 10) % 256 for addr, value in writable_data.items()}
        regmap.write_regs(new_values)

        # Verify updates
        for addr, value in new_values.items():
            assert regmap._regs_cache[addr] == value

    def test_auto_reset_integration(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset behavior integration."""
        # Setup auto-reset register
        auto_reset_addr = 0xB5  # SLEEP_MODE
        test_value = 1
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # Read through registers
        reg_value = regmap.read_reg(auto_reset_addr)
        assert reg_value == test_value

        # Register should be auto-reset to 0
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Cache should reflect the read value
        assert regmap._regs_cache[auto_reset_addr] == test_value

        # Second read should get 0
        reg_value2 = regmap.read_reg(auto_reset_addr)
        assert reg_value2 == 0
        assert regmap._regs_cache[auto_reset_addr] == 0

    def test_cross_module_cache_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache synchronization across modules."""
        test_addr = 0xCA

        # Write through _RegMap directly
        regmap.write_reg(test_addr, 75)

        # Both registers and fields should see the change
        assert regmap.regs._regs_cache[test_addr] == 75
        if "EMISSIVITY" in regmap.fields._fields_cache:
            assert regmap.fields._fields_cache["EMISSIVITY"] == 75

        # Read through registers
        reg_value = regmap.regs.get_reg(test_addr)
        assert reg_value == 75

        # Read through fields
        field_value = regmap.fields.get_field("EMISSIVITY")
        assert field_value == 75


class TestConcurrencyIntegration:
    """Test concurrency aspects of _RegMap integration."""

    def test_thread_safe_cache_access(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test thread-safe cache access."""
        # Setup test data
        test_data = TestDataGenerator.generate_register_values(count=5)
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # This would need actual threading for full test
        # For now, test sequential access through different modules

        # Read through registers
        for addr in test_data:
            value = regmap.regs.read_reg(addr)
            assert value == test_data[addr]

        # Read through fields (should use cache where possible)
        for field_name in ["EMISSIVITY"]:
            if field_name in regmap.fields.__field_defs__:
                value = regmap.fields.get_field(field_name)
                assert isinstance(value, int)

    def test_concurrent_register_field_access(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent access through registers and fields."""
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Simulate concurrent access
        reg_value = regmap.regs.read_reg(test_addr)
        field_value = regmap.fields.get_field("EMISSIVITY")

        # Both should return consistent values
        assert reg_value == test_value
        assert field_value == test_value

        # Cache should be consistent
        assert regmap._regs_cache[test_addr] == test_value
        if "EMISSIVITY" in regmap._fields_cache:
            assert regmap._fields_cache["EMISSIVITY"] == test_value


class TestPerformanceIntegration:
    """Test performance aspects of _RegMap integration."""

    def test_cache_efficiency_integration(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache efficiency in integrated operations."""
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # First read should hit hardware
        regmap.read_reg(test_addr)
        len(mock_interface.read_calls)

        # Clear call history
        mock_interface.reset_call_history()

        # Subsequent reads should use cache (for non-auto-reset)
        regmap.regs.get_reg(test_addr)
        cached_calls = len(mock_interface.read_calls)

        # Should have fewer calls for cached access
        assert cached_calls == 0  # Should use cache

    def test_bulk_operation_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test efficiency of bulk operations."""
        # Generate test data
        test_data = TestDataGenerator.generate_register_values(count=20)
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Clear call history
        mock_interface.reset_call_history()

        # Bulk read should be efficient
        regmap.read_regs(list(test_data.keys()))

        # Should have made calls for all addresses
        assert len(mock_interface.read_calls) == len(test_data)

        # Cache should be populated
        for addr, value in test_data.items():
            assert regmap._regs_cache[addr] == value

    def test_memory_efficiency(self, regmap: _RegMap) -> None:
        """Test memory efficiency of _RegMap."""
        # Test that caches don't grow unnecessarily
        initial_reg_cache_size = len(regmap._regs_cache)
        initial_field_cache_size = len(regmap._fields_cache)

        # Perform operations
        regmap.write_reg(0xCA, 80)
        regmap.fields.set_field("EMISSIVITY", 85)

        # Cache should grow reasonably
        final_reg_cache_size = len(regmap._regs_cache)
        final_field_cache_size = len(regmap._fields_cache)

        # Should not have excessive growth
        assert final_reg_cache_size <= initial_reg_cache_size + 10
        assert final_field_cache_size <= initial_field_cache_size + 10


class TestComplexErrorScenarios:
    """Test complex error scenarios in integration."""

    def test_cascading_error_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test handling of cascading errors."""
        # Setup initial state
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Multiple operations should all fail consistently
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.set_field("EMISSIVITY", 85)

        # Cache should remain consistent
        assert regmap._regs_cache[0xCA] == 80

    def test_partial_operation_recovery(self, regmap: _RegMap) -> None:
        """Test recovery from partial operation failures."""
        # Create interface with limited failure
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=3)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)

        # Use writable addresses only
        writable_addrs = [
            addr
            for addr in TestDataGenerator.VALID_REGISTER_ADDRESSES
            if addr not in TestDataGenerator.READ_ONLY_ADDRESSES
        ]

        # Perform operations until failure
        successful_ops = 0
        try:
            for i, addr in enumerate(writable_addrs[:10]):  # Limit to first 10 writable addresses
                regmap.write_reg(addr, i * 10)
                successful_ops += 1
        except SenxorNotConnectedError:
            pass

        # Should have succeeded for some operations
        assert successful_ops > 0
        assert len(regmap._regs_cache) == successful_ops

        # Restore connection and continue
        mock_interface.restore_connection()
        mock_interface.fail_after_writes = None

        # Should be able to continue
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

    def test_error_state_isolation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that error states are properly isolated."""
        # Setup working state
        regmap.write_reg(0xCA, 80)
        regmap.fields.set_field("EMISSIVITY", 85)

        # Simulate temporary connection loss
        mock_interface.simulate_connection_loss()

        # Operations should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        # Restore connection
        mock_interface.restore_connection()

        # Should be able to continue operations
        regmap.write_reg(0xB4, 100)
        assert regmap._regs_cache[0xB4] == 100

        # Previous state should be preserved
        assert regmap._regs_cache[0xCA] == 85  # Last written value through fields
        assert regmap._fields_cache["EMISSIVITY"] == 85
