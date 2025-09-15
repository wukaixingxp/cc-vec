"""CC Query handler for MCP server."""

import logging
from typing import Any, Dict, List

from mcp.types import TextContent
from .base import BaseHandler
from ... import query_vector_store, list_vector_stores

logger = logging.getLogger(__name__)


class CCQueryHandler(BaseHandler):
    """Handler for cc_query MCP method."""

    def __init__(self, api_method=None):
        super().__init__(api_method)

    async def handle(self, args: Dict[str, Any]) -> List[TextContent]:
        """Handle cc_query tool calls."""
        query = args["query"]
        limit = args.get("limit", 5)

        vector_store_name = args.get("vector_store_name")
        vector_store_id = args.get("vector_store_id")

        if not vector_store_name and not vector_store_id:
            error_text = "Either vector_store_name or vector_store_id must be provided"
            return [TextContent(type="text", text=error_text)]

        try:
            if vector_store_name and not vector_store_id:
                stores = list_vector_stores()
                matching_stores = [
                    store for store in stores if store["name"] == vector_store_name
                ]
                if not matching_stores:
                    error_text = (
                        f"Vector store with name '{vector_store_name}' not found"
                    )
                    return [TextContent(type="text", text=error_text)]
                vector_store_id = matching_stores[0]["id"]
                store_identifier = f"'{vector_store_name}'"
            else:
                store_identifier = f"ID '{vector_store_id}'"

            results = query_vector_store(vector_store_id, query, limit=limit)

            query_results = results.get("results", [])
            if not query_results:
                response_text = f"No results found for query '{query}' in vector store {store_identifier}"
                return [TextContent(type="text", text=response_text)]

            response_text = (
                f"Query results for '{query}' in vector store {store_identifier}:\n"
                f"Found {len(query_results)} relevant result(s):\n\n"
            )

            for i, result in enumerate(query_results, 1):
                response_text += f"Result {i}:\n"
                response_text += f"Score: {result.get('score', 'N/A')}\n"
                response_text += f"File: {result.get('file_id', 'N/A')}\n"

                content = result.get("content", "")
                if isinstance(content, list) and content:
                    content_text = (
                        content[0].text
                        if hasattr(content[0], "text")
                        else str(content[0])
                    )
                else:
                    content_text = str(content)

                if content_text:
                    preview = content_text[:200]
                    if len(content_text) > 200:
                        preview += "..."
                    response_text += f"Content: {preview}\n"

                response_text += "\n" + "=" * 40 + "\n\n"

            return [TextContent(type="text", text=response_text)]

        except Exception as e:
            error_text = f"Query failed: {str(e)}"
            logger.error(error_text)
            return [TextContent(type="text", text=error_text)]
