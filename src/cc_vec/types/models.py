"""Data models for cc-vec."""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, HttpUrl, Field, field_validator, ConfigDict


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


class VectorStoreConfig(BaseModel):
    """Configuration for vector store operations."""

    name: str = Field(min_length=1)
    provider: str = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: Optional[int] = Field(None, gt=0)
    settings: Optional[Dict[str, Any]] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v):
        """Validate supported providers."""
        supported = ["openai", "pinecone", "chroma", "weaviate"]
        if v not in supported:
            raise ValueError(f"Provider must be one of {supported}")
        return v

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v):
        """Validate embedding model names."""
        openai_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
        ]
        # For now, only validate OpenAI models
        if v not in openai_models:
            raise ValueError(f"Embedding model must be one of {openai_models}")
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


class PipelineConfig(BaseModel):
    """Configuration for the entire processing pipeline."""

    name: str = Field(min_length=1)
    filter_config: FilterConfig
    vector_store_config: Optional[VectorStoreConfig] = None

    # Processing options
    batch_size: int = Field(default=100, ge=1, le=1000)
    processing_options: Optional[Dict[str, Any]] = None

    # Validation settings
    max_pages: Optional[int] = Field(None, gt=0)
    max_size_mb: Optional[int] = Field(None, gt=0)
    require_user_confirmation: bool = Field(default=False)

    # Progress tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(validate_assignment=True)  # Validate on assignment

    @field_validator("processing_options")
    @classmethod
    def validate_processing_options(cls, v):
        """Validate processing options."""
        if v:
            allowed_keys = {
                "chunk_size",
                "chunk_overlap",
                "quality_threshold",
                "hate_speech_filtering",
                "language_detection",
                "max_chunk_size",
                "min_chunk_size",
            }
            for key in v.keys():
                if key not in allowed_keys:
                    raise ValueError(f"Unknown processing option: {key}")
        return v
