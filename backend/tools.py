"""
Central tool registry for Commander.

Each tool defines both the LLM schema and execution logic.
Tools are registered by action type for easy dispatch.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .models import ActionType


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class ScheduleMeetingInput(BaseModel):
    """Input for scheduling a meeting."""
    meeting_title: str = Field(..., description="Title of the meeting")
    meeting_description: str = Field(..., description="Description of the meeting")
    meeting_time: str = Field(..., description="Date and time of the meeting (ISO format)")
    duration_mins: int = Field(30, description="Duration of the meeting in minutes")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class CreateTodoInput(BaseModel):
    """Input for creating a todo item."""
    title: str = Field(..., description="Title of the todo item")
    notes: Optional[str] = Field(None, description="Additional notes")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Core Tools (schema + execution)
# --------------------------------------------------------------------------- #

@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting(
    meeting_title: str,
    meeting_description: str,
    meeting_time: str,
    duration_mins: int = 30,
    **kwargs,
) -> Dict[str, Any]:
    """Schedule a meeting on the user's calendar."""
    # TODO: Integrate with calendar API
    return {
        "success": True,
        "note": "Meeting scheduled (mock)",
        "meeting_title": meeting_title,
        "meeting_time": meeting_time,
        "duration_mins": duration_mins,
    }


@tool(args_schema=CreateTodoInput)
def create_todo(
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a follow-up task in the user's todo list."""
    # TODO: Integrate with todo API
    return {
        "success": True,
        "note": "Todo created (mock)",
        "title": title,
        "notes": notes,
        "due_date": due_date,
    }


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

# Core tools list (for LLM binding)
CORE_TOOLS = [schedule_meeting, create_todo]

from .integrations.gmail.tools import GMAIL_TOOLS, GMAIL_TOOL_EXECUTORS

# All tools for LLM
ALL_TOOLS = GMAIL_TOOLS + CORE_TOOLS

# Map ActionType to executor function
TOOL_EXECUTORS: Dict[ActionType, Callable] = {
    ActionType.SCHEDULE_MEETING: schedule_meeting,
    ActionType.CREATE_TODO: create_todo,
} | GMAIL_TOOL_EXECUTORS


def execute_tool(action_type: ActionType, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by action type with the given payload.
    
    Args:
        action_type: The ActionType enum value
        payload: Tool parameters
    
    Returns:
        Execution result dict
    """
    executor = TOOL_EXECUTORS.get(action_type)
    if not executor:
        return {"success": False, "error": f"No executor for action type: {action_type}"}
    
    try:
        return executor.invoke(payload)
    except Exception as e:
        return {"success": False, "error": str(e)}
