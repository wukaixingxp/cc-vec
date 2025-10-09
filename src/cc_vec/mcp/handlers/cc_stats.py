"""CC Stats handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import stats as stats_function
from ...types import FilterConfig

logger = logging.getLogger(__name__)


class CCStatsHandler(BaseHandler):
    """Handler for cc_stats MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_stats tool calls."""
        url_pattern = args.get("url_pattern")

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
            response = stats_function(filter_config)

            backend_info = f"via {response.backend.title()}"
            if response.crawl_id:
                backend_info += f" - {response.crawl_id}"

            filter_desc = (
                f"pattern '{url_pattern}'" if url_pattern else "specified filters"
            )
            response_text = f"Statistics for {filter_desc} ({backend_info}):\n\n"

            if response.backend == "athena":
                response_text += f"Data to scan: {response.data_scanned_gb:.2f} GB\n"
                response_text += f"Athena cost: ${response.estimated_cost_usd:.4f}\n"
                response_text += f"Estimated records: ~{response.estimated_records:,}\n"
                response_text += (
                    "\n💡 Athena provides more reliable access than CDX HTTP API"
                )
            else:
                response_text += f"Estimated records: {response.estimated_records:,}\n"
                response_text += (
                    f"Estimated size: {response.estimated_size_mb:.2f} MB\n"
                )
                response_text += (
                    "\n⚠️ CDX HTTP API can be unreliable - consider using Athena"
                )

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"Statistics calculation failed: {str(e)}"
            return [TextContent(type="text", text=error_text)]
