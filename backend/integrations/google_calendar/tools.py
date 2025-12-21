"""
Google Calendar tools for LLM integration.

These tools define the schema for LLM tool-calling and contain
the execution logic that runs when actions are approved.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ...models import ActionType
from .client import get_calendar


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class ScheduleMeetingInput(BaseModel):
    """Input schema for scheduling a meeting on Google Calendar."""
    meeting_title: str = Field(..., description="Title of the meeting")
    meeting_description: str = Field(..., description="Description of the meeting")
    meeting_time: str = Field(..., description="Date and time of the meeting (ISO format, e.g., '2025-12-20T10:00:00')")
    duration_mins: int = Field(30, description="Duration of the meeting in minutes")
    attendees: Optional[List[str]] = Field(None, description="List of attendee email addresses to invite")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Tool Functions (schema for LLM + execution logic)
# --------------------------------------------------------------------------- #

@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting(
    meeting_title: str,
    meeting_description: str,
    meeting_time: str,
    duration_mins: int = 30,
    attendees: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Schedule a meeting on the user's Google Calendar. Use when a call/meeting is requested or complex coordination is needed."""
    calendar = get_calendar()
    
    if not calendar.is_connected():
        return {"success": False, "error": "Google Calendar is not connected. Please authenticate first."}
    
    result = calendar.create_event(
        title=meeting_title,
        description=meeting_description,
        start_time=meeting_time,
        duration_mins=duration_mins,
        attendees=attendees,
    )
    
    if result:
        return {
            "success": True,
            "event_id": result.get("id"),
            "html_link": result.get("htmlLink"),
            "meeting_title": meeting_title,
            "meeting_time": meeting_time,
            "duration_mins": duration_mins,
            "attendees": attendees or [],
        }
    return {"success": False, "error": "Failed to create calendar event"}


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

# List of Calendar tools for LLM binding
CALENDAR_TOOLS = [schedule_meeting]

# Map tool names to functions for execution
CALENDAR_TOOL_EXECUTORS = {
    ActionType.SCHEDULE_MEETING: schedule_meeting,
}
