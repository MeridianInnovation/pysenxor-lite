from __future__ import annotations

from typing import Callable

import pytest

from senxor.interface.protocol import IDevice, ISenxorInterface
from senxor.regmap.core import SenxorFieldsManager, SenxorRegistersManager


class MockDevice(IDevice):
    def __init__(self, name: str = "mock_device"):
        self.name = name


class MockInterface(ISenxorInterface[MockDevice]):
    def __init__(self, device: MockDevice) -> None:
        self.device = device
        self.is_connected = True
        self.values = {}

    def set_value(self, reg: int, value: int) -> None:
        self.values[reg] = value

    @classmethod
    def list_devices(cls) -> list[MockDevice]:
        return [MockDevice(name="test_device")]

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def read(self, block: bool = True) -> tuple:
        return (None, None)

    def read_reg(self, reg: int) -> int:
        return self.values.get(reg, 0)

    def read_regs(self, regs: list[int]) -> dict[int, int]:
        return {reg: self.values.get(reg, 0) for reg in regs}

    def write_reg(self, reg: int, value: int) -> None:
        self.values[reg] = value

    def write_regs(self, regs: dict[int, int]) -> None:
        self.values.update(regs)

    def on_open(self, callback: Callable[[], None]) -> None:
        pass

    def on_close(self, callback: Callable[[], None]) -> None:
        pass

    def on_data(self, callback: Callable[[bytes | None, bytes], None]) -> None:
        pass

    def on_error(self, callback: Callable[[Exception], None]) -> None:
        pass


@pytest.fixture
def mock_device():
    return MockDevice(name="test_device")


@pytest.fixture
def mock_interface(mock_device):
    return MockInterface(mock_device)


@pytest.fixture
def mock_regmap(mock_interface: MockInterface) -> SenxorRegistersManager:
    return SenxorRegistersManager(mock_interface)


@pytest.fixture
def mock_fieldmap(mock_regmap: SenxorRegistersManager) -> SenxorFieldsManager:
    return mock_regmap.fieldmap
