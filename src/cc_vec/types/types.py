"""Library-specific types and result classes."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SearchResult:
    """Result from cc_search method."""

    url: str
    timestamp: str
    status: int
    mime_type: str
    length: int


@dataclass
class SearchResponse:
    """Response from cc_search method."""

    results: List[SearchResult]
    total_found: int
    backend: str  # "athena" or "cdx"
    crawl_id: Optional[str] = None


@dataclass
class PerCrawlStats:
    """Statistics for a single crawl."""

    crawl_id: str
    estimated_records: int
    estimated_size_mb: float
    estimated_cost_usd: float
    data_scanned_gb: float


@dataclass
class StatsResponse:
    """Response from cc_stats method."""

    per_crawl_stats: List[PerCrawlStats]
    total_estimated_records: int
    total_estimated_size_mb: float
    total_estimated_cost_usd: float
    total_data_scanned_gb: float
    backend: str = "athena"


@dataclass
class ProcessResponse:
    """Response from cc_process method."""

    pipeline_name: str
    total_processed: int
    successful: int
    failed: int
    success_rate: float
    duration_seconds: float
    backend: str
    dry_run: bool
    vector_store_name: Optional[str] = None


@dataclass
class MonitorResponse:
    """Response from cc_monitor method."""

    has_active_pipeline: bool
    pipeline_name: Optional[str] = None
    status: Optional[str] = None
    processed_records: Optional[int] = None
    total_records: Optional[int] = None
    success_rate: Optional[float] = None
    duration_seconds: Optional[float] = None
    recent_errors: List[str] = field(default_factory=list)


@dataclass
class VectorStore:
    """Vector store information."""

    name: str
    id: str
    file_count: int
    status: str
    created_at: Optional[datetime] = None


@dataclass
class VectorStoresResponse:
    """Response from cc_list_vector_stores method."""

    stores: List[VectorStore]
    total_count: int


@dataclass
class VectorSearchResult:
    """Single vector search result."""

    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorSearchResponse:
    """Response from cc_vector_search method."""

    results: List[VectorSearchResult]
    query: str
    vector_store_name: str
    total_found: int
