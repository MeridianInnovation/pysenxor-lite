from senxor.core import Senxor
from tests.senxor.conftest import MockInterface


class TestSenxorFieldsChangedCallback:
    def test_user_callback_on_register_write(self, mock_interface: MockInterface):
        received: list[dict[str, int]] = []

        senxor = Senxor(mock_interface, auto_open=False)
        senxor.on_fields_changed(received.append)

        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)
        assert received == [{"EMISSIVITY": 95}]

        senxor.write_reg(reg.address, 95)
        assert received == [{"EMISSIVITY": 95}]

    def test_clear_user_callback(self, mock_interface: MockInterface):
        received: list[dict[str, int]] = []

        senxor = Senxor(mock_interface, auto_open=False)
        senxor.on_fields_changed(received.append)
        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)

        senxor.on_fields_changed(None)
        senxor.write_reg(reg.address, 96)
        assert received == [{"EMISSIVITY": 95}]

    def test_no_callback_by_default(self, mock_interface: MockInterface):
        senxor = Senxor(mock_interface, auto_open=False)
        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)
