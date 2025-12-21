"""
Token storage for OAuth credentials using Supabase.

Stores tokens securely in the database, per user per service.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from ..supabase_client import get_db


# --------------------------------------------------------------------------- #
# Token Storage Functions
# --------------------------------------------------------------------------- #

def save_token(user_id: str, service: str, token_data: Dict[str, Any]) -> None:
    """
    Save OAuth token data for a service.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "calendar", "drive")
        token_data: Token data including access_token, refresh_token, etc.
    """
    db = get_db()
    
    # Add updated_at timestamp
    token_data_with_ts = {
        **token_data,
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    # Upsert - insert or update on conflict
    db.table("integration_tokens").upsert({
        "user_id": user_id,
        "service": service,
        "token_data": token_data_with_ts,
        "updated_at": datetime.utcnow().isoformat(),
    }, on_conflict="user_id,service").execute()


def get_token(user_id: str, service: str) -> Optional[Dict[str, Any]]:
    """
    Get OAuth token data for a service.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "calendar", "drive")
    
    Returns:
        Token data dict or None if not found
    """
    db = get_db()
    
    result = db.table("integration_tokens").select("token_data").eq("user_id", user_id).eq("service", service).execute()
    
    if result.data:
        return result.data[0]["token_data"]
    return None


def delete_token(user_id: str, service: str) -> bool:
    """
    Delete OAuth token for a service.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "calendar", "drive")
    
    Returns:
        True if token was deleted, False if it didn't exist
    """
    db = get_db()
    
    result = db.table("integration_tokens").delete().eq("user_id", user_id).eq("service", service).execute()
    
    return len(result.data) > 0


def has_token(user_id: str, service: str) -> bool:
    """Check if a service has stored credentials for a user."""
    return get_token(user_id, service) is not None


def list_services(user_id: str) -> list[str]:
    """List all services with stored tokens for a user."""
    db = get_db()
    
    result = db.table("integration_tokens").select("service").eq("user_id", user_id).execute()
    
    return [row["service"] for row in result.data]


# --------------------------------------------------------------------------- #
# Gmail-specific helpers
# --------------------------------------------------------------------------- #

def save_gmail_history_id(user_id: str, history_id: str) -> None:
    """
    Save the last Gmail history ID for incremental sync.
    
    Args:
        user_id: The user's ID
        history_id: The Gmail history ID to save
    """
    token_data = get_token(user_id, "gmail") or {}
    token_data["last_history_id"] = history_id
    token_data["history_updated_at"] = datetime.utcnow().isoformat()
    save_token(user_id, "gmail", token_data)


def get_gmail_history_id(user_id: str) -> Optional[str]:
    """Get the last Gmail history ID for incremental sync."""
    token_data = get_token(user_id, "gmail")
    if token_data:
        return token_data.get("last_history_id")
    return None
