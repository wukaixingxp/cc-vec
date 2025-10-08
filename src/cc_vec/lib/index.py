"""Index functionality for loading Common Crawl content into vector stores."""

import io
import logging
from typing import List, Optional, Tuple, Dict, Any
from openai import OpenAI

from ..types import FilterConfig, CrawlRecord
from ..core import CCAthenaClient, CCS3Client
from ..types.config import load_config
from .fetch import fetch

logger = logging.getLogger(__name__)


class VectorStoreLoader:
    """Loads Common Crawl content into OpenAI vector stores."""

    def __init__(self, openai_client: OpenAI):
        """Initialize vector store loader.

        Args:
            openai_client: Pre-configured OpenAI client
        """
        config = load_config()

        self.client = openai_client
        self.embedding_model = config.openai.embedding_model
        self.embedding_dimensions = config.openai.embedding_dimensions

    def create_vector_store(
        self, name: str, chunk_size: int = 800, overlap: int = 400
    ) -> str:
        """Create a new vector store with chunking strategy and embedding configuration.

        Args:
            name: Name for the vector store
            chunk_size: Maximum chunk size in tokens (100-4096, default 800)
            overlap: Token overlap between chunks (default 400, must not exceed half of chunk_size)

        Returns:
            Vector store ID
        """
        chunk_size = max(100, min(4096, chunk_size))  # Clamp to valid range
        max_overlap = chunk_size // 2
        overlap = min(
            max_overlap, overlap
        )  # Ensure overlap doesn't exceed half of chunk_size

        logger.info(
            f"Creating vector store: {name} with max_chunk_size_tokens={chunk_size}, chunk_overlap_tokens={overlap}"
        )
        if self.embedding_model:
            logger.info(f"Using embedding model: {self.embedding_model}")
        if self.embedding_dimensions:
            logger.info(f"Using embedding dimensions: {self.embedding_dimensions}")

        create_kwargs = {
            "name": name,
            "metadata": {"created_by": "cc-vec", "cc_vec_version": "0.1.0"},
            "chunking_strategy": {
                "type": "static",
                "static": {
                    "max_chunk_size_tokens": chunk_size,
                    "chunk_overlap_tokens": overlap,
                },
            },
        }

        extra_body = {}
        if self.embedding_model:
            extra_body["embedding_model"] = self.embedding_model
        if self.embedding_dimensions:
            extra_body["embedding_dimensions"] = self.embedding_dimensions
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        vector_store = self.client.vector_stores.create(**create_kwargs)

        logger.info(f"Created vector store {name} with ID: {vector_store.id}")
        return vector_store.id

    def prepare_files(
        self, record: CrawlRecord, processed_content: Dict[str, Any]
    ) -> List[Tuple[str, io.BytesIO]]:
        """Prepare processed content for upload.

        Args:
            record: Crawl record metadata
            processed_content: Processed content dictionary with clean text

        Returns:
            List of (filename, file_stream) tuples
        """
        files = []
        metadata = processed_content["crawl_metadata"]

        url_str = str(record.url)
        safe_url = url_str.replace("://", "_").replace("/", "_")[:100]
        filename = f"{safe_url}_{record.timestamp}.txt"

        content_text = f"""Title: {processed_content.get("title", "N/A")}
URL: {metadata["url"]}
Timestamp: {metadata["timestamp"]}
Status: {metadata["status"]}
MIME Type: {metadata["mime"]}
Word Count: {processed_content["word_count"]}
Meta Description: {processed_content.get("meta_description", "N/A")}

--- Content ---
{processed_content["text"]}
"""

        file_stream = io.BytesIO(content_text.encode("utf-8"))
        file_stream.name = filename

        files.append((filename, file_stream))
        return files

    def upload_to_vector_store(
        self, vector_store_id: str, files_data: List[Tuple[CrawlRecord, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Upload processed content to vector store.

        Args:
            vector_store_id: ID of the vector store
            files_data: List of (record, processed_content) tuples

        Returns:
            Upload result with status and file counts
        """
        if not files_data:
            logger.warning("No files to upload")
            return {"status": "completed", "file_counts": {"total": 0}}

        logger.info(
            f"Preparing processed content from {len(files_data)} records for upload to vector store {vector_store_id}"
        )

        all_files = []
        all_filenames = []

        for record, processed_content in files_data:
            if processed_content:
                files = self.prepare_files(record, processed_content)
                for filename, file_stream in files:
                    all_filenames.append(filename)
                    all_files.append(file_stream)

        if not all_files:
            logger.warning("No processed content files to upload")
            return {"status": "completed", "file_counts": {"total": 0}}

        logger.info(
            f"Uploading {len(all_files)} processed content chunks to vector store..."
        )

        try:
            file_batch = self.client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store_id, files=all_files
            )

            logger.info(f"Upload completed with status: {file_batch.status}")
            logger.info(f"File counts: {file_batch.file_counts}")

            return {
                "status": file_batch.status,
                "file_counts": file_batch.file_counts,
                "batch_id": file_batch.id,
                "filenames": all_filenames[:10],  # Show first 10 filenames
                "total_chunks": len(all_files),
                "total_pages": len([f for f in files_data if f[1] is not None]),
            }

        except Exception as e:
            logger.error(f"Failed to upload processed content to vector store: {e}")
            raise

        finally:
            for stream in all_files:
                try:
                    stream.close()
                except Exception:
                    pass


def index(
    filter_config: FilterConfig,
    athena_client: CCAthenaClient,
    vector_store_name: str,
    openai_client: OpenAI,
    s3_client: Optional[CCS3Client] = None,
    crawl: str = "CC-MAIN-2024-33",
    limit: int = 10,
    chunk_size: int = 1000,
    overlap: int = 100,
) -> Dict[str, Any]:
    """Index Common Crawl content into a vector store.

    This function fetches content based on filter criteria and indexes it into
    an OpenAI vector store for search and retrieval.

    Args:
        filter_config: Filter configuration with URL patterns
        athena_client: Athena client for searching records
        vector_store_name: Name for the vector store (will be created if needed)
        openai_client: Pre-configured OpenAI client
        s3_client: Optional S3 client for fetching content
        crawl: Crawl ID to search in
        limit: Maximum number of records to process

    Returns:
        Dictionary with index results including vector store ID and upload status
    """
    logger.info(
        f"Indexing content into vector store '{vector_store_name}' (limit: {limit})"
    )

    if s3_client is None:
        s3_client = CCS3Client()

    loader = VectorStoreLoader(openai_client)

    logger.info("Fetching and processing content from Common Crawl...")
    fetch_results = fetch(filter_config, athena_client, s3_client, crawl, limit)

    successful_fetches = [
        (record, processed_content)
        for record, processed_content in fetch_results
        if processed_content is not None
    ]

    if not successful_fetches:
        logger.warning("No content was successfully fetched and processed")
        return {
            "vector_store_id": None,
            "status": "no_content",
            "total_fetched": len(fetch_results),
            "successful_fetches": 0,
        }

    total_chunks = sum(
        len(content.get("chunks", [])) for _, content in successful_fetches if content
    )
    logger.info(
        f"Successfully processed {len(successful_fetches)}/{len(fetch_results)} records into {total_chunks} chunks"
    )

    vector_store_id = loader.create_vector_store(vector_store_name, chunk_size, overlap)

    upload_result = loader.upload_to_vector_store(vector_store_id, successful_fetches)

    return {
        "vector_store_id": vector_store_id,
        "vector_store_name": vector_store_name,
        "crawl": crawl,
        "total_fetched": len(fetch_results),
        "successful_fetches": len(successful_fetches),
        "total_chunks": upload_result.get("total_chunks", total_chunks),
        "total_pages": upload_result.get("total_pages", len(successful_fetches)),
        "upload_status": upload_result["status"],
        "file_counts": upload_result["file_counts"],
        "batch_id": upload_result["batch_id"],
        "filenames": upload_result["filenames"],
    }
