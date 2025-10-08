"""List vector stores functionality for cc-vec."""

import logging
from typing import Any, Dict, List

from openai import OpenAI


logger = logging.getLogger(__name__)


def list_vector_stores(
    openai_client: OpenAI, cc_vec_only: bool = False
) -> List[Dict[str, Any]]:
    """List available OpenAI vector stores.

    Args:
        openai_client: Pre-configured OpenAI client
        cc_vec_only: If True, only return vector stores created by cc-vec

    Returns:
        List of vector store information dictionaries
    """
    logger.info("Listing available vector stores")

    try:
        vector_stores = openai_client.vector_stores.list()

        store_list = []
        for store in vector_stores.data:
            # Convert metadata to dict
            metadata_dict = dict(store.metadata) if store.metadata else {}

            # Filter by cc-vec if requested
            if cc_vec_only and metadata_dict.get("created_by") != "cc-vec":
                continue

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
                "metadata": metadata_dict,
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
