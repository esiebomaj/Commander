"""
Gmail integration for Commander.

Provides OAuth authentication, email reading, sending, and push notifications.
"""
from .client import GmailIntegration, get_gmail
from .orchestrator import (
    connect_gmail_interactive,
    disconnect_gmail,
    get_gmail_status,
    process_new_emails,
    sync_recent_emails,
    setup_push_notifications,
)

from .tools import (
    GMAIL_TOOLS,
    GMAIL_TOOL_EXECUTORS,
    gmail_send_email,
    gmail_create_draft,
)

__all__ = [
    # Gmail client
    "GmailIntegration",
    "get_gmail",
    
    # Orchestrator functions
    "connect_gmail_interactive",
    "disconnect_gmail",
    "get_gmail_status",
    "process_new_emails",
    "sync_recent_emails",
    "setup_push_notifications",

    # Tools (for LLM + execution)
    "GMAIL_TOOLS",
    "GMAIL_TOOL_EXECUTORS",
    "gmail_send_email",
    "gmail_create_draft",
]
