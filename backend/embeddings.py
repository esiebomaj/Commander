"""
Embedding generation service for Commander.

Provides functions for:
- Token counting using tiktoken
- Text truncation to fit within token limits
- Embedding generation using OpenAI API
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

import tiktoken
from openai import OpenAI

from .config import settings


# --------------------------------------------------------------------------- #
# Token Counting & Truncation
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _get_encoder() -> tiktoken.Encoding:
    """Get cached tiktoken encoder for the embedding model."""
    # text-embedding-3-small and all modern OpenAI models use cl100k_base encoding
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """
    Count the number of tokens in a text string.
    
    Args:
        text: The text to count tokens for
    
    Returns:
        Number of tokens
    """
    encoder = _get_encoder()
    return len(encoder.encode(text))


def truncate_to_tokens(text: str, max_tokens: int ) -> str:
    """
    Truncate text to fit within a maximum token count.
    
    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens 
    
    Returns:
        Truncated text string
    """
    encoder = _get_encoder()
    
    tokens = encoder.encode(text)
    
    if len(tokens) <= max_tokens:
        return text
    
    # Truncate and decode back to text
    truncated_tokens = tokens[:max_tokens]
    truncated_text = encoder.decode(truncated_tokens)
    
    print(f"Text truncated from {len(tokens)} to {len(truncated_tokens)} tokens")
    
    return truncated_text


# --------------------------------------------------------------------------- #
# Embedding Generation
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    """Get cached OpenAI client."""
    return OpenAI(api_key=settings.openai_api_key)


def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text.
    
    Automatically truncates text if it exceeds max_embedding_tokens.
    
    Args:
        text: The text to embed
    
    Returns:
        List of floats representing the embedding vector
    
    Raises:
        ValueError: If text is empty
        OpenAI API errors: If embedding generation fails
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")
    
    # Truncate if necessary
    text = truncate_to_tokens(text, settings.max_embedding_tokens)
    
    # Generate embedding
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model=settings.embedding_model
    )
    
    embedding = response.data[0].embedding
    
    return embedding


def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in a single API call.
    
    More efficient than calling generate_embedding() multiple times.
    Automatically truncates texts that exceed max_embedding_tokens.
    
    Args:
        texts: List of texts to embed
    
    Returns:
        List of embedding vectors
    
    Raises:
        ValueError: If texts list is empty or contains empty strings
    """
    if not texts:
        raise ValueError("Cannot generate embeddings for empty list")
    
    # Truncate all texts if necessary
    processed_texts = []
    for text in texts:
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        text = truncate_to_tokens(text, settings.max_embedding_tokens)
        
        processed_texts.append(text)
    
    # Generate embeddings in batch
    client = _get_openai_client()
    response = client.embeddings.create(
        input=processed_texts,
        model=settings.embedding_model
    )
    
    # Extract embeddings in order
    embeddings = [item.embedding for item in response.data]
    
    return embeddings
