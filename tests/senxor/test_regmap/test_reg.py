from senxor.regmap.core import SenxorRegistersManager
from tests.senxor.conftest import MockInterface


class TestRegister:
    def test_attributes(self, mock_regmap: SenxorRegistersManager):
        reg = mock_regmap.EMISSIVITY
        assert reg.name == "EMISSIVITY"
        assert reg.description is not None
        assert reg.address is not None
        assert reg.writable is not None
        assert reg.readable is not None
        assert reg.self_reset is not None
        assert reg.default_value is not None

    def test_repr(self, mock_regmap: SenxorRegistersManager):
        reg = mock_regmap.EMISSIVITY
        assert repr(reg) == "<Register(name=EMISSIVITY, address=0xCA)>"
        assert str(reg) == "EMISSIVITY(0xCA)"
        reg._value = 95
        assert repr(reg) == "<Register(name=EMISSIVITY, address=0xCA)>"
        assert str(reg) == "EMISSIVITY(0xCA)=95"

    def test_get(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        # Test normal case
        reg = mock_regmap.EMISSIVITY
        mock_interface.set_value(reg.address, 95)
        assert reg._value is None
        assert reg.get() == 95
        assert reg._value == 95

        # Test self-reset case
        reg = mock_regmap.MCU_RESET
        mock_interface.set_value(reg.address, 0x1)
        assert reg.get() == 0x1
        mock_interface.set_value(reg.address, 0x0)
        assert reg.get() == 0x0
        mock_interface.set_value(reg.address, 0x1)
        assert reg.get(refresh=False) == 0x0  # No refresh, so the value is still 0x0
        assert reg.get(refresh=True) == 0x1  # Refresh, so the value is 0x1

    def test_value(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        """Value property always returns the same value as the get() method."""
        reg = mock_regmap.EMISSIVITY
        mock_interface.set_value(reg.address, 0x95)
        assert reg.value == 0x95
        assert reg.value == reg.get()

    def test_read(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        reg = mock_regmap.EMISSIVITY
        mock_interface.set_value(reg.address, 0x95)
        assert reg.read() == 0x95

    def test_set(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        reg = mock_regmap.EMISSIVITY
        reg.set(0x95)
        assert mock_interface.values[reg.address] == 0x95
        assert reg.read() == 0x95
        assert reg.value == 0x95
        assert reg.get() == 0x95
        assert reg._value == 0x95
