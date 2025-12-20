"""
Initialize Qdrant collection for Commander.

Called automatically on app startup to ensure the collection exists.
"""
from __future__ import annotations

from .vector_store import QdrantVectorStore


def init_qdrant():
    """Initialize Qdrant collection. Called on app startup."""
    # Instantiating QdrantVectorStore ensures the collection exists
    QdrantVectorStore()
