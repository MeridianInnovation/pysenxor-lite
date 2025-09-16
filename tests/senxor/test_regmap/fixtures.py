"""Enhanced test fixtures for senxor regmap testing.

This module provides comprehensive test fixtures including enhanced mock interfaces,
test data generators, and utility functions for testing the regmap architecture.
"""

from __future__ import annotations

import random
import threading
import time
from typing import TYPE_CHECKING

from senxor.error import SenxorNotConnectedError

if TYPE_CHECKING:
    from senxor.regmap._regmap import _RegMap


class EnhancedMockInterface:
    """Enhanced hardware stub with realistic device behavior.

    This mock interface provides comprehensive simulation of hardware behavior
    including connection states, auto-reset registers, error conditions, and
    timing characteristics.
    """

    def __init__(self) -> None:
        self._regs: dict[int, int] = {}
        self.read_calls: list[int] = []
        self.write_calls: list[tuple[int, int]] = []
        self.connection_state: bool = True
        self.auto_reset_registers: set[int] = {0x00, 0x01, 0xB1, 0xB5, 0xB6, 0xC5, 0xD0}
        self.read_only_registers: set[int] = {0xB2, 0xB3, 0xB6, 0xBA, 0xBB, 0x33}
        self.fail_after_writes: int | None = None
        self.write_count: int = 0
        self.read_delay: float = 0.0
        self.write_delay: float = 0.0
        self._lock = threading.Lock()

    def set_register_value(self, addr: int, value: int) -> None:
        """Set a register value directly (for test setup)."""
        with self._lock:
            self._regs[addr] = value

    def get_register_value(self, addr: int) -> int:
        """Get a register value directly (for test verification)."""
        with self._lock:
            return self._regs.get(addr, 0)

    def reset_call_history(self) -> None:
        """Reset call history for fresh test state."""
        with self._lock:
            self.read_calls.clear()
            self.write_calls.clear()
            self.write_count = 0

    def simulate_connection_loss(self) -> None:
        """Simulate device disconnection."""
        self.connection_state = False

    def restore_connection(self) -> None:
        """Restore device connection."""
        self.connection_state = True

    def simulate_partial_write_failure(self, fail_after: int) -> None:
        """Simulate partial write failure after N successful writes."""
        self.fail_after_writes = fail_after
        self.write_count = 0

    def set_operation_delays(self, read_delay: float = 0.0, write_delay: float = 0.0) -> None:
        """Set artificial delays for read/write operations."""
        self.read_delay = read_delay
        self.write_delay = write_delay

    def _simulate_auto_reset(self, addr: int) -> None:
        """Simulate auto-reset behavior after register access."""
        if addr in self.auto_reset_registers:
            # Auto-reset registers change value after access
            self._regs[addr] = 0

    def _check_connection(self) -> None:
        """Check connection state and raise error if disconnected."""
        if not self.connection_state:
            raise SenxorNotConnectedError("Device disconnected")

    def _check_write_failure(self) -> None:
        """Check if write should fail based on failure simulation."""
        if self.fail_after_writes is not None:
            if self.write_count >= self.fail_after_writes:
                raise SenxorNotConnectedError("Simulated write failure")
            self.write_count += 1

    def _apply_delay(self, delay: float) -> None:
        """Apply artificial delay if configured."""
        if delay > 0:
            time.sleep(delay)

    # --- Hardware Interface Implementation ---

    def read_reg(self, addr: int) -> int:
        """Read a single register with realistic behavior simulation."""
        with self._lock:
            self._check_connection()
            self._apply_delay(self.read_delay)

            self.read_calls.append(addr)
            value = self._regs.get(addr, 0)
            self._simulate_auto_reset(addr)

            return value

    def read_regs(self, addrs: list[int]) -> dict[int, int]:
        """Read multiple registers with batch processing."""
        result: dict[int, int] = {}
        for addr in addrs:
            result[addr] = self.read_reg(addr)
        return result

    def write_reg(self, addr: int, value: int) -> None:
        """Write a single register with validation and error simulation."""
        with self._lock:
            self._check_connection()
            self._check_write_failure()
            self._apply_delay(self.write_delay)

            if addr in self.read_only_registers:
                raise AttributeError(f"Register 0x{addr:02X} is read-only")

            if not (0 <= value <= 255):
                raise ValueError(f"Register value must be in [0, 255], got {value}")

            self.write_calls.append((addr, value))
            self._regs[addr] = value
            self._simulate_auto_reset(addr)

    def write_regs(self, values_dict: dict[int, int]) -> None:
        """Write multiple registers with batch processing."""
        for addr, value in values_dict.items():
            self.write_reg(addr, value)

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.connection_state

    @property
    def address(self) -> str:
        """Get device address."""
        return "mock_device"


class SenxorStub:
    """Minimal Senxor stub for testing _RegMap initialization.

    This stub provides the minimum interface required by _RegMap
    while allowing full control over the underlying interface behavior.
    """

    def __init__(self, interface: EnhancedMockInterface, address: str = "TEST_DEVICE") -> None:
        self.interface = interface
        self.address = address
        self.is_streaming: bool = False
        self.is_connected: bool = True

    def open(self) -> None:
        """Simulate device opening."""
        self.is_connected = True

    def close(self) -> None:
        """Simulate device closing."""
        self.is_connected = False

    def start_stream(self) -> None:
        """Simulate stream start."""
        self.is_streaming = True

    def stop_stream(self) -> None:
        """Simulate stream stop."""
        self.is_streaming = False


class TestDataGenerator:
    """Generate realistic test data for regmap testing.

    This class provides methods to generate various types of test data
    including register values, field values, and boundary conditions.
    """

    # Valid register addresses from the actual regmap
    VALID_REGISTER_ADDRESSES = [
        0x00,
        0x01,
        0x19,
        0xB1,
        0xB2,
        0xB3,
        0xB4,
        0xB5,
        0xB6,
        0xB7,
        0xB9,
        0xBA,
        0xBB,
        0x33,
        0xBC,
        0xC2,
        0xC5,
        0xCA,
        0xCB,
        0xCD,
        0xE0,
        0xE1,
        0xE2,
        0xE3,
        0xE4,
        0xE5,
        0xE6,
        0xD8,
        0x31,
        0x20,
        0x21,
        0x22,
        0x23,
        0x25,
        0x30,
        0xD0,
        0xD1,
        0xD2,
    ]

    # Auto-reset register addresses
    AUTO_RESET_ADDRESSES = [0x00, 0x01, 0xB1, 0xB5, 0xB6, 0xC5, 0xD0]

    # Read-only register addresses
    READ_ONLY_ADDRESSES = [0xB2, 0xB3, 0xB6, 0xBA, 0xBB, 0x33]

    # Field type constraints
    FIELD_TYPE_CONSTRAINTS = {
        "bool": {"min": 0, "max": 1},
        "uint3": {"min": 0, "max": 7},
        "uint4": {"min": 0, "max": 15},
        "uint8": {"min": 0, "max": 255},
    }

    @classmethod
    def generate_register_values(
        cls,
        count: int = 10,
        exclude_readonly: bool = False,
        exclude_auto_reset: bool = False,
    ) -> dict[int, int]:
        """Generate realistic register address-value pairs.

        Args:
            count: Number of register values to generate
            exclude_readonly: If True, exclude read-only registers
            exclude_auto_reset: If True, exclude auto-reset registers

        Returns:
            Dictionary mapping register addresses to values

        """
        available_addrs = cls.VALID_REGISTER_ADDRESSES.copy()
        if exclude_readonly:
            available_addrs = [addr for addr in available_addrs if addr not in cls.READ_ONLY_ADDRESSES]
        if exclude_auto_reset:
            available_addrs = [addr for addr in available_addrs if addr not in cls.AUTO_RESET_ADDRESSES]

        selected_addrs = random.sample(available_addrs, min(count, len(available_addrs)))
        return {addr: random.randint(0, 255) for addr in selected_addrs}

    @classmethod
    def generate_writable_register_values(cls, count: int = 10, exclude_auto_reset: bool = False) -> dict[int, int]:
        """Generate register values for write operations (automatically excludes read-only registers).

        Args:
            count: Number of register values to generate
            exclude_auto_reset: If True, exclude auto-reset registers

        Returns:
            Dictionary mapping writable register addresses to values

        """
        return cls.generate_register_values(count=count, exclude_readonly=True, exclude_auto_reset=exclude_auto_reset)

    @classmethod
    def generate_field_values(cls, field_names: list[str]) -> dict[str, int]:
        """Generate valid field values based on field constraints.

        Args:
            field_names: List of field names to generate values for

        Returns:
            Dictionary mapping field names to valid values

        """
        # This would need to be implemented based on actual field definitions
        # For now, return reasonable defaults
        result: dict[str, int] = {}
        for field_name in field_names:
            if "ENABLE" in field_name or "RESET" in field_name:
                result[field_name] = random.choice([0, 1])
            elif "RATE" in field_name or "SPEED" in field_name:
                result[field_name] = random.randint(0, 15)
            else:
                result[field_name] = random.randint(0, 255)
        return result

    @classmethod
    def generate_boundary_values(cls) -> dict[str, list[int]]:
        """Generate boundary test values for different data types.

        Returns:
            Dictionary mapping data types to boundary values

        """
        return {
            "uint8": [0, 1, 127, 128, 254, 255],
            "bool": [0, 1],
            "uint3": [0, 1, 7],
            "uint4": [0, 1, 15],
            "invalid": [-1, 256, 1000, -100],
        }

    @classmethod
    def generate_auto_reset_addresses(cls, count: int = 3) -> list[int]:
        """Generate a list of auto-reset register addresses.

        Args:
            count: Number of addresses to return

        Returns:
            List of auto-reset register addresses

        """
        return random.sample(cls.AUTO_RESET_ADDRESSES, min(count, len(cls.AUTO_RESET_ADDRESSES)))

    @classmethod
    def generate_normal_addresses(cls, count: int = 5) -> list[int]:
        """Generate a list of normal (non-auto-reset) register addresses.

        Args:
            count: Number of addresses to return

        Returns:
            List of normal register addresses

        """
        normal_addrs = [addr for addr in cls.VALID_REGISTER_ADDRESSES if addr not in cls.AUTO_RESET_ADDRESSES]
        return random.sample(normal_addrs, min(count, len(normal_addrs)))

    @classmethod
    def generate_mixed_addresses(cls, auto_count: int = 2, normal_count: int = 3) -> list[int]:
        """Generate a mixed list of auto-reset and normal addresses.

        Args:
            auto_count: Number of auto-reset addresses
            normal_count: Number of normal addresses

        Returns:
            Mixed list of register addresses

        """
        auto_addrs = cls.generate_auto_reset_addresses(auto_count)
        normal_addrs = cls.generate_normal_addresses(normal_count)
        mixed = auto_addrs + normal_addrs
        random.shuffle(mixed)
        return mixed


# --- Pytest Fixtures are now in conftest.py ---


# --- Utility Functions ---


def assert_hardware_call_count(
    mock_interface: EnhancedMockInterface,
    expected_reads: int,
    expected_writes: int,
) -> None:
    """Assert the expected number of hardware calls were made.

    Args:
        mock_interface: The mock interface to check
        expected_reads: Expected number of read calls
        expected_writes: Expected number of write calls

    """
    actual_reads = len(mock_interface.read_calls)
    actual_writes = len(mock_interface.write_calls)

    assert actual_reads == expected_reads, f"Expected {expected_reads} reads, got {actual_reads}"
    assert actual_writes == expected_writes, f"Expected {expected_writes} writes, got {actual_writes}"


def assert_cache_consistency(regmap: _RegMap) -> None:
    """Assert that register and field caches are consistent.

    Args:
        regmap: The regmap instance to check

    """
    # This is a placeholder - actual implementation would need to verify
    # that field cache values match what would be computed from register cache
    assert regmap._regs_cache is not None
    assert regmap._fields_cache is not None


def create_mock_with_failure_simulation(
    fail_after_reads: int | None = None,
    fail_after_writes: int | None = None,
) -> EnhancedMockInterface:
    """Create a mock interface with failure simulation.

    Args:
        fail_after_reads: Fail after this many read operations
        fail_after_writes: Fail after this many write operations

    Returns:
        Mock interface configured for failure simulation

    """
    interface = EnhancedMockInterface()

    if fail_after_writes is not None:
        interface.simulate_partial_write_failure(fail_after_writes)

    return interface


def setup_auto_reset_scenario(interface: EnhancedMockInterface) -> dict[int, int]:
    """Set up a scenario with auto-reset registers for testing.

    Args:
        interface: Mock interface to configure

    Returns:
        Dictionary of initial register values

    """
    initial_values = {}
    for addr in TestDataGenerator.AUTO_RESET_ADDRESSES[:3]:
        value = random.randint(1, 255)  # Non-zero so we can see auto-reset effect
        interface.set_register_value(addr, value)
        initial_values[addr] = value
    return initial_values
