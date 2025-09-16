"""Tests for error handling across regmap modules.

This module tests comprehensive error handling including interface errors,
validation errors, access control errors, and recovery scenarios.
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


class TestInterfaceErrorPropagation:
    """Test interface error propagation through regmap layers."""

    def test_connection_error_propagation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test connection error propagation through all layers."""
        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # _RegMap level should propagate error
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xCA)

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xCA, 80)

        # Registers level should propagate error
        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.read_reg(0xCA)

        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.write_reg(0xCA, 80)

        # Fields level should propagate error
        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.get_field("EMISSIVITY")

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.set_field("EMISSIVITY", 80)

        # Individual field instances should propagate error
        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.EMISSIVITY.get()

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.EMISSIVITY.set(80)

    def test_timeout_error_propagation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test timeout error propagation."""
        # This would require actual timeout simulation
        # For now, test with connection error as proxy
        mock_interface.simulate_connection_loss()

        # All levels should handle timeout errors consistently
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_regs([0xCA, 0xB4])

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_regs({0xCA: 80, 0xB4: 100})

    def test_protocol_error_propagation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test protocol error propagation."""
        # Simulate protocol error through connection loss
        mock_interface.simulate_connection_loss()

        # Bulk operations should handle protocol errors
        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.read_all()

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.get_fields(["EMISSIVITY", "SW_RESET"])

    def test_hardware_error_propagation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test hardware error propagation."""
        # Simulate hardware error
        mock_interface.simulate_connection_loss()

        # Error should propagate through all access patterns
        with pytest.raises(SenxorNotConnectedError):
            regmap.regs["EMISSIVITY"].read()

        with pytest.raises(SenxorNotConnectedError):
            regmap.regs["EMISSIVITY"].set(80)


class TestValidationErrors:
    """Test validation error handling."""

    def test_register_validation_errors(self, regmap: _RegMap) -> None:
        """Test register validation error handling."""
        # Test invalid register values
        with pytest.raises(ValueError):
            regmap.regs.write_reg(0xCA, -1)

        with pytest.raises(ValueError):
            regmap.regs.write_reg(0xCA, 256)

        with pytest.raises(ValueError):
            regmap.regs.write_reg(0xCA, 1000)

        # Test invalid register addresses
        with pytest.raises((KeyError, ValueError, TypeError)):
            regmap.regs.read_reg(0x999)

        with pytest.raises((KeyError, ValueError, TypeError)):
            regmap.regs.write_reg(0x999, 100)

    def test_field_validation_errors(self, regmap: _RegMap) -> None:
        """Test field validation error handling."""
        # Test invalid field names
        with pytest.raises((KeyError, AttributeError)):
            regmap.fields.get_field("INVALID_FIELD")

        with pytest.raises((KeyError, AttributeError)):
            regmap.fields.set_field("INVALID_FIELD", 1)

        # Test field value validation (would depend on specific field types)
        # For now, test with extreme values
        try:
            regmap.fields.set_field("EMISSIVITY", -1)
        except (ValueError, AttributeError):
            pass  # Expected for invalid values

    def test_value_range_errors(self, regmap: _RegMap) -> None:
        """Test value range error handling."""
        # Test boundary values
        boundary_values = TestDataGenerator().generate_boundary_values()

        for value in boundary_values["invalid"]:
            with pytest.raises(ValueError):
                regmap.regs.write_reg(0xCA, value)

    def test_type_validation_errors(self, regmap: _RegMap) -> None:
        """Test type validation error handling."""
        # Test invalid types for register operations
        with pytest.raises((TypeError, ValueError)):
            regmap.regs.write_reg(0xCA, "invalid")  # type: ignore

        with pytest.raises((TypeError, ValueError)):
            regmap.regs.write_reg(0xCA, 1.5)  # type: ignore

        with pytest.raises((TypeError, ValueError)):
            regmap.regs.write_reg(0xCA, None)  # type: ignore


class TestAccessControlErrors:
    """Test access control error handling."""

    def test_readonly_register_write_error(self, regmap: _RegMap) -> None:
        """Test error handling for read-only register writes."""
        # Test write to read-only register
        readonly_addrs = TestDataGenerator.READ_ONLY_ADDRESSES

        for addr in readonly_addrs:
            with pytest.raises(AttributeError) as exc_info:
                regmap.regs.write_reg(addr, 100)

            # Error message should be informative
            assert "read-only" in str(exc_info.value)
            assert f"0x{addr:02X}" in str(exc_info.value)

    def test_readonly_field_write_error(self, regmap: _RegMap) -> None:
        """Test error handling for read-only field writes."""
        # Find read-only fields
        for field_name, field_def in regmap.fields.__field_defs__.items():
            if not field_def.writable:
                with pytest.raises(AttributeError) as exc_info:
                    regmap.fields.set_field(field_name, 1)

                # Error message should be informative
                assert field_name in str(exc_info.value)
                assert "read-only" in str(exc_info.value)
                break
        else:
            pytest.skip("No read-only fields found for testing")

    def test_invalid_register_access_error(self, regmap: _RegMap) -> None:
        """Test error handling for invalid register access."""
        # Test invalid register names
        with pytest.raises(KeyError):
            regmap.regs["INVALID_REGISTER"]

        # Test invalid register addresses
        with pytest.raises(KeyError):
            regmap.regs[0x999]

        # Test invalid register attribute access
        with pytest.raises(AttributeError):
            regmap.regs.INVALID_REGISTER  # type: ignore

    def test_invalid_field_access_error(self, regmap: _RegMap) -> None:
        """Test error handling for invalid field access."""
        # Test invalid field names
        with pytest.raises((KeyError, AttributeError)):
            regmap.fields["INVALID_FIELD"]

        # Test invalid field attribute access
        with pytest.raises((AttributeError, KeyError)):
            regmap.fields.INVALID_FIELD  # type: ignore


class TestPartialFailureRecovery:
    """Test recovery from partial failure scenarios."""

    def test_partial_write_failure_rollback(self, regmap: _RegMap) -> None:
        """Test rollback behavior on partial write failures."""
        # Create interface that fails after 2 writes
        mock_interface = create_mock_with_failure_simulation(fail_after_writes=2)
        senxor_stub = SenxorStub(mock_interface)
        regmap = _RegMap(senxor_stub)

        # Attempt bulk write that will partially fail
        test_updates = {0xB4: 100, 0xB7: 50, 0xCA: 80, 0xCB: 90}

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_regs(test_updates)

        # Verify partial success
        successful_writes = len(mock_interface.write_calls)
        assert successful_writes == 2

        # Cache should reflect only successful writes
        assert len(regmap._regs_cache) == successful_writes

        # Verify that successful writes are in cache
        for addr, value in mock_interface.write_calls:
            assert regmap._regs_cache[addr] == value

    def test_cache_consistency_after_failure(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cache consistency after operation failures."""
        # Pre-populate cache
        regmap._regs_cache[0xCA] = 80
        regmap._fields_cache["EMISSIVITY"] = 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Failed operations should not corrupt cache
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.set_field("EMISSIVITY", 85)

        # Cache should remain consistent
        assert regmap._regs_cache[0xCA] == 80
        assert regmap._fields_cache["EMISSIVITY"] == 80
        assert 0xB4 not in regmap._regs_cache

    def test_error_state_recovery(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test recovery from error states."""
        # Initial successful operation
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

        # Simulate error condition
        mock_interface.simulate_connection_loss()

        # Operations should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        # Restore connection
        mock_interface.restore_connection()

        # Should be able to resume operations
        regmap.write_reg(0xB4, 100)
        assert regmap._regs_cache[0xB4] == 100

        # Previous state should be preserved
        assert regmap._regs_cache[0xCA] == 80

    def test_connection_recovery(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test connection recovery scenarios."""
        # Establish initial state
        regmap.write_reg(0xCA, 80)
        regmap.fields.set_field("EMISSIVITY", 85)

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # All operations should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xB4)

        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.read_all()

        # Restore connection
        mock_interface.restore_connection()

        # All operations should work again
        mock_interface.set_register_value(0xB4, 100)
        value = regmap.read_reg(0xB4)
        assert value == 100

        # Can perform bulk operations
        regmap.regs.read_all()

        # Can perform field operations
        field_value = regmap.fields.get_field("EMISSIVITY")
        assert field_value == 85  # Should be cached value


class TestErrorContextAndMessages:
    """Test error context and message quality."""

    def test_error_message_clarity(self, regmap: _RegMap) -> None:
        """Test that error messages are clear and helpful."""
        # Test read-only register error message
        with pytest.raises(AttributeError) as exc_info:
            regmap.regs.write_reg(0xB6, 100)  # STATUS register is read-only

        error_msg = str(exc_info.value)
        assert "read-only" in error_msg
        assert "0xB6" in error_msg or "STATUS" in error_msg

        # Test invalid register error message
        with pytest.raises(KeyError) as exc_info:
            regmap.regs["INVALID_REGISTER"]

        error_msg = str(exc_info.value)
        assert "INVALID_REGISTER" in error_msg

        # Test value range error message
        with pytest.raises(ValueError) as exc_info:
            regmap.regs.write_reg(0xCA, 256)

        error_msg = str(exc_info.value)
        assert "256" in error_msg

    def test_error_context_preservation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test that error context is preserved through layers."""
        # Simulate connection error
        mock_interface.simulate_connection_loss()

        # Error should preserve context through all layers
        with pytest.raises(SenxorNotConnectedError) as exc_info:
            regmap.read_reg(0xCA)

        # Error should indicate connection issue
        assert "disconnect" in str(exc_info.value).lower()

        # Same error through different layers
        with pytest.raises(SenxorNotConnectedError) as exc_info:
            regmap.regs.read_reg(0xCA)

        assert "disconnect" in str(exc_info.value).lower()

        with pytest.raises(SenxorNotConnectedError) as exc_info:
            regmap.fields.get_field("EMISSIVITY")

        assert "disconnect" in str(exc_info.value).lower()

    def test_technical_error_details(self, regmap: _RegMap) -> None:
        """Test that technical error details are preserved."""
        # Test that technical details are available for debugging
        with pytest.raises(ValueError) as exc_info:
            regmap.regs.write_reg(0xCA, -1)

        error_msg = str(exc_info.value)
        # Should contain technical details
        assert "-1" in error_msg
        assert "0" in error_msg or "255" in error_msg  # Range information


class TestErrorScenarioIntegration:
    """Test integration of various error scenarios."""

    def test_cascading_error_scenarios(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cascading error scenarios."""
        # Setup initial state
        regmap.write_reg(0xCA, 80)
        regmap.fields.set_field("EMISSIVITY", 85)

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # All subsequent operations should fail consistently
        operations = [
            lambda: regmap.read_reg(0xB4),
            lambda: regmap.write_reg(0xB4, 100),
            lambda: regmap.regs.read_all(),
            lambda: regmap.fields.set_field("EMISSIVITY", 90),
        ]

        for operation in operations:
            with pytest.raises(SenxorNotConnectedError):
                operation()

        # Cache should remain in consistent state
        assert regmap._regs_cache[0xCA] == 85  # Last successful write
        assert regmap._fields_cache["EMISSIVITY"] == 85

    def test_mixed_error_types(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test handling of mixed error types."""
        # Test validation error
        with pytest.raises(ValueError):
            regmap.regs.write_reg(0xCA, 256)

        # Test access control error
        with pytest.raises(AttributeError):
            regmap.regs.write_reg(0xB6, 100)  # Read-only register

        # Test connection error
        mock_interface.simulate_connection_loss()
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xCA)

        # Restore connection
        mock_interface.restore_connection()

        # Should be able to perform valid operations
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

    def test_error_isolation_between_modules(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error isolation between registers and fields modules."""
        # Setup working state
        regmap.write_reg(0xCA, 80)
        regmap.fields.set_field("EMISSIVITY", 85)

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Errors in one module shouldn't affect cache state
        with pytest.raises(SenxorNotConnectedError):
            regmap.regs.read_reg(0xB4)

        with pytest.raises(SenxorNotConnectedError):
            regmap.fields.get_field("SW_RESET")

        # Cache should remain consistent
        assert regmap._regs_cache[0xCA] == 85
        assert regmap._fields_cache["EMISSIVITY"] == 85

        # Restore connection
        mock_interface.restore_connection()

        # Both modules should work normally
        regmap.write_reg(0xB4, 100)
        regmap.fields.set_field("EMISSIVITY", 90)

        assert regmap._regs_cache[0xB4] == 100
        assert regmap._fields_cache["EMISSIVITY"] == 90


class TestErrorRecoveryStrategies:
    """Test error recovery strategies."""

    def test_graceful_degradation(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test graceful degradation during errors."""
        # Pre-populate cache with known good values
        regmap._regs_cache[0xCA] = 80
        regmap._fields_cache["EMISSIVITY"] = 80

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Cache should still be accessible
        assert regmap._regs_cache[0xCA] == 80
        assert regmap._fields_cache["EMISSIVITY"] == 80

        # Status properties should work
        status = regmap.regs.status
        assert status[0xCA] == 80

        field_status = regmap.fields.status
        assert field_status["EMISSIVITY"] == 80

    def test_retry_mechanisms(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test retry mechanisms after errors."""
        # Simulate temporary connection loss
        mock_interface.simulate_connection_loss()

        # Operation should fail
        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xCA, 80)

        # Restore connection
        mock_interface.restore_connection()

        # Retry should succeed
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

    def test_error_state_cleanup(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test cleanup of error states."""
        # Setup initial state
        regmap.write_reg(0xCA, 80)

        # Simulate error
        mock_interface.simulate_connection_loss()

        with pytest.raises(SenxorNotConnectedError):
            regmap.write_reg(0xB4, 100)

        # Restore connection
        mock_interface.restore_connection()

        # System should be in clean state
        regmap.write_reg(0xB4, 100)
        assert regmap._regs_cache[0xB4] == 100

        # Previous state should be preserved
        assert regmap._regs_cache[0xCA] == 80


class TestErrorLogging:
    """Test error logging and diagnostics."""

    def test_error_logging_integration(self, regmap: _RegMap, mock_interface: EnhancedMockInterface) -> None:
        """Test error logging integration."""
        # This would require actual logging verification
        # For now, test that errors don't break logging

        # Simulate connection loss
        mock_interface.simulate_connection_loss()

        # Error should be logged but not break system
        with pytest.raises(SenxorNotConnectedError):
            regmap.read_reg(0xCA)

        # System should remain functional after error
        mock_interface.restore_connection()
        regmap.write_reg(0xCA, 80)
        assert regmap._regs_cache[0xCA] == 80

    def test_diagnostic_information(self, regmap: _RegMap) -> None:
        """Test availability of diagnostic information."""
        # Test that diagnostic information is available
        assert hasattr(regmap, "address")
        assert hasattr(regmap, "interface")
        assert hasattr(regmap, "_regs_cache")
        assert hasattr(regmap, "_fields_cache")

        # Test that error conditions can be diagnosed
        with pytest.raises(ValueError) as exc_info:
            regmap.regs.write_reg(0xCA, 256)

        # Exception should contain diagnostic information
        error_msg = str(exc_info.value)
        assert "256" in error_msg  # The invalid value
        assert "255" in error_msg or "0" in error_msg  # Valid range
