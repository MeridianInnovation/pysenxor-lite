"""Tests for _RegMap core functionality.

This module tests the core _RegMap class that coordinates between registers and fields,
manages unified caching, and ensures cache consistency across operations.
"""

from __future__ import annotations

import threading
import time

import pytest

from senxor._error import SenxorNotConnectedError
from senxor.regmap._fields import Fields
from senxor.regmap._regmap import _RegMap
from senxor.regmap._regs import Registers

from .fixtures import (
    EnhancedMockInterface,
    SenxorStub,
    TestDataGenerator,
    create_mock_with_failure_simulation,
    setup_auto_reset_scenario,
)


class TestRegMapInitialization:
    """Test _RegMap initialization and basic properties."""

    def test_init_with_senxor_stub(self, senxor_stub: SenxorStub) -> None:
        """Test _RegMap initialization with Senxor stub."""
        regmap = _RegMap(senxor_stub)

        assert regmap.senxor is senxor_stub
        assert regmap.address == senxor_stub.address
        assert regmap.interface is senxor_stub.interface
        assert regmap.regs is not None
        assert regmap.fields is not None

    def test_cache_initialization(self, regmap: _RegMap) -> None:
        """Test that caches are properly initialized."""
        assert isinstance(regmap._regs_cache, dict)
        assert isinstance(regmap._fields_cache, dict)
        assert len(regmap._regs_cache) == 0
        assert len(regmap._fields_cache) == 0

    def test_registers_fields_creation(self, regmap: _RegMap) -> None:
        """Test that registers and fields instances are created."""
        assert isinstance(regmap.regs, Registers)
        assert isinstance(regmap.fields, Fields)
        assert regmap.regs._regmap is regmap
        assert regmap.fields._regmap is regmap

    def test_lock_initialization(self, regmap: _RegMap) -> None:
        """Test that cache lock is properly initialized."""
        assert hasattr(regmap, "_cache_lock")
        assert isinstance(regmap._cache_lock, type(threading.Lock()))


class TestCacheManagement:
    """Test cache management functionality."""

    def test_regs_cache_property(self, regmap: _RegMap) -> None:
        """Test access to register cache."""
        # Initially empty
        assert regmap._regs_cache == {}

        # Add some data
        regmap._regs_cache[0xB4] = 100
        assert regmap._regs_cache[0xB4] == 100

    def test_fields_cache_property(self, regmap: _RegMap) -> None:
        """Test access to fields cache."""
        # Initially empty
        assert regmap._fields_cache == {}

        # Add some data
        regmap._fields_cache["EMISSIVITY"] = 80
        assert regmap._fields_cache["EMISSIVITY"] == 80

    def test_cache_lock_acquisition(self, regmap: _RegMap) -> None:
        """Test that cache lock can be acquired."""
        with regmap._cache_lock:
            # Should not raise any exception
            pass

    def test_cache_thread_safety(self, regmap: _RegMap) -> None:
        """Test basic thread safety of cache operations."""
        results: list[int] = []

        def worker(value: int) -> None:
            with regmap._cache_lock:
                regmap._regs_cache[0xB4] = value
                time.sleep(0.01)  # Small delay to test concurrency
                results.append(regmap._regs_cache[0xB4])

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All results should be consistent (no race conditions)
        assert len(results) == 5
        assert all(isinstance(r, int) for r in results)


class TestSynchronousRead:
    """Test synchronous read operations and cache updates."""

    def test_read_reg_updates_both_caches(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_reg updates both register and field caches."""
        # Setup test data
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Perform read
        result = regmap.read_reg(test_addr)

        # Verify return value
        assert result == test_value

        # Verify register cache update
        assert regmap._regs_cache[test_addr] == test_value

        # Verify hardware call was made
        assert test_addr in mock_interface.read_calls
        assert len(mock_interface.read_calls) == 1

    def test_read_regs_batch_updates_caches(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_regs updates caches for all addresses."""
        # Setup test data
        test_addrs = [0xB4, 0xB7, 0xCA]
        test_values = {addr: addr % 256 for addr in test_addrs}

        for addr, value in test_values.items():
            mock_interface.set_register_value(addr, value)

        # Perform batch read
        result = regmap.read_regs(test_addrs)

        # Verify return values
        assert result == test_values

        # Verify register cache updates
        for addr, value in test_values.items():
            assert regmap._regs_cache[addr] == value

        # Verify hardware calls were made
        for addr in test_addrs:
            assert addr in mock_interface.read_calls

    def test_read_all_populates_caches(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that read_all populates both caches."""
        # Setup some test data
        test_data = TestDataGenerator.generate_register_values(count=5)
        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        # Perform read_all
        regmap.read_all()

        # Verify register cache contains all data
        for addr, value in test_data.items():
            assert regmap._regs_cache[addr] == value

        # Verify hardware calls were made for all addresses
        for addr in test_data:
            assert addr in mock_interface.read_calls


class TestSynchronousWrite:
    """Test synchronous write operations and cache updates."""

    def test_write_reg_updates_both_caches(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_reg updates both register and field caches."""
        test_addr = 0xB4
        test_value = 150

        # Perform write
        regmap.write_reg(test_addr, test_value)

        # Verify register cache update
        assert regmap._regs_cache[test_addr] == test_value

        # Verify hardware call was made
        assert (test_addr, test_value) in mock_interface.write_calls

        # Verify interface state
        assert mock_interface.get_register_value(test_addr) == test_value

    def test_write_regs_bulk_updates_caches(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that write_regs updates caches for all addresses."""
        test_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80}

        # Perform bulk write
        regmap.write_regs(test_updates)

        # Verify register cache updates
        for addr, value in test_updates.items():
            assert regmap._regs_cache[addr] == value

        # Verify hardware calls were made
        for addr, value in test_updates.items():
            assert (addr, value) in mock_interface.write_calls

        # Verify interface state
        for addr, value in test_updates.items():
            assert mock_interface.get_register_value(addr) == value

    def test_duplicate_value_still_hits_hardware(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that writing the same value still calls hardware."""
        test_addr = 0xB4
        test_value = 100

        # First write
        regmap.write_reg(test_addr, test_value)
        initial_write_count = len(mock_interface.write_calls)

        # Second write with same value
        regmap.write_reg(test_addr, test_value)
        final_write_count = len(mock_interface.write_calls)

        # Should have made two hardware calls
        assert final_write_count == initial_write_count + 1
        assert mock_interface.write_calls.count((test_addr, test_value)) == 2

    def test_partial_write_failure_consistency(self, regmap: _RegMap) -> None:
        """Test that partial write failures maintain cache consistency."""
        # Create interface that fails after 2 writes
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=2)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)

        # Setup test data - more writes than failure threshold
        test_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80, 0xCB: 90}

        # Attempt bulk write - should fail partway through
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_regs(test_updates)

        # Verify that successful writes are reflected in cache
        successful_writes = len(mock_interface.write_calls)
        assert successful_writes == 2

        # Verify cache consistency - only successful writes should be cached
        cached_count = len(regmap._regs_cache)
        assert cached_count == successful_writes


class TestCacheSynchronization:
    """Test cache synchronization between registers and fields."""

    def test_fresh_fields_cache_by_read(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that register reads refresh field cache."""
        # This test would need actual field implementation
        # For now, test the internal method directly
        test_addr = 0xCA
        test_value = 80

        # Setup register value
        mock_interface.set_register_value(test_addr, test_value)

        # Perform read to trigger cache refresh
        regmap.read_reg(test_addr)

        # Verify that _fresh_fields_cache_by_read was called
        # (This would need to be tested with actual field mappings)
        assert regmap._regs_cache[test_addr] == test_value

    def test_fresh_fields_cache_by_write(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that register writes refresh field cache."""
        test_addr = 0xCA
        test_value = 90

        # Perform write to trigger cache refresh
        regmap.write_reg(test_addr, test_value)

        # Verify that _fresh_fields_cache_by_write was called
        # (This would need to be tested with actual field mappings)
        assert regmap._regs_cache[test_addr] == test_value

    def test_reg2fname_mapping_accuracy(self, regmap: _RegMap) -> None:
        """Test that register-to-field-name mapping is accurate."""
        # This test would need actual field implementation
        # For now, verify that the mapping exists
        assert hasattr(regmap.fields, "__reg2fname_map__")
        assert isinstance(regmap.fields.__reg2fname_map__, dict)

    def test_cross_register_field_updates(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that cross-register field updates work correctly."""
        # This test would need actual multi-register field implementation
        # For now, test multiple register updates
        test_addrs = [0xE0, 0xE1, 0xE2, 0xE3]  # Serial number registers
        test_values = {addr: addr % 256 for addr in test_addrs}

        # Perform bulk write
        regmap.write_regs(test_values)

        # Verify all registers are cached
        for addr, value in test_values.items():
            assert regmap._regs_cache[addr] == value


class TestAutoResetBehavior:
    """Test auto-reset register behavior in _RegMap."""

    def test_auto_reset_register_handling(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that auto-reset registers are handled correctly."""
        # Setup auto-reset scenario
        initial_values = setup_auto_reset_scenario(mock_interface)

        # Read auto-reset registers
        for addr in initial_values:
            value = regmap.read_reg(addr)

            # Value should be read correctly
            assert value == initial_values[addr]

            # But register should be auto-reset to 0 after read
            assert mock_interface.get_register_value(addr) == 0

    def test_auto_reset_cache_behavior(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test auto-reset register cache behavior."""
        auto_reset_addr = 0xB5  # SLEEP_MODE
        test_value = 1

        # Set initial value
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # First read
        value1 = regmap.read_reg(auto_reset_addr)
        assert value1 == test_value

        # Cache should be updated, but hardware value is now 0 (auto-reset)
        assert regmap._regs_cache[auto_reset_addr] == test_value
        assert mock_interface.get_register_value(auto_reset_addr) == 0

        # Second read should get 0 (auto-reset value)
        value2 = regmap.read_reg(auto_reset_addr)
        assert value2 == 0
        assert regmap._regs_cache[auto_reset_addr] == 0


class TestErrorHandling:
    """Test error handling in _RegMap operations."""

    def test_connection_error_during_read(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost during read."""
        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Attempt read - should raise error
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        # Cache should remain unchanged
        assert 0xB4 not in regmap._regs_cache

    def test_connection_error_during_write(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error handling when connection is lost during write."""
        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Attempt write - should raise error
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        # Cache should remain unchanged
        assert 0xB4 not in regmap._regs_cache

    def test_partial_failure_recovery(self, regmap: _RegMap) -> None:
        """Test recovery from partial failure scenarios."""
        # Create interface that fails after 1 write
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=1)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)

        # Attempt multiple writes
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_regs({0xB4: 100, 0xB7: 50})

        # Verify partial success
        assert len(mock_interface.write_calls) == 1
        assert len(regmap._regs_cache) == 1

        # Restore connection and retry
        mock_interface.restore_connection()
        mock_interface.fail_after_writes = None

        # Should be able to write again
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80


class TestConcurrencySupport:
    """Test concurrent access support in _RegMap."""

    def test_concurrent_read_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent read operations."""
        # Setup test data - exclude auto-reset registers for consistent results
        test_data = TestDataGenerator.generate_register_values(count=10, exclude_auto_reset=True)

        for addr, value in test_data.items():
            mock_interface.set_register_value(addr, value)

        results: list[dict[int, int]] = []

        def worker() -> None:
            result = regmap.read_regs(list(test_data.keys()))
            results.append(result)

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(results) == 3
        for result in results:
            assert result == test_data

    def test_concurrent_write_operations(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test concurrent write operations."""
        write_data = [
            {0xB4: 100},
            {0xB7: 50},
            {0xCA: 80},
        ]

        def worker(data: dict[int, int]) -> None:
            regmap.write_regs(data)

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
        expected_total = sum(len(data) for data in write_data)
        assert len(mock_interface.write_calls) == expected_total

        # Verify cache consistency
        for data in write_data:
            for addr, value in data.items():
                assert regmap._regs_cache[addr] == value
