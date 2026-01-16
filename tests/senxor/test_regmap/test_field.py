import pytest

from senxor.regmap.core import SenxorFieldsManager
from tests.senxor.conftest import MockInterface


class TestField:
    def test_attributes(self, mock_fieldmap: SenxorFieldsManager):
        field = mock_fieldmap.EMISSIVITY
        assert field.name == "EMISSIVITY"
        assert field.description is not None
        assert field.help is not None
        assert field.address is not None
        assert field.bits_range is not None
        assert field.writable is not None
        assert field.readable is not None
        assert field.self_reset is not None
        assert field.available is not None
        assert hasattr(field, "unavailable_reason")
        assert hasattr(field, "default_value")

    def test_repr(self, mock_fieldmap: SenxorFieldsManager):
        field = mock_fieldmap.EMISSIVITY
        assert repr(field) == "<Field(name=EMISSIVITY, address=0xCA, bits_range=(0, 8))>"
        assert str(field) == "EMISSIVITY(0xCA:0-8)"
        field._value = 95
        assert repr(field) == "<Field(name=EMISSIVITY, address=0xCA, bits_range=(0, 8))>"
        assert str(field) == "EMISSIVITY(0xCA:0-8)=95"

    def test_get(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        # Test normal case
        field = mock_fieldmap.EMISSIVITY
        mock_interface.set_value(field.address, 0x95)
        assert field._value is None
        assert field.get() == 0x95
        assert field._value == 0x95

        # Test self-reset case
        field = mock_fieldmap.SW_RESET
        mock_interface.set_value(field.address, 0x1)
        assert field.get() == 0x1
        mock_interface.set_value(field.address, 0x0)
        assert field.get() == 0x0
        mock_interface.set_value(field.address, 0x1)
        assert field.get(refresh=False) == 0x0  # No refresh, so the value is still 0x0
        assert field.get(refresh=True) == 0x1  # Refresh, so the value is 0x1

    def test_value(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        """Value property always returns the same value as the get() method."""
        field = mock_fieldmap.EMISSIVITY
        mock_interface.set_value(field.address, 0x95)
        assert field.value == 0x95
        assert field.value == field.get()

    def test_read(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        field = mock_fieldmap.EMISSIVITY
        mock_interface.set_value(field.address, 0x95)
        assert field.read() == 0x95

    def test_set(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        field = mock_fieldmap.EMISSIVITY
        field.set(0x95)
        assert mock_interface.values[field.address] == 0x95
        assert field.read() == 0x95
        assert field.value == 0x95
        assert field.get() == 0x95
        assert field._value == 0x95

    def test_reset(self, mock_fieldmap: SenxorFieldsManager):
        # Test reset with no default value raises ValueError
        field = mock_fieldmap.EMISSIVITY
        with pytest.raises(ValueError, match="Default value is not set for the field"):
            field.reset()

    def test_display(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        # Test display property and get_display method
        field = mock_fieldmap.EMISSIVITY
        mock_interface.set_value(field.address, 100)  # value = 100
        # Note: EMISSIVITY get_display returns round(value * 0.01, 2)
        # get_display(100) = round(100 * 0.01, 2) = round(1.0, 2) = 1.0
        expected_display = round(100 * 0.01, 2)
        assert field.get_display(100) == expected_display
        # Test display property
        field.read()  # This should update field._value
        assert field.display == expected_display
