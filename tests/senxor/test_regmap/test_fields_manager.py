import pytest
from structlog.testing import capture_logs

from senxor.regmap.base import Field
from senxor.regmap.core import SenxorFieldsManager, SenxorRegistersManager
from tests.senxor.conftest import MockInterface


class TestFieldsManager:
    def test_attributes(self, mock_fieldmap: SenxorFieldsManager):
        cache = mock_fieldmap.cache
        for key, value in cache.items():
            assert key in mock_fieldmap.fields
            assert value is None

        cache_display = mock_fieldmap.cache_display
        for key, value in cache_display.items():
            assert key in mock_fieldmap.fields
            assert value is None

    def test_iter(self, mock_fieldmap: SenxorFieldsManager):
        assert len(list(mock_fieldmap)) == len(mock_fieldmap.fields)
        for field in mock_fieldmap:
            assert isinstance(field, Field)
            assert field.name in mock_fieldmap.fields

    def test_getitem(self, mock_fieldmap: SenxorFieldsManager):
        field = mock_fieldmap["SW_RESET"]
        assert field.name == "SW_RESET"

        with pytest.raises(KeyError):
            mock_fieldmap["INVALID_FIELD"]  # type: ignore[reportArgumentType]

        with pytest.raises((KeyError, TypeError)):
            mock_fieldmap[114]  # type: ignore[reportArgumentType]

    def test_contains(self, mock_fieldmap: SenxorFieldsManager):
        assert "SW_RESET" in mock_fieldmap
        assert 0x00 not in mock_fieldmap  # type: ignore[reportOperatorIssue]
        assert "INVALID_FIELD" not in mock_fieldmap

    def test_get_field(self, mock_fieldmap: SenxorFieldsManager):
        field = mock_fieldmap.get_field("SW_RESET")
        assert field.name == "SW_RESET"
        assert field.address == 0x00
        assert field.bits_range == (0, 1)

        with pytest.raises(KeyError):
            mock_fieldmap.get_field("INVALID_FIELD")  # type: ignore[reportArgumentType]
        with pytest.raises((KeyError, TypeError)):
            mock_fieldmap.get_field(114)  # type: ignore[reportArgumentType]

    def test_get_fields_by_addr(self, mock_fieldmap: SenxorFieldsManager):
        fields = mock_fieldmap.get_fields_by_addr(0xB1)
        assert isinstance(fields, list)
        for field in fields:
            assert isinstance(field, Field)
            assert field.address == 0xB1
        with pytest.raises(KeyError):
            mock_fieldmap.get_fields_by_addr(0xFFFF)  # type: ignore[reportArgumentType]
        with pytest.raises(KeyError):
            mock_fieldmap.get_fields_by_addr("SW_RESET")  # type: ignore[reportArgumentType]

    def test_read_field(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        field_name = "EMISSIVITY"
        field = mock_fieldmap.get_field(field_name)

        mock_interface.set_value(field.address, 95)
        assert mock_fieldmap.read_field(field_name) == 95

        mock_interface.set_value(field.address, 96)
        assert mock_fieldmap.read_field(field_name) == 96

        with pytest.raises(KeyError):
            mock_fieldmap.read_field("INVALID_FIELD")  # type: ignore[reportArgumentType]
        with pytest.raises((KeyError, TypeError)):
            mock_fieldmap.read_field(114)  # type: ignore[reportArgumentType]

    def test_set_field(self, mock_fieldmap: SenxorFieldsManager, mock_interface: MockInterface):
        field_name = "EMISSIVITY"
        field = mock_fieldmap.get_field(field_name)

        mock_fieldmap.set_field(field_name, 95)
        assert field._value == 95
        assert mock_interface.values[field.address] == 95
        assert mock_fieldmap.read_field(field_name) == 95
        assert field.value == 95
        assert field.get() == 95

        mock_fieldmap.set_field(field_name, 96)
        assert field._value == 96
        assert mock_interface.values[field.address] == 96
        assert mock_fieldmap.read_field(field_name) == 96
        assert field.value == 96
        assert field.get() == 96

    def test_set_field_errors(self, mock_fieldmap: SenxorFieldsManager):
        # Test invalid field name
        with pytest.raises(KeyError):
            mock_fieldmap.set_field("INVALID_FIELD", 95)  # type: ignore[reportArgumentType]
        with pytest.raises((KeyError, TypeError)):
            mock_fieldmap.set_field(114, 95)  # type: ignore[reportArgumentType]

        # Test invalid field value or type
        with pytest.raises(ValueError):  # noqa: PT011
            mock_fieldmap.set_field("EMISSIVITY", -1)
        with pytest.raises(ValueError):  # noqa: PT011
            mock_fieldmap.set_field("EMISSIVITY", 0xFF + 1)
        with pytest.raises(TypeError):
            mock_fieldmap.set_field("EMISSIVITY", 1.0)  # type: ignore[reportArgumentType]

        # Test read-only field
        assert mock_fieldmap.FW_VERSION_MAJOR.writable is False
        with pytest.raises(AttributeError):
            mock_fieldmap.set_field("FW_VERSION_MAJOR", 2)

        # Test disabled field
        mock_fieldmap.TEMP_UNITS.enabled = False
        with pytest.raises(AttributeError):
            mock_fieldmap.set_field("TEMP_UNITS", 1)

        # Test force set disabled field
        mock_fieldmap.set_field("TEMP_UNITS", 1, force=True)
        assert mock_fieldmap.TEMP_UNITS._value == 1

        # Test force set read-only field
        with pytest.raises(AttributeError):
            # Set read-only field is never allowed
            mock_fieldmap.set_field("FW_VERSION_MAJOR", 2, force=True)

        # Test force set invalid field value
        with pytest.raises(ValueError):  # noqa: PT011
            mock_fieldmap.set_field("EMISSIVITY", 0xFF + 1, force=True)
        with pytest.raises(ValueError):  # noqa: PT011
            mock_fieldmap.set_field("EMISSIVITY", -1, force=True)
        with pytest.raises(TypeError):
            mock_fieldmap.set_field("EMISSIVITY", 1.0, force=True)  # type: ignore[reportArgumentType]

        def mock_validate_value(_, __: int) -> None:
            raise ValueError("Invalid value")

        mock_fieldmap.EMISSIVITY.validate_value = mock_validate_value.__get__(mock_fieldmap.EMISSIVITY, Field)

        with pytest.raises(ValueError):  # noqa: PT011
            mock_fieldmap.set_field("EMISSIVITY", 1, force=True)

    def test_update_field_values(self, mock_fieldmap: SenxorFieldsManager, mock_regmap: SenxorRegistersManager):
        # 1. Update a register that contains only one field
        reg = mock_regmap.EMISSIVITY
        field = mock_fieldmap.EMISSIVITY
        # Ensure only one field is associated with the register
        assert mock_fieldmap.__reg2fields__[reg.address] == ["EMISSIVITY"]

        mock_regmap.write_reg(reg.address, 0)
        assert reg._value == 0
        assert field._value == 0
        updated_fields = mock_fieldmap._update_field_values({reg.address: 95})
        assert updated_fields == {"EMISSIVITY": 95}
        assert field._value == 95
        # '_update_field_values' only updates the field value
        assert reg._value == 0

        # 2. Update a register that contains multiple fields
        reg = mock_regmap.FRAME_MODE
        fields = mock_fieldmap.get_fields_by_addr(reg.address)

        assert [field.name for field in fields] == [
            "GET_SINGLE_FRAME",
            "CONTINUOUS_STREAM",
            "READOUT_MODE",
            "NO_HEADER",
            "ADC_ENABLE",
        ]

        mock_regmap.write_reg(reg.address, 0b00000000)
        assert reg._value == 0b00000000
        assert [field._value for field in fields] == [0, 0, 0, 0, 0]

        # No fields are updated
        updated_fields = mock_fieldmap._update_field_values({reg.address: 0b00000000})
        assert updated_fields == {}
        assert [field._value for field in fields] == [0, 0, 0, 0, 0]

        # GET_SINGLE_FRAME is set to 1
        updated_fields = mock_fieldmap._update_field_values({reg.address: 0b00000001})

        assert updated_fields == {"GET_SINGLE_FRAME": 1}
        assert [field._value for field in fields] == [1, 0, 0, 0, 0]

        # No fields are updated
        updated_fields = mock_fieldmap._update_field_values({reg.address: 0b00000001})
        assert updated_fields == {}
        assert [field._value for field in fields] == [1, 0, 0, 0, 0]

        # CONTINUOUS_STREAM and ADC_ENABLE are set to 1
        updated_fields = mock_fieldmap._update_field_values({reg.address: 0b10000011})
        assert updated_fields == {"CONTINUOUS_STREAM": 1, "ADC_ENABLE": 1}
        assert [field._value for field in fields] == [1, 1, 0, 0, 1]

        # READOUT_MODE is set to 7
        updated_fields = mock_fieldmap._update_field_values({reg.address: 0b10011111})
        assert updated_fields == {"READOUT_MODE": 7}
        assert [field._value for field in fields] == [1, 1, 7, 0, 1]

        # Test Update multiple registers
        reg1 = mock_regmap.EMISSIVITY
        reg2 = mock_regmap.SENSITIVITY_FACTOR

        mock_regmap.write_reg(reg1.address, 0)
        mock_regmap.write_reg(reg2.address, 0)
        assert reg1._value == 0
        assert reg2._value == 0
        assert mock_fieldmap.EMISSIVITY._value == 0
        assert mock_fieldmap.CORR_FACTOR._value == 0

        updated_fields = mock_fieldmap._update_field_values({reg1.address: 95, reg2.address: 99})
        assert updated_fields == {"EMISSIVITY": 95, "CORR_FACTOR": 99}

        # Test Update with unknown register
        addr = 0x99
        assert addr not in mock_regmap
        updated_fields = mock_fieldmap._update_field_values({addr: 1})
        assert updated_fields == {}

    def test_warn_disabled_fields(self, mock_fieldmap: SenxorFieldsManager):
        assert mock_fieldmap.TEMP_UNITS.enabled is False
        with capture_logs() as logs:
            mock_fieldmap._warn_disabled_fields({"TEMP_UNITS": 1})
        assert len(logs) == 1
        assert logs[0]["log_level"] == "warning"

    @pytest.mark.parametrize(
        ("reg_value", "bits_range", "expected"),
        [
            (0b00000000, (0, 1), 0),
            (0b00000001, (0, 1), 1),
            (0b00000010, (0, 1), 0),
            (0b00000111, (0, 3), 7),
            (0b11111111, (0, 8), 255),
            (0b11111111, (0, 7), 127),
            (0b00001100, (2, 4), 3),
        ],
    )
    def test_decode_field_value(self, reg_value: int, bits_range: tuple[int, int], expected: int):
        result = SenxorFieldsManager._decode_field_value(reg_value, bits_range)
        assert result == expected

    @pytest.mark.parametrize(
        ("reg_value", "field_value", "bits_range", "expected"),
        [
            # --- 1-bit field (bit 0) ---
            (0b00000000, 0, (0, 1), 0b00000000),  # write 0 to 0
            (0b00000000, 1, (0, 1), 0b00000001),  # write 1 to 0
            (0b11111111, 0, (0, 1), 0b11111110),  # write 0 to 1
            (0b11111111, 1, (0, 1), 0b11111111),  # write 1 to 1
            # --- 2-bit field (bits 1-2) ---
            (0b00000000, 0, (1, 3), 0b00000000),  # write 0 to 00
            (0b00000000, 3, (1, 3), 0b00000110),  # write 3 to 00
            (0b11111111, 0, (1, 3), 0b11111001),  # write 0 to 11
            (0b11111111, 3, (1, 3), 0b11111111),  # write 3 to 11
            # --- 4-bit field (bits 4-7) ---
            (0b00000000, 0xA, (4, 8), 0b10100000),  # write 0xA to 0000
            (0b11110000, 0x5, (4, 8), 0b01010000),  # write 0x5 to 1111
            # --- 8-bit field (bits 0-7) ---
            (0b00000000, 0x55, (0, 8), 0x55),  # write 0x55 to 0x00
            (0b11111111, 0xAA, (0, 8), 0xAA),  # write 0xAA to 0xFF
            # --- nibble overwrite (bits 0-3) ---
            (0b11110000, 0x0F, (0, 4), 0b11111111),  # lower nibble overwrite
            (0b00001111, 0xF, (4, 8), 0b11111111),  # upper nibble overwrite
            # --- edge cases ---
            (0b10101010, 0, (3, 4), 0b10100010),  # single bit in middle
            (0b00000000, 0b111, (5, 8), 0b11100000),  # unaligned 3-bit
        ],
    )
    def test_encode_field_value(self, reg_value: int, field_value: int, bits_range: tuple[int, int], expected: int):
        result = SenxorFieldsManager._encode_field_value(reg_value, field_value, bits_range)
        print(
            f"reg_value: {reg_value:08b}, field_value: {field_value:08b}, bits_range: {bits_range}, "
            f"expected: {expected:08b}, result: {result:08b}",
        )
        assert result == expected
