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




# --------------------------------------------------------------------------- #
# Webhook Info Helpers (generic for any service)
# --------------------------------------------------------------------------- #

def save_webhook_info(user_id: str, service: str, webhook_info: Dict[str, Any]) -> None:
    """
    Save webhook info nested in the service's token data.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "google_drive")
        webhook_info: Webhook configuration (channel_id, expiration, etc.)
    """
    token_data = get_token(user_id, service) or {}
    token_data["webhook"] = {
        **webhook_info,
        "updated_at": datetime.utcnow().isoformat(),
    }
    save_token(user_id, service, token_data)


def get_webhook_info(user_id: str, service: str) -> Optional[Dict[str, Any]]:
    """
    Get webhook info from the service's token data.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "google_drive")
    
    Returns:
        Webhook info dict or None if not set
    """
    token_data = get_token(user_id, service)
    if token_data:
        return token_data.get("webhook")
    return None


def clear_webhook_info(user_id: str, service: str) -> None:
    """
    Remove webhook info from the service's token data.
    
    Args:
        user_id: The user's ID
        service: The service name (e.g., "gmail", "google_drive")
    """
    token_data = get_token(user_id, service)
    if token_data and "webhook" in token_data:
        del token_data["webhook"]
        save_token(user_id, service, token_data)


def get_user_ids_by_webhook_email(service: str, email: str) -> list[str]:
    """
    Find all user_ids that have this email in their webhook info.
    
    Used by webhooks to identify which user(s) a notification is for.
    Returns a list since multiple users could have the same email connected.
    
    Args:
        service: The service name (e.g., "gmail")
        email: The email address to look up
    
    Returns:
        List of user_ids that have this email connected
    """
    db = get_db()
    
    # Use Postgres JSONB operator to query directly
    # This queries: token_data -> 'webhook' ->> 'email' = email
    result = db.table("integration_tokens") \
        .select("user_id") \
        .eq("service", service) \
        .filter("token_data->webhook->>email", "eq", email) \
        .execute()
    
    return [row["user_id"] for row in result.data]
