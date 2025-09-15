"""CC List Vector Stores handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import list_vector_stores as list_vector_stores_function

logger = logging.getLogger(__name__)


class CCListVectorStoresHandler(BaseHandler):
    """Handler for cc_list_vector_stores MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_list_vector_stores tool calls."""
        try:
            stores = list_vector_stores_function()

            if not stores:
                response_text = "No vector stores found."
                return [TextContent(type="text", text=response_text)]

            response_text = f"Found {len(stores)} vector store(s):\n\n"

            for i, store in enumerate(stores, 1):
                response_text += f"{i}. {store['name']}\n"
                response_text += f"   ID: {store['id']}\n"
                response_text += f"   Status: {store['status']}\n"

                if store["file_counts"]:
                    response_text += f"   Files: {store['file_counts']}\n"

                if store["usage_bytes"]:
                    usage_mb = store["usage_bytes"] / (1024 * 1024)
                    if usage_mb < 1:
                        response_text += f"   Usage: {store['usage_bytes']} bytes\n"
                    else:
                        response_text += f"   Usage: {usage_mb:.2f} MB\n"

                import datetime

                created_date = datetime.datetime.fromtimestamp(store["created_at"])
                response_text += (
                    f"   Created: {created_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )

                if store.get("expires_at"):
                    expires_date = datetime.datetime.fromtimestamp(store["expires_at"])
                    response_text += (
                        f"   Expires: {expires_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )

                response_text += "\n"

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"List vector stores failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
