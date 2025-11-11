"""cc-vec public types and configuration."""

# Configuration classes
from .config import (
    AthenaSettings,
    CCVecConfig,
    OpenAISettings,
    LoggingSettings,
    load_config,
)

# Data models
from .models import (
    FilterConfig,
    VectorStoreConfig,
    CrawlRecord,
    ProcessedContent,
)

# Response types
from .types import (
    StatsResponse,
    PerCrawlStats,
    SearchResponse,
    SearchResult,
    ProcessResponse,
    MonitorResponse,
    VectorStore,
    VectorStoresResponse,
    VectorSearchResult,
    VectorSearchResponse,
)

__all__ = [
    # Configuration
    "AthenaSettings",
    "CCVecConfig",
    "OpenAISettings",
    "LoggingSettings",
    "load_config",
    # Models
    "FilterConfig",
    "VectorStoreConfig",
    "CrawlRecord",
    "ProcessedContent",
    # Response types
    "StatsResponse",
    "PerCrawlStats",
    "SearchResponse",
    "SearchResult",
    "ProcessResponse",
    "MonitorResponse",
    "VectorStore",
    "VectorStoresResponse",
    "VectorSearchResult",
    "VectorSearchResponse",
]
