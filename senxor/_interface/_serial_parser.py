# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from senxor.error import SenxorAckInvalidError


class SenxorAckParser:
    # ---------------------------------------------
    # The Serial and TCP/IP interfaces follow the same communication
    # message format.
    #
    # The only difference is the communication method,
    # e.g. Serial.read() and Serial.write(),
    #      TCP/IP.recv() and TCP/IP.send().
    #
    # So, we can define the common communication message format here,
    # and the actual communication method can be implemented in the
    # derived classes.
    # ---------------------------------------------
    # Message Format
    # --------------
    # Message Header
    # Both write command and ack message have the same header format.
    #
    #      | PREFIX: '   #'  | MSG LENGTH |  MSG BODY    |
    # LEN: |        4        |     4      | MSG LENGTH   |
    #
    # The PREFIX is always "   #"
    # example:
    # '   #000ARREGB1XXXX': length: '000A' -> 10, body: 'RREGB1XXXX'
    # '   #0008WREG01FD': length: '0008' -> 8, body: 'WREG01FD'
    #
    # Message Body
    #
    #      |   CMD  | CONTENTS | CHECKSUM |
    # LEN: |    4   |   VARY   |    4     |
    #
    # e.g.
    # 'RREGB1XXXX': cmd: 'RREG', contents: 'B1', checksum: 'XXXX'
    # 'WREG01FD': cmd: 'WREG', contents: '', checksum: '01FD'

    ACK_HEADER = b"   #"

    ACK_LENGTH_LENGTH = 4
    ACK_CMD_LENGTH = 4
    ACK_CHECKSUM_LENGTH = 4

    ACK_HEADER_IDX = slice(0, 4)
    ACK_LENGTH_IDX = slice(4, 8)
    ACK_CMD_IDX = slice(8, 12)

    ACK_DATA_START_IDX = 12

    def __init__(self, logger):
        self.logger = logger

    def is_buffer_empty(self, buffer: bytearray) -> bool:
        return len(buffer) < self.ACK_LENGTH_IDX.stop

    def is_buffer_unaligned(self, buffer: bytearray) -> bool:
        # call `is_buffer_empty` first
        return not buffer.startswith(self.ACK_HEADER)

    def is_buffer_pending(self, buffer: bytearray) -> bool:
        # call `is_buffer_unaligned` first
        length = self.parse_ack_header(buffer)
        return len(buffer) < self.ACK_LENGTH_IDX.stop + length

    def parse_ack(self, buffer: bytearray) -> tuple[str, bytearray, int]:
        # Call `has_ack_prefix` and `has_enough_data` before calling this method.
        ack_len = self.parse_ack_header(buffer)
        cmd, data = self.parse_ack_body(buffer, ack_len)
        total_len = self.ACK_LENGTH_IDX.stop + ack_len
        return cmd, data, total_len

    def parse_ack_header(self, buffer: bytearray) -> int:
        length_str = buffer[self.ACK_LENGTH_IDX]
        try:
            length = int(length_str, base=16)
        except Exception as e:
            raise SenxorAckInvalidError(f"Invalid ack length: {length_str}") from e
        return length

    def parse_ack_body(self, buffer: bytearray, ack_len: int) -> tuple[str, bytearray]:
        length_bytes = bytes(buffer[self.ACK_LENGTH_IDX])
        cmd_bytes = bytes(buffer[self.ACK_CMD_IDX])

        data_start = self.ACK_DATA_START_IDX
        data_len = ack_len - self.ACK_CHECKSUM_LENGTH - self.ACK_CMD_LENGTH
        data_stop = data_start + data_len

        # Keep data_bytes as bytearray to avoid copying large data
        data_bytes = buffer[data_start:data_stop]

        checksum_start = data_stop
        checksum_stop = checksum_start + self.ACK_CHECKSUM_LENGTH
        checksum_bytes = bytes(buffer[checksum_start:checksum_stop])

        cmd = self._parse_cmd(cmd_bytes)
        checksum = self.parse_checksum(checksum_bytes)

        self.validate_checksum(checksum, length_bytes, cmd_bytes, data_bytes)
        return cmd, data_bytes

    def _parse_cmd(self, cmd: bytes) -> str:
        cmd_str = cmd.decode("ascii")
        if not cmd_str.isalpha():
            raise SenxorAckInvalidError(f"Invalid ack cmd: {cmd_str}")
        return cmd_str

    def parse_checksum(self, checksum: bytes) -> int:
        try:
            checksum_value = int(checksum, base=16)
        except Exception as e:
            raise SenxorAckInvalidError(f"Invalid ack checksum: {checksum}") from e
        return checksum_value

    def validate_checksum(self, checksum: int, len_bytes: bytes, cmd_bytes: bytes, data_bytes: bytearray) -> bool:
        actual_checksum = (sum(len_bytes) + sum(cmd_bytes) + sum(data_bytes)) & 0xFFFF
        if actual_checksum != checksum:
            raise SenxorAckInvalidError(f"Checksum mismatch: {actual_checksum:04X} != {checksum:04X}")
        return True


@dataclass
class GFRAData:
    header_slice: slice | None
    data_slice: slice
    data_len: int


class SenxorAckDecoder:
    # ------------------------------------------------
    # Details:
    #
    #  W/R |  CMD   | MSG LENGTH |   MSG BODY
    #      | ------ | ---------- | ------------------------------------------------------ |
    #  W   |  RREG  |    000A    | RREG{REG_ADDR:2x}XXXX
    #      |  WREG  |    000C    | WREG{REG_ADDR:2x}{REG_VALUE:2x}XXXX
    #      |  RRSE  |    VARY    | RRSE{REG_ADDR:2x}...{REG_ADDR:2x}FFXXXX
    #      | ------ | ---------- | ------------------------------------------------------ |
    #  R   |  RREG  |    000A    | RREG{REG_VALUE:2x}{CHECKSUM:4x}
    # (ACK)|  WREG  |    0008    | WREG01FD  # The checksum is always 01FD
    #      |  RRSE  |    VARY    | RRSE{REG_ADDR:2x}{REG_VALUE:2x}...{CHECKSUM:4x}
    #      |  GFRA  |    VARY    | GFRA{RESERVED:vary}{HEADER:vary}{DATA:vary}{CHECKSUM:4x}
    #
    # W: the command is sent to the device.
    # R(ACK): the acknowledgement message from the device.
    #
    # The checksum is the sum of (MSG LENGTH + MSG BODY)
    # e.g. sum(b"0008WREG") & 0xFFFF = 0x01FD -> '0008WREG01FD'
    # For write command, do not need checksum, use 'XXXX' instead.
    # The contents of GFRA depends on the sensor type and frame mode.
    # ------------------------------------------------

    # ------------------------------------------------
    # GFRA FORMAT:
    #
    #        |   CMD  |   RESERVED   |  HEADER |     DATA      | CHECKSUM |
    # MI08   |  GFRA  |    80 * 2    |  80 * 2 |  80 * 62 * 2  |    4     | data_len: 10240 body_len: 10248(0x2808)
    # MI16   |  GFRA  |  3 * 160 * 2 | 160 * 2 | 160 * 120 * 2 |    4     | data_len: 39680 body_len: 39688(0x9B08)
    #
    # ------------------------------------------------

    MI08_NOHEADER = GFRAData(None, slice(160, 10080), 10080)
    MI08 = GFRAData(slice(160, 320), slice(320, 10240), 10240)
    MI16_NOHEADER = GFRAData(None, slice(960, 39360), 39360)
    MI16 = GFRAData(slice(960, 1280), slice(1280, 39680), 39680)

    GFRA_DATA_MAP: ClassVar = {
        MI08_NOHEADER.data_len: MI08_NOHEADER,
        MI08.data_len: MI08,
        MI16_NOHEADER.data_len: MI16_NOHEADER,
        MI16.data_len: MI16,
    }

    @staticmethod
    def _parse_ack_rreg(data: bytearray) -> int:
        try:
            value = int(data, base=16)
        except Exception as e:
            raise SenxorAckInvalidError(f"Invalid ack rreg: {data}") from e
        return value

    @staticmethod
    def _parse_ack_wreg(data: bytearray) -> bool:
        if data != b"":
            raise SenxorAckInvalidError(f"Invalid ack wreg: {data}")
        return True

    @staticmethod
    def _parse_ack_rrse(data: bytearray) -> dict[int, int]:
        key_value_pairs = data.decode("ascii")
        if len(key_value_pairs) % 4 != 0:
            raise SenxorAckInvalidError(f"Invalid ack rrse: {data}")
        reg_values = {}
        for i in range(0, len(key_value_pairs), 4):
            reg_addr = int(key_value_pairs[i : i + 2], base=16)
            reg_value = int(key_value_pairs[i + 2 : i + 4], base=16)
            reg_values[reg_addr] = reg_value
        return reg_values

    @staticmethod
    def _parse_ack_gfra(data: bytearray) -> tuple[bytearray | None, bytearray]:
        data_len = len(data)
        struct = SenxorAckDecoder.GFRA_DATA_MAP[data_len]
        header = None if struct.header_slice is None else data[struct.header_slice]
        temp_data = data[struct.data_slice]

        return header, temp_data


class SenxorCmdEncoder:
    @staticmethod
    def encode_ack_rreg(reg: int) -> bytes:
        return f"   #000ARREG{reg:02X}XXXX".encode("ascii")

    @staticmethod
    def encode_ack_wreg(reg: int, value: int) -> bytes:
        return f"   #000CWREG{reg:02X}{value:02X}XXXX".encode("ascii")

    @staticmethod
    def encode_ack_rrse(regs: list[int]) -> bytes:
        len_regs = len(regs)
        cmd_length = 2 * len_regs + 10
        reg_list = "".join([f"{reg:02X}" for reg in regs])
        return f"   #{cmd_length:04X}RRSE{reg_list}FFXXXX".encode("ascii")
