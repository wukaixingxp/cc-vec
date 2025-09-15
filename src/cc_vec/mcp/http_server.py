"""HTTP MCP server implementation using FastMCP and reusing existing handlers."""

import logging
from typing import List

from mcp.server import FastMCP

from ..core import (
    CCAthenaClient,
    load_config,
)
from ..types import AthenaSettings
from .handlers import (
    CCStatsHandler,
    CCSearchHandler,
    CCFetchHandler,
    CCIndexHandler,
    CCListVectorStoresHandler,
    CCQueryHandler,
)

logger = logging.getLogger(__name__)


class CCVecHTTPServer:
    """HTTP MCP server for Common Crawl vectorization tools using FastMCP."""

    def __init__(
        self,
        name: str = "cc-vec-http",
        version: str = "1.0.0",
        host: str = "127.0.0.1",
        port: int = 1729,
    ):
        """Initialize CC-Vec HTTP MCP server.

        Args:
            name: Server name
            version: Server version
            host: Host to bind to
            port: Port to listen on

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

        # Store host/port for logging
        self.host = host
        self.port = port

        # Initialize FastMCP server
        self.server = FastMCP(
            name=name,
            host=host,
            port=port,
            debug=False,
            log_level="INFO",
            stateless_http=True,
        )

        # Initialize Athena client
        try:
            athena_settings = AthenaSettings(
                output_bucket=self.config.athena.output_bucket,
                region_name=self.config.athena.region_name,
                max_results=self.config.athena.max_results,
                timeout_seconds=self.config.athena.timeout_seconds,
            )
            self._athena_client = CCAthenaClient(athena_settings)
            logger.info(
                f"Athena backend configured with bucket: {self.config.athena.output_bucket}"
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Athena client: {e}") from e

        # Initialize handlers (reusing existing ones)
        logger.info("Initializing handlers...")
        self._init_handlers()

        # Register tools with FastMCP
        logger.info("Registering tools with FastMCP...")
        self._register_tools()
        logger.info("HTTP MCP server initialization complete")

    def _init_handlers(self):
        """Initialize method handlers - same as stdio server."""
        self.handlers = {
            "cc_search": CCSearchHandler(None, self._athena_client),
            "cc_stats": CCStatsHandler(None, self._athena_client),
            "cc_fetch": CCFetchHandler(None, self._athena_client),
            "cc_index": CCIndexHandler(None, self._athena_client),
            "cc_list_vector_stores": CCListVectorStoresHandler(
                None, self._athena_client
            ),
            "cc_query": CCQueryHandler(None, self._athena_client),
        }

    def _register_tools(self):
        """Register tools with FastMCP server."""

        @self.server.tool(
            name="cc_search",
            description="Search Common Crawl CDX index for URLs matching patterns",
        )
        async def cc_search(
            url_pattern: str,
            limit: int = 10,
            filters: List[str] = None,
        ) -> str:
            """Search Common Crawl for URLs matching patterns."""
            if filters is None:
                filters = ["status:200", "mime:text/html"]

            arguments = {
                "url_pattern": url_pattern,
                "limit": limit,
                "filters": filters,
            }

            result = await self.handlers["cc_search"].handle(arguments)
            # Convert TextContent list to string
            return "\n".join([content.text for content in result])

        @self.server.tool(
            name="cc_stats",
            description="Calculate statistics for Common Crawl query patterns",
        )
        async def cc_stats(
            url_pattern: str,
            sample_size: int = 100,
        ) -> str:
            """Get statistics for Common Crawl patterns."""
            arguments = {
                "url_pattern": url_pattern,
                "sample_size": sample_size,
            }

            result = await self.handlers["cc_stats"].handle(arguments)
            return "\n".join([content.text for content in result])

        @self.server.tool(
            name="cc_fetch",
            description="Fetch Common Crawl content for URLs matching patterns",
        )
        async def cc_fetch(
            url_pattern: str,
            limit: int = 3,
            crawl: str = "CC-MAIN-2024-33",
            max_bytes: int = 1024,
        ) -> str:
            """Fetch Common Crawl content for URLs matching patterns."""
            arguments = {
                "url_pattern": url_pattern,
                "limit": limit,
                "crawl": crawl,
                "max_bytes": max_bytes,
            }

            result = await self.handlers["cc_fetch"].handle(arguments)
            return "\n".join([content.text for content in result])

        @self.server.tool(
            name="cc_index",
            description="Index Common Crawl content into OpenAI vector store",
        )
        async def cc_index(
            url_pattern: str,
            vector_store_name: str,
            limit: int = 5,
            crawl: str = "CC-MAIN-2024-33",
        ) -> str:
            """Index Common Crawl content into OpenAI vector store."""
            arguments = {
                "url_pattern": url_pattern,
                "vector_store_name": vector_store_name,
                "limit": limit,
                "crawl": crawl,
            }

            result = await self.handlers["cc_index"].handle(arguments)
            return "\n".join([content.text for content in result])

        @self.server.tool(
            name="cc_list_vector_stores",
            description="List available OpenAI vector stores",
        )
        async def cc_list_vector_stores() -> str:
            """List available OpenAI vector stores."""
            result = await self.handlers["cc_list_vector_stores"].handle({})
            return "\n".join([content.text for content in result])

        @self.server.tool(
            name="cc_query",
            description="Query OpenAI vector stores for relevant content",
        )
        async def cc_query(
            query: str,
            vector_store_name: str = None,
            vector_store_id: str = None,
            limit: int = 5,
        ) -> str:
            """Query OpenAI vector stores for relevant content."""
            if not vector_store_name and not vector_store_id:
                raise ValueError(
                    "Either vector_store_name or vector_store_id must be provided"
                )

            arguments = {
                "query": query,
                "limit": limit,
            }
            if vector_store_name:
                arguments["vector_store_name"] = vector_store_name
            if vector_store_id:
                arguments["vector_store_id"] = vector_store_id

            result = await self.handlers["cc_query"].handle(arguments)
            return "\n".join([content.text for content in result])

        # Add health check endpoint
        @self.server.custom_route("/health", methods=["GET"])
        async def health_check(request) -> dict:
            """Health check endpoint."""
            from starlette.responses import JSONResponse

            return JSONResponse({"status": "ok", "server": "cc-vec-http"})

    def run(self, transport: str = "sse"):
        """Run the HTTP MCP server.

        Args:
            transport: Transport protocol to use ("sse" or "streamable-http")
        """
        logger.info(f"Starting CC-Vec HTTP MCP server on {self.host}:{self.port}")
        logger.info(f"Using transport: {transport}")

        if transport == "sse":
            logger.info(f"Available at: http://{self.host}:{self.port}/sse")
        elif transport == "streamable-http":
            logger.info(f"Available at: http://{self.host}:{self.port}/mcp")

        try:
            logger.info("About to start FastMCP server...")
            logger.info(f"Server object: {self.server}")
            logger.info(f"Transport: {transport}")
            logger.info("Calling server.run()...")

            self.server.run(transport=transport)

            logger.info("server.run() returned (this should not happen)")
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(
                f"Server failed to start or exited unexpectedly: {e}", exc_info=True
            )
            raise
        finally:
            logger.info("Server run() method completed")

    async def run_async(self, transport: str = "sse"):
        """Run the HTTP MCP server asynchronously.

        Args:
            transport: Transport protocol to use ("sse" or "streamable-http")
        """
        logger.info(f"Starting CC-Vec HTTP MCP server on {self.host}:{self.port}")
        logger.info(f"Using transport: {transport}")

        if transport == "sse":
            await self.server.run_sse_async()
        elif transport == "streamable-http":
            await self.server.run_streamable_http_async()
        else:
            raise ValueError(
                f"Invalid transport: {transport}. Use 'sse' or 'streamable-http'"
            )


def main():
    """Main entry point for HTTP MCP server."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="CC-Vec HTTP MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=1729, help="Port to listen on")
    parser.add_argument(
        "--transport",
        choices=["sse", "streamable-http"],
        default="sse",
        help="Transport protocol to use",
    )

    args = parser.parse_args()

    try:
        server = CCVecHTTPServer(host=args.host, port=args.port)
        # Use server's config for logging
        server.config.setup_logging()
        server.run(transport=args.transport)
    except KeyboardInterrupt:
        logger.info("HTTP MCP server stopped by user")
    except Exception as e:
        logger.error(f"HTTP MCP server failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
