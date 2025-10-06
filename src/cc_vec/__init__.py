"""cc-vec: Common Crawl vectorization toolkit."""

# Public API - simplified operations
from .api import fetch, index, list_vector_stores, query_vector_store, search, stats

# Public API - RAG agent
from .rag_agent import (
    CCVecRAGAgent,
    create_rag_agent,
)

# Public API - types and configuration
from .types import (
    AthenaSettings,
    CrawlRecord,
    FilterConfig,
    ProcessedContent,
    SearchResponse,
    StatsResponse,
)

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
    # RAG Agent
    "CCVecRAGAgent",
    "InteractiveRAGAgent",
    "create_rag_agent",
    "create_interactive_agent",
]

__version__ = "0.1.0"


def main() -> None:
    """CLI entry point."""
    print("Hello from cc-vec!")
