"""
Web Push Notifications module for Commander.

This module handles:
- VAPID key generation and storage
- Push subscription management (per-user in Supabase)
- Sending notifications to subscribed clients
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pywebpush import webpush, WebPushException

from backend.models import ProposedAction

from .config import settings
from .supabase_client import get_db


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# VAPID keys are shared across all users (stored locally)
VAPID_KEYS_FILE = settings.data_dir / "vapid_keys.json"

# VAPID contact email - used by push services to contact you if needed
VAPID_CLAIMS_EMAIL = "mailto:admin@commander.local"


# --------------------------------------------------------------------------- #
# VAPID Key Management (Local file - shared across users)
# --------------------------------------------------------------------------- #

def _load_vapid_keys() -> Optional[Dict[str, str]]:
    """Load VAPID keys from file."""
    try:
        return json.loads(VAPID_KEYS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _save_vapid_keys(keys: Dict[str, str]):
    """Save VAPID keys to file."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    VAPID_KEYS_FILE.write_text(json.dumps(keys, indent=2))


def _generate_vapid_keys() -> Dict[str, str]:
    """
    Generate new VAPID keys using the cryptography library.
    
    Returns:
        Dict with 'public_key' and 'private_key' in appropriate formats
    """
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    
    # Generate an ECDSA key pair on the P-256 curve
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()
    
    # Get the raw private key bytes (32 bytes for P-256)
    private_numbers = private_key.private_numbers()
    private_bytes = private_numbers.private_value.to_bytes(32, byteorder='big')
    
    # Get the uncompressed public key (65 bytes: 0x04 + 32 bytes x + 32 bytes y)
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # URL-safe base64 encode (without padding) - this is what browsers expect
    private_key_b64 = base64.urlsafe_b64encode(private_bytes).decode('utf-8').rstrip('=')
    public_key_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
    
    return {
        "private_key": private_key_b64,
        "public_key": public_key_b64,
    }


def get_vapid_keys() -> Dict[str, str]:
    """
    Get VAPID keys, generating them if they don't exist.
    
    Returns:
        Dict with 'public_key' and 'private_key' in base64url format
    """
    keys = _load_vapid_keys()
    if keys is None:
        keys = _generate_vapid_keys()
        _save_vapid_keys(keys)
    return keys


def get_public_key() -> str:
    """Get the VAPID public key for frontend subscription."""
    keys = get_vapid_keys()
    return keys["public_key"]


# --------------------------------------------------------------------------- #
# Subscription Management (Supabase - per user)
# --------------------------------------------------------------------------- #

def subscribe(user_id: str, subscription: Dict[str, Any]) -> bool:
    """
    Add a new push subscription for a user.
    
    Args:
        user_id: The user's ID
        subscription: The PushSubscription object from the browser
        
    Returns:
        True if subscription was added/updated
    """
    db = get_db()
    
    endpoint = subscription.get("endpoint", "")
    keys = subscription.get("keys", {})
    
    # Upsert - update if endpoint exists, otherwise insert
    db.table("push_subscriptions").upsert({
        "user_id": user_id,
        "endpoint": endpoint,
        "keys": keys,
    }, on_conflict="endpoint").execute()
    
    return True


def unsubscribe(user_id: str, endpoint: str) -> bool:
    """
    Remove a push subscription by endpoint for a user.
    
    Args:
        user_id: The user's ID
        endpoint: The push subscription endpoint URL
        
    Returns:
        True if subscription was removed, False if not found
    """
    db = get_db()
    
    result = db.table("push_subscriptions").delete().eq("user_id", user_id).eq("endpoint", endpoint).execute()
    
    return len(result.data) > 0


def get_subscription_count(user_id: Optional[str] = None) -> int:
    """
    Get the number of active subscriptions.
    
    Args:
        user_id: If provided, count only for this user. Otherwise count all.
    """
    db = get_db()
    
    query = db.table("push_subscriptions").select("id", count="exact")
    if user_id:
        query = query.eq("user_id", user_id)
    
    result = query.execute()
    return result.count or 0


def get_user_subscriptions(user_id: str) -> List[Dict[str, Any]]:
    """Get all push subscriptions for a user."""
    db = get_db()
    
    result = db.table("push_subscriptions").select("endpoint, keys").eq("user_id", user_id).execute()
    
    return [{"endpoint": row["endpoint"], "keys": row["keys"]} for row in result.data]


# --------------------------------------------------------------------------- #
# Notification Sending
# --------------------------------------------------------------------------- #

def send_notification(
    user_id: str,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/commander.png",
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a push notification to all subscribed devices for a user.
    
    Args:
        user_id: The user's ID
        title: Notification title
        body: Notification body text
        url: URL to open when notification is clicked
        icon: Icon URL for the notification
        tag: Optional tag to group/replace notifications
        
    Returns:
        Dict with 'sent', 'failed', and 'removed' counts
    """
    subscriptions = get_user_subscriptions(user_id)
    keys = get_vapid_keys()
    
    if not subscriptions:
        return {"sent": 0, "failed": 0, "removed": 0}
    
    # Build notification payload
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": icon,
        "tag": tag,
    })
    
    sent = 0
    failed = 0
    removed_endpoints: List[str] = []
    
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=keys["private_key"],
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
            )
            sent += 1
        except WebPushException as e:
            failed += 1
            # If subscription is no longer valid, mark for removal
            if e.response is not None and e.response.status_code in (404, 410):
                removed_endpoints.append(subscription.get("endpoint", ""))
                print(f"Removing invalid subscription: {e}")
            else:
                print(f"WebPush error: {e}")
        except Exception as e:
            failed += 1
            print(f"Unexpected push error: {e}")
    
    # Remove invalid subscriptions
    db = get_db()
    for endpoint in removed_endpoints:
        db.table("push_subscriptions").delete().eq("endpoint", endpoint).execute()
    
    return {
        "sent": sent,
        "failed": failed,
        "removed": len(removed_endpoints),
    }


# --------------------------------------------------------------------------- #
# Helper for Action Notifications
# --------------------------------------------------------------------------- #

def notify_new_action(
    user_id: str,
    action: ProposedAction,
):
    """
    Send a notification about a new proposed action.
    
    Args:
        user_id: The user's ID
        action_type: The type of action (e.g., "send_email", "create_event")
        summary: Optional summary text for the action
        action_id: Optional action ID for deep linking
    """
    # Don't send notifications if there are no subscriptions for this user
    if get_subscription_count(user_id) == 0:
        return
        
    action_type = action.type.replace('_', ' ')
    title = f"Review {action_type} Action"
    body = f"A new {action_type} action needs your review."
    
    send_notification(
        user_id=user_id,
        title=title,
        body=body,
        url=f"/actions?edit={action.id}" if action.id else "/actions",
        tag="new-action",  # Group all new action notifications
    )
