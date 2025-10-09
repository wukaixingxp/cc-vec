"""Clean MCP server implementation using organized handlers."""

import asyncio
import logging
from typing import Any, Dict

from mcp.server import Server
from mcp.types import Tool, TextContent

from ..core import load_config
from .handlers import (
    CCStatsHandler,
    CCSearchHandler,
    CCFetchHandler,
    CCIndexHandler,
    CCListVectorStoresHandler,
    CCQueryHandler,
    CCListCrawlsHandler,
)
from .. import api

logger = logging.getLogger(__name__)


class CCVecServer:
    """MCP server for Common Crawl vectorization tools."""

    def __init__(
        self,
        name: str = "cc-vec",
        version: str = "1.0.0",
    ):
        """Initialize CC-Vec MCP server.

        Args:
            name: Server name
            version: Server version

        Raises:
            ValueError: If required environment variables are not set
        """
        # Load configuration from environment variables
        self.config = load_config()

        # Check for required configuration
        if not self.config.openai.is_configured():
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for MCP server"
            )

        if not self.config.athena.is_configured():
            raise ValueError(
                "ATHENA_OUTPUT_BUCKET environment variable is required for MCP server. "
                "Please set it to an S3 bucket path (e.g., 's3://your-bucket/athena-results/')"
            )

        self.server = Server(name, version)

        # Validate configuration - the API layer will handle actual client creation
        logger.info(
            f"Athena backend configured with bucket: {self.config.athena.output_bucket}"
        )
        logger.info("OpenAI client configured for vector operations")
        logger.info("S3 client configured for content retrieval")

        # Initialize handlers
        self._init_handlers()

        # Setup MCP server handlers
        self._setup_server()

    def _init_handlers(self):
        """Initialize method handlers."""
        self.handlers = {
            "cc_search": CCSearchHandler(api_method=api.search),
            "cc_stats": CCStatsHandler(api_method=api.stats),
            "cc_fetch": CCFetchHandler(api_method=api.fetch),
            "cc_index": CCIndexHandler(api_method=api.index),
            "cc_list_vector_stores": CCListVectorStoresHandler(
                api_method=api.list_vector_stores
            ),
            "cc_query": CCQueryHandler(api_method=api.query_vector_store),
            "cc_list_crawls": CCListCrawlsHandler(api_method=api.list_crawls),
        }

    def _setup_server(self):
        """Setup MCP server event handlers."""

        @self.server.list_tools()
        async def list_tools():
            """List available Common Crawl tools."""
            return self._get_tool_definitions()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Handle tool calls by routing to appropriate handlers."""
            if name in self.handlers:
                return await self.handlers[name].handle(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    def _get_tool_definitions(self):
        """Get MCP tool definitions dynamically from handler API methods."""
        tool_descriptions = {
            "cc_search": "Search Common Crawl CDX index for URLs matching patterns with advanced filtering",
            "cc_stats": "Calculate statistics for Common Crawl query patterns with advanced filtering",
            "cc_fetch": "Fetch and process Common Crawl content for URLs matching patterns with advanced filtering",
            "cc_index": "Index Common Crawl content into OpenAI vector store with advanced filtering and chunking",
            "cc_query": "Query OpenAI vector stores for relevant content",
            "cc_list_vector_stores": "List available OpenAI vector stores",
            "cc_list_crawls": "List available Common Crawl dataset IDs",
        }

        tools = []
        for tool_name, handler in self.handlers.items():
            description = tool_descriptions.get(tool_name, f"Handler for {tool_name}")
            try:
                tool = handler.get_tool_definition(tool_name, description)
                tools.append(tool)
            except Exception as e:
                logger.warning(
                    f"Failed to generate tool definition for {tool_name}: {e}"
                )
                # Fallback to a basic tool definition
                tools.append(
                    Tool(
                        name=tool_name,
                        description=description,
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    )
                )

        return tools

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


def main():
    """Main entry point for MCP server."""
    import sys

    try:
        server = CCVecServer()
        # Use server's config for logging
        server.config.setup_logging()
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
