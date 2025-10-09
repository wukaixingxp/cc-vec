"""CC List Crawls handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import list_crawls as list_crawls_function

logger = logging.getLogger(__name__)


class CCListCrawlsHandler(BaseHandler):
    """Handler for cc_list_crawls MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_list_crawls tool calls."""
        try:
            crawls = list_crawls_function()

            if not crawls:
                response_text = "No crawls found."
                return [TextContent(type="text", text=response_text)]

            response_text = (
                f"Available Common Crawl datasets ({len(crawls)} total):\n\n"
            )

            # Show first 20 crawls
            for i, crawl in enumerate(crawls[:20], 1):
                response_text += f"{i}. {crawl}\n"

            if len(crawls) > 20:
                response_text += f"\n... and {len(crawls) - 20} more\n"

            response_text += f"\nTotal available crawls: {len(crawls)}\n"
            response_text += "\nUse these crawl IDs with the crawl or crawl_ids parameter in other operations."

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"List crawls failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
