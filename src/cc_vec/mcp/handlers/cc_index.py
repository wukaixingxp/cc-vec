"""CC Index handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import index as index_function
from ...types import FilterConfig, VectorStoreConfig

logger = logging.getLogger(__name__)


class CCIndexHandler(BaseHandler):
    """Handler for cc_index MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_index tool calls."""
        url_pattern = args.get("url_pattern")
        vector_store_name = args.get("vector_store_name")
        limit = args.get("limit", 5)

        url_host_names = args.get("url_host_names")
        crawl_ids = args.get("crawl_ids")
        status_codes = args.get("status_codes")
        mime_types = args.get("mime_types")
        charsets = args.get("charsets")
        languages = args.get("languages")
        date_from = args.get("date_from")
        date_to = args.get("date_to")
        custom_filters = args.get("custom_filters")
        chunk_size = args.get("chunk_size", 800)
        overlap = args.get("overlap", 400)

        # Generate vector store name if not provided
        if not vector_store_name:
            import re
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            if url_pattern:
                clean_pattern = re.sub(r"[^a-zA-Z0-9_-]", "_", url_pattern)
                clean_pattern = re.sub(r"_+", "_", clean_pattern).strip("_")
                vector_store_name = f"ccvec_{clean_pattern}_{timestamp}"
            elif url_host_names:
                clean_hosts = re.sub(
                    r"[^a-zA-Z0-9_-]",
                    "_",
                    url_host_names[0]
                    if isinstance(url_host_names, list)
                    else url_host_names,
                )
                vector_store_name = f"ccvec_{clean_hosts}_{timestamp}"
            elif crawl_ids:
                crawl_id = crawl_ids[0] if isinstance(crawl_ids, list) else crawl_ids
                vector_store_name = f"ccvec_{crawl_id}_{timestamp}"
            else:
                vector_store_name = f"ccvec_{timestamp}"

        # Convert url_pattern to list if provided
        url_patterns_list = [url_pattern] if url_pattern else None

        # Convert crawl_ids to list if needed
        crawl_ids_list = crawl_ids

        # Construct FilterConfig
        filter_config = FilterConfig(
            url_patterns=url_patterns_list,
            url_host_names=url_host_names,
            crawl_ids=crawl_ids_list,
            status_codes=status_codes,
            mime_types=mime_types,
            charsets=charsets,
            languages=languages,
            date_from=date_from,
            date_to=date_to,
            custom_filters=custom_filters,
        )

        # Construct VectorStoreConfig
        vector_store_config = VectorStoreConfig(
            name=vector_store_name,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        try:
            result = index_function(filter_config, vector_store_config, limit=limit)

            if result.get("upload_status") == "no_content":
                filter_desc = (
                    f"pattern '{url_pattern}'" if url_pattern else "specified filters"
                )
                response_text = f"No content found for {filter_desc}"
                return [TextContent(type="text", text=response_text)]

            response_text = f"Successfully loaded content into vector store '{result['vector_store_name']}':\n\n"
            response_text += f"Vector Store ID: {result['vector_store_id']}\n"
            if result.get("crawl"):
                response_text += f"Crawl: {result['crawl']}\n"
            response_text += "\n"

            response_text += f"Records processed: {result['total_fetched']}\n"
            response_text += f"Successfully fetched: {result['successful_fetches']}\n"
            response_text += f"Upload status: {result['upload_status']}\n"

            if result.get("file_counts"):
                file_counts = result["file_counts"]
                response_text += f"Files uploaded: {file_counts}\n"

            if result.get("filenames"):
                response_text += "\nSample filenames:\n"
                for filename in result["filenames"][:3]:
                    response_text += f"  - {filename}\n"
                if len(result["filenames"]) > 3:
                    response_text += f"  ... and {len(result['filenames']) - 3} more\n"

            response_text += (
                f"\n✅ Vector store '{result['vector_store_name']}' ready for search!\n"
            )

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"Index failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
