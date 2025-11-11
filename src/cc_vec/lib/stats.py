"""Stats function implementation."""

import logging
import re

from ..types import StatsResponse, PerCrawlStats, FilterConfig
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
        StatsResponse with per-crawl statistics and totals
    """
    logger.info(f"Getting statistics for patterns: {filter_config.url_patterns}")

    try:
        # Determine which crawl IDs to query
        # - No --crawl-ids specified: use default (won't do GROUP BY, single crawl)
        # - --crawl-ids ALL: query all crawls with GROUP BY
        # - --crawl-ids with patterns: expand patterns and query those crawls
        # - --crawl-ids with exact IDs: query those specific crawls

        query_all_crawls = False

        if filter_config.crawl_ids:
            # Check if user specified "ALL"
            if len(filter_config.crawl_ids) == 1 and filter_config.crawl_ids[0].upper() == "ALL":
                query_all_crawls = True
                logger.info("Querying ALL crawls (--crawl-ids ALL)")
            else:
                # User specified specific crawl IDs or patterns (e.g., CC-MAIN-2024-*)
                # The query builder will handle both exact IDs and patterns with LIKE
                logger.info(f"Querying crawl IDs/patterns: {filter_config.crawl_ids}")
        else:
            # No crawl IDs specified - use default behavior (query builder will use CC-MAIN-2024-33)
            logger.info("No crawl IDs specified, using default crawl ID")

        # Build the query
        if query_all_crawls:
            # Build query without crawl filter, then add GROUP BY
            # Use temporary crawl ID to build query, then strip it out
            modified_filter = FilterConfig(
                url_patterns=filter_config.url_patterns,
                url_host_names=filter_config.url_host_names,
                url_host_tlds=filter_config.url_host_tlds,
                url_host_registered_domains=filter_config.url_host_registered_domains,
                url_paths=filter_config.url_paths,
                status_codes=filter_config.status_codes,
                mime_types=filter_config.mime_types,
                languages=filter_config.languages,
                charsets=filter_config.charsets,
                date_from=filter_config.date_from,
                date_to=filter_config.date_to,
                custom_filters=filter_config.custom_filters,
                crawl_ids=["CC-MAIN-2024-33"],  # Temporary, will be removed
            )

            query_builder = CrawlQueryBuilder(modified_filter, limit=None)
            base_query = query_builder.to_sql(count_only=True)

            # Replace SELECT COUNT(*) with SELECT crawl, COUNT(*)
            grouped_query = base_query.replace(
                "SELECT COUNT(*)",
                "SELECT crawl, COUNT(*) as record_count"
            )

            # Remove the crawl filter since we want all crawls
            grouped_query = re.sub(
                r"crawl\s*(?:=\s*'[^']+'\s*|IN\s*\([^)]+\)\s*)AND\s+",
                "",
                grouped_query
            )

            # Add GROUP BY and ORDER BY
            grouped_query += " GROUP BY crawl ORDER BY crawl DESC"

            logger.info("Executing grouped stats query for ALL crawls")
            logger.debug(f"Grouped query: {grouped_query}")
        else:
            # Use normal query builder (handles default or specific crawl IDs)
            query_builder = CrawlQueryBuilder(filter_config, limit=None)
            base_query = query_builder.to_sql(count_only=True)

            # Replace SELECT COUNT(*) with SELECT crawl, COUNT(*)
            grouped_query = base_query.replace(
                "SELECT COUNT(*)",
                "SELECT crawl, COUNT(*) as record_count"
            )

            # Add GROUP BY and ORDER BY (will group by the specified crawl IDs)
            grouped_query += " GROUP BY crawl ORDER BY crawl DESC"

            logger.info("Executing grouped stats query for specified crawls")
            logger.debug(f"Grouped query: {grouped_query}")

        # Execute the query once
        query_execution_id = athena_client._execute_query(grouped_query)
        results = athena_client._get_query_results(query_execution_id)

        # Get query statistics (this is for the single query execution)
        query_stats = athena_client.athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )

        data_scanned_bytes = query_stats["QueryExecution"]["Statistics"].get(
            "DataScannedInBytes", 0
        )

        # Calculate cost for the single query
        total_query_cost = (
            data_scanned_bytes / (1024**4)
        ) * 5.0  # Athena pricing: $5 per TB scanned

        logger.info(f"Query scanned {data_scanned_bytes / (1024**3):.2f} GB, cost: ${total_query_cost:.4f}")

        # Parse results - each row is [crawl_id, count]
        per_crawl_stats = []
        total_records = 0

        for row in results:
            if row and len(row) >= 2:
                crawl_id = row[0]
                record_count = int(row[1]) if row[1] and row[1].isdigit() else 0

                # Note: We can't easily split the data_scanned_bytes per crawl
                # So we'll estimate it proportionally based on record count
                # This is an approximation - actual scan might vary per crawl

                per_crawl_stats.append(PerCrawlStats(
                    crawl_id=crawl_id,
                    estimated_records=record_count,
                    estimated_size_mb=0.0,  # Not available per-crawl with GROUP BY
                    estimated_cost_usd=0.0,  # Not available per-crawl with GROUP BY
                    data_scanned_gb=0.0,  # Not available per-crawl with GROUP BY
                ))

                total_records += record_count

        # If we got results, proportionally distribute the scan cost/size
        if total_records > 0 and per_crawl_stats:
            for crawl_stat in per_crawl_stats:
                proportion = crawl_stat.estimated_records / total_records
                crawl_stat.estimated_size_mb = (data_scanned_bytes / (1024 * 1024)) * proportion
                crawl_stat.estimated_cost_usd = total_query_cost * proportion
                crawl_stat.data_scanned_gb = (data_scanned_bytes / (1024 * 1024 * 1024)) * proportion

        return StatsResponse(
            per_crawl_stats=per_crawl_stats,
            total_estimated_records=total_records,
            total_estimated_size_mb=data_scanned_bytes / (1024 * 1024),
            total_estimated_cost_usd=total_query_cost,
            total_data_scanned_gb=data_scanned_bytes / (1024 * 1024 * 1024),
            backend="athena",
        )

    except Exception as e:
        logger.error(f"Stats function failed: {e}")
        # Return empty stats on error
        return StatsResponse(
            per_crawl_stats=[],
            total_estimated_records=0,
            total_estimated_size_mb=0.0,
            total_estimated_cost_usd=0.0,
            total_data_scanned_gb=0.0,
            backend="error",
        )
