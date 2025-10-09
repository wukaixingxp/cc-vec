"""Fetch functionality for retrieving Common Crawl content."""

import gzip
import logging
import re
from typing import List, Optional, Dict, Any
from ..types import FilterConfig, CrawlRecord
from ..core import CCAthenaClient, CCS3Client
from ..core.text_processor import WARCTextProcessor
from .search import search

logger = logging.getLogger(__name__)


def fetch(
    filter_config: FilterConfig,
    athena_client: CCAthenaClient,
    s3_client: Optional[CCS3Client] = None,
    limit: int = 10,
) -> List[tuple[CrawlRecord, Optional[Dict[str, Any]]]]:
    """Fetch and process Common Crawl content for records matching filter criteria.

    Args:
        filter_config: Filter configuration with search criteria (including crawl_ids)
        athena_client: Athena client for searching records
        s3_client: S3 client for fetching content (created if None)
        limit: Maximum number of records to fetch

    Returns:
        List of tuples containing (CrawlRecord, processed_content_dict)
        processed_content_dict will be None if processing failed
    """
    logger.info(
        f"Fetching content for patterns: {filter_config.url_patterns} (limit: {limit})"
    )

    records = search(filter_config, athena_client, limit)

    if not records:
        logger.info("No records found to fetch")
        return []

    logger.info(f"Found {len(records)} records, now fetching S3 content")

    if s3_client is None:
        s3_client = CCS3Client()

    processor = WARCTextProcessor()

    results = []

    for i, record in enumerate(records, 1):
        logger.info(f"Fetching content for record {i}/{len(records)}: {record.url}")

        if not record.filename or not record.offset or not record.length:
            logger.warning(f"Record missing S3 location data: {record.url}")
            results.append((record, None))
            continue

        raw_content = s3_client.fetch_warc_content(
            filename=record.filename, offset=record.offset, length=record.length
        )

        if raw_content:
            try:
                decompressed_content = gzip.decompress(raw_content)
                logger.info(
                    f"Successfully fetched and decompressed {len(raw_content)} -> {len(decompressed_content)} bytes for {record.url}"
                )
                warc_content = decompressed_content
            except gzip.BadGzipFile:
                # Content is not gzipped or already decompressed
                logger.info(
                    f"Successfully fetched {len(raw_content)} bytes (not gzipped) for {record.url}"
                )
                warc_content = raw_content

            processed = processor.process_warc_record(
                warc_content, str(record.url), include_chunks=False
            )
            if processed:
                # Extract crawl_id from filename (format: crawl-data/CC-MAIN-2024-33/segments/...)
                crawl_id = None
                if record.filename:
                    match = re.search(r'(CC-MAIN-\d{4}-\d{2})', record.filename)
                    crawl_id = match.group(1)
                assert(crawl_id is not None)

                processed["crawl_metadata"] = {
                    "url": str(record.url),
                    "status": record.status,
                    "mime": record.mime,
                    "timestamp": record.timestamp,
                    "crawl": crawl_id,
                    "length": record.length,
                }

                logger.info(
                    f"Successfully processed content for {record.url}: {processed['word_count']} words"
                )
                results.append((record, processed))
            else:
                logger.warning(f"Failed to process content for {record.url}")
                results.append((record, None))
        else:
            logger.warning(f"Failed to fetch content for {record.url}")
            results.append((record, None))

    logger.info(
        f"Fetch complete: {len([r for r in results if r[1] is not None])}/{len(results)} successful"
    )
    return results
