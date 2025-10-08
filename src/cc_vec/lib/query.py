"""Query vector stores functionality for cc-vec."""

import logging
from typing import Dict, Any
from openai import OpenAI


logger = logging.getLogger(__name__)


def query_vector_store(
    vector_store_id: str, query: str, limit: int, openai_client: OpenAI
) -> Dict[str, Any]:
    """Query a vector store for relevant content.

    Args:
        vector_store_id: ID of the vector store to query
        query: Query string to search for
        limit: Maximum number of results to return
        openai_client: Pre-configured OpenAI client

    Returns:
        Dictionary with search results and metadata
    """
    logger.info(
        f"Querying vector store {vector_store_id} with query: '{query}' (limit: {limit})"
    )

    try:
        search_response = openai_client.vector_stores.search(
            vector_store_id=vector_store_id, query=query
        )

        results = []
        for item in search_response.data[:limit]:
            result = {
                "file_id": item.file_id,
                "score": getattr(item, "score", None),
                "content": getattr(item, "content", ""),
                "metadata": getattr(item, "metadata", {}),
                "annotations": getattr(item, "annotations", []),
                "citations": getattr(item, "citations", []),
            }
            results.append(result)

        logger.info(f"Query completed, found {len(results)} results")
        return {
            "vector_store_id": vector_store_id,
            "query": query,
            "results": results,
            "total_results": len(search_response.data),
        }

    except Exception as e:
        logger.error(f"Failed to query vector store: {e}")
        raise


def query_vector_store_by_name(
    vector_store_name: str, query: str, limit: int, openai_client: OpenAI
) -> Dict[str, Any]:
    """Query a vector store by name for relevant content.

    Args:
        vector_store_name: Name of the vector store to query
        query: Query string to search for
        limit: Maximum number of results to return
        openai_client: Pre-configured OpenAI client

    Returns:
        Dictionary with search results and metadata

    Raises:
        ValueError: If vector store with given name is not found
    """
    from .list_vector_stores import list_vector_stores

    stores = list_vector_stores(openai_client)
    matching_stores = [store for store in stores if store["name"] == vector_store_name]

    if not matching_stores:
        raise ValueError(f"Vector store with name '{vector_store_name}' not found")

    if len(matching_stores) > 1:
        logger.warning(
            f"Multiple vector stores found with name '{vector_store_name}', using the first one"
        )

    vector_store_id = matching_stores[0]["id"]
    return query_vector_store(vector_store_id, query, limit, openai_client)
