"""
Gmail orchestrator for Commander.

Connects the Gmail integration with the existing context/action system.
Handles:
- Initial sync of recent emails (context only, no actions)
- Processing new emails (context + actions)
- Connection management

Note: Email sending/drafting tools are in tools.py
"""
from __future__ import annotations

from typing import List, Optional, Any
from typing_extensions import Dict

from ...adapters import email_to_context
from ...models import EmailMessage, ProposedAction
from ...context_storage import save_context
from .client import get_gmail


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULT_HISTORY_LIMIT = 10


# --------------------------------------------------------------------------- #
# Gmail Sync Functions
# --------------------------------------------------------------------------- #

def sync_recent_emails(
    max_results: int = 20,
) -> int:
    """
    Sync recent emails from Gmail and store as context.
    This is used for initial sync when connecting Gmail.
    
    Args:
        max_results: Maximum number of emails to fetch
    
    Returns:
        Number of emails synced
    """
    gmail = get_gmail()
    
    if not gmail.is_connected():
        raise ValueError("Gmail is not connected. Please authenticate first.")
    
    emails = gmail.fetch_recent_emails(max_results=max_results)

    for email in emails:
        context = email_to_context(email)
        save_context(context)

    return len(emails)


def process_new_emails() -> List[ProposedAction]:
    """
    Fetch and process new emails since last sync.
    
    This uses Gmail's history API for incremental sync and generates
    actions for new emails.
    
    Returns:
        List of newly created proposed actions
        
    """
    from ...orchestrator import process_new_context
    gmail = get_gmail()
    
    if not gmail.is_connected():
        raise ValueError("Gmail is not connected. Please authenticate first.")
    
    emails = gmail.fetch_new_emails()
    print(f"Found {len(emails)} new emails")

    if not emails:
        return []

    actions: List[ProposedAction] = []

    for email in emails:

        if "SENT" in email.labels:
            continue

        # Convert to context
        context = email_to_context(email)
     
        new_actions = process_new_context(context)
        actions.extend(new_actions)
    
    print(f"Created {len(actions)} actions")
    return actions


# --------------------------------------------------------------------------- #
# Push Notifications (Webhook Setup)
# --------------------------------------------------------------------------- #
def setup_push_notifications(topic_name: str) -> Optional[Dict[str, Any]]:
    """
    Setup Gmail push notifications.
    """
    gmail = get_gmail()
    return gmail.setup_push_notifications(topic_name)


# --------------------------------------------------------------------------- #
# Connection Management
# --------------------------------------------------------------------------- #

def get_gmail_status() -> dict:
    """Get the current Gmail connection status."""
    gmail = get_gmail()
    
    connected = gmail.is_connected()
    
    return {
        "connected": connected,
        "email": gmail.get_user_email() if connected else None,
    }


def connect_gmail_interactive() -> bool:
    """
    Run interactive OAuth flow to connect Gmail.
    
    This opens a browser window for the user to authorize.
    Returns True if successful.
    """
    gmail = get_gmail()
    return gmail.run_local_auth_flow()


def disconnect_gmail() -> bool:
    """Disconnect Gmail and remove stored credentials."""
    gmail = get_gmail()
    return gmail.disconnect()
