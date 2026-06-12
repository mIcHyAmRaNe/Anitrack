"""Re-export the user-preferences singleton alongside AppConfig."""

from __future__ import annotations

from .app_config import AppConfig
from .settings import cfg

__all__ = ["AppConfig", "cfg"]
