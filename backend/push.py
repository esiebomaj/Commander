"""
Web Push Notifications module for Commander.

This module handles:
- VAPID key generation and storage
- Push subscription management
- Sending notifications to subscribed clients
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pywebpush import webpush, WebPushException

from .config import settings


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

VAPID_KEYS_FILE = settings.data_dir / "vapid_keys.json"
SUBSCRIPTIONS_FILE = settings.data_dir / "push_subscriptions.json"

# VAPID contact email - used by push services to contact you if needed
VAPID_CLAIMS_EMAIL = "mailto:admin@commander.local"


# --------------------------------------------------------------------------- #
# VAPID Key Management
# --------------------------------------------------------------------------- #

def _load_vapid_keys() -> Optional[Dict[str, str]]:
    """Load VAPID keys from file."""
    try:
        return json.loads(VAPID_KEYS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def _save_vapid_keys(keys: Dict[str, str]):
    """Save VAPID keys to file."""
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
# Subscription Management
# --------------------------------------------------------------------------- #

def _load_subscriptions() -> List[Dict[str, Any]]:
    """Load subscriptions from file."""
    try:
        return json.loads(SUBSCRIPTIONS_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_subscriptions(subscriptions: List[Dict[str, Any]]):
    """Save subscriptions to file."""
    SUBSCRIPTIONS_FILE.write_text(json.dumps(subscriptions, indent=2))


def subscribe(subscription: Dict[str, Any]) -> bool:
    """
    Add a new push subscription.
    
    Args:
        subscription: The PushSubscription object from the browser
        
    Returns:
        True if subscription was added, False if it already exists
    """
    subscriptions = _load_subscriptions()
    
    # Check for existing subscription by endpoint
    endpoint = subscription.get("endpoint", "")
    for sub in subscriptions:
        if sub.get("endpoint") == endpoint:
            # Update existing subscription (keys might have changed)
            sub.update(subscription)
            _save_subscriptions(subscriptions)
            return True
    
    # Add new subscription
    subscriptions.append(subscription)
    _save_subscriptions(subscriptions)
    return True


def unsubscribe(endpoint: str) -> bool:
    """
    Remove a push subscription by endpoint.
    
    Args:
        endpoint: The push subscription endpoint URL
        
    Returns:
        True if subscription was removed, False if not found
    """
    subscriptions = _load_subscriptions()
    original_count = len(subscriptions)
    
    subscriptions = [s for s in subscriptions if s.get("endpoint") != endpoint]
    
    if len(subscriptions) < original_count:
        _save_subscriptions(subscriptions)
        return True
    
    return False


def get_subscription_count() -> int:
    """Get the number of active subscriptions."""
    return len(_load_subscriptions())


# --------------------------------------------------------------------------- #
# Notification Sending
# --------------------------------------------------------------------------- #

def send_notification(
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/commander.svg",
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a push notification to all subscribed clients.
    
    Args:
        title: Notification title
        body: Notification body text
        url: URL to open when notification is clicked
        icon: Icon URL for the notification
        tag: Optional tag to group/replace notifications
        
    Returns:
        Dict with 'sent', 'failed', and 'removed' counts
    """
    subscriptions = _load_subscriptions()
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
    if removed_endpoints:
        subscriptions = [
            s for s in subscriptions 
            if s.get("endpoint") not in removed_endpoints
        ]
        _save_subscriptions(subscriptions)
    
    return {
        "sent": sent,
        "failed": failed,
        "removed": len(removed_endpoints),
    }


# --------------------------------------------------------------------------- #
# Helper for Action Notifications
# --------------------------------------------------------------------------- #

def notify_new_action(action_type: str, summary: Optional[str] = None, action_id: Optional[int] = None):
    """
    Send a notification about a new proposed action.
    
    Args:
        action_type: The type of action (e.g., "send_email", "create_event")
        summary: Optional summary text for the action
    """
    # Don't send notifications if there are no subscriptions
    if get_subscription_count() == 0:
        return
    
    title = "New Action Proposed"
    body = summary if summary else f"A new {action_type.replace('_', ' ')} action needs your review."
    
    send_notification(
        title=title,
        body=body,
        url=f"/actions?edit={action_id}",
        tag="new-action",  # Group all new action notifications
    )

