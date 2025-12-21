"""
Supabase client initialization for Commander backend.

Provides both service-role client (for backend operations bypassing RLS)
and user-context client (for operations respecting RLS).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from .config import settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Get a Supabase client with service role key.
    
    This client bypasses Row Level Security and should only be used
    for backend operations where we've already verified the user.
    
    Returns:
        Supabase client instance
    """
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def get_user_supabase_client(access_token: str) -> Client:
    """
    Get a Supabase client authenticated as a specific user.
    
    This client respects Row Level Security policies.
    
    Args:
        access_token: The user's JWT access token
    
    Returns:
        Supabase client instance authenticated as the user
    """
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
    client.auth.set_session(access_token, "")
    return client


# Convenience aliases
get_db = get_supabase_client 
