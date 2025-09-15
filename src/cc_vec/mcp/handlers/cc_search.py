"""CC Search handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import search as search_function

logger = logging.getLogger(__name__)


class CCSearchHandler(BaseHandler):
    """Handler for cc_search MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_search tool calls."""
        url_pattern = args["url_pattern"]
        crawl = args.get("crawl", "CC-MAIN-2024-33")
        limit = args.get("limit", 10)

        status_codes = args.get("status_codes")
        mime_types = args.get("mime_types")
        languages = args.get("languages")
        date_from = args.get("date_from")
        date_to = args.get("date_to")
        custom_filters = args.get("custom_filters")

        try:
            results = search_function(
                url_pattern,
                limit=limit,
                crawl=crawl,
                status_codes=status_codes,
                mime_types=mime_types,
                languages=languages,
                date_from=date_from,
                date_to=date_to,
                custom_filters=custom_filters,
            )

            if not results:
                response_text = f"SEARCH RESULTS: 0 URLs found for pattern '{url_pattern}' in {crawl}"
                return [TextContent(type="text", text=response_text)]

            summary = f"SEARCH RESULTS: Found {len(results)} URLs for pattern '{url_pattern}' in {crawl}"

            url_list = "\n\nURL LIST:"
            for i, record in enumerate(results, 1):
                url_list += f"\n{i}. {record.url}"
                url_list += f"\n   - Status: {record.status}"
                url_list += f"\n   - MIME: {record.mime or 'N/A'}"
                url_list += f"\n   - Timestamp: {record.timestamp}"
                if record.length:
                    url_list += f"\n   - Size: {record.length:,} bytes"
                url_list += "\n"

            metadata = "\n\nSUMMARY:"
            metadata += f"\n- Total URLs found: {len(results)}"
            metadata += f"\n- Search pattern: {url_pattern}"
            metadata += f"\n- Dataset: {crawl}"
            metadata += f"\n- Limit applied: {limit}"

            if limit < 100:
                metadata += "\n- Note: Increase limit (max 100) to see more results"

            response_text = summary + url_list + metadata

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"Search failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
