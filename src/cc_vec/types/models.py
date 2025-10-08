"""Data models for cc-vec."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator


class CrawlRecord(BaseModel):
    """Represents a record from Common Crawl index."""

    url: HttpUrl
    urlkey: str
    timestamp: str
    status: int = Field(ge=100, le=599)  # Valid HTTP status codes
    mime: Optional[str] = None
    digest: Optional[str] = None
    length: Optional[int] = Field(None, ge=0)
    offset: Optional[int] = Field(None, ge=0)
    filename: Optional[str] = None
    languages: Optional[List[str]] = None
    charset: Optional[str] = None

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp format (Common Crawl uses yyyyMMddhhmmss)."""
        if len(v) not in [4, 6, 8, 10, 12, 14]:
            raise ValueError("Timestamp must be in format yyyy, yyyyMM, yyyyMMdd, etc.")
        return v


class ProcessedContent(BaseModel):
    """Represents content after processing and cleaning."""

    source_url: HttpUrl
    title: Optional[str] = None
    text: str
    chunks: List[str] = Field(min_length=1)  # Must have at least one chunk
    language: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None
    processing_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("chunks")
    @classmethod
    def validate_chunks(cls, v):
        """Ensure chunks are not empty."""
        if not v or all(not chunk.strip() for chunk in v):
            raise ValueError("Chunks cannot be empty")
        return v


class FilterConfig(BaseModel):
    """Configuration for filtering Common Crawl data."""

    url_patterns: List[str] = Field(min_length=1)  # Must have at least one pattern
    status_codes: Optional[List[int]] = Field(default=[200])
    mime_types: Optional[List[str]] = Field(default=["text/html"])
    languages: Optional[List[str]] = None
    date_from: Optional[str] = None  # Format: yyyy, yyyyMM, or yyyyMMdd
    date_to: Optional[str] = None
    custom_filters: Optional[List[str]] = None  # Additional CDX filter strings

    @field_validator("status_codes")
    @classmethod
    def validate_status_codes(cls, v):
        """Validate HTTP status codes."""
        if v:
            for code in v:
                if not (100 <= code <= 599):
                    raise ValueError(f"Invalid HTTP status code: {code}")
        return v

    @field_validator("url_patterns")
    @classmethod
    def validate_url_patterns(cls, v):
        """Ensure URL patterns are not empty."""
        if not v or all(not pattern.strip() for pattern in v):
            raise ValueError("URL patterns cannot be empty")
        return v
