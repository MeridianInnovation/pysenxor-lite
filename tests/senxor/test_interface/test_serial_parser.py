import logging

import pytest

from senxor._interface._serial_parser import SenxorAckDecoder, SenxorAckParser, SenxorCmdEncoder
from senxor.error import SenxorAckInvalidError


class TestSenxorCmdEncoder:
    @pytest.mark.parametrize(
        ("reg", "expected_cmd"),
        [
            (0x01, b"   #000ARREG01XXXX"),
            (0xB2, b"   #000ARREGB2XXXX"),
        ],
    )
    def test_encode_ack_rreg(self, reg, expected_cmd):
        cmd = SenxorCmdEncoder.encode_ack_rreg(reg)
        assert cmd == expected_cmd

    @pytest.mark.parametrize(
        ("reg", "value", "expected_cmd"),
        [
            (0x01, 0x02, b"   #000CWREG0102XXXX"),
            (0xB2, 0x02, b"   #000CWREGB202XXXX"),
        ],
    )
    def test_encode_ack_wreg(self, reg, value, expected_cmd):
        cmd = SenxorCmdEncoder.encode_ack_wreg(reg, value)
        assert cmd == expected_cmd

    @pytest.mark.parametrize(
        ("regs", "expected_cmd"),
        [
            ([0x01, 0x02], b"   #000ERRSE0102FFXXXX"),
            ([0xB1, 0xB2, 0xB3], b"   #0010RRSEB1B2B3FFXXXX"),
            ([0xD3], b"   #000CRRSED3FFXXXX"),
            ([0xC1] * 10, b"   #001ERRSE" + b"C1" * 10 + b"FFXXXX"),
        ],
    )
    def test_encode_ack_rrse(self, regs, expected_cmd):
        cmd = SenxorCmdEncoder.encode_ack_rrse(regs)
        assert cmd == expected_cmd


class TestSenxorAckParser:
    @pytest.fixture
    def parser(self):
        logger = logging.getLogger("test")
        return SenxorAckParser(logger)

    def test_is_buffer_empty(self, parser: SenxorAckParser):
        assert parser.is_buffer_empty(bytearray())
        assert parser.is_buffer_empty(bytearray(b"   "))
        assert parser.is_buffer_empty(bytearray(b"   #000"))
        assert not parser.is_buffer_empty(bytearray(b"   #000A"))

    def test_is_buffer_unaligned(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #000ARREG01XXXX")
        assert not parser.is_buffer_unaligned(buffer)

        buffer = bytearray(b"invalid")
        assert parser.is_buffer_unaligned(buffer)

    def test_is_buffer_pending(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #000ARREG01XXXX")
        assert not parser.is_buffer_pending(buffer)

        buffer = bytearray(b"   #000ARREG")
        assert parser.is_buffer_pending(buffer)

    def test_parse_ack_header(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #000ARREG01XXXX")
        length = parser.parse_ack_header(buffer)
        assert length == 10

    def test_parse_ack_header_invalid(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #INVALID")
        with pytest.raises(SenxorAckInvalidError):
            parser.parse_ack_header(buffer)

    def test_parse_checksum(self, parser: SenxorAckParser):
        checksum_bytes = b"01FD"
        checksum = parser.parse_checksum(checksum_bytes)
        assert checksum == 0x01FD

    def test_parse_checksum_invalid(self, parser: SenxorAckParser):
        checksum_bytes = b"INVALID"
        with pytest.raises(SenxorAckInvalidError):
            parser.parse_checksum(checksum_bytes)

    def test_validate_checksum(self, parser: SenxorAckParser):
        len_bytes = b"0008"
        cmd_bytes = b"WREG"
        data_bytes = bytearray()
        checksum = 0x01FD
        assert parser.validate_checksum(checksum, len_bytes, cmd_bytes, data_bytes)

    def test_validate_checksum_mismatch(self, parser: SenxorAckParser):
        len_bytes = b"0008"
        cmd_bytes = b"WREG"
        data_bytes = bytearray()
        checksum = 0x0000
        with pytest.raises(SenxorAckInvalidError):
            parser.validate_checksum(checksum, len_bytes, cmd_bytes, data_bytes)

    def test_parse_ack(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #0008WREG01FD")
        cmd, data, total_len = parser.parse_ack(buffer)
        assert cmd == "WREG"
        assert data == b""
        assert total_len == 16

    def test_parse_ack_rreg(self, parser: SenxorAckParser):
        buffer = bytearray(b"   #000ARREG010262")
        cmd, data, total_len = parser.parse_ack(buffer)
        assert cmd == "RREG"
        assert data == b"01"
        assert total_len == 18


class TestSenxorAckDecoder:
    def test_parse_ack_rreg(self):
        data = bytearray(b"01")
        result = SenxorAckDecoder._parse_ack_rreg(data)
        assert result == 0x01

    def test_parse_ack_rreg_invalid(self):
        data = bytearray(b"INVALID")
        with pytest.raises(SenxorAckInvalidError):
            SenxorAckDecoder._parse_ack_rreg(data)

    def test_parse_ack_wreg(self):
        data = bytearray(b"")
        result = SenxorAckDecoder._parse_ack_wreg(data)
        assert result is True

    def test_parse_ack_wreg_invalid(self):
        data = bytearray(b"INVALID")
        with pytest.raises(SenxorAckInvalidError):
            SenxorAckDecoder._parse_ack_wreg(data)

    def test_parse_ack_rrse(self):
        data = bytearray(b"0102B1B2")
        result = SenxorAckDecoder._parse_ack_rrse(data)
        expected = {0x01: 0x02, 0xB1: 0xB2}
        assert result == expected

    def test_parse_ack_rrse_invalid_length(self):
        data = bytearray(b"0102B1")
        with pytest.raises(SenxorAckInvalidError):
            SenxorAckDecoder._parse_ack_rrse(data)

    def test_parse_ack_gfra_mi08(self):
        data = bytearray(b"0" * 10240)
        header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
        assert header is not None
        assert len(temp_data) == 9920

    def test_parse_ack_gfra_mi08_noheader(self):
        data = bytearray(b"0" * 10080)
        header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
        assert header is None
        assert len(temp_data) == 9920

    def test_parse_ack_gfra_mi16(self):
        data = bytearray(b"0" * 39680)
        header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
        assert header is not None
        assert len(temp_data) == 38400

    def test_parse_ack_gfra_mi16_noheader(self):
        data = bytearray(b"0" * 39360)
        header, temp_data = SenxorAckDecoder._parse_ack_gfra(data)
        assert header is None
        assert len(temp_data) == 38400
