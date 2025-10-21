"""Athena configuration for cc-vec."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AthenaSettings:
    """Athena backend configuration."""

    output_bucket: Optional[str] = None
    region_name: str = "us-west-2"
    max_results: int = 100
    timeout_seconds: int = 120

    @property
    def output_location(self) -> Optional[str]:
        """Get S3 output location for Athena."""
        if not self.output_bucket:
            return None
        
        # Ensure the bucket path starts with s3://
        if self.output_bucket.startswith("s3://"):
            return self.output_bucket
        else:
            return f"s3://{self.output_bucket}/"

    def is_configured(self) -> bool:
        """Check if Athena is properly configured."""
        return bool(self.output_bucket)
