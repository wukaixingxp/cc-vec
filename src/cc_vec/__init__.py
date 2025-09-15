"""cc-vec: Common Crawl vectorization toolkit."""

# Public API - types and configuration
from .types import (
    FilterConfig,
    AthenaSettings,
    StatsResponse,
    SearchResponse,
    CrawlRecord,
    ProcessedContent,
)

# Public API - simplified operations
from .api import stats, search, fetch, index, list_vector_stores, query_vector_store

__all__ = [
    # Types and configuration
    "FilterConfig",
    "AthenaSettings",
    "StatsResponse",
    "SearchResponse",
    "CrawlRecord",
    "ProcessedContent",
    # Operations
    "stats",
    "search",
    "fetch",
    "index",
    "list_vector_stores",
    "query_vector_store",
]

__version__ = "0.1.0"


def main() -> None:
    """CLI entry point."""
    print("Hello from cc-vec!")
