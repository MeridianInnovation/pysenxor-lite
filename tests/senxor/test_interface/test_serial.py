import pytest

from senxor._interface.parser import SenxorMsgParser


class TestSenxorInterfaceBase:
    @pytest.fixture
    def interface(self) -> SenxorMsgParser:
        return SenxorMsgParser()

    def test_init(self, interface):
        assert interface is not None

    @pytest.mark.parametrize(
        "reg, expected_cmd",
        [
            (0x01, b"   #000ARREG01XXXX"),
            (0xB2, b"   #000ARREGB2XXXX"),
        ],
    )
    def test_get_rreg_cmd(self, interface, reg, expected_cmd):
        cmd = SenxorMsgParser._get_rreg_cmd(reg)
        assert cmd == expected_cmd

    @pytest.mark.parametrize(
        "invalid_reg",
        # The interface only checks the type of the register address.
        [
            1.5,
            "0x01",
            None,
        ],
    )
    def test_get_rreg_cmd_invalid(self, interface, invalid_reg):
        with pytest.raises((ValueError, TypeError)):
            SenxorMsgParser._get_rreg_cmd(invalid_reg)

    @pytest.mark.parametrize(
        "reg, value, expected_cmd",
        [
            (0x01, 0x02, b"   #000CWREG0102XXXX"),
            (0xB2, 0x02, b"   #000CWREGB202XXXX"),
        ],
    )
    def test_get_wreg_cmd(self, interface, reg, value, expected_cmd):
        cmd = SenxorMsgParser._get_wreg_cmd(reg, value)
        assert cmd == expected_cmd

    @pytest.mark.parametrize(
        "invalid_params",
        [
            (0xB1, 2.5),
            (0xB1, "0x02"),
            (0xB1, None),
            ("0xB1", 0x02),
            (1.5, 0x02),
            (None, 0x02),
        ],
    )
    def test_get_wreg_cmd_invalid(self, interface, invalid_params):
        with pytest.raises((ValueError, TypeError)):
            SenxorMsgParser._get_wreg_cmd(*invalid_params)

    @pytest.mark.parametrize(
        "regs, expected_cmd",
        [
            ([0x01, 0x02], b"   #000ERRSE0102FFXXXX"),
            ([0xB1, 0xB2, 0xB3], b"   #0010RRSEB1B2B3FFXXXX"),
            ([0xD3], b"   #000CRRSED3FFXXXX"),
            ([0xC1] * 10, b"   #001ERRSE" + b"C1" * 10 + b"FFXXXX"),
        ],
    )
    def test_get_rrse_cmd(self, interface, regs, expected_cmd):
        cmd = SenxorMsgParser._get_rrse_cmd(regs)
        assert cmd == expected_cmd

    @pytest.mark.parametrize(
        "invalid_regs",
        [
            [1.5, 0x02],
            ["0x01", 0x02],
            [None, 0x02],
            [0x01, "0x02"],
            [0x01, None],
            [],
            None,
        ],
    )
    def test_get_rrse_cmd_invalid(self, interface, invalid_regs):
        with pytest.raises((ValueError, TypeError)):
            SenxorMsgParser._get_rrse_cmd(invalid_regs)

    @pytest.mark.parametrize(
        "msg, expected_checksum",
        [
            (b"0008WREG", b"01FD"),
            (b"000ARREG01", b"0262"),
            (b"000ARREG02", b"0263"),
        ],
    )
    def test_check_sum(self, interface, msg, expected_checksum):
        checksum = SenxorMsgParser._check_sum(msg)
        assert checksum == expected_checksum

    @pytest.mark.parametrize(
        "msg_header, expected_length",
        [
            (b"0008", 8),
            (b"000A", 10),
            (b"0010", 16),
            (b"00FF", 255),
            (b"0100", 256),
        ],
    )
    def test_parse_msg_length(self, interface, msg_header, expected_length):
        length = SenxorMsgParser._parse_msg_length(msg_header)
        assert length == expected_length

    @pytest.mark.parametrize(
        "invalid_msg_header",
        [
            b"x\x0bB\x0bY\x0b^\x0b",
            b"'b\x0bk\x0b[\x0b:\x0b",
        ],
    )
    def test_parse_msg_length_invalid(self, interface, invalid_msg_header):
        with pytest.raises((ValueError, Exception)):
            SenxorMsgParser._parse_msg_length(invalid_msg_header)
