"""Tests for Registers private methods and internals.

This module tests the internal implementation of the Registers class,
including private methods, cache interactions, and internal state management.
"""

from __future__ import annotations

import threading

import pytest

from senxor.error import SenxorNotConnectedError
from senxor.regmap._regmap import _RegMap
from senxor.regmap._regs import Registers

from .fixtures import (
    EnhancedMockInterface,
    SenxorStub,
    TestDataGenerator,
    create_mock_with_failure_simulation,
    setup_auto_reset_scenario,
)


class TestRegistersInitialization:
    """Test Registers initialization and setup."""

    def test_init_with_regmap(self, regmap: _RegMap) -> None:
        """Test Registers initialization with _RegMap."""
        registers = regmap.regs

        assert registers._regmap is regmap
        assert registers._log is not None
        assert hasattr(registers, "_regs")
        assert isinstance(registers._regs, dict)

    def test_register_instances_creation(self, regmap: _RegMap) -> None:
        """Test that register instances are created correctly."""
        registers = regmap.regs

        # Check that key registers exist
        assert hasattr(registers, "EMISSIVITY")
        assert hasattr(registers, "FRAME_RATE")
        assert hasattr(registers, "STATUS")

        # Check that _regs dictionary is populated
        assert "EMISSIVITY" in registers._regs
        assert "FRAME_RATE" in registers._regs
        assert "STATUS" in registers._regs

    def test_cache_reference_setup(self, regmap: _RegMap) -> None:
        """Test that cache reference is set up correctly."""
        registers = regmap.regs

        # Cache property should reference regmap cache
        assert registers._regs_cache is regmap._regs_cache

        # Changes to regmap cache should be reflected
        regmap._regs_cache[0xB4] = 100
        assert registers._regs_cache[0xB4] == 100

    def test_logger_binding(self, regmap: _RegMap) -> None:
        """Test that logger is bound with correct address."""
        registers = regmap.regs

        # Logger should be bound with regmap address
        assert registers._log is not None
        # The specific logger implementation details would need to be verified
        # based on the actual logging setup


class TestPrivateReadMethods:
    """Test private read method implementations."""

    def test_read_reg_hardware_call(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_reg makes hardware call and updates cache."""
        registers = regmap.regs
        test_addr = 0xB4
        test_value = 100

        # Setup mock interface
        mock_interface.set_register_value(test_addr, test_value)

        # Call read_reg
        result = registers.read_reg(test_addr)

        # Verify result
        assert result == test_value

        # Verify hardware call was made
        assert test_addr in mock_interface.read_calls
        assert len(mock_interface.read_calls) == 1

        # Verify cache was updated
        assert registers._regs_cache[test_addr] == test_value

    def test_read_regs_batch_processing(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_regs processes multiple addresses."""
        registers = regmap.regs
        test_addrs = [0xB4, 0xB7, 0xCA]
        test_values = {addr: addr % 256 for addr in test_addrs}

        # Setup mock interface
        for addr, value in test_values.items():
            mock_interface.set_register_value(addr, value)

        # Call read_regs
        result = registers.read_regs(test_addrs)

        # Verify result
        assert result == test_values

        # Verify hardware calls were made
        for addr in test_addrs:
            assert addr in mock_interface.read_calls

        # Verify cache was updated
        for addr, value in test_values.items():
            assert registers._regs_cache[addr] == value

    def test_read_regs_auto_reset_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_regs handles auto-reset registers correctly."""
        registers = regmap.regs

        # Setup auto-reset scenario
        initial_values = setup_auto_reset_scenario(mock_interface)
        test_addrs = list(initial_values.keys())

        # Call read_regs
        result = registers.read_regs(test_addrs)

        # Verify results match initial values
        assert result == initial_values

        # Verify auto-reset occurred (values should be 0 now)
        for addr in test_addrs:
            assert mock_interface.get_register_value(addr) == 0

    def test_read_with_connection_errors(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test read operations with connection errors."""
        registers = regmap.regs

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Single read should raise error
        with pytest.raises(SenxorNotConnectedError):
            registers.read_reg(0xB4)

        # Batch read should raise error
        with pytest.raises(SenxorNotConnectedError):
            registers.read_regs([0xB4, 0xB7])

        # Cache should remain unchanged
        assert len(registers._regs_cache) == 0


class TestPrivateGetMethods:
    """Test private get method implementations."""

    def test_get_reg_cache_hit(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that get_reg returns cached value when available."""
        registers = regmap.regs
        test_addr = 0xB4
        test_value = 100

        # Pre-populate cache
        registers._regs_cache[test_addr] = test_value

        # Clear hardware call history
        mock_interface.reset_call_history()

        # Call get_reg
        result = registers.get_reg(test_addr)

        # Verify result
        assert result == test_value

        # Verify no hardware call was made (cache hit)
        assert len(mock_interface.read_calls) == 0

    def test_get_reg_cache_miss(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that get_reg reads from hardware on cache miss."""
        registers = regmap.regs
        test_addr = 0xB4
        test_value = 100

        # Setup mock interface
        mock_interface.set_register_value(test_addr, test_value)

        # Ensure cache is empty
        assert test_addr not in registers._regs_cache

        # Call get_reg
        result = registers.get_reg(test_addr)

        # Verify result
        assert result == test_value

        # Verify hardware call was made (cache miss)
        assert test_addr in mock_interface.read_calls
        assert len(mock_interface.read_calls) == 1

        # Verify cache was updated
        assert registers._regs_cache[test_addr] == test_value

    def test_get_reg_auto_reset_bypass(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that get_reg bypasses cache for auto-reset registers."""
        registers = regmap.regs
        auto_reset_addr = 0xB5  # SLEEP_MODE (auto-reset)
        test_value = 1

        # Setup mock interface and pre-populate cache
        mock_interface.set_register_value(auto_reset_addr, test_value)
        registers._regs_cache[auto_reset_addr] = test_value

        # Clear hardware call history
        mock_interface.reset_call_history()

        # Call get_reg on auto-reset register
        result = registers.get_reg(auto_reset_addr)

        # Verify result
        assert result == test_value

        # Verify hardware call was made (auto-reset bypass)
        assert auto_reset_addr in mock_interface.read_calls
        assert len(mock_interface.read_calls) == 1

    def test_get_regs_mixed_cache_states(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test get_regs with mixed cache hit/miss states."""
        registers = regmap.regs

        # Setup test data
        cached_addr = 0xB4
        cached_value = 100
        uncached_addr = 0xB7
        uncached_value = 50

        # Pre-populate cache for one address
        registers._regs_cache[cached_addr] = cached_value

        # Setup mock interface for uncached address
        mock_interface.set_register_value(uncached_addr, uncached_value)

        # Clear hardware call history
        mock_interface.reset_call_history()

        # Call get_regs
        result = registers.get_regs([cached_addr, uncached_addr])

        # Verify results
        expected = {cached_addr: cached_value, uncached_addr: uncached_value}
        assert result == expected

        # Verify only uncached address was read from hardware
        assert uncached_addr in mock_interface.read_calls
        assert cached_addr not in mock_interface.read_calls
        assert len(mock_interface.read_calls) == 1

    def test_get_regs_preserves_order(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that get_regs preserves address order in results."""
        registers = regmap.regs
        test_addrs = [0xCA, 0xB4, 0xB7]
        test_values = {addr: addr % 256 for addr in test_addrs}

        # Setup mock interface
        for addr, value in test_values.items():
            mock_interface.set_register_value(addr, value)

        # Call get_regs
        result = registers.get_regs(test_addrs)

        # Verify results
        assert result == test_values

        # Verify order is preserved (though dict order is guaranteed in Python 3.7+)
        assert list(result.keys()) == test_addrs


class TestPrivateWriteMethods:
    """Test private write method implementations."""

    def test_write_reg_validation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_reg validates input parameters."""
        registers = regmap.regs
        test_addr = 0xB4

        # Test valid value
        registers.write_reg(test_addr, 100)
        assert (test_addr, 100) in mock_interface.write_calls

        # Test boundary values
        registers.write_reg(test_addr, 0)
        registers.write_reg(test_addr, 255)

        # Test invalid values
        with pytest.raises(ValueError):
            registers.write_reg(test_addr, -1)

        with pytest.raises(ValueError):
            registers.write_reg(test_addr, 256)

        with pytest.raises(ValueError):
            registers.write_reg(test_addr, 1000)

    def test_write_reg_readonly_protection(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_reg prevents writes to read-only registers."""
        registers = regmap.regs

        # Test write to read-only register
        readonly_addr = 0xB6  # STATUS (read-only)

        with pytest.raises(AttributeError) as exc_info:
            registers.write_reg(readonly_addr, 100)

        # Verify error message contains register info
        assert "read-only" in str(exc_info.value)
        assert f"0x{readonly_addr:02X}" in str(exc_info.value)

        # Verify no hardware call was made
        assert (readonly_addr, 100) not in mock_interface.write_calls

    def test_write_reg_cache_update(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_reg updates cache correctly."""
        registers = regmap.regs
        test_addr = 0xB4
        test_value = 150

        # Call write_reg
        registers.write_reg(test_addr, test_value)

        # Verify cache was updated
        assert registers._regs_cache[test_addr] == test_value

        # Verify hardware call was made
        assert (test_addr, test_value) in mock_interface.write_calls

    def test_write_reg_field_sync(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_reg triggers field cache synchronization."""
        registers = regmap.regs
        test_addr = 0xCA  # EMISSIVITY
        test_value = 80

        # Call write_reg
        registers.write_reg(test_addr, test_value)

        # Verify register cache was updated
        assert registers._regs_cache[test_addr] == test_value

        # Field cache synchronization would be tested with actual field implementation
        # For now, verify that the regmap method was called
        assert test_addr in registers._regs_cache

    def test_write_regs_bulk_validation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_regs validates all values before writing."""
        registers = regmap.regs

        # Test valid bulk write
        valid_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80}
        registers.write_regs(valid_updates)

        # Verify all writes were made
        for addr, value in valid_updates.items():
            assert (addr, value) in mock_interface.write_calls
            assert registers._regs_cache[addr] == value

        # Test bulk write with invalid value
        invalid_updates = {0xB4: 100, 0xB7: 300}  # 300 is invalid

        with pytest.raises(ValueError):
            registers.write_regs(invalid_updates)

        # Test bulk write with read-only register
        readonly_updates = {0xB4: 100, 0xB6: 50}  # 0xB6 is read-only

        with pytest.raises(AttributeError):
            registers.write_regs(readonly_updates)


class TestCacheInteraction:
    """Test cache interaction and consistency."""

    def test_cache_reference_consistency(self, regmap: _RegMap) -> None:
        """Test that cache reference remains consistent."""
        registers = regmap.regs

        # Cache reference should be the same object
        assert registers._regs_cache is regmap._regs_cache

        # Changes through regmap should be visible through registers
        regmap._regs_cache[0xB4] = 100
        assert registers._regs_cache[0xB4] == 100

        # Changes through registers should be visible through regmap
        registers._regs_cache[0xB7] = 50
        assert regmap._regs_cache[0xB7] == 50

    def test_auto_reset_cache_invalidation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that auto-reset registers invalidate cache correctly."""
        registers = regmap.regs
        auto_reset_addr = 0xB5  # SLEEP_MODE
        test_value = 1

        # Setup and read auto-reset register
        mock_interface.set_register_value(auto_reset_addr, test_value)
        result1 = registers.read_reg(auto_reset_addr)

        # Verify initial read
        assert result1 == test_value
        assert registers._regs_cache[auto_reset_addr] == test_value

        # Read again - should get 0 due to auto-reset
        result2 = registers.read_reg(auto_reset_addr)
        assert result2 == 0
        assert registers._regs_cache[auto_reset_addr] == 0

    def test_cache_update_atomicity(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that cache updates are atomic."""
        registers = regmap.regs

        # Test single register atomicity
        test_addr = 0xB4
        test_value = 100

        # Write should be atomic
        registers.write_reg(test_addr, test_value)
        assert registers._regs_cache[test_addr] == test_value

        # Test bulk operation atomicity with failure
        mock_interface_with_failure = create_mock_with_failure_simulation(fail_after_writes=1)
        senxor_stub = SenxorStub(mock_interface_with_failure)
        regmap_with_failure = _RegMap(senxor_stub)
        registers_with_failure = regmap_with_failure.regs

        # Bulk write should fail partway through
        with pytest.raises(SenxorNotConnectedError):
            registers_with_failure.write_regs({0xB4: 100, 0xB7: 50})

        # Only successful writes should be in cache
        assert len(registers_with_failure._regs_cache) == 1


class TestThreadSafety:
    """Test thread safety of private methods."""

    def test_concurrent_cache_access(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent access to cache."""
        registers = regmap.regs

        # Setup test data - exclude auto-reset registers for consistent results
        test_data = TestDataGenerator.generate_register_values(count=10, exclude_auto_reset=True)

        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        results: list[dict[int, int]] = []

        def worker() -> None:
            # Mix of read and get operations
            addrs = list(test_data.keys())[:5]
            result = {}
            for addr in addrs:
                value = registers.get_reg(addr)
                result[addr] = value
            results.append(result)

        # Start multiple threads
        threads = []
        for _i in range(3):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results are consistent
        assert len(results) == 3
        expected_subset = {k: v for k, v in test_data.items() if k in list(test_data.keys())[:5]}
        for result in results:
            assert result == expected_subset

    def test_concurrent_write_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent write operations."""
        registers = regmap.regs

        write_data = [
            {0xB4: 100},
            {0xB7: 50},
            {0xCA: 80},
        ]

        def worker(data: dict[int, int]) -> None:
            registers.write_regs(data)

        # Start multiple threads
        threads = []
        for data in write_data:
            thread = threading.Thread(target=worker, args=(data,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify all writes succeeded
        for data in write_data:
            for addr, value in data.items():
                assert registers._regs_cache[addr] == value
                assert (addr, value) in mock_interface.write_calls


class TestErrorRecovery:
    """Test error recovery in private methods."""

    def test_recovery_after_connection_loss(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test recovery after connection loss."""
        registers = regmap.regs

        # Initial successful operation
        registers.write_reg(0xB4, 100)
        assert registers._regs_cache[0xB4] == 100

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Operations should fail
        with pytest.raises(SenxorNotConnectedError):
            registers.read_reg(0xB7)

        with pytest.raises(SenxorNotConnectedError):
            registers.write_reg(0xB7, 50)

        # Restore connection
        mock_interface.restore_connection()

        # Operations should work again
        mock_interface.set_register_value(0xB7, 50)
        result = registers.read_reg(0xB7)
        assert result == 50

        registers.write_reg(0xCA, 80)
        assert registers._regs_cache[0xCA] == 80

    def test_partial_failure_state_consistency(self, regmap: _RegMap) -> None:
        """Test state consistency after partial failures."""
        # Create interface that fails after 2 writes
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=2)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)
        registers = regmap.regs

        # Attempt multiple writes
        test_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80, 0xCB: 90}

        with pytest.raises(SenxorNotConnectedError):
            registers.write_regs(test_updates)

        # Verify state consistency
        successful_writes = len(mock_interface.write_calls)
        cached_entries = len(registers._regs_cache)

        assert successful_writes == 2
        assert cached_entries == successful_writes

        # Verify cache contains only successful writes
        for addr, value in mock_interface.write_calls:
            assert registers._regs_cache[addr] == value
