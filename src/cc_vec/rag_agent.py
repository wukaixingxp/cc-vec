"""RAG Agent using cc-vec and Llama Stack for document retrieval and generation."""

import logging
import os
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from llama_stack_client import LlamaStackClient

from . import api as cc_vec_api
from .types import CrawlRecord

logger = logging.getLogger(__name__)


class CCVecRAGAgent:
    """RAG Agent that combines cc-vec for Common Crawl indexing with Llama Stack for generation."""

    def __init__(
        self,
        llama_stack_url: Optional[str] = None,
        model: str = "meta-llama/Llama-3.3-70B-Instruct",
    ):
        """Initialize the RAG agent.

        Args:
            llama_stack_url: Llama Stack server URL (defaults to env var LLAMA_STACK_PORT)
            model: Model to use for generation
        """
        # Initialize Llama Stack client
        if llama_stack_url is None:
            port = os.environ.get("LLAMA_STACK_PORT", "8321")
            llama_stack_url = f"http://localhost:{port}"

        self.llama_client = LlamaStackClient(base_url=llama_stack_url)
        self.model = model

        logger.info(
            f"Initialized RAG agent with Llama Stack at {llama_stack_url}, model: {model}"
        )

    def create_knowledge_base_from_common_crawl(
        self,
        url_pattern: str,
        vector_store_name: str,
        *,
        limit: int = 50,
        crawl: str = "CC-MAIN-2024-33",
        status_codes: Optional[List[int]] = None,
        mime_types: Optional[List[str]] = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_dimension: int = 384,
        provider_id: str = "faiss",
    ) -> Dict[str, Any]:
        """Create a Llama Stack knowledge base from Common Crawl data.

        Args:
            url_pattern: URL pattern to search (e.g. '%.github.io')
            vector_store_name: Name for the vector store
            limit: Maximum number of pages to index
            crawl: Common Crawl dataset to use
            status_codes: HTTP status codes to filter by
            mime_types: MIME types to filter by
            embedding_model: Embedding model to use
            embedding_dimension: Dimension of embeddings
            provider_id: Vector database backend

        Returns:
            Dictionary with knowledge base creation results
        """
        logger.info(
            f"Creating knowledge base '{vector_store_name}' from Common Crawl pattern: {url_pattern}"
        )

        # Step 1: Fetch content from Common Crawl using cc-vec
        logger.info("Fetching content from Common Crawl...")
        content_results = cc_vec_api.fetch(
            url_pattern,
            limit=limit,
            crawl=crawl,
            status_codes=status_codes,
            mime_types=mime_types,
        )

        if not content_results:
            raise ValueError(f"No content found for pattern: {url_pattern}")

        # Filter successful results
        successful_results = [
            (record, content)
            for record, content in content_results
            if content is not None
        ]

        if not successful_results:
            raise ValueError(
                f"No successfully processed content found for pattern: {url_pattern}"
            )

        logger.info(
            f"Successfully processed {len(successful_results)}/{len(content_results)} pages"
        )

        # Step 2: Upload documents to Llama Stack Files API
        logger.info("Uploading documents to Llama Stack...")
        file_ids = []

        for record, processed_content in successful_results:
            try:
                # Prepare document content
                content_text = self._prepare_document_content(record, processed_content)

                # Create file buffer
                with BytesIO(content_text.encode("utf-8")) as file_buffer:
                    # Generate safe filename
                    url_str = str(record.url)
                    safe_url = url_str.replace("://", "_").replace("/", "_")[:50]
                    file_buffer.name = f"{safe_url}_{record.timestamp}.txt"

                    # Upload to Llama Stack
                    create_file_response = self.llama_client.files.create(
                        file=file_buffer, purpose="assistants"
                    )
                    file_ids.append(create_file_response.id)
                    logger.debug(f"Uploaded: {create_file_response.id}")

            except Exception as e:
                logger.warning(f"Failed to upload content from {record.url}: {e}")
                continue

        if not file_ids:
            raise ValueError("Failed to upload any documents to Llama Stack")

        logger.info(f"Successfully uploaded {len(file_ids)} documents")

        # Step 3: Create Llama Stack vector store
        logger.info("Creating Llama Stack vector store...")
        vector_store = self.llama_client.vector_stores.create(
            name=vector_store_name,
            file_ids=file_ids,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            provider_id=provider_id,
        )

        logger.info(
            f"Created vector store: {vector_store.name} (ID: {vector_store.id})"
        )

        return {
            "vector_store_id": vector_store.id,
            "vector_store_name": vector_store.name,
            "file_ids": file_ids,
            "total_documents": len(file_ids),
            "crawl": crawl,
            "url_pattern": url_pattern,
            "embedding_model": embedding_model,
            "embedding_dimension": embedding_dimension,
            "provider_id": provider_id,
        }

    def query_knowledge_base(
        self, vector_store_id: str, query: str, *, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query the knowledge base and get an AI-generated response.

        Args:
            vector_store_id: ID of the vector store to query
            query: Question or query to ask
            model: Model to use (defaults to instance model)

        Returns:
            Dictionary with query results and generated response
        """
        model = model or self.model
        logger.info(f"Querying knowledge base {vector_store_id} with: '{query}'")

        try:
            # Query using Llama Stack Responses API with file_search tool
            response = self.llama_client.responses.create(
                model=model,
                input=query,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store_id],
                    },
                ],
            )

            logger.info("Query completed successfully")
            return {
                "query": query,
                "vector_store_id": vector_store_id,
                "model": model,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Failed to query knowledge base: {e}")
            raise

    def query_multiple_knowledge_bases(
        self, vector_store_ids: List[str], query: str, *, model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query multiple knowledge bases simultaneously.

        Args:
            vector_store_ids: List of vector store IDs to search
            query: Question or query to ask
            model: Model to use (defaults to instance model)

        Returns:
            Dictionary with query results and generated response
        """
        model = model or self.model
        logger.info(f"Querying {len(vector_store_ids)} knowledge bases with: '{query}'")

        try:
            response = self.llama_client.responses.create(
                model=model,
                input=query,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": vector_store_ids,
                    },
                ],
            )

            logger.info("Multi-base query completed successfully")
            return {
                "query": query,
                "vector_store_ids": vector_store_ids,
                "model": model,
                "response": response,
            }

        except Exception as e:
            logger.error(f"Failed to query multiple knowledge bases: {e}")
            raise

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """List all available Llama Stack vector stores.

        Returns:
            List of vector store information
        """
        try:
            vector_stores = self.llama_client.vector_stores.list()

            result = []
            for vs in vector_stores:
                # Get files in vector store
                files_in_store = self.llama_client.vector_stores.files.list(
                    vector_store_id=vs.id
                )

                result.append(
                    {
                        "id": vs.id,
                        "name": vs.name,
                        "file_count": len(files_in_store) if files_in_store else 0,
                        "created_at": getattr(vs, "created_at", None),
                        "status": getattr(vs, "status", "unknown"),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Failed to list knowledge bases: {e}")
            raise

    def delete_knowledge_base(self, vector_store_id: str) -> Dict[str, Any]:
        """Delete a knowledge base.

        Args:
            vector_store_id: ID of the vector store to delete

        Returns:
            Dictionary with deletion result
        """
        try:
            self.llama_client.vector_stores.delete(vector_store_id=vector_store_id)
            logger.info(f"Deleted knowledge base: {vector_store_id}")

            return {"vector_store_id": vector_store_id, "status": "deleted"}

        except Exception as e:
            logger.error(f"Failed to delete knowledge base {vector_store_id}: {e}")
            raise

    def _prepare_document_content(
        self, record: CrawlRecord, processed_content: Dict[str, Any]
    ) -> str:
        """Prepare document content for upload to Llama Stack.

        Args:
            record: Crawl record metadata
            processed_content: Processed content dictionary

        Returns:
            Formatted content string
        """
        metadata = processed_content["crawl_metadata"]

        content_text = f"""Title: {processed_content.get('title', 'N/A')}
URL: {metadata['url']}
Timestamp: {metadata['timestamp']}
Status: {metadata['status']}
MIME Type: {metadata['mime']}
Word Count: {processed_content['word_count']}
Meta Description: {processed_content.get('meta_description', 'N/A')}

--- Content ---
{processed_content['text']}
"""
        return content_text




# Convenience functions for direct usage
def create_rag_agent(
    llama_stack_url: Optional[str] = None,
    model: str = "meta-llama/Llama-3.3-70B-Instruct",
) -> CCVecRAGAgent:
    """Create a RAG agent instance.

    Args:
        llama_stack_url: Llama Stack server URL
        model: Model to use for generation

    Returns:
        Configured RAG agent
    """
    return CCVecRAGAgent(llama_stack_url=llama_stack_url, model=model)




if __name__ == "__main__":
    # Create a basic RAG agent when run directly
    rag_agent = create_rag_agent()
    print("CC-Vec RAG Agent initialized. Use the create_rag_agent() function to get started.")
