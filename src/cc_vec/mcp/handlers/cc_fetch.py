"""CC Fetch handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import fetch as fetch_function
from ...types import FilterConfig

logger = logging.getLogger(__name__)


class CCFetchHandler(BaseHandler):
    """Handler for cc_fetch MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_fetch tool calls."""
        url_pattern = args.get("url_pattern")
        limit = args.get("limit", 3)
        max_bytes = args.get("max_bytes", 1024)

        url_host_names = args.get("url_host_names")
        crawl_ids = args.get("crawl_ids")
        status_codes = args.get("status_codes")
        mime_types = args.get("mime_types")
        charsets = args.get("charsets")
        languages = args.get("languages")
        date_from = args.get("date_from")
        date_to = args.get("date_to")
        custom_filters = args.get("custom_filters")

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

        try:
            results = fetch_function(filter_config, limit=limit)

            if not results:
                filter_desc = (
                    f"pattern '{url_pattern}'" if url_pattern else "specified filters"
                )
                response_text = f"No content fetched for {filter_desc}"
                return [TextContent(type="text", text=response_text)]

            response_text = f"Fetched content for {len(results)} records:\n\n"

            for i, (record, content) in enumerate(results, 1):
                response_text += f"=== Record {i}: {record.url} ===\n"
                response_text += (
                    f"Status: {record.status}, MIME: {record.mime or 'N/A'}\n"
                )
                if record.length:
                    response_text += f"Length: {record.length:,} bytes\n"
                response_text += f"Timestamp: {record.timestamp}\n"
                response_text += (
                    f"S3 Location: {record.filename} at offset {record.offset}\n\n"
                )

                if content:
                    response_text += "Processed content:\n"
                    response_text += "-" * 40 + "\n"
                    response_text += f"Title: {content.get('title', 'N/A')}\n"
                    response_text += f"Word count: {content.get('word_count', 'N/A')}\n"
                    response_text += f"Language: {content.get('language', 'N/A')}\n"
                    response_text += f"Chunks: {len(content.get('chunks', []))}\n\n"

                    text_content = content.get("text", "")
                    if text_content:
                        display_text = text_content[:max_bytes]
                        response_text += f"Text preview ({len(text_content)} chars):\n"
                        response_text += display_text
                        if len(text_content) > max_bytes:
                            response_text += f"\n... (truncated, showing {max_bytes} of {len(text_content)} characters)\n"
                        response_text += "\n"
                    response_text += "-" * 40 + "\n"
                else:
                    response_text += "❌ Failed to process content\n"

                response_text += "\n"

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"Fetch failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
