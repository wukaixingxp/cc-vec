"""Logging configuration for cc-vec."""

import logging
from dataclasses import dataclass


@dataclass
class LoggingSettings:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @property
    def log_level(self) -> int:
        """Get logging level as integer."""
        return getattr(logging, self.level.upper(), logging.INFO)
