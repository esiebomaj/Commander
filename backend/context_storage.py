"""
Context storage with Qdrant vector database backend.

This module provides high-level context operations that combine
embedding generation with vector storage. For simple CRUD operations,
use the QdrantVectorStore directly via get_vector_store().
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .embeddings import generate_embedding
from .models import ContextItem, ProposedAction, SourceType
from .storage import get_actions_for_context
from .vector_store import QdrantVectorStore


# --------------------------------------------------------------------------- #
# Vector Store Singleton
# --------------------------------------------------------------------------- #

_vector_store: Optional[QdrantVectorStore] = None


def get_vector_store() -> QdrantVectorStore:
    """
    Get the shared vector store instance.
    
    Use this for simple operations like:
    - store.get_by_id(id)
    - store.check_exist(user_id, source_id, source_type)
    - store.update_processed(id, True)
    - store.list_contexts(user_id, ...)
    
    For operations that require embedding generation, use the 
    module-level functions like save_context() and search_similar_contexts().
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = QdrantVectorStore()
    return _vector_store


# --------------------------------------------------------------------------- #
# High-Level Operations (with embedding generation)
# --------------------------------------------------------------------------- #

def save_context(user_id: str, context: ContextItem) -> ContextItem:
    """
    Save a context item with its embedding to Qdrant.
    
    Generates an embedding from context_text before storing.
    If the context already exists (by ID), it will be updated.
    
    Args:
        user_id: The user's ID
        context: The context item to save
    
    Returns:
        The saved context item
    """
    store = get_vector_store()
    
    # Generate embedding from context_text
    embedding = generate_embedding(context.context_text)
    
    # Upsert to Qdrant
    store.upsert(user_id, context, embedding)
    
    return context


def search_similar_contexts(
    user_id: str,
    query_text: str,
    limit: int = 10,
    score_threshold: float | None = None,
    source_type: Optional[SourceType] = None,
) -> List[Tuple[ContextItem, float]]:
    """
    Search for contexts similar to the given query text.
    
    Generates an embedding for the query before searching.
    
    Args:
        user_id: The user's ID
        query_text: The text to search for
        limit: Maximum number of results
        score_threshold: Minimum similarity score (0-1)
        source_type: Optional filter by source type
    
    Returns:
        List of (ContextItem, similarity_score) tuples
    """
    store = get_vector_store()
    
    # Generate embedding for query
    query_embedding = generate_embedding(query_text)
    
    # Search in Qdrant
    return store.search_similar(
        user_id=user_id,
        embedding=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
        source_type=source_type,
    )


# --------------------------------------------------------------------------- #
# Complex Operations (orchestration logic)
# --------------------------------------------------------------------------- #

def get_relevant_history(
    user_id: str,
    current_context: ContextItem,
    semantic_limit: int = 5,
    recent_limit: int = 5,
) -> Tuple[List[Tuple[ContextItem, List[ProposedAction]]], List[Tuple[ContextItem, List[ProposedAction]]]]:
    """
    Get relevant historical contexts for LLM decision-making.
    
    Returns two separate lists:
    1. Semantically similar contexts (topically related for background info)
    2. Recent chronological contexts (temporal awareness of current state)
    
    Args:
        user_id: The user's ID
        current_context: The context being processed
        semantic_limit: Number of semantically similar contexts to fetch
        recent_limit: Number of recent contexts to fetch
    
    Returns:
        Tuple of (similar_history, recent_history) where each is a list of 
        (ContextItem, List[ProposedAction]) tuples
    """
    store = get_vector_store()
    
    # 1. Get semantically similar contexts
    similar_results = search_similar_contexts(
        user_id=user_id,
        query_text=current_context.context_text,
        limit=semantic_limit + 1,  # +1 to account for current context
    )
    
    # Extract contexts and filter out current context
    similar_contexts = [
        ctx for ctx, score in similar_results 
        if ctx.id != current_context.id
    ][:semantic_limit]
    
    # 2. Get recent processed contexts (native ordering from Qdrant)
    recent_contexts_raw = store.list_contexts(
        user_id=user_id,
        limit=recent_limit + semantic_limit + 1,  # Extra for deduplication
        processed=True,
        order_desc=True,
    )
    
    # Deduplicate: exclude current context and any already in similar contexts
    similar_ids = {ctx.id for ctx in similar_contexts}
    recent_contexts = [
        ctx for ctx in recent_contexts_raw
        if ctx.id != current_context.id and ctx.id not in similar_ids
    ][:recent_limit]
    
    # 3. Fetch associated actions for each context
    similar_history: List[Tuple[ContextItem, List[ProposedAction]]] = []
    for ctx in similar_contexts:
        actions = get_actions_for_context(user_id, ctx.id)
        similar_history.append((ctx, actions))
    
    recent_history: List[Tuple[ContextItem, List[ProposedAction]]] = []
    for ctx in recent_contexts:
        actions = get_actions_for_context(user_id, ctx.id)
        recent_history.append((ctx, actions))
    
    return similar_history, recent_history
