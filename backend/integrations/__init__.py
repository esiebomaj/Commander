"""
Integrations package for Commander.

This package contains integrations with external services like Gmail, Slack, etc.
Each integration has its own subfolder.
"""
from .gmail import (
    GmailIntegration,
    get_gmail,
    connect_gmail_interactive,
    disconnect_gmail,
    get_gmail_status,
    process_new_emails,
    sync_recent_emails,
)

__all__ = [
    # Gmail
    "GmailIntegration",
    "get_gmail",
    "connect_gmail_interactive",
    "disconnect_gmail",
    "get_gmail_status",
    "process_new_emails",
    "sync_recent_emails",
]
