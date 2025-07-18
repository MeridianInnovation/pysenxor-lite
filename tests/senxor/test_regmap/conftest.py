"""Test configuration and fixtures for senxor regmap tests.

This module provides pytest fixtures that are automatically available
to all test files in the regmap test directory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from senxor.regmap._regmap import _RegMap

from .fixtures import EnhancedMockInterface, SenxorStub


@pytest.fixture
def mock_interface() -> EnhancedMockInterface:
    """Provide a fresh mock interface for each test."""
    return EnhancedMockInterface()


@pytest.fixture
def senxor_stub(mock_interface: EnhancedMockInterface) -> SenxorStub:
    """Provide a Senxor stub with mock interface."""
    return SenxorStub(mock_interface)


@pytest.fixture
def regmap(senxor_stub: SenxorStub) -> _RegMap:
    """Provide a _RegMap instance for testing."""
    return _RegMap(senxor_stub)  # type: ignore[arg-type]
