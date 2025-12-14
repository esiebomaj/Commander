from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .models import ActionType, ContextItem, EmailMessage, ProposedAction, SourceType


# --------------------------------------------------------------------------- #
# Tool input schemas (Pydantic models for structured tool arguments)
# --------------------------------------------------------------------------- #

class SendEmailInput(BaseModel):
    """Input for sending an email."""
    thread_id: Optional[str] = Field(None, description="The thread ID if this is a reply")
    to_email: str = Field(..., description="The recipient's email address")
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class ScheduleMeetingInput(BaseModel):
    """Input for scheduling a meeting."""
    meeting_title: str = Field(..., description="Title of the meeting")
    meeting_description: str = Field(..., description="Description of the meeting")
    meeting_date: str = Field(..., description="Date and time of the meeting (ISO format)")
    duration_mins: int = Field(30, description="Duration of the meeting in minutes")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class CreateTodoInput(BaseModel):
    """Input for creating a todo item."""
    title: str = Field(..., description="Title of the todo item")
    notes: Optional[str] = Field(None, description="Additional notes")
    due_date: Optional[str] = Field(None, description="Due date (ISO format)")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class NoActionInput(BaseModel):
    """Input when no action is needed."""
    reason: str = Field(..., description="Reason why no action is needed")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Tool definitions using LangChain's @tool decorator
# --------------------------------------------------------------------------- #

@tool(args_schema=SendEmailInput)
def send_email(
    to_email: str,
    subject: str,
    body: str,
    thread_id: Optional[str] = None,
    confidence: float = 0.7,
) -> str:
    """Send a new email or reply to an existing thread. For replies, include thread_id."""
    return "Email action recorded"


@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting(
    meeting_title: str,
    meeting_description: str,
    meeting_date: str,
    duration_mins: int = 30,
    confidence: float = 0.7,
) -> str:
    """Schedule a meeting on the user's calendar."""
    return "Meeting action recorded"


@tool(args_schema=CreateTodoInput)
def create_todo(
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[str] = None,
    confidence: float = 0.7,
) -> str:
    """Create a follow-up task in the user's todo list."""
    return "Todo action recorded"


@tool(args_schema=NoActionInput)
def no_action(reason: str, confidence: float = 0.7) -> str:
    """Choose when no meaningful action is required."""
    return "No action recorded"


# All available tools
TOOLS = [send_email, schedule_meeting, create_todo, no_action]

_SYSTEM_PROMPT = """\
You are Commander, an executive assistant that helps manage work communications.

For each input context (email, Slack message, meeting transcript, etc.), decide what actions to take:
- send_email: Reply to emails or send new messages when a clear question/request needs a response
- schedule_meeting: When a call/meeting is requested or complex coordination is needed
- create_todo: When follow-up is needed but no immediate action can be taken
- no_action: When the message is informational only or no response is needed

Guidelines:
- You may call multiple tools if multiple actions are needed
- Consider the history of previous contexts and actions to avoid duplicate work
- If you've already taken action on a similar request, don't repeat it
- Keep email replies concise and professional
- Set 'confidence' between 0.5 (uncertain) and 0.95 (very confident)
"""


def _build_history_section(
    history: List[Tuple[ContextItem, List[ProposedAction]]]
) -> str:
    """Build the history section of the prompt."""
    if not history:
        return ""
    
    lines = ["", "=== RECENT HISTORY (for context) ===", ""]
    
    for ctx, actions in history:
        lines.append(ctx.context_text)
        
        # Format actions taken using model's method
        if actions:
            lines.append("Actions taken:")
            for action in actions:
                lines.append(action.to_prompt_string())
        else:
            lines.append("Actions taken: (none)")
        
        lines.append("")  # Blank line between history items
    
    lines.append("=== END HISTORY ===")
    lines.append("")
    
    return "\n".join(lines)


def _build_user_prompt(
    context: ContextItem,
    history: Optional[List[Tuple[ContextItem, List[ProposedAction]]]] = None,
) -> str:
    """Build the user prompt with current context and optional history."""
    parts = []
    
    # Add history section if provided
    if history:
        parts.append(_build_history_section(history))
    
    # Add current context (use pre-computed context_text from adapter)
    parts.append("=== CURRENT INPUT (decide actions for this) ===")
    parts.append("")
    parts.append(context.context_text)
    
    return "\n".join(parts)


# Legacy support for EmailMessage
def _build_user_prompt_legacy(email: EmailMessage) -> str:
    return (
        f"From: {email.from_email}\n"
        f"Subject: {email.subject}\n"
        f"Received At: {email.received_at.isoformat()}\n\n"
        f"Body:\n{email.body_text}"
    )


def _parse_tool_call(tool_call: Dict[str, Any]) -> Tuple[ActionType, Dict[str, Any], float]:
    """Parse a LangChain tool call into (action_type, payload, confidence)."""
    name = tool_call["name"]
    args = tool_call.get("args", {})

    confidence = float(args.get("confidence", 0.7))
    
    if name == "send_email":
        return ActionType.SEND_EMAIL, {
            "thread_id": args.get("thread_id"),
            "to_email": args.get("to_email"),
            "subject": args.get("subject"),
            "body": args.get("body"),
        }, confidence
    
    if name == "schedule_meeting":
        return ActionType.SCHEDULE_MEETING, {
            "duration_mins": args.get("duration_mins", 30),
            "meeting_date": args.get("meeting_date"),
            "meeting_title": args.get("meeting_title"),
            "meeting_description": args.get("meeting_description"),
        }, confidence
    
    if name == "create_todo":
        return ActionType.CREATE_TODO, {
            "title": args.get("title"),
            "notes": args.get("notes"),
            "due_date": args.get("due_date"),
        }, confidence
    
    # default: no_action
    return ActionType.NO_ACTION, {"reason": args.get("reason", "Not necessary")}, confidence


def decide_actions_for_context(
    context: ContextItem,
    history: Optional[List[Tuple[ContextItem, List[ProposedAction]]]] = None,
    model: str = "gpt-4o-mini",
) -> List[Tuple[ActionType, Dict[str, Any], float]]:
    """
    Call the LLM with tool-calling enabled and return a list of decided actions.
    
    Args:
        context: The current context item to process
        history: Optional list of (context, actions) tuples for historical context
        model: The OpenAI model to use
    
    Returns:
        List of (ActionType, payload_dict, confidence) tuples
    """
    # Initialize LangChain ChatOpenAI (reads OPENAI_API_KEY from env automatically)
    llm = ChatOpenAI(model=model, temperature=0.2)
    
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(TOOLS)
    print(_SYSTEM_PROMPT)
    print("-" * 100)
    print(_build_user_prompt(context, history))
    print("-" * 100)
    # Build messages with history
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(context, history)),
    ]
    
    # Invoke the model
    response = llm_with_tools.invoke(messages)
    
    # Extract tool calls from the response
    tool_calls = response.tool_calls or []
    print(f"Tool calls: {tool_calls}")
    
    actions: List[Tuple[ActionType, Dict[str, Any], float]] = []
    for tool_call in tool_calls:
        action_type, payload, confidence = _parse_tool_call(tool_call)

        # For send_email on email contexts, default to replying to sender
        if action_type == ActionType.SEND_EMAIL and not payload.get("to_email"):
            if context.source_type == SourceType.EMAIL:
                payload.setdefault("thread_id", context.content.get("thread_id"))
                payload.setdefault("to_email", context.content.get("from_email"))

        actions.append((action_type, payload, confidence))

    return actions


# Legacy function for backward compatibility
def decide_actions(email: EmailMessage, model: str = "gpt-4o-mini") -> List[Tuple[ActionType, Dict[str, Any], float]]:
    """
    Legacy function for EmailMessage input.
    Call the LLM with tool-calling enabled and return a list of decided actions.
    Uses LangChain for cleaner tool binding and invocation.
    """
    # Initialize LangChain ChatOpenAI (reads OPENAI_API_KEY from env automatically)
    llm = ChatOpenAI(model=model, temperature=0.2)
    
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # Build messages
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt_legacy(email)),
    ]
    
    # Invoke the model
    response = llm_with_tools.invoke(messages)
    
    # Extract tool calls from the response
    tool_calls = response.tool_calls or []
    print(f"Tool calls: {tool_calls}")
    
    actions: List[Tuple[ActionType, Dict[str, Any], float]] = []
    for tool_call in tool_calls:
        action_type, payload, confidence = _parse_tool_call(tool_call)

        # For send_email, default to replying to sender if no to_email provided
        if action_type == ActionType.SEND_EMAIL and not payload.get("to_email"):
            payload.setdefault("thread_id", email.thread_id)
            payload.setdefault("to_email", email.from_email)

        actions.append((action_type, payload, confidence))

    return actions


