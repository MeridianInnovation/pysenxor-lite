# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Register and field definitions for MI6 devices."""

from __future__ import annotations

from senxor.regmap.base import Field, FieldDescriptor, Register, RegisterDescriptor, describe, describe_field
from senxor.regmap.core import SenxorFieldsManager, SenxorRegistersManager
from senxor.regmap.fields import Fields
from senxor.regmap.registers import Registers

__all__ = [
    "MI6FieldsManager",
    "MI6RegistersManager",
]


class MI6FieldsManager(SenxorFieldsManager):
    """The Senxor field system with MI6 stream and image processing controls."""

    @describe_field
    class DNCNN_ENABLE(Field):
        name = "DNCNN_ENABLE"
        description = "Enable DnCNN"
        help = "Enable DnCNN image processing."
        address = 0x34
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_ENABLE(Field):
        name = "DETECTION_ENABLE"
        description = "Enable detection"
        help = "Run YOLO detection when enabled, or pause it when disabled."
        address = 0x34
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class FUSION_STYLE(Field):
        name = "FUSION_STYLE"
        description = "Fusion display style"
        help = "Select blend (0), hot regions (1), edges (2), or raw index (3)."
        address = 0x35
        bits_range = (0, 2)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return ("blend", "hot_regions", "edges", "raw_index")[value]

    @describe_field
    class FUSION_SHRINK_STEP(Field):
        name = "FUSION_SHRINK_STEP"
        description = "Fusion mask shrink step"
        help = "Steps 0 to 7 correspond to 0, 3, 5, 7, 9, 11, 13, and 15 thermal pixels."
        address = 0x35
        bits_range = (2, 5)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return f"{(0, 3, 5, 7, 9, 11, 13, 15)[value]} px"

    @describe_field
    class FUSION_MASK_ENABLE(Field):
        name = "FUSION_MASK_ENABLE"
        description = "Enable the fusion thermal mask"
        help = "Limit thermal content to the detected regions."
        address = 0x35
        bits_range = (5, 6)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_BOXES_ENABLE(Field):
        name = "DETECTION_BOXES_ENABLE"
        description = "Draw detection boxes"
        help = "Draw boxes instead of outlines when the detection overlay is enabled."
        address = 0x35
        bits_range = (6, 7)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_OVERLAY_ENABLE(Field):
        name = "DETECTION_OVERLAY_ENABLE"
        description = "Enable the detection overlay"
        help = "Draw detection results on the fusion image."
        address = 0x35
        bits_range = (7, 8)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_PERSON_ENABLE(Field):
        name = "DETECTION_PERSON_ENABLE"
        description = "Enable person detections"
        help = "Include the person category in detection results."
        address = 0x38
        bits_range = (0, 1)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_DRINKWARE_ENABLE(Field):
        name = "DETECTION_DRINKWARE_ENABLE"
        description = "Enable drinkware detections"
        help = "Include the drinkware category in detection results."
        address = 0x38
        bits_range = (1, 2)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_APPLIANCES_ENABLE(Field):
        name = "DETECTION_APPLIANCES_ENABLE"
        description = "Enable appliance detections"
        help = "Include the appliances category in detection results."
        address = 0x38
        bits_range = (2, 3)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"

    @describe_field
    class DETECTION_OTHER_ENABLE(Field):
        name = "DETECTION_OTHER_ENABLE"
        description = "Enable other detections"
        help = "Include the other category in detection results."
        address = 0x38
        bits_range = (3, 4)
        writable = True
        readable = True
        self_reset = True
        available = True

        def get_display(self, value: int) -> str:
            return "Enabled" if value == 1 else "Disabled"


class MI6RegistersManager(SenxorRegistersManager):
    """The Senxor register system with MI6-specific control registers."""

    @describe
    class STREAM_CTRL(Register):
        name = "STREAM_CTRL"
        description = "Select MI6 image streams"
        address = 0xB5
        writable = True
        readable = False
        self_reset = True
        enabled = True
        default_value = None

    @describe
    class DETECTION_CTRL(Register):
        name = "DETECTION_CTRL"
        description = "Control DnCNN and detection"
        address = 0x34
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = None

    @describe
    class FUSION_CTRL(Register):
        name = "FUSION_CTRL"
        description = "Control fusion style, mask, and detection overlay"
        address = 0x35
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = None

    @describe
    class DETECTION_TYPES(Register):
        name = "DETECTION_TYPES"
        description = "Select detection categories"
        address = 0x38
        writable = True
        readable = True
        self_reset = True
        enabled = True
        default_value = None

    @describe
    class FUSION_DISTANCE(Register):
        name = "FUSION_DISTANCE"
        description = "Fusion working distance"
        address = 0x39
        writable = True
        readable = True
        self_reset = False
        enabled = True
        default_value = 0x14

    def _create_fieldmap(self) -> MI6FieldsManager:
        """Create the MI6 field manager."""
        return MI6FieldsManager(self)


MI6RegistersManager.__regs__ = [register for register in Registers.__regs__ if register.address != 0xB5] + [
    value.cls for value in MI6RegistersManager.__dict__.values() if isinstance(value, RegisterDescriptor)
]
MI6RegistersManager.__addrs__ = {register.address: register.name for register in MI6RegistersManager.__regs__}

MI6FieldsManager.__fields__ = [field for field in Fields.__fields__ if field.address != 0xB5] + [
    value.cls for value in MI6FieldsManager.__dict__.values() if isinstance(value, FieldDescriptor)
]
MI6FieldsManager.__reg2fields__ = {addr: [] for addr in MI6RegistersManager.__addrs__}
for field in MI6FieldsManager.__fields__:
    MI6FieldsManager.__reg2fields__[field.address].append(field.name)
