"""Stats function implementation."""

import logging

from ..types import StatsResponse, FilterConfig
from ..core.cc_athena_client import CCAthenaClient, CrawlQueryBuilder

logger = logging.getLogger(__name__)


def stats(
    filter_config: FilterConfig,
    athena_client: CCAthenaClient,
) -> StatsResponse:
    """Execute stats with FilterConfig and CCAthenaClient.

    Args:
        filter_config: FilterConfig with search criteria (including crawl_ids)
        athena_client: Configured CCAthenaClient instance

    Returns:
        StatsResponse with count and cost estimates
    """
    logger.info(f"Getting statistics for patterns: {filter_config.url_patterns}")

    try:
        query_builder = CrawlQueryBuilder(filter_config, limit=None)

        count_query = query_builder.to_sql(count_only=True)
        logger.debug(f"Count query: {count_query}")

        query_execution_id = athena_client._execute_query(count_query)
        results = athena_client._get_query_results(query_execution_id)

        estimated_records = 0
        if results and len(results) > 0 and len(results[0]) > 0:
            estimated_records = int(results[0][0]) if results[0][0].isdigit() else 0

        query_stats = athena_client.athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        data_scanned_bytes = query_stats["QueryExecution"]["Statistics"].get(
            "DataScannedInBytes", 0
        )

        cost_usd = (
            data_scanned_bytes / (1024**4)
        ) * 5.0  # Athena pricing: $5 per TB scanned

        # Get crawl_id from filter_config or use default
        crawl_id = (
            filter_config.crawl_ids[0]
            if filter_config.crawl_ids
            else "CC-MAIN-2024-33"
        )

        return StatsResponse(
            estimated_records=estimated_records,
            estimated_size_mb=data_scanned_bytes / (1024 * 1024),  # Convert bytes to MB
            estimated_cost_usd=cost_usd,
            data_scanned_gb=data_scanned_bytes
            / (1024 * 1024 * 1024),  # Convert bytes to GB
            backend="athena",
            crawl_id=crawl_id,
        )

    except Exception as e:
        logger.error(f"Stats function failed: {e}")
        return StatsResponse(
            estimated_records=0, estimated_size_mb=0.0, backend="error"
        )
