# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Message length parsing for MI6 command replies and image frames."""

from __future__ import annotations

from senxor.error import SenxorAckInvalidError
from senxor.interface.serial_port.parser import SenxorAckParser

_BINARY_LENGTH_COMMANDS = {b"GRGB", b"GFUC", b"GFUS"}
_MAX_PACKET_LENGTH = 1 << 20


class MI6AckParser(SenxorAckParser):
    """Parse MI6 replies using the length encoding selected by the message tag.

    Notes
    -----
    GRGB, GFUC, and GFUS use a four-byte little-endian length. Other replies
    use a four-character ASCII hexadecimal length.

    """

    def is_buffer_pending(self, buffer: bytearray) -> bool:
        """Check whether more data is needed to parse a reply.

        Parameters
        ----------
        buffer : bytearray
            The receive buffer, aligned to a reply prefix.

        Returns
        -------
        bool
            Whether the command header or the remaining reply is incomplete.
            Invalid complete headers also return False.

        """
        if len(buffer) < self.ACK_DATA_START_IDX:
            return True
        try:
            return super().is_buffer_pending(buffer)
        except SenxorAckInvalidError:
            return False

    def parse_ack_header(self, buffer: bytearray) -> int:
        """Parse the reply length from a complete MI6 header.

        Parameters
        ----------
        buffer : bytearray
            The receive buffer containing the prefix, length, and command tag.

        Returns
        -------
        int
            The message body length, including the command and checksum.

        Raises
        ------
        SenxorAckInvalidError
            If the length encoding is invalid or the body length is outside
            the range from 8 bytes to 1 MiB.

        """
        if bytes(buffer[self.ACK_CMD_IDX]) in _BINARY_LENGTH_COMMANDS:
            length = int.from_bytes(buffer[self.ACK_LENGTH_IDX], byteorder="little")
        else:
            length = super().parse_ack_header(buffer)
        if not self.ACK_CMD_LENGTH + self.ACK_CHECKSUM_LENGTH <= length <= _MAX_PACKET_LENGTH:
            raise SenxorAckInvalidError(f"Invalid ack length: {length}")
        return length
