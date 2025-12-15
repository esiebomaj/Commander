"""
Gmail tools for LLM integration.

These tools define the schema for LLM tool-calling and contain
the execution logic that runs when actions are approved.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ...models import ActionType
from .client import get_gmail


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class SendEmailInput(BaseModel):
    """Input schema for sending an email via Gmail."""
    to_email: str = Field(..., description="The recipient's email address")
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email (plain text)")
    thread_id: Optional[str] = Field(None, description="The thread ID if this is a reply to an existing thread")
    cc: Optional[List[str]] = Field(None, description="List of CC recipients")
    bcc: Optional[List[str]] = Field(None, description="List of BCC recipients")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class CreateDraftInput(BaseModel):
    """Input schema for creating an email draft in Gmail."""
    to_email: str = Field(..., description="The recipient's email address")
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email (plain text)")
    thread_id: Optional[str] = Field(None, description="The thread ID if this is a reply draft")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Tool Functions (schema for LLM + execution logic)
# --------------------------------------------------------------------------- #

@tool(args_schema=SendEmailInput)
def gmail_send_email(
    to_email: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Send an email via Gmail. Use for replies or new emails when a response is clearly needed."""
    try:
        gmail = get_gmail()
    except FileNotFoundError:
        return {"success": False, "error": "Gmail credentials not configured"}
    
    if not gmail.is_connected():
        return {"success": False, "error": "Gmail is not connected. Please authenticate first."}
    
    result = gmail.send_email(
        to=to_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
        cc=cc,
        bcc=bcc,
    )
    
    if result:
        return {
            "success": True,
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
        }
    return {"success": False, "error": "Failed to send email"}


@tool(args_schema=CreateDraftInput)
def gmail_create_draft(
    to_email: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create an email draft in Gmail. Use when you want to prepare a response for user review before sending."""
    try:
        gmail = get_gmail()
    except FileNotFoundError:
        return {"success": False, "error": "Gmail credentials not configured"}
    
    if not gmail.is_connected():
        return {"success": False, "error": "Gmail is not connected. Please authenticate first."}
    
    result = gmail.create_draft(
        to=to_email,
        subject=subject,
        body=body,
        thread_id=thread_id,
    )
    
    if result:
        return {
            "success": True,
            "draft_id": result.get("id"),
        }
    return {"success": False, "error": "Failed to create draft"}


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

# List of Gmail tools for LLM binding
GMAIL_TOOLS = [gmail_send_email, gmail_create_draft]
# Add Gmail tools if available

# Map tool names to functions for execution
GMAIL_TOOL_EXECUTORS = {
    ActionType.GMAIL_SEND_EMAIL: gmail_send_email,
    ActionType.GMAIL_CREATE_DRAFT: gmail_create_draft,
}
