"""
Qdrant vector store client for Commander.

Provides a wrapper around the Qdrant client for managing context embeddings.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    OrderBy,
    PointStruct,
    VectorParams,
)

from .config import settings
from .models import ContextItem, SourceType

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Qdrant Client Singleton
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Get cached Qdrant client instance."""
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


# --------------------------------------------------------------------------- #
# Context Item Conversion
# --------------------------------------------------------------------------- #

def _context_to_payload(context: ContextItem) -> Dict[str, Any]:
    """Convert ContextItem to Qdrant payload."""
    return {
        "id": context.id,
        "source_type": context.source_type.value,
        "source_id": context.source_id,
        "timestamp": context.timestamp.isoformat(),
        "created_at": context.created_at.isoformat(),
        "content": context.content,
        "context_text": context.context_text,
        "sender": context.sender,
        "summary": context.summary,
        "processed": context.processed,
    }


def _payload_to_context(payload: Dict[str, Any]) -> ContextItem:
    """Convert Qdrant payload to ContextItem."""
    from datetime import datetime

    return ContextItem(
        id=payload["id"],
        source_type=SourceType(payload["source_type"]),
        source_id=payload["source_id"],
        timestamp=datetime.fromisoformat(payload["timestamp"]),
        created_at=datetime.fromisoformat(payload["created_at"]),
        content=payload.get("content", {}),
        context_text=payload.get("context_text", ""),
        sender=payload.get("sender"),
        summary=payload.get("summary"),
        processed=payload.get("processed", False),
    )


# --------------------------------------------------------------------------- #
# Vector Store Class
# --------------------------------------------------------------------------- #

class QdrantVectorStore:
    """Wrapper for Qdrant operations on context items."""
    
    DEFAULT_VECTOR_SIZE = 1536  # text-embedding-3-small
    DEFAULT_DISTANCE = Distance.COSINE
    
    def __init__(
        self,
        collection_name: str | None = None,
        vector_size: int = DEFAULT_VECTOR_SIZE,
        distance: Distance = DEFAULT_DISTANCE,
    ):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the collection (defaults to settings.qdrant_collection_name)
            vector_size: Size of the embedding vectors (default 1536 for text-embedding-3-small)
            distance: Distance metric for similarity search (default COSINE)
        """
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.client = get_qdrant_client()
        self._ensure_collection_exists()
    
    # ----------------------------------------------------------------------- #
    # Collection Management
    # ----------------------------------------------------------------------- #
    
    def _ensure_collection_exists(self) -> None:
        """Ensure the collection exists. Creates it if it doesn't."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name in collection_names:
            logger.debug(f"Collection '{self.collection_name}' already exists")
            return
        
        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=self.distance,
            ),
        )
        
        # Create payload indexes for efficient filtering and sorting
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source_id",
            field_schema="keyword",
        )
        
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="source_type",
            field_schema="keyword",
        )
        
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="processed",
            field_schema="bool",
        )
        
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="timestamp",
            field_schema="datetime",
        )
        
        logger.info(f"Collection '{self.collection_name}' created successfully")
    
    def delete_collection(self) -> None:
        """Delete the collection (use with caution!)."""
        self.client.delete_collection(collection_name=self.collection_name)
        logger.info(f"Collection '{self.collection_name}' deleted")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection.
        
        Returns:
            Dictionary with collection info
        """
        info = self.client.get_collection(collection_name=self.collection_name)
        
        return {
            "name": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "config": {
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
            }
        }
    
    # ----------------------------------------------------------------------- #
    # CRUD Operations
    # ----------------------------------------------------------------------- #
    
    def upsert(self, context: ContextItem, embedding: List[float]) -> None:
        """
        Insert or update a context item with its embedding.
        
        Args:
            context: The context item to store
            embedding: The embedding vector for the context
        """
        point = PointStruct(
            id=context.id,
            vector=embedding,
            payload=_context_to_payload(context),
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )
    
    def get_by_id(self, context_id: str) -> Optional[ContextItem]:
        """
        Retrieve a context by its ID.
        
        Args:
            context_id: The context ID to retrieve
        
        Returns:
            ContextItem if found, None otherwise
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[context_id],
            )
            
            if not result:
                return None
            
            return _payload_to_context(result[0].payload)
        except Exception as e:
            logger.error(f"Error retrieving context {context_id}: {e}")
            return None
    
    def get_by_source_id(
        self,
        source_id: str,
        source_type: Optional[SourceType] = None
    ) -> Optional[ContextItem]:
        """
        Retrieve a context by its source system ID.
        
        Args:
            source_id: The source system ID
            source_type: Optional source type filter
        
        Returns:
            ContextItem if found, None otherwise
        """
        filter_conditions = [
            FieldCondition(
                key="source_id",
                match=MatchValue(value=source_id),
            )
        ]
        
        if source_type:
            filter_conditions.append(
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type.value),
                )
            )
        
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(must=filter_conditions),
            limit=1,
        )
        
        if not results:
            return None
        
        return _payload_to_context(results[0].payload)

    def check_exist(self, source_id: str, source_type: SourceType) -> bool:
        """
        Check if a context exists by its source ID and type.
        
        Args:
            source_id: The source system ID
            source_type: The source type
        """
        return self.get_by_source_id(source_id, source_type) is not None
    
    def update_processed(self, context_id: str, processed: bool = True) -> bool:
        """
        Update the processed flag for a context.
        
        Args:
            context_id: The context ID to update
            processed: New processed status
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload={"processed": processed},
                points=[context_id],
            )
            return True
        except Exception as e:
            logger.error(f"Error updating processed status for {context_id}: {e}")
            return False
    
    # ----------------------------------------------------------------------- #
    # Search & List Operations
    # ----------------------------------------------------------------------- #
    
    def search_similar(
        self,
        embedding: List[float],
        limit: int = 10,
        score_threshold: float | None = None,
        source_type: Optional[SourceType] = None,
        processed: Optional[bool] = None,
    ) -> List[Tuple[ContextItem, float]]:
        """
        Search for similar contexts using vector similarity.
        
        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            source_type: Optional filter by source type
            processed: Optional filter by processed status
        
        Returns:
            List of (ContextItem, similarity_score) tuples
        """
        filter_conditions = []
        
        if source_type:
            filter_conditions.append(
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type.value),
                )
            )
        
        if processed is not None:
            filter_conditions.append(
                FieldCondition(
                    key="processed",
                    match=MatchValue(value=processed),
                )
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
        )
        print(results)
        return [
            (_payload_to_context(result.payload), result.score)
            for result in results.points
        ]
    
    def list_contexts(
        self,
        limit: int = 100,
        source_type: Optional[SourceType] = None,
        processed: Optional[bool] = None,
        order_desc: bool = True,
    ) -> List[ContextItem]:
        """
        List contexts with optional filtering, ordered by timestamp.
        
        Args:
            limit: Maximum number of contexts to return
            source_type: Optional filter by source type
            processed: Optional filter by processed status
            order_desc: If True, return newest first (default True)
        
        Returns:
            List of ContextItem objects ordered by timestamp
        """
        filter_conditions = []
        
        if source_type:
            filter_conditions.append(
                FieldCondition(
                    key="source_type",
                    match=MatchValue(value=source_type.value),
                )
            )
        
        if processed is not None:
            filter_conditions.append(
                FieldCondition(
                    key="processed",
                    match=MatchValue(value=processed),
                )
            )
        
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=search_filter,
            limit=limit,
            order_by=OrderBy(
                key="timestamp",
                direction="desc" if order_desc else "asc",
            ),
        )
        
        return [_payload_to_context(result.payload) for result in results]
