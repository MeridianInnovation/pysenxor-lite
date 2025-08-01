# Copyright (c) 2025 Meridian Innovation. All rights reserved.

import numpy as np

from senxor._error import ChecksumError, InvalidAckBodyError


class SenxorMsgParser:
    """The message parser for the senxor, used for both Serial and TCP/IP interfaces."""

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
    #
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

    MSG_PREFIX = b"   #"
    LEN_MSG_PREFIX = 4
    LEN_MSG_LENGTH = 4
    LEN_MSG_HEADER = LEN_MSG_PREFIX + LEN_MSG_LENGTH

    LEN_BODY_CMD = 4
    LEN_BODY_CHECKSUM = 4

    CMD_RREG = b"RREG"
    CMD_WREG = b"WREG"
    CMD_RRSE = b"RRSE"
    CMD_GFRA = b"GFRA"

    ACK_RREG_LEN = 0x0A
    ACK_WREG = b"WREG01FD"

    # ------------------------------------------------
    # GFRA FORMAT:
    #
    #        |   CMD  |   RESERVED   |  HEADER |     DATA      | CHECKSUM |
    # MI08   |  GFRA  |    80 * 2    |  80 * 2 |  80 * 62 * 2  |    4     | total: 10248(0x2808)
    # MI16   |  GFRA  |  3 * 160 * 2 | 160 * 2 | 160 * 120 * 2 |    4     | total: 39688(0x9B08)
    #
    # ------------------------------------------------

    ACK_GFRA_LEN_MI08 = 0x2808 - LEN_BODY_CMD - LEN_BODY_CHECKSUM
    ACK_GFRA_LEN_MI16 = 0x9B08 - LEN_BODY_CMD - LEN_BODY_CHECKSUM

    ACK_GFRA_MI08_HEADER_SLICE = slice(160, 320)
    ACK_GFRA_MI08_DATA_SLICE = slice(320, 10240)

    ACK_GFRA_MI16_HEADER_SLICE = slice(960, 1280)
    ACK_GFRA_MI16_DATA_SLICE = slice(1280, 39680)

    @staticmethod
    def _get_rreg_cmd(reg: int) -> bytes:
        command = f"   #000ARREG{reg:02X}XXXX"
        command = command.encode("ascii")
        return command

    @staticmethod
    def _get_wreg_cmd(reg: int, value: int) -> bytes:
        command = f"   #000CWREG{reg:02X}{value:02X}XXXX"
        command = command.encode("ascii")
        return command

    @staticmethod
    def _get_rrse_cmd(regs: list[int]) -> bytes:
        len_regs = len(regs)
        if len_regs == 0:
            raise ValueError("regs is empty")
        cmd_length = 2 * len_regs + 10
        reg_list = "".join([f"{reg:02X}" for reg in regs])
        command = f"   #{cmd_length:04X}RRSE{reg_list}FFXXXX"
        command = command.encode("ascii")
        return command

    @staticmethod
    def _parse_ack_gfra(ack: bytes) -> tuple[np.ndarray, np.ndarray]:
        # The ack does not contain the cmd.
        ack_len = len(ack)
        if ack_len == SenxorMsgParser.ACK_GFRA_LEN_MI08:
            header = ack[SenxorMsgParser.ACK_GFRA_MI08_HEADER_SLICE]
            data = ack[SenxorMsgParser.ACK_GFRA_MI08_DATA_SLICE]
        elif ack_len == SenxorMsgParser.ACK_GFRA_LEN_MI16:
            header = ack[SenxorMsgParser.ACK_GFRA_MI16_HEADER_SLICE]
            data = ack[SenxorMsgParser.ACK_GFRA_MI16_DATA_SLICE]
        else:
            raise ValueError("Unsupported GFRA ack length", ack_len)

        header = np.frombuffer(header, dtype=np.uint16)
        data = np.frombuffer(data, dtype=np.uint16)
        return header, data

    @staticmethod
    def _parse_ack_rreg(ack: bytes) -> int:
        ack_ = ack.decode("ascii")
        reg_value = int(ack_, base=16)
        return reg_value

    @staticmethod
    def _parse_ack_rrse(ack: bytes) -> dict[int, int]:
        ack_ = ack.decode("ascii")
        len_ack = len(ack_)
        if len_ack % 4 != 0:
            raise ValueError("RRSE ack length should be the multiple of 4", len_ack)
        reg_values = {}
        for i in range(0, len_ack, 4):
            reg_addr = int(ack[i : i + 2], base=16)
            reg_value = int(ack[i + 2 : i + 4], base=16)
            reg_values[reg_addr] = reg_value
        return reg_values

    @staticmethod
    def _parse_ack_wreg(ack: bytes) -> None:
        # wreg ack should be empty
        if len(ack) != 0:
            raise ValueError("WREG ack should be empty", ack)
        return None

    @staticmethod
    def _check_sum(msg: bytes) -> bytes:
        """Calculate the checksum of a message.

        Note: This method returns a string of 4 characters in hex format instead of bytes.
        """
        # summing all bytes within the message contents
        # retaining the least significant 16 bits, and
        # encoding them as ASCII characters (hence the 4 bytes).
        checksum_int = sum(msg) & 0xFFFF
        checksum_str = f"{checksum_int:04X}"
        checksum = checksum_str.encode("ascii")
        return checksum

    @staticmethod
    def _parse_msg_length(msg_length_str: bytes) -> int:
        msg_length = int(msg_length_str, base=16)
        return msg_length

    @staticmethod
    def _parse_msg_body(msg_body: bytes) -> tuple[bytes, bytes, bytes]:
        body = msg_body[: -SenxorMsgParser.LEN_BODY_CHECKSUM]
        checksum = msg_body[-SenxorMsgParser.LEN_BODY_CHECKSUM :]
        cmd = body[: SenxorMsgParser.LEN_BODY_CMD]
        ack = body[SenxorMsgParser.LEN_BODY_CMD :]

        try:
            # When the temperature reaches to 1233.6K, the checksum can parse successfully([12336, 12336] -> 0x0000).
            # Now senxor can not read such high temperature.
            _ = int(checksum, base=16)
        except ValueError:
            # There is a bug on the windows platform.
            # the gfra data is shorter than expected, so the msg_body includes the next msg.
            next_msg_header_pos = body.find(SenxorMsgParser.MSG_PREFIX)
            if next_msg_header_pos != -1:
                err_body_length = next_msg_header_pos - 4
                expected_body_length = len(body) - 4
                raise InvalidAckBodyError(
                    f"corrupted data, expected: {expected_body_length}, actual: {err_body_length}",
                ) from None
            raise InvalidAckBodyError from None

        return cmd, ack, checksum

    @staticmethod
    def _check_msg_checksum(source: bytes, checksum: bytes) -> None:
        expected_checksum = SenxorMsgParser._check_sum(source)
        if expected_checksum != checksum:
            source_str = str(source)
            source_str = source_str[:18] if len(source_str) > 18 else source_str
            raise ChecksumError(expected_checksum, checksum)
