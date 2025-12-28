from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Source Types - extensible enum for different input sources
# --------------------------------------------------------------------------- #

class SourceType(str, Enum):
    """Type of input source for context items."""
    GMAIL = "gmail"
    SLACK = "slack"
    MEETING_TRANSCRIPT = "meeting_transcript"
    CALENDAR_EVENT = "calendar_event"


# --------------------------------------------------------------------------- #
# Generic Context Item - unified model for all input types
# --------------------------------------------------------------------------- #

class ContextItem(BaseModel):
    """
    Generic context item that can represent any type of input.
    Content schema varies by source_type.
    """
    id: str  # Internal UUID
    source_type: SourceType
    source_id: str  # Original ID from the source system (for deduplication)
    timestamp: datetime  # When the original event occurred
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    
    # Flexible content dict - schema varies by source_type
    # Email: {"from_email", "subject", "body_text", "thread_id"}
    # Slack: {"channel", "user", "message", "thread_ts"}
    # Meeting: {"title", "participants", "transcript"}
    content: Dict[str, Any] = Field(default_factory=dict)
    
    # Pre-formatted text for LLM prompts (set by adapter at creation time)
    context_text: str = ""
    
    # Common metadata for display/preview
    sender: Optional[str] = None
    summary: Optional[str] = None  # Short preview/snippet
    
    # Processing state
    processed: bool = False


# --------------------------------------------------------------------------- #
# Legacy Email Model (kept for adapter compatibility)
# --------------------------------------------------------------------------- #

class EmailMessage(BaseModel):
    """Normalized email structure used by the core loop."""

    id: str
    user_id: str
    thread_id: str
    from_email: str
    subject: str
    body_text: str
    received_at: datetime
    labels: List[str] = []


class SlackMessage(BaseModel):
    """Normalized Slack message structure."""

    id: str
    channel_id: str
    user_id: str
    channel_name: Optional[str] = None
    user_id: str
    user_name: str
    text: str
    timestamp: datetime
    thread_ts: Optional[str] = None  # Thread timestamp for replies


class MeetingTranscript(BaseModel):
    """Normalized meeting transcript structure."""

    id: str
    user_id: str
    title: str
    participants: List[str]
    transcript: str
    meeting_time: datetime
    duration_mins: Optional[int] = None
    summary: Optional[str] = None  # LLM-generated summary
    drive_file_id: Optional[str] = None  # Google Drive file ID
    drive_link: Optional[str] = None  # Google Drive web view link


class ActionType(str, Enum):
    GMAIL_SEND_EMAIL = "gmail_send_email"
    GMAIL_CREATE_DRAFT = "gmail_create_draft"
    SCHEDULE_MEETING = "schedule_meeting"
    CREATE_TODO = "create_todo"


    # github MCP actions
    CREATE_REPOSITORY = "create_repository"
    CREATE_ISSUE = "create_issue"
    CREATE_BRANCH = "create_branch"
    CREATE_PULL_REQUEST = "create_pull_request"
    MERGE_PULL_REQUEST = "merge_pull_request"
    UPDATE_ISSUE = "update_issue"


    # slack MCP actions
    SLACK_SEND_MESSAGE = "slack_post_message"
    SLACK_REPLY_TO_THREAD = "slack_reply_to_thread"
    SLACK_ADD_REACTION = "slack_add_reaction"
    SLACK_UPLOAD_FILE = "slack_upload_file"


class ProposedAction(BaseModel):
    """Action proposed by the LLM for a specific context item."""

    id: int
    context_id: str  # Reference to the ContextItem that triggered this action
    user_id: str
    type: ActionType
    payload: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    status: Literal["pending", "executed", "skipped", "error"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Preview fields for UI display
    source_type: SourceType = SourceType.GMAIL
    sender: Optional[str] = None
    summary: Optional[str] = None  # Short description of what triggered this
    result: Optional[Dict[str, Any]] = Field(default_factory=dict)

    def to_prompt_string(self) -> str:
        """Format this action as a string for LLM history prompts."""
        if self.type == ActionType.GMAIL_SEND_EMAIL:
            to = self.payload.get("to_email", "unknown")
            desc = f"gmail_send_email to {to}"
        elif self.type == ActionType.GMAIL_CREATE_DRAFT:
            to = self.payload.get("to_email", "unknown")
            desc = f"gmail_create_draft to {to}"
        elif self.type == ActionType.SCHEDULE_MEETING:
            title = self.payload.get("meeting_title", "meeting")
            desc = f"schedule_meeting: {title}\n"
            desc += f"Meeting time: {self.payload.get('meeting_time', 'unknown')}\n"
            desc += f"Meeting duration: {self.payload.get('duration_mins', 'unknown')} minutes\n"
        elif self.type == ActionType.CREATE_TODO:
            title = self.payload.get("title", "task")
            desc = f"create_todo: {title}"
        else:
            desc = self.type.value
        
        return f"  - {desc} (status: {self.status}, confidence: {self.confidence:.2f})"


class ExecutionResult(BaseModel):
    action_id: int
    status: Literal["executed", "skipped", "error"]
    result: Dict[str, Any] = Field(default_factory=dict)
    executed_at: str = Field(default_factory=datetime.utcnow().isoformat())


class RunResponse(BaseModel):
    proposed_actions: List[ProposedAction]


class ListActionsResponse(BaseModel):
    actions: List[ProposedAction]


