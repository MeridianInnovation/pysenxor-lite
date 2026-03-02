# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Top-level package for Senxor devices."""

from senxor.core import Senxor
from senxor.utils import connect, list_senxor

__all__ = ["Senxor", "connect", "list_senxor"]
