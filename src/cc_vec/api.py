"""Simplified API layer for cc-vec that handles client initialization."""

import logging
from typing import List, Dict, Any, Optional

from openai import OpenAI
from .types import FilterConfig, CrawlRecord, StatsResponse
from .types.config import load_config
from .core import CCAthenaClient, CCS3Client
from .types import AthenaSettings
from .lib.search import search as search_lib
from .lib.stats import stats as stats_lib
from .lib.fetch import fetch as fetch_lib
from .lib.index import index as index_lib
from .lib.list_vector_stores import list_vector_stores as list_vector_stores_lib
from .lib.query import query_vector_store as query_vector_store_lib
from .lib.delete_vector_store import delete_vector_store as delete_vector_store_lib
from .lib.delete_vector_store import (
    delete_vector_store_by_name as delete_vector_store_by_name_lib,
)

logger = logging.getLogger(__name__)

_athena_client: Optional[CCAthenaClient] = None
_s3_client: Optional[CCS3Client] = None
_openai_client: Optional[OpenAI] = None


def _get_athena_client() -> CCAthenaClient:
    """Get cached Athena client."""
    global _athena_client
    if _athena_client is None:
        config = load_config()
        athena_settings = AthenaSettings(
            output_bucket=config.athena.output_bucket,
            region_name=config.athena.region_name,
            max_results=config.athena.max_results,
            timeout_seconds=config.athena.timeout_seconds,
        )
        _athena_client = CCAthenaClient(athena_settings)
    return _athena_client


def _get_s3_client() -> CCS3Client:
    """Get cached S3 client."""
    global _s3_client
    if _s3_client is None:
        _s3_client = CCS3Client()
    return _s3_client


def _get_openai_client() -> OpenAI:
    """Get cached OpenAI client."""
    global _openai_client
    if _openai_client is None:
        config = load_config()
        _openai_client = OpenAI(
            api_key=config.openai.api_key,
            base_url=config.openai.base_url,
        )
    return _openai_client


def search(
    url_pattern: str,
    *,
    limit: int = 10,
    crawl: str = "CC-MAIN-2024-33",
    status_codes: Optional[List[int]] = None,
    mime_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    custom_filters: Optional[List[str]] = None,
) -> List[CrawlRecord]:
    """Search Common Crawl for URLs matching a pattern.

    Args:
        url_pattern: URL pattern to search (e.g. '%.github.io%')
        limit: Maximum number of results to return
        crawl: Common Crawl dataset to search
        status_codes: HTTP status codes to filter by (default: [200])
        mime_types: MIME types to filter by (default: ["text/html"])
        languages: Languages to filter by (default: None)
        date_from: Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        date_to: End date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        custom_filters: Additional CDX filter strings

    Returns:
        List of CrawlRecord objects
    """
    filter_config = FilterConfig(
        url_patterns=[url_pattern],
        status_codes=status_codes,
        mime_types=mime_types,
        languages=languages,
        date_from=date_from,
        date_to=date_to,
        custom_filters=custom_filters,
    )
    athena_client = _get_athena_client()
    return search_lib(filter_config, athena_client, crawl, limit)


def stats(
    url_pattern: str,
    *,
    crawl: str = "CC-MAIN-2024-33",
    status_codes: Optional[List[int]] = None,
    mime_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    custom_filters: Optional[List[str]] = None,
) -> StatsResponse:
    """Get statistics for URLs matching a pattern.

    Args:
        url_pattern: URL pattern to analyze (e.g. '%.github.io%')
        crawl: Common Crawl dataset to analyze
        status_codes: HTTP status codes to filter by (default: [200])
        mime_types: MIME types to filter by (default: ["text/html"])
        languages: Languages to filter by (default: None)
        date_from: Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        date_to: End date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        custom_filters: Additional CDX filter strings

    Returns:
        StatsResponse with count and cost estimates
    """
    filter_config = FilterConfig(
        url_patterns=[url_pattern],
        status_codes=status_codes,
        mime_types=mime_types,
        languages=languages,
        date_from=date_from,
        date_to=date_to,
        custom_filters=custom_filters,
    )
    athena_client = _get_athena_client()
    return stats_lib(filter_config, athena_client, crawl)


def fetch(
    url_pattern: str,
    *,
    limit: int = 10,
    crawl: str = "CC-MAIN-2024-33",
    status_codes: Optional[List[int]] = None,
    mime_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    custom_filters: Optional[List[str]] = None,
) -> List[tuple]:
    """Fetch and process content for URLs matching a pattern.

    Args:
        url_pattern: URL pattern to fetch (e.g. '%.github.io%')
        limit: Maximum number of records to fetch
        crawl: Common Crawl dataset to fetch from
        status_codes: HTTP status codes to filter by (default: [200])
        mime_types: MIME types to filter by (default: ["text/html"])
        languages: Languages to filter by (default: None)
        date_from: Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        date_to: End date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        custom_filters: Additional CDX filter strings

    Returns:
        List of (CrawlRecord, processed_content_dict) tuples
        Content is processed and cleaned but not chunked - use index() for chunking
    """
    filter_config = FilterConfig(
        url_patterns=[url_pattern],
        status_codes=status_codes,
        mime_types=mime_types,
        languages=languages,
        date_from=date_from,
        date_to=date_to,
        custom_filters=custom_filters,
    )
    athena_client = _get_athena_client()
    s3_client = _get_s3_client()
    return fetch_lib(filter_config, athena_client, s3_client, crawl, limit)


def index(
    url_pattern: str,
    vector_store_name: str,
    *,
    limit: int = 10,
    crawl: str = "CC-MAIN-2024-33",
    status_codes: Optional[List[int]] = None,
    mime_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    custom_filters: Optional[List[str]] = None,
    chunk_size: int = 800,
    overlap: int = 400,
) -> Dict[str, Any]:
    """Index processed Common Crawl content into a vector store for RAG.

    Args:
        url_pattern: URL pattern to index (e.g. '%.github.io%')
        vector_store_name: Name for the vector store
        limit: Maximum number of records to index
        crawl: Common Crawl dataset to index from
        status_codes: HTTP status codes to filter by (default: [200])
        mime_types: MIME types to filter by (default: ["text/html"])
        languages: Languages to filter by (default: None)
        date_from: Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        date_to: End date filter (format: yyyy, yyyyMM, or yyyyMMdd)
        custom_filters: Additional CDX filter strings
        chunk_size: Maximum chunk size in tokens for OpenAI chunking (100-4096, default 800)
        overlap: Token overlap between chunks (default 400, must not exceed half of chunk_size)

    Returns:
        Dictionary with indexing results including vector store ID and chunk statistics
    """
    filter_config = FilterConfig(
        url_patterns=[url_pattern],
        status_codes=status_codes,
        mime_types=mime_types,
        languages=languages,
        date_from=date_from,
        date_to=date_to,
        custom_filters=custom_filters,
    )
    athena_client = _get_athena_client()
    s3_client = _get_s3_client()
    return index_lib(
        filter_config,
        athena_client,
        vector_store_name,
        s3_client=s3_client,
        crawl=crawl,
        limit=limit,
        chunk_size=chunk_size,
        overlap=overlap,
    )


def list_vector_stores() -> List[Dict[str, Any]]:
    """List available OpenAI vector stores.

    Returns:
        List of vector store information dictionaries
    """
    return list_vector_stores_lib()


def query_vector_store(
    vector_store_id: str, query: str, *, limit: int = 5
) -> List[Dict[str, Any]]:
    """Query a vector store for relevant content.

    Args:
        vector_store_id: ID of the vector store to query
        query: Query string to search for
        limit: Maximum number of results to return

    Returns:
        List of search results with content and metadata
    """
    return query_vector_store_lib(vector_store_id, query, limit)


def delete_vector_store(vector_store_id: str) -> Dict[str, Any]:
    """Delete a vector store by ID.

    Args:
        vector_store_id: ID of the vector store to delete

    Returns:
        Dictionary with deletion result
    """
    return delete_vector_store_lib(vector_store_id)


def delete_vector_store_by_name(vector_store_name: str) -> Dict[str, Any]:
    """Delete a vector store by name.

    Args:
        vector_store_name: Name of the vector store to delete

    Returns:
        Dictionary with deletion result
    """
    return delete_vector_store_by_name_lib(vector_store_name)
