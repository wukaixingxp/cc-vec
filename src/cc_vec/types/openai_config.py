"""OpenAI configuration for cc-vec."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAISettings:
    """OpenAI API configuration."""

    api_key: Optional[str] = None
    base_url: Optional[str] = None

    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return bool(self.api_key)
