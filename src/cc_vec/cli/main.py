#!/usr/bin/env python3
"""Main CLI entry point for cc-vec."""

import json
import logging
import os
import sys

import click

# Use the simplified API
from .. import (
    fetch as fetch_function,
    index as index_function,
    list_vector_stores as list_vector_stores_function,
    query_vector_store as query_vector_store_function,
    search as search_function,
    stats as stats_function,
)
from ..types.config import load_config

logger = logging.getLogger(__name__)


# Removed get_athena_client - now using simplified API that handles client creation


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def cli(ctx, debug):
    """cc-vec: Common Crawl Vectorizer CLI"""
    ctx.ensure_object(dict)

    # Load configuration from environment variables
    try:
        app_config = load_config()
    except Exception as e:
        click.echo(f"Error loading config: {e}", err=True)
        sys.exit(1)

    # Override log level if debug flag is set
    if debug:
        app_config.logging.level = "DEBUG"

    # Setup logging
    app_config.setup_logging()

    # Store config in context
    ctx.obj["config"] = app_config


@cli.command()
@click.argument("url_pattern")
@click.option("--limit", "-l", default=10, help="Maximum number of results")
@click.option("--crawl", default="CC-MAIN-2024-33", help="Common Crawl dataset to use")
@click.option(
    "--status-codes",
    help="HTTP status codes to filter by (comma-separated, e.g., '200,201')",
)
@click.option(
    "--mime-types",
    help="MIME types to filter by (comma-separated, e.g., 'text/html,text/plain')",
)
@click.option(
    "--languages", help="Languages to filter by (comma-separated, e.g., 'en,es')"
)
@click.option(
    "--date-from", help="Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)"
)
@click.option("--date-to", help="End date filter (format: yyyy, yyyyMM, or yyyyMMdd)")
@click.option(
    "--custom-filters", help="Additional CDX filter strings (comma-separated)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def search(
    ctx,
    url_pattern,
    limit,
    crawl,
    status_codes,
    mime_types,
    languages,
    date_from,
    date_to,
    custom_filters,
    output,
):
    """Search Common Crawl for URLs matching patterns."""
    try:
        # Parse comma-separated values
        status_codes_list = (
            [int(x.strip()) for x in status_codes.split(",")] if status_codes else None
        )
        mime_types_list = (
            [x.strip() for x in mime_types.split(",")] if mime_types else None
        )
        languages_list = (
            [x.strip() for x in languages.split(",")] if languages else None
        )
        custom_filters_list = (
            [x.strip() for x in custom_filters.split(",")] if custom_filters else None
        )

        # Use the simplified API that handles client initialization
        results = search_function(
            url_pattern,
            limit=limit,
            crawl=crawl,
            status_codes=status_codes_list,
            mime_types=mime_types_list,
            languages=languages_list,
            date_from=date_from,
            date_to=date_to,
            custom_filters=custom_filters_list,
        )

        if output == "json":
            result = {
                "results": [
                    {
                        "url": str(r.url),  # Convert HttpUrl to string
                        "timestamp": r.timestamp,
                        "status": r.status,
                        "mime_type": r.mime,
                        "length": r.length,
                        "filename": r.filename,
                        "offset": r.offset,
                    }
                    for r in results
                ],
                "total_found": len(results),
                "backend": "athena",
                "crawl_id": crawl,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Found {len(results)} results via athena:")
            click.echo(f"Crawl: {crawl}")
            click.echo()

            for i, result in enumerate(results, 1):
                click.echo(f"{i}. {result.url}")
                click.echo(f"   Status: {result.status}, MIME: {result.mime or 'N/A'}")
                if result.length:
                    click.echo(f"   Length: {result.length:,} bytes")
                click.echo(f"   Timestamp: {result.timestamp}")
                click.echo()

    except Exception as e:
        logger.error("Search failed", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("url_pattern")
@click.option("--crawl", default="CC-MAIN-2024-33", help="Common Crawl dataset to use")
@click.option(
    "--status-codes",
    help="HTTP status codes to filter by (comma-separated, e.g., '200,201')",
)
@click.option(
    "--mime-types",
    help="MIME types to filter by (comma-separated, e.g., 'text/html,text/plain')",
)
@click.option(
    "--languages", help="Languages to filter by (comma-separated, e.g., 'en,es')"
)
@click.option(
    "--date-from", help="Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)"
)
@click.option("--date-to", help="End date filter (format: yyyy, yyyyMM, or yyyyMMdd)")
@click.option(
    "--custom-filters", help="Additional CDX filter strings (comma-separated)"
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def stats(
    ctx,
    url_pattern,
    crawl,
    status_codes,
    mime_types,
    languages,
    date_from,
    date_to,
    custom_filters,
    output,
):
    """Get statistics for Common Crawl query patterns."""
    try:
        # Parse comma-separated values
        status_codes_list = (
            [int(x.strip()) for x in status_codes.split(",")] if status_codes else None
        )
        mime_types_list = (
            [x.strip() for x in mime_types.split(",")] if mime_types else None
        )
        languages_list = (
            [x.strip() for x in languages.split(",")] if languages else None
        )
        custom_filters_list = (
            [x.strip() for x in custom_filters.split(",")] if custom_filters else None
        )

        # Use the simplified API that handles client initialization
        response = stats_function(
            url_pattern,
            crawl=crawl,
            status_codes=status_codes_list,
            mime_types=mime_types_list,
            languages=languages_list,
            date_from=date_from,
            date_to=date_to,
            custom_filters=custom_filters_list,
        )

        if output == "json":
            result = {
                "estimated_records": response.estimated_records,
                "estimated_size_mb": response.estimated_size_mb,
                "backend": response.backend,
                "crawl_id": response.crawl_id,
                "estimated_cost_usd": response.estimated_cost_usd,
                "data_scanned_gb": response.data_scanned_gb,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Statistics for '{url_pattern}' via {response.backend}:")
            if response.crawl_id:
                click.echo(f"Crawl: {response.crawl_id}")

            click.echo(f"Estimated records: {response.estimated_records:,}")
            click.echo(f"Estimated size: {response.estimated_size_mb:.2f} MB")

            if response.estimated_cost_usd:
                click.echo(f"Athena cost: ${response.estimated_cost_usd:.4f}")
            if response.data_scanned_gb:
                click.echo(f"Data to scan: {response.data_scanned_gb:.2f} GB")

    except Exception as e:
        logger.error("Stats failed", exc_info=ctx.obj["debug"])
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("url_pattern")
@click.option("--limit", "-l", default=3, help="Maximum number of records to fetch")
@click.option("--crawl", default="CC-MAIN-2024-33", help="Common Crawl dataset to use")
@click.option("--max-bytes", default=1024, help="Maximum bytes to display per record")
@click.option("--full", is_flag=True, help="Display full content without truncation")
@click.option(
    "--status-codes",
    help="HTTP status codes to filter by (comma-separated, e.g., '200,201')",
)
@click.option(
    "--mime-types",
    help="MIME types to filter by (comma-separated, e.g., 'text/html,text/plain')",
)
@click.option(
    "--languages", help="Languages to filter by (comma-separated, e.g., 'en,es')"
)
@click.option(
    "--date-from", help="Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)"
)
@click.option("--date-to", help="End date filter (format: yyyy, yyyyMM, or yyyyMMdd)")
@click.option(
    "--custom-filters", help="Additional CDX filter strings (comma-separated)"
)
@click.pass_context
def fetch(
    ctx,
    url_pattern,
    limit,
    crawl,
    max_bytes,
    full,
    status_codes,
    mime_types,
    languages,
    date_from,
    date_to,
    custom_filters,
):
    """Fetch Common Crawl content for URLs matching patterns."""
    try:
        # Parse comma-separated values
        status_codes_list = (
            [int(x.strip()) for x in status_codes.split(",")] if status_codes else None
        )
        mime_types_list = (
            [x.strip() for x in mime_types.split(",")] if mime_types else None
        )
        languages_list = (
            [x.strip() for x in languages.split(",")] if languages else None
        )
        custom_filters_list = (
            [x.strip() for x in custom_filters.split(",")] if custom_filters else None
        )

        # Use the simplified API that handles client initialization
        results = fetch_function(
            url_pattern,
            limit=limit,
            crawl=crawl,
            status_codes=status_codes_list,
            mime_types=mime_types_list,
            languages=languages_list,
            date_from=date_from,
            date_to=date_to,
            custom_filters=custom_filters_list,
        )

        click.echo(f"Fetched content for {len(results)} records from crawl {crawl}:")
        click.echo()

        for i, (record, content) in enumerate(results, 1):
            click.echo(f"=== Record {i}: {record.url} ===")
            click.echo(f"Status: {record.status}, MIME: {record.mime or 'N/A'}")
            if record.length:
                click.echo(f"Length: {record.length:,} bytes")
            click.echo(f"Timestamp: {record.timestamp}")
            click.echo(f"S3 Location: {record.filename} at offset {record.offset}")
            click.echo()

            if content:
                # Display processed content (structured data, not raw bytes)
                click.echo("Processed content:")
                click.echo("-" * 40)
                click.echo(f"Title: {content.get('title', 'N/A')}")
                click.echo(
                    f"Meta Description: {content.get('meta_description', 'N/A')}"
                )
                click.echo(f"Word Count: {content.get('word_count', 0)}")
                click.echo(f"Character Count: {content.get('char_count', 0)}")

                # Display the clean text
                text = content.get("text", "")
                if text:
                    if full:
                        click.echo("\nClean Text:")
                        click.echo("-" * 40)
                        click.echo(text)
                    else:
                        # Truncate text for preview
                        preview_text = (
                            text[:max_bytes] if len(text) > max_bytes else text
                        )
                        click.echo("\nClean Text Preview:")
                        click.echo("-" * 40)
                        click.echo(preview_text)
                        if len(text) > max_bytes:
                            click.echo(
                                f"... (truncated, showing {len(preview_text)} of {len(text)} characters)"
                            )
                click.echo("-" * 40)
            else:
                click.echo("❌ Failed to fetch content from S3")

            click.echo()

    except Exception as e:
        logger.error("Fetch failed", exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def list(ctx, output):
    """List available OpenAI vector stores."""
    try:
        # Use the simplified API that handles OpenAI key validation
        stores = list_vector_stores_function()

        if output == "json":
            click.echo(json.dumps(stores, indent=2))
        else:
            if not stores:
                click.echo("No vector stores found.")
            else:
                click.echo(f"Found {len(stores)} vector store(s):\n")
                for store in stores:
                    click.echo(f"📦 {store['name']}")
                    click.echo(f"   ID: {store['id']}")
                    click.echo(f"   Status: {store['status']}")

                    # Handle file_counts which can be a dict or Pydantic object
                    file_counts = store["file_counts"]
                    if hasattr(file_counts, "total"):
                        total_files = file_counts.total
                    elif isinstance(file_counts, dict):
                        total_files = file_counts.get("total", 0)
                    else:
                        total_files = 0

                    click.echo(f"   Files: {total_files}")
                    click.echo(f"   Size: {store['usage_bytes']:,} bytes")
                    click.echo(f"   Created: {store['created_at']}")
                    click.echo()

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error("List failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--vector-store-name", help="Name of the vector store to query")
@click.option("--vector-store-id", help="ID of the vector store to query")
@click.option("--limit", "-l", default=5, help="Maximum number of results")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.option("--save", help="Save results to file (for RAG usage)")
@click.pass_context
def query(ctx, query, vector_store_name, vector_store_id, limit, output, save):
    """Query OpenAI vector stores for relevant content.

    Requires either --vector-store-name or --vector-store-id.
    """
    try:
        # Validate that either name or id is provided
        if not vector_store_name and not vector_store_id:
            click.echo(
                "Error: Either --vector-store-name or --vector-store-id is required",
                err=True,
            )
            sys.exit(1)

        # Use the simplified API that handles OpenAI key validation
        # For now, simplified API only takes vector_store_id, so if name is provided,
        # we need to look it up first
        if vector_store_name and not vector_store_id:
            stores = list_vector_stores_function()
            matching_stores = [
                store for store in stores if store["name"] == vector_store_name
            ]
            if not matching_stores:
                click.echo(
                    f"Error: Vector store with name '{vector_store_name}' not found",
                    err=True,
                )
                sys.exit(1)
            vector_store_id = matching_stores[0]["id"]

        results = query_vector_store_function(vector_store_id, query, limit=limit)

        if output == "json":
            click.echo(json.dumps(results, indent=2))
        else:
            click.echo(f"Query results for: '{query}'")
            click.echo(
                f"Vector store: {results.get('vector_store_name', 'Unknown')} ({results['vector_store_id']})"
            )
            click.echo(f"Found {len(results['results'])} relevant result(s):\n")

            for i, result in enumerate(results["results"], 1):
                click.echo(f"=== Result {i} ===")
                click.echo(f"Relevance Score: {result.get('score', 'N/A')}")
                click.echo(f"File ID: {result.get('file_id', 'N/A')}")

                # Extract full content
                content = result.get("content", "")

                # Handle OpenAI Content objects and other types
                if hasattr(content, "text"):
                    # OpenAI Content object
                    content = content.text
                elif hasattr(content, "__iter__") and not isinstance(content, str):
                    # List or other iterable
                    content = " ".join(str(item) for item in content)
                elif not isinstance(content, str):
                    content = str(content)

                # Show full content (no truncation for RAG usage)
                click.echo("\nContent Chunk:")
                click.echo("-" * 60)
                click.echo(content.strip())
                click.echo("-" * 60)

                # Show metadata and citations
                metadata = result.get("metadata", {})
                if metadata:
                    click.echo("\nMetadata:")
                    for key, value in metadata.items():
                        click.echo(f"  {key}: {value}")

                # Show annotations/citations if present
                annotations = result.get("annotations", [])
                if annotations:
                    click.echo(f"\nCitations ({len(annotations)} source(s)):")
                    for j, annotation in enumerate(annotations, 1):
                        if hasattr(annotation, "text"):
                            click.echo(f"  [{j}] {annotation.text}")
                        else:
                            click.echo(f"  [{j}] {annotation}")

                click.echo("\n" + "=" * 80 + "\n")

        # Save results to file if requested
        if save:
            save_data = {
                "query": query,
                "vector_store_id": results["vector_store_id"],
                "vector_store_name": results.get("vector_store_name", "Unknown"),
                "total_results": len(results["results"]),
                "results": results["results"],
            }
            with open(save, "w", encoding="utf-8") as f:
                if output == "json":
                    # For JSON, we need to handle OpenAI objects
                    def serialize_openai_obj(obj):
                        if hasattr(obj, "text"):
                            return obj.text
                        elif hasattr(obj, "__dict__"):
                            return obj.__dict__
                        return str(obj)

                    # Deep convert OpenAI objects to serializable format
                    def convert_results(data):
                        if isinstance(data, dict):
                            return {k: convert_results(v) for k, v in data.items()}
                        elif isinstance(data, list):
                            return [convert_results(item) for item in data]
                        elif hasattr(data, "text"):
                            return data.text
                        elif hasattr(data, "__dict__"):
                            return convert_results(data.__dict__)
                        else:
                            return data

                    converted_data = convert_results(save_data)
                    json.dump(converted_data, f, indent=2, ensure_ascii=False)
                else:
                    # Save as structured text for RAG usage
                    f.write(f"Query: {query}\n")
                    f.write(
                        f"Vector Store: {results.get('vector_store_name', 'Unknown')} ({results['vector_store_id']})\n"
                    )
                    f.write(f"Total Results: {len(results['results'])}\n\n")

                    for i, result in enumerate(results["results"], 1):
                        f.write(f"=== Chunk {i} ===\n")
                        f.write(f"Relevance Score: {result.get('score', 'N/A')}\n")
                        f.write(f"File ID: {result.get('file_id', 'N/A')}\n")

                        # Extract content
                        content = result.get("content", "")
                        if hasattr(content, "text"):
                            content = content.text
                        elif not isinstance(content, str):
                            content = str(content)

                        f.write(f"\nContent:\n{content.strip()}\n")

                        # Add metadata
                        metadata = result.get("metadata", {})
                        if metadata:
                            f.write(f"\nMetadata: {metadata}\n")

                        f.write("\n" + "=" * 60 + "\n\n")

            click.echo(f"\nResults saved to: {save}")

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Query failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("url_pattern")
@click.argument("vector_store_name", required=False)
@click.option("--limit", "-l", default=5, help="Maximum number of records to index")
@click.option("--crawl", default="CC-MAIN-2024-33", help="Common Crawl dataset to use")
@click.option(
    "--status-codes",
    help="HTTP status codes to filter by (comma-separated, e.g., '200,201')",
)
@click.option(
    "--mime-types",
    help="MIME types to filter by (comma-separated, e.g., 'text/html,text/plain')",
)
@click.option(
    "--languages", help="Languages to filter by (comma-separated, e.g., 'en,es')"
)
@click.option(
    "--date-from", help="Start date filter (format: yyyy, yyyyMM, or yyyyMMdd)"
)
@click.option("--date-to", help="End date filter (format: yyyy, yyyyMM, or yyyyMMdd)")
@click.option(
    "--custom-filters", help="Additional CDX filter strings (comma-separated)"
)
@click.option(
    "--chunk-size",
    default=800,
    help="Maximum chunk size in tokens for OpenAI chunking (100-4096)",
)
@click.option(
    "--overlap",
    default=400,
    help="Token overlap between chunks (must not exceed half of chunk-size)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def index(
    ctx,
    url_pattern,
    vector_store_name,
    limit,
    crawl,
    status_codes,
    mime_types,
    languages,
    date_from,
    date_to,
    custom_filters,
    chunk_size,
    overlap,
    output,
):
    """Index Common Crawl content into OpenAI vector store.

    If VECTOR_STORE_NAME is not provided, one will be auto-generated based on the URL pattern and timestamp.
    """
    try:
        # Generate vector store name if not provided
        if not vector_store_name:
            import re
            from datetime import datetime

            # Clean up URL pattern to make a safe name
            clean_pattern = re.sub(r"[^a-zA-Z0-9_-]", "_", url_pattern)
            clean_pattern = re.sub(r"_+", "_", clean_pattern).strip("_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            vector_store_name = f"ccvec_{clean_pattern}_{timestamp}"
            click.echo(f"Auto-generated vector store name: {vector_store_name}")

        # Parse comma-separated values
        status_codes_list = (
            [int(x.strip()) for x in status_codes.split(",")] if status_codes else None
        )
        mime_types_list = (
            [x.strip() for x in mime_types.split(",")] if mime_types else None
        )
        languages_list = (
            [x.strip() for x in languages.split(",")] if languages else None
        )
        custom_filters_list = (
            [x.strip() for x in custom_filters.split(",")] if custom_filters else None
        )

        # Use the simplified API that handles all client initialization
        result = index_function(
            url_pattern,
            vector_store_name,
            limit=limit,
            crawl=crawl,
            status_codes=status_codes_list,
            mime_types=mime_types_list,
            languages=languages_list,
            date_from=date_from,
            date_to=date_to,
            custom_filters=custom_filters_list,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if output == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(
                f"Indexed content into vector store '{result['vector_store_name']}':"
            )
            click.echo(f"Vector Store ID: {result['vector_store_id']}")
            click.echo(f"Crawl: {result['crawl']}")
            click.echo()

            click.echo(f"Records processed: {result['total_fetched']}")
            click.echo(f"Successfully fetched: {result['successful_fetches']}")
            click.echo(f"Upload status: {result['upload_status']}")

            if result.get("file_counts"):
                file_counts = result["file_counts"]
                click.echo(f"Files uploaded: {file_counts}")

            if result.get("filenames"):
                click.echo("\nSample filenames:")
                for filename in result["filenames"][:3]:
                    click.echo(f"  - {filename}")
                if len(result["filenames"]) > 3:
                    click.echo(f"  ... and {len(result['filenames']) - 3} more")

            click.echo(
                f"\n✅ Vector store '{result['vector_store_name']}' ready for search!"
            )

    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Index failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("identifier")
@click.option(
    "--by-name", is_flag=True, help="Delete by vector store name instead of ID"
)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def delete(ctx, identifier, by_name, confirm, output):
    """Delete an OpenAI vector store by ID or name.

    IDENTIFIER can be either a vector store ID (vs_xxx) or name (use --by-name flag).
    """
    try:
        from ..api import delete_vector_store, delete_vector_store_by_name

        # Show confirmation unless --confirm flag is used
        if not confirm:
            if by_name:
                click.echo(
                    f"Are you sure you want to delete vector store named '{identifier}'?"
                )
            else:
                click.echo(
                    f"Are you sure you want to delete vector store with ID '{identifier}'?"
                )

            if not click.confirm("This action cannot be undone"):
                click.echo("Deletion cancelled.")
                return

        # Delete the vector store
        if by_name:
            result = delete_vector_store_by_name(identifier)
        else:
            result = delete_vector_store(identifier)

        if output == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            if result.get("deleted", False):
                click.echo(f"✅ Successfully deleted vector store: {result['id']}")
            else:
                click.echo(f"❌ Failed to delete vector store: {result['id']}")

    except ValueError as e:
        if "not found" in str(e).lower():
            click.echo(f"❌ Vector store not found: {identifier}", err=True)
        else:
            click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error("Delete failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("url_pattern")
@click.argument("vector_store_name", required=False)
@click.option("--limit", "-l", default=50, help="Maximum number of pages to index")
@click.option("--crawl", default="CC-MAIN-2024-33", help="Common Crawl dataset to use")
@click.option(
    "--status-codes",
    help="HTTP status codes to filter by (comma-separated, e.g., '200,201')",
)
@click.option(
    "--mime-types",
    help="MIME types to filter by (comma-separated, e.g., 'text/html,text/plain')",
)
@click.option(
    "--embedding-model",
    default="sentence-transformers/all-MiniLM-L6-v2",
    help="Embedding model to use",
)
@click.option("--embedding-dimension", default=384, help="Dimension of embeddings")
@click.option("--provider-id", default="faiss", help="Vector database backend")
@click.option(
    "--llama-stack-url",
    help="Llama Stack server URL (defaults to LLAMA_STACK_PORT env var)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def rag_create(
    ctx,
    url_pattern,
    vector_store_name,
    limit,
    crawl,
    status_codes,
    mime_types,
    embedding_model,
    embedding_dimension,
    provider_id,
    llama_stack_url,
    output,
):
    """Create a Llama Stack knowledge base from Common Crawl data for RAG.

    This creates a knowledge base using Llama Stack's Files API and Vector Stores API,
    combining cc-vec's Common Crawl indexing with Llama Stack's RAG capabilities.

    Example: uv run cc-vec rag-create "%.arxiv.org" ml-papers --limit 100
    """
    try:
        from ..rag_agent import CCVecRAGAgent

        # Generate name if not provided
        if not vector_store_name:
            import re
            from datetime import datetime

            clean_pattern = re.sub(r"[%.*]", "", url_pattern).replace("/", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            vector_store_name = f"kb_{clean_pattern}_{timestamp}"
            click.echo(f"Auto-generated knowledge base name: {vector_store_name}")

        # Parse comma-separated values
        status_codes_list = (
            [int(x.strip()) for x in status_codes.split(",")] if status_codes else None
        )
        mime_types_list = (
            [x.strip() for x in mime_types.split(",")] if mime_types else None
        )

        # Create RAG agent
        rag_agent = CCVecRAGAgent(llama_stack_url=llama_stack_url)

        # Show progress
        click.echo(f"Creating knowledge base from Common Crawl pattern: {url_pattern}")
        click.echo(f"Limit: {limit} pages")
        click.echo(f"Crawl: {crawl}")

        # Create knowledge base
        result = rag_agent.create_knowledge_base_from_common_crawl(
            url_pattern=url_pattern,
            vector_store_name=vector_store_name,
            limit=limit,
            crawl=crawl,
            status_codes=status_codes_list,
            mime_types=mime_types_list,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            provider_id=provider_id,
        )

        if output == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"\n✅ Knowledge base created successfully!")
            click.echo(f"   Name: {result['vector_store_name']}")
            click.echo(f"   ID: {result['vector_store_id']}")
            click.echo(f"   Documents: {result['total_documents']}")
            click.echo(f"   Embedding Model: {result['embedding_model']}")
            click.echo(f"   Provider: {result['provider_id']}")
            click.echo(f"\nYou can now query it with:")
            click.echo(
                f"   uv run cc-vec rag-query '{result['vector_store_id']}' 'your question here'"
            )

    except Exception as e:
        logger.error("RAG knowledge base creation failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("vector_store_id")
@click.argument("query")
@click.option(
    "--model",
    default="meta-llama/Llama-3.3-70B-Instruct",
    help="Model to use for generation",
)
@click.option(
    "--llama-stack-url",
    help="Llama Stack server URL (defaults to LLAMA_STACK_PORT env var)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.option("--save", help="Save response to file")
@click.pass_context
def rag_query(
    ctx,
    vector_store_id,
    query,
    model,
    llama_stack_url,
    output,
    save,
):
    """Query a Llama Stack knowledge base for RAG responses.

    This queries the knowledge base using Llama Stack's Responses API with file_search tool
    to provide AI-generated answers based on the indexed Common Crawl content.

    Example: uv run cc-vec rag-query vs_abc123 "What is machine learning?"
    """
    try:
        from ..rag_agent import CCVecRAGAgent

        # Create RAG agent
        rag_agent = CCVecRAGAgent(llama_stack_url=llama_stack_url, model=model)

        click.echo(f"Querying knowledge base {vector_store_id}...")
        click.echo(f"Query: {query}")
        click.echo(f"Model: {model}")
        click.echo()

        # Query knowledge base
        result = rag_agent.query_knowledge_base(vector_store_id, query, model=model)

        if output == "json":
            # Convert response to serializable format
            serializable_result = {
                "query": result["query"],
                "vector_store_id": result["vector_store_id"],
                "model": result["model"],
                "response": str(
                    result["response"]
                ),  # Convert response object to string
            }
            click.echo(json.dumps(serializable_result, indent=2))
        else:
            click.echo("🤖 AI Response:")
            click.echo("-" * 60)
            click.echo(str(result["response"]))
            click.echo("-" * 60)

        # Save to file if requested
        if save:
            with open(save, "w", encoding="utf-8") as f:
                f.write(f"Query: {query}\n")
                f.write(f"Knowledge Base: {vector_store_id}\n")
                f.write(f"Model: {model}\n")
                f.write(f"Timestamp: {ctx.obj.get('timestamp', 'N/A')}\n\n")
                f.write("Response:\n")
                f.write("-" * 60 + "\n")
                f.write(str(result["response"]))
                f.write("\n" + "-" * 60 + "\n")

            click.echo(f"\nResponse saved to: {save}")

    except Exception as e:
        logger.error("RAG query failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--llama-stack-url",
    help="Llama Stack server URL (defaults to LLAMA_STACK_PORT env var)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def rag_list(ctx, llama_stack_url, output):
    """List available Llama Stack knowledge bases for RAG."""
    try:
        from ..rag_agent import CCVecRAGAgent

        # Create RAG agent
        rag_agent = CCVecRAGAgent(llama_stack_url=llama_stack_url)

        # List knowledge bases
        knowledge_bases = rag_agent.list_knowledge_bases()

        if output == "json":
            click.echo(json.dumps(knowledge_bases, indent=2))
        else:
            if not knowledge_bases:
                click.echo("No knowledge bases found.")
            else:
                click.echo(f"Found {len(knowledge_bases)} knowledge base(s):\n")
                for kb in knowledge_bases:
                    click.echo(f"📚 {kb['name']}")
                    click.echo(f"   ID: {kb['id']}")
                    click.echo(f"   Status: {kb['status']}")
                    click.echo(f"   Files: {kb['file_count']}")
                    if kb.get("created_at"):
                        click.echo(f"   Created: {kb['created_at']}")
                    click.echo()

    except Exception as e:
        logger.error("RAG list failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("vector_store_id")
@click.option(
    "--llama-stack-url",
    help="Llama Stack server URL (defaults to LLAMA_STACK_PORT env var)",
)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.pass_context
def rag_delete(ctx, vector_store_id, llama_stack_url, confirm, output):
    """Delete a Llama Stack knowledge base."""
    try:
        from ..rag_agent import CCVecRAGAgent

        # Show confirmation unless --confirm flag is used
        if not confirm:
            click.echo(
                f"Are you sure you want to delete knowledge base '{vector_store_id}'?"
            )
            if not click.confirm("This action cannot be undone"):
                click.echo("Deletion cancelled.")
                return

        # Create RAG agent
        rag_agent = CCVecRAGAgent(llama_stack_url=llama_stack_url)

        # Delete knowledge base
        result = rag_agent.delete_knowledge_base(vector_store_id)

        if output == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"✅ Successfully deleted knowledge base: {vector_store_id}")

    except Exception as e:
        logger.error("RAG delete failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--llama-stack-url",
    help="Llama Stack server URL (defaults to LLAMA_STACK_PORT env var)",
)
@click.option(
    "--model",
    default="meta-llama/Llama-3.3-70B-Instruct",
    help="Model to use for generation",
)
@click.pass_context
def rag_chat(ctx, llama_stack_url, model):
    """Start an interactive chat session with RAG knowledge bases.

    This provides a conversational interface for creating and querying knowledge bases
    from Common Crawl data using Llama Stack.

    Example: uv run cc-vec rag-chat
    """
    try:
        from ..rag_agent import create_interactive_agent

        # Create interactive agent
        interactive_agent = create_interactive_agent(
            llama_stack_url=llama_stack_url, model=model
        )

        # Run interactive session
        interactive_agent.run_interactive_session()

    except KeyboardInterrupt:
        click.echo("\nGoodbye!")
    except Exception as e:
        logger.error("RAG chat failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--mode",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="MCP server mode: stdio for local/pipe communication, http for web/remote access",
)
@click.option("--host", default="127.0.0.1", help="Host to bind to (http mode only)")
@click.option(
    "--port",
    type=int,
    default=1729,
    help="Port to listen on (http mode only, default: 1729)",
)
@click.option(
    "--transport",
    type=click.Choice(["sse", "streamable-http"]),
    default="sse",
    help="HTTP transport protocol (http mode only)",
)
@click.option(
    "--config-file",
    default="mcp-config.json",
    help="Path to write MCP config file (http mode only, default: mcp-config.json)",
)
@click.pass_context
def mcp_serve(ctx, mode, host, port, transport, config_file):
    """Start MCP server for cc-vec tools.

    Supports two modes:
    - stdio: Standard input/output for local MCP clients (default)
    - http: HTTP server for web integrations and remote access

    Examples:
        cc-vec mcp-serve                    # stdio mode (default)
        cc-vec mcp-serve --mode http        # HTTP mode on default port 1729
        cc-vec mcp-serve --mode http --port 8080 --transport sse
    """
    try:
        if mode == "stdio":
            import asyncio
            import sys

            # Use the existing stdio server
            from ..mcp.server import CCVecServer

            # In stdio mode, we must NOT output anything to stdout except JSON-RPC messages
            # Redirect any print/click.echo statements to stderr
            if sys.stdout.isatty():
                # Only show messages if running in a terminal (not from Claude Desktop)
                click.echo("Starting CC-Vec MCP server in stdio mode...", err=True)
                click.echo(
                    "Listening on stdin/stdout for MCP protocol messages", err=True
                )
                click.echo("Press Ctrl+C to stop the server", err=True)

            # Configure logging to stderr BEFORE creating server
            import logging

            logging.basicConfig(
                stream=sys.stderr,
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                force=True,  # Override any existing configuration
            )

            server = CCVecServer()
            # Don't call server.config.setup_logging() as it might log to stdout
            asyncio.run(server.run())

        elif mode == "http":
            from pathlib import Path

            # Use the HTTP server
            from ..mcp.http_server import CCVecHTTPServer

            click.echo("Starting CC-Vec MCP server in http mode...")
            click.echo(f"Host: {host}")
            click.echo(f"Port: {port}")
            click.echo(f"Transport: {transport}")

            # Determine the server URL based on transport
            if transport == "sse":
                server_url = f"http://{host}:{port}/sse"
                click.echo(f"Server will be available at: {server_url}")
            elif transport == "streamable-http":
                server_url = f"http://{host}:{port}/mcp"
                click.echo(f"Server will be available at: {server_url}")

            # Generate HTTP config (for future Claude Desktop HTTP support)
            http_config = {
                "mcpServers": {
                    "cc-vec-http": {"url": server_url, "transport": transport}
                }
            }

            # Also generate stdio config that proxies to HTTP (for current Claude Desktop)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(current_dir))
            )

            # For now, use the HTTP config format
            # Claude Desktop may need updates to support HTTP MCP servers directly
            config_to_write = http_config

            # Write config file
            config_path = Path(config_file)
            with open(config_path, "w") as f:
                json.dump(config_to_write, f, indent=2)

            click.echo(f"\n📁 Generated MCP config file: {config_path.absolute()}")
            click.echo("\n⚠️  Claude Desktop only supports stdio MCP servers directly.")
            click.echo("\n📋 For Claude Desktop, you have two options:")
            click.echo("\nOption 1: Use stdio mode (RECOMMENDED)")
            click.echo("-" * 40)
            click.echo(
                "Add this to ~/Library/Application Support/Claude/claude_desktop_config.json:"
            )
            click.echo(
                json.dumps(
                    {
                        "mcpServers": {
                            "cc-vec": {
                                "command": "uv",
                                "args": [
                                    "run",
                                    "--directory",
                                    project_root,
                                    "cc-vec",
                                    "mcp-serve",
                                    "--mode",
                                    "stdio",
                                ],
                                "env": {
                                    "ATHENA_OUTPUT_BUCKET": os.environ.get(
                                        "ATHENA_OUTPUT_BUCKET",
                                        "s3://your-bucket/athena-results/",
                                    ),
                                    "OPENAI_API_KEY": "your-openai-key",
                                },
                            }
                        }
                    },
                    indent=2,
                )
            )

            click.echo("\nOption 2: Use HTTP with proxy bridge")
            click.echo("-" * 40)
            click.echo("First install the proxy: npm install -g mcp-stdio-http-proxy")
            click.echo("Then add this to claude_desktop_config.json:")
            click.echo(
                json.dumps(
                    {
                        "mcpServers": {
                            "cc-vec-http": {
                                "command": "npx",
                                "args": ["mcp-stdio-http-proxy"],
                                "env": {"MCP_SERVER_URL": server_url},
                            }
                        }
                    },
                    indent=2,
                )
            )
            click.echo("\nPress Ctrl+C to stop the server")

            click.echo("DEBUG: About to create CCVecHTTPServer...")
            try:
                server = CCVecHTTPServer(host=host, port=port)
                click.echo("DEBUG: CCVecHTTPServer created successfully")
            except Exception as e:
                click.echo(f"DEBUG: CCVecHTTPServer creation failed: {e}")
                import traceback

                click.echo(f"DEBUG: Traceback: {traceback.format_exc()}")
                raise
            click.echo("DEBUG: About to call server.run()...")
            server.run(transport=transport)
            click.echo("DEBUG: server.run() completed")

    except ImportError as e:
        click.echo("❌ Error: Server dependencies not available", err=True)
        click.echo(f"Details: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n✅ MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server ({mode} mode) failed", exc_info=True)
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for cc-vec CLI."""
    cli()


if __name__ == "__main__":
    main()
