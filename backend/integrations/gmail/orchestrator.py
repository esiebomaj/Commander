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
from ...models import ContextItem, EmailMessage, ProposedAction
from ...context_storage import get_relevant_history, get_vector_store, save_context
from ...storage import get_next_action_id, save_action
from .client import GmailIntegration, get_gmail


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DEFAULT_HISTORY_LIMIT = 10


# --------------------------------------------------------------------------- #
# Gmail Sync Functions
# --------------------------------------------------------------------------- #

def sync_recent_emails(
    max_results: int = 20,
    generate_actions: bool = False,
    gmail: Optional[GmailIntegration] = None,
) -> List[ContextItem]:
    """
    Sync recent emails from Gmail and store as context.
    
    This is used for initial sync when connecting Gmail. By default,
    it does NOT generate actions for these emails (they're historical).
    
    Args:
        max_results: Maximum number of emails to fetch
        generate_actions: Whether to generate actions (default False for initial sync)
        gmail: Optional Gmail instance (uses global if not provided)
    
    Returns:
        List of saved ContextItem objects
    """
    if gmail is None:
        gmail = get_gmail()
    
    if not gmail.is_connected():
        raise ValueError("Gmail is not connected. Please authenticate first.")
    
    emails = gmail.fetch_recent_emails(max_results=max_results)
    return _process_emails(emails, generate_actions=generate_actions)


def process_new_emails(
    gmail: Optional[GmailIntegration] = None,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> List[ProposedAction]:
    """
    Fetch and process new emails since last sync.
    
    This uses Gmail's history API for incremental sync and generates
    actions for new emails.
    
    Args:
        gmail: Optional Gmail instance (uses global if not provided)
        history_limit: Number of recent context items to include in LLM prompt
    
    Returns:
        List of newly created proposed actions
    """
    if gmail is None:
        gmail = get_gmail()
    
    if not gmail.is_connected():
        raise ValueError("Gmail is not connected. Please authenticate first.")
    
    emails = gmail.fetch_new_emails()
    print(f"Found {len(emails)} new emails")

    if not emails:
        return []
    
    # Process emails and generate actions
    contexts = _process_emails(emails, generate_actions=True, history_limit=history_limit)
    print(f"Processed {len(contexts)} contexts")
    # Collect all actions created
    from ...storage import get_actions_for_context
    
    actions: List[ProposedAction] = []
    for ctx in contexts:
        ctx_actions = get_actions_for_context(ctx.id)
        actions.extend(ctx_actions)
    
    return actions


def _process_emails(
    emails: List[EmailMessage],
    generate_actions: bool = False,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> List[ContextItem]:
    """
    Process a list of emails into context items.
    
    Args:
        emails: List of EmailMessage objects
        generate_actions: Whether to generate actions for these emails
        history_limit: Number of recent context items for LLM context
    
    Returns:
        List of saved ContextItem objects
    """
    saved_contexts: List[ContextItem] = []
    store = get_vector_store()
    print(f"Processing {len(emails)} emails")
    for email in emails:

    
        # Convert to context
        context = email_to_context(email)
        
        # Check for duplicate
        if store.check_exist(context.source_id, context.source_type):
            print(f"Skipping duplicate email: {email.subject[:50]}...")
            continue
        
        if generate_actions and "SENT" not in email.labels: # dont generate actions for sent emails
            # Get relevant history for LLM context (semantic + recent)
            similar_history, recent_history = get_relevant_history(
                current_context=context,
                semantic_limit=history_limit // 2,
                recent_limit=history_limit // 2,
            )
            
            # Get LLM decisions
            # Local import avoids circular dependency when tools load Gmail integration
            from ...llm import decide_actions_for_context

            actions = decide_actions_for_context(
                context,
                similar_history=similar_history,
                recent_history=recent_history
            )
            
            # Save actions
            for action_type, payload, confidence in actions:
                proposed = ProposedAction(
                    id=get_next_action_id(),
                    context_id=context.id,
                    type=action_type,
                    payload=payload,
                    confidence=confidence,
                    status="pending",
                    source_type=context.source_type,
                    sender=context.sender,
                    summary=context.summary,
                )
                save_action(proposed)
        

        # Save context (with embedding)
        save_context(context)
        saved_contexts.append(context)

        # Mark as processed
        store.update_processed(context.id)
    print(f"Saved {len(saved_contexts)} contexts")
    return saved_contexts


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
