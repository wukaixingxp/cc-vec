"""List available crawls functionality for cc-vec."""

import logging
from typing import List

from ..core import CCAthenaClient

logger = logging.getLogger(__name__)


def list_crawls(athena_client: CCAthenaClient) -> List[str]:
    """List available Common Crawl crawls.

    Args:
        athena_client: Pre-configured Athena client

    Returns:
        List of crawl IDs sorted in descending order (newest first)
    """
    logger.info("Listing available Common Crawl crawls")
    return athena_client.list_crawls()
