"""CC Stats handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import stats as stats_function

logger = logging.getLogger(__name__)


class CCStatsHandler(BaseHandler):
    """Handler for cc_stats MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_stats tool calls."""
        url_pattern = args["url_pattern"]
        crawl = args.get("crawl", "CC-MAIN-2024-33")

        status_codes = args.get("status_codes")
        mime_types = args.get("mime_types")
        languages = args.get("languages")
        date_from = args.get("date_from")
        date_to = args.get("date_to")
        custom_filters = args.get("custom_filters")

        try:
            response = stats_function(
                url_pattern,
                crawl=crawl,
                status_codes=status_codes,
                mime_types=mime_types,
                languages=languages,
                date_from=date_from,
                date_to=date_to,
                custom_filters=custom_filters,
            )

            backend_info = f"via {response.backend.title()}"
            if response.crawl_id:
                backend_info += f" - {response.crawl_id}"

            response_text = (
                f"Statistics for pattern '{url_pattern}' ({backend_info}):\n\n"
            )

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
