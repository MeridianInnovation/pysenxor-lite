# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Register system for the senxor."""

from senxor.regmap.core import SenxorRegistersManager
from senxor.regmap.fields import Fields
from senxor.regmap.registers import Registers

__all__ = ["Fields", "Registers", "SenxorRegistersManager"]
