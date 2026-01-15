import pytest
from structlog.testing import capture_logs

from senxor.regmap.base import Register
from senxor.regmap.core import SenxorRegistersManager
from tests.senxor.conftest import MockInterface


class TestRegistersManager:
    def test_attributes(self, mock_regmap: SenxorRegistersManager):
        cache = mock_regmap.cache
        for addr, value in cache.items():
            assert addr in mock_regmap.registers
            assert value is None

    def test_iter(self, mock_regmap: SenxorRegistersManager):
        assert len(list(mock_regmap)) == len(mock_regmap.registers)
        for reg in mock_regmap:
            assert isinstance(reg, Register)
            assert reg.address in mock_regmap.registers

    def test_getitem(self, mock_regmap: SenxorRegistersManager):
        reg1 = mock_regmap["EMISSIVITY"]
        assert reg1.name == "EMISSIVITY"

        addr1 = reg1.address
        assert mock_regmap[addr1].name == "EMISSIVITY"

        with pytest.raises(KeyError):
            mock_regmap["INVALID_REGISTER"]  # type: ignore[reportArgumentType]
        with pytest.raises(KeyError):
            mock_regmap[114]  # type: ignore[reportArgumentType]

    def test_contains(self, mock_regmap: SenxorRegistersManager):
        assert "MCU_RESET" in mock_regmap
        assert 0x00 in mock_regmap

        assert "INVALID_REGISTER" not in mock_regmap
        assert 0x999 not in mock_regmap

    def test_refresh_all(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        assert all(value is None for value in mock_regmap.cache.values())
        mock_interface.values = {addr: 1 for addr in mock_regmap.registers}
        mock_regmap.refresh_all()
        assert all(value == 1 for value in mock_regmap.cache.values())

    def test_get_reg(self, mock_regmap: SenxorRegistersManager):
        reg = mock_regmap.get_reg("EMISSIVITY")
        assert reg.name == "EMISSIVITY"
        addr = reg.address
        assert mock_regmap.get_reg(addr).name == "EMISSIVITY"

        with pytest.raises(KeyError):
            mock_regmap.get_reg("INVALID_REGISTER")  # type: ignore[reportArgumentType]
        with pytest.raises(KeyError):
            mock_regmap.get_reg(999)  # type: ignore[reportArgumentType]
        with pytest.raises(TypeError):
            mock_regmap.get_reg(1.0)  # type: ignore[reportArgumentType]

    def test_read_reg(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        reg_name = "EMISSIVITY"
        reg = mock_regmap.get_reg(reg_name)

        mock_interface.set_value(reg.address, 95)
        assert mock_regmap.read_reg(reg.address) == 95

        mock_interface.set_value(reg.address, 96)
        assert mock_regmap.read_reg(reg.address) == 96

        # Test with invalid address
        with pytest.raises(ValueError):  # noqa: PT011
            mock_regmap.read_reg(0x100)  # type: ignore[reportArgumentType]
        with pytest.raises(TypeError):
            mock_regmap.read_reg("INVALID")  # type: ignore[reportArgumentType]

    def test_write_reg(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        reg_name = "EMISSIVITY"
        reg = mock_regmap.get_reg(reg_name)

        mock_regmap.write_reg(reg.address, 95)
        assert reg._value == 95
        assert mock_interface.values[reg.address] == 95

        mock_regmap.write_reg(reg.address, 96)
        assert reg._value == 96
        assert mock_interface.values[reg.address] == 96

    def test_read_regs(self, mock_regmap: SenxorRegistersManager, mock_interface: MockInterface):
        reg1 = mock_regmap.get_reg("EMISSIVITY")
        reg2 = mock_regmap.get_reg("SENSITIVITY_FACTOR")

        mock_interface.set_value(reg1.address, 95)
        mock_interface.set_value(reg2.address, 99)

        result = mock_regmap.read_regs([reg1.address, reg2.address])
        assert result == {reg1.address: 95, reg2.address: 99}

        # Test with single register
        result = mock_regmap.read_regs([reg1.address])
        assert result == {reg1.address: 95}

        # Test with invalid address
        with pytest.raises(ValueError):  # noqa: PT011
            mock_regmap.read_regs([0x100])  # type: ignore[reportArgumentType]

    def test_write_reg_errors(self, mock_regmap: SenxorRegistersManager):
        # Test invalid address type
        with pytest.raises(TypeError):
            mock_regmap.write_reg("INVALID", 95)  # type: ignore[reportArgumentType]

        # Test invalid address range
        with pytest.raises(ValueError):  # noqa: PT011
            mock_regmap.write_reg(0x100, 95)  # type: ignore[reportArgumentType]
        with pytest.raises(ValueError):  # noqa: PT011
            mock_regmap.write_reg(-1, 95)  # type: ignore[reportArgumentType]

        # Test read-only register
        fw_version_reg = mock_regmap.get_reg("FW_VERSION_1")
        assert fw_version_reg.writable is False
        with pytest.raises(AttributeError):
            mock_regmap.write_reg(fw_version_reg.address, 2)

    def test_warn_unknown_reg(self, mock_regmap: SenxorRegistersManager):
        with capture_logs() as logs:
            mock_regmap._warn_unknown_reg(0x999, "read")
        assert len(logs) == 1
        assert logs[0]["log_level"] == "warning"
        assert logs[0]["op"] == "read"
        assert logs[0]["addr"] == 0x999
