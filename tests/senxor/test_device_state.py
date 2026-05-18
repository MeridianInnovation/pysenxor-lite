from senxor.core import Senxor
from senxor.interface.protocol import DeviceState
from tests.senxor.conftest import MockDevice, MockInterface


def _seed_mock_values(interface: MockInterface) -> None:
    interface.values[0xBA] = 0
    interface.values[0xB4] = 10
    interface.values[0xB1] = 0


class TrackingMockInterface(MockInterface):
    def __init__(self, device: MockDevice) -> None:
        super().__init__(device)
        self.bound_states: list[DeviceState] = []

    def bind_state(self, state: DeviceState) -> None:
        super().bind_state(state)
        self.bound_states.append(state)


class TestDeviceStateSync:
    def test_open_syncs_state(self):
        interface = TrackingMockInterface(MockDevice())
        _seed_mock_values(interface)

        Senxor(interface, auto_open=True)
        assert len(interface.bound_states) >= 1
        state = interface.bound_states[-1]
        assert state.frame_shape == (62, 80)
        assert state.fps_divider == 10
        assert state.no_header is False
        assert state.is_streaming is False

    def test_field_write_syncs_state(self):
        interface = TrackingMockInterface(MockDevice())
        _seed_mock_values(interface)
        interface.values[0xB4] = 1

        senxor = Senxor(interface, auto_open=False)
        senxor.open()

        before = len(interface.bound_states)
        senxor.write_reg(senxor.regs.FRAME_MODE.address, 0b00100000)
        assert len(interface.bound_states) == before + 1
        assert interface.bound_states[-1].no_header is True

    def test_bind_state_on_default_mock(self, mock_interface: MockInterface):
        _seed_mock_values(mock_interface)
        senxor = Senxor(mock_interface, auto_open=False)
        senxor.open()
        senxor.write_reg(senxor.regs.EMISSIVITY.address, 95)
        assert mock_interface._device_state is not None

    def test_user_callback_after_state_sync(self):
        interface = TrackingMockInterface(MockDevice())
        _seed_mock_values(interface)

        senxor = Senxor(interface, auto_open=False)
        senxor.open()

        order: list[str] = []

        def on_changed(_updated: dict[str, int]) -> None:
            order.append("user")
            assert interface._device_state is not None
            assert interface._device_state.no_header is True

        senxor.on_fields_changed(on_changed)
        senxor.write_reg(senxor.regs.FRAME_MODE.address, 0b00100000)
        assert order == ["user"]
