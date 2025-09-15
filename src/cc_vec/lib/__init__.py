"""Library interface for cc-vec operations."""

from .stats import stats
from .search import search
from .fetch import fetch
from .index import index
from .list_vector_stores import list_vector_stores
from .query import query_vector_store, query_vector_store_by_name
from .delete_vector_store import delete_vector_store, delete_vector_store_by_name

__all__ = ["stats", "search", "fetch", "index", "list_vector_stores", "query_vector_store", "query_vector_store_by_name", "delete_vector_store", "delete_vector_store_by_name"]