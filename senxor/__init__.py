"""Top-level package for Senxor devices."""

from senxor import log  # This will configure structlog
from senxor._senxor import Senxor
from senxor.utils import connect, connect_senxor, list_senxor

__all__ = ["Senxor", "connect", "connect_senxor", "list_senxor"]
