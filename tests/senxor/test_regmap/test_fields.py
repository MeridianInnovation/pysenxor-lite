from typing import TYPE_CHECKING

from senxor.regmap import Fields, Registers

if TYPE_CHECKING:
    from senxor.regmap.base import Field, Register


class TestFields:
    def test_field_bit_ranges_do_not_overlap(self):
        """Ensure no two fields of the same register overlap in their bit positions."""
        reg_bitmap: dict[int, int] = {}
        overlaps = []

        for field in Fields.__fields__:
            addr = field.address
            start_bit, end_bit = field.bits_range

            field_mask = ((1 << (end_bit - start_bit)) - 1) << start_bit

            if addr not in reg_bitmap:
                reg_bitmap[addr] = 0

            if reg_bitmap[addr] & field_mask:
                overlaps.append(f"{field.name} (bits {start_bit}-{end_bit}) overlaps at 0x{addr:02X}")

            reg_bitmap[addr] |= field_mask

        assert not overlaps, "Field bit range overlaps detected:\n" + "\n".join(overlaps)

    def test_field_addresses_are_valid(self):
        """Ensure all field addresses are valid register addresses."""
        for field in Fields.__fields__:
            assert field.address in Registers.__addrs__

    def test_field_required_attributes(self):
        """Ensure all fields have required attributes."""
        for field in Fields.__fields__:
            assert hasattr(field, "name")
            assert hasattr(field, "description")
            assert hasattr(field, "address")
            assert hasattr(field, "bits_range")
            assert hasattr(field, "writable")
            assert hasattr(field, "readable")
            assert hasattr(field, "available")
            assert field.writable or field.readable

    def test_reg2fields_consistency(self):
        """Ensure __reg2fields__ mapping is consistent with field definitions."""
        for addr, field_names in Fields.__reg2fields__.items():
            assert addr in Registers.__addrs__
            for field_name in field_names:
                assert hasattr(Fields, field_name)
                field: Field = getattr(Fields, field_name)
                assert field.address == addr

    def test_field_names_are_unique(self):
        """Ensure all field names are unique."""
        field_names = [field.name for field in Fields.__fields__]
        assert len(field_names) == len(set(field_names))

    def test_field_self_reset_consistency(self):
        for field in Fields.__fields__:
            reg_name = Registers.__addrs__[field.address]
            reg: Register = getattr(Registers, reg_name)
            if field.self_reset:
                assert reg.self_reset
