"""List vector stores functionality for cc-vec."""

import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..types.config import load_config

logger = logging.getLogger(__name__)


def list_vector_stores(openai_client: Optional[OpenAI] = None) -> List[Dict[str, Any]]:
    """List available OpenAI vector stores.

    Args:
        openai_client: Optional pre-configured OpenAI client

    Returns:
        List of vector store information dictionaries

    Raises:
        ValueError: If OpenAI API key is not configured
    """
    logger.info("Listing available vector stores")

    if openai_client is None:
        config = load_config()
        if not config.openai.is_configured():
            raise ValueError("OpenAI API key is required for vector store operations")
        openai_client = OpenAI(api_key=config.openai.api_key)

    try:
        vector_stores = openai_client.vector_stores.list()

        store_list = []
        for store in vector_stores.data:
            # Convert file_counts object to dictionary for JSON serialization
            file_counts_dict = None
            if store.file_counts:
                file_counts_dict = {
                    "in_progress": getattr(store.file_counts, "in_progress", 0),
                    "completed": getattr(store.file_counts, "completed", 0),
                    "failed": getattr(store.file_counts, "failed", 0),
                    "cancelled": getattr(store.file_counts, "cancelled", 0),
                    "total": getattr(store.file_counts, "total", 0),
                }
            
            store_info = {
                "id": store.id,
                "name": store.name,
                "status": store.status,
                "file_counts": file_counts_dict,
                "created_at": store.created_at,
                "usage_bytes": store.usage_bytes,
                "expires_after": getattr(store, "expires_after", None),
                "expires_at": getattr(store, "expires_at", None),
                "last_active_at": getattr(store, "last_active_at", None),
            }
            store_list.append(store_info)

        logger.info(f"Found {len(store_list)} vector stores")
        return store_list

    except Exception as e:
        logger.error(f"Failed to list vector stores: {e}")
        raise
