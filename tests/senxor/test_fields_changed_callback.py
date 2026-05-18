from senxor.core import Senxor
from tests.senxor.conftest import MockInterface


def _open_senxor(mock_interface: MockInterface) -> Senxor:
    mock_interface.values[0xBA] = 0
    mock_interface.values[0xB4] = 1
    mock_interface.values[0xB1] = 0
    senxor = Senxor(mock_interface, auto_open=False)
    senxor.open()
    return senxor


class TestSenxorFieldsChangedCallback:
    def test_user_callback_on_register_write(self, mock_interface: MockInterface):
        received: list[dict[str, int]] = []
        senxor = _open_senxor(mock_interface)
        senxor.on_fields_changed(received.append)

        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)
        assert received == [{"EMISSIVITY": 95}]

        senxor.write_reg(reg.address, 95)
        assert received == [{"EMISSIVITY": 95}]

    def test_clear_user_callback(self, mock_interface: MockInterface):
        received: list[dict[str, int]] = []
        senxor = _open_senxor(mock_interface)
        senxor.on_fields_changed(received.append)
        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)

        senxor.on_fields_changed(None)
        senxor.write_reg(reg.address, 96)
        assert received == [{"EMISSIVITY": 95}]

    def test_no_callback_by_default(self, mock_interface: MockInterface):
        senxor = _open_senxor(mock_interface)
        reg = senxor.regs.EMISSIVITY
        senxor.write_reg(reg.address, 95)
