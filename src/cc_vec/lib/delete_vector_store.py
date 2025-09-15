"""Delete vector store functionality for cc-vec."""

import logging
from typing import Optional, Dict, Any
from openai import OpenAI

from ..types.config import load_config
from .list_vector_stores import list_vector_stores

logger = logging.getLogger(__name__)


def delete_vector_store(
    vector_store_id: str,
    openai_client: Optional[OpenAI] = None
) -> Dict[str, Any]:
    """Delete a vector store by ID.

    Args:
        vector_store_id: ID of the vector store to delete
        openai_client: Optional pre-configured OpenAI client

    Returns:
        Dictionary with deletion result

    Raises:
        ValueError: If OpenAI API key is not configured or vector store not found
    """
    logger.info(f"Deleting vector store: {vector_store_id}")

    if openai_client is None:
        config = load_config()
        if not config.openai.is_configured():
            raise ValueError("OpenAI API key is required for vector store operations")
        openai_client = OpenAI(api_key=config.openai.api_key)

    try:
        deletion_status = openai_client.vector_stores.delete(vector_store_id)

        logger.info(f"Successfully deleted vector store: {vector_store_id}")
        return {
            "id": vector_store_id,
            "deleted": deletion_status.deleted,
            "object": deletion_status.object
        }

    except Exception as e:
        logger.error(f"Failed to delete vector store {vector_store_id}: {e}")
        raise


def delete_vector_store_by_name(
    vector_store_name: str,
    openai_client: Optional[OpenAI] = None
) -> Dict[str, Any]:
    """Delete a vector store by name.

    Args:
        vector_store_name: Name of the vector store to delete
        openai_client: Optional pre-configured OpenAI client

    Returns:
        Dictionary with deletion result

    Raises:
        ValueError: If vector store with given name is not found
    """
    logger.info(f"Looking for vector store with name: {vector_store_name}")

    stores = list_vector_stores(openai_client)
    matching_stores = [store for store in stores if store["name"] == vector_store_name]

    if not matching_stores:
        raise ValueError(f"Vector store with name '{vector_store_name}' not found")

    if len(matching_stores) > 1:
        logger.warning(f"Multiple vector stores found with name '{vector_store_name}', deleting the first one")

    vector_store_id = matching_stores[0]["id"]
    logger.info(f"Found vector store '{vector_store_name}' with ID: {vector_store_id}")

    return delete_vector_store(vector_store_id, openai_client)