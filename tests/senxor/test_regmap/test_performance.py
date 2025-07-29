"""Tests for performance characteristics of regmap modules.

This module tests performance aspects including cache efficiency, hardware interaction
optimization, scalability limits, and performance regression monitoring.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from senxor.regmap._regmap import _RegMap

    from .fixtures import EnhancedMockInterface


class TestHardwareInteractionEfficiency:
    """Test hardware interaction efficiency."""

    def test_minimal_hardware_calls(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that hardware calls are minimized."""
        # Setup test data
        test_addrs = [0xCA, 0xB4, 0xB7]
        for addr in test_addrs:
            mock_interface.set_register_value(addr, addr % 256)

        # Clear call history
        mock_interface.reset_call_history()

        # Read each register once
        for addr in test_addrs:
            regmap.read_reg(addr)

        # Should have made exactly one call per register
        assert len(mock_interface.read_calls) == len(test_addrs)

        # Clear call history
        mock_interface.reset_call_history()

        # Read same registers again (should use cache)
        for addr in test_addrs:
            regmap.regs.get_reg(addr)

        # Should not have made additional hardware calls
        assert len(mock_interface.read_calls) == 0

    def test_redundant_call_elimination(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test elimination of redundant hardware calls."""
        test_addr = 0xCA
        test_value = 80
        mock_interface.set_register_value(test_addr, test_value)

        # Clear call history
        mock_interface.reset_call_history()

        # Multiple reads of same register
        for _ in range(10):
            regmap.regs.get_reg(test_addr)

        # Should have made minimal hardware calls
        assert len(mock_interface.read_calls) <= 1

    def test_auto_reset_handling_efficiency(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test efficient handling of auto-reset registers."""
        # Test with auto-reset register
        auto_reset_addr = 0xB5  # SLEEP_MODE
        test_value = 1
        mock_interface.set_register_value(auto_reset_addr, test_value)

        # Clear call history
        mock_interface.reset_call_history()

        # Multiple reads of auto-reset register
        for _ in range(5):
            regmap.read_reg(auto_reset_addr)

        # Should have made hardware calls for each read (no caching)
        assert len(mock_interface.read_calls) == 5

        # Compare with normal register
        normal_addr = 0xCA
        mock_interface.set_register_value(normal_addr, 80)
        mock_interface.reset_call_history()

        # Multiple reads of normal register
        for _ in range(5):
            regmap.regs.get_reg(normal_addr)

        # Should have made only one hardware call (cached)
        assert len(mock_interface.read_calls) <= 1


class TestCacheOptimization:
    """Test cache optimization strategies."""

    def test_cache_hit_ratio_optimization(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache hit ratio optimization."""
        # Setup test data
        test_addrs = [0xCA, 0xB4, 0xB7, 0xCB]
        for addr in test_addrs:
            mock_interface.set_register_value(addr, addr % 256)

        # Initial reads (cache misses)
        for addr in test_addrs:
            regmap.read_reg(addr)

        # Clear call history
        mock_interface.reset_call_history()

        # Repeated reads (should be cache hits)
        for _ in range(10):
            for addr in test_addrs:
                regmap.regs.get_reg(addr)

        # Should have high cache hit ratio (minimal hardware calls)
        assert len(mock_interface.read_calls) == 0
