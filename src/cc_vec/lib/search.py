"""Search function implementation."""

import logging
from typing import List

from ..types import FilterConfig, CrawlRecord
from ..core.cc_athena_client import CCAthenaClient

logger = logging.getLogger(__name__)


def search(
    filter_config: FilterConfig, 
    athena_client: CCAthenaClient, 
    crawl: str = "CC-MAIN-2024-33",
    limit: int = 10
) -> List[CrawlRecord]:
    """Execute search with FilterConfig and CCAthenaClient.
    
    Args:
        filter_config: FilterConfig with search criteria
        athena_client: Configured CCAthenaClient instance
        crawl: Specific crawl to search
        limit: Maximum number of records to return
        
    Returns:
        List of CrawlRecord objects
    """
    logger.info(f"Searching for patterns: {filter_config.url_patterns} (limit: {limit})")

    try:
        records = athena_client.search_with_filter(
            filter_config=filter_config,
            limit=limit,
            crawl=crawl
        )
        
        logger.info(f"Found {len(records)} records")
        return records

    except Exception as e:
        logger.error(f"Search function failed: {e}")
        raise Exception(f"Search failed: {str(e)}")