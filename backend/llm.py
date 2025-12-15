"""
LLM integration for Commander.

Uses tool-calling to decide what actions to take for each context.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import settings
from .models import ActionType, ContextItem, ProposedAction
from .tools import ALL_TOOLS


# --------------------------------------------------------------------------- #
# System Prompt
# --------------------------------------------------------------------------- #

_SYSTEM_PROMPT = """\
You are Commander, an executive assistant that helps manage work communications.

For each input context (email, Slack message, meeting transcript, etc.), decide what actions to take:
- gmail_send_email: Send an email via Gmail when a response is clearly needed
- gmail_create_draft: Create a draft email for user review before sending
- schedule_meeting: When a call/meeting is requested or complex coordination is needed
- create_todo: When follow-up is needed but no immediate action can be taken

If no action is needed (e.g., informational messages, newsletters, automated notifications), simply don't call any tool.

Guidelines:
- You may call multiple tools if multiple actions are needed
- Consider the history of previous contexts and actions to avoid duplicate work
- If you've already taken action on a similar request, don't repeat it
- Keep email replies concise and professional
- Set 'confidence' between 0.5 (uncertain) and 0.95 (very confident)
"""


# --------------------------------------------------------------------------- #
# Prompt Building
# --------------------------------------------------------------------------- #

def _build_history_section(
    history: List[Tuple[ContextItem, List[ProposedAction]]]
) -> str:
    """Build the history section of the prompt."""
    if not history:
        return ""
    
    lines = ["", "=== RECENT HISTORY (for context) ===", ""]
    
    for ctx, actions in history:
        lines.append(ctx.context_text)
        print(ctx.context_text[:200])
        print("--------------------------------")
        
        if actions:
            lines.append("----- ACTIONS TAKEN -----")
            for action in actions:
                lines.append(action.to_prompt_string())
                print(action.to_prompt_string())
                print("--------------------------------")

        else:
            lines.append("----- ACTIONS TAKEN -----")
            lines.append("None")
        
        lines.append("")
    
    lines.append("=== END HISTORY ===")
    lines.append("")
    
    return "\n".join(lines)


def _build_user_prompt(
    context: ContextItem,
    history: Optional[List[Tuple[ContextItem, List[ProposedAction]]]] = None,
) -> str:
    """Build the user prompt with current context and optional history."""
    parts = []
    
    if history:
        parts.append(_build_history_section(history))
    
    parts.append("=== CURRENT INPUT (decide actions for this) ===")
    parts.append("")
    parts.append(context.context_text)
    
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Tool Call Parsing
# --------------------------------------------------------------------------- #

def _parse_tool_call(tool_call: Dict[str, Any]) -> Tuple[ActionType, Dict[str, Any], float]:
    """Parse a LangChain tool call into (action_type, payload, confidence)."""
    name = tool_call["name"]
    args = dict(tool_call.get("args", {}))
    
    # Extract confidence (not part of payload)
    confidence = float(args.pop("confidence", 0.7))
    
    # Tool names match ActionType values directly
    action_type = ActionType(name)
    
    return action_type, args, confidence


# --------------------------------------------------------------------------- #
# Main LLM Function
# --------------------------------------------------------------------------- #

def decide_actions_for_context(
    context: ContextItem,
    history: Optional[List[Tuple[ContextItem, List[ProposedAction]]]] = None,
    model: str | None = None,
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
    model = model or settings.llm_model
    llm = ChatOpenAI(model=model, temperature=0.2, api_key=settings.openai_api_key)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    print(_build_user_prompt(context, history))
    
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_prompt(context, history)),
    ]
    
    response = llm_with_tools.invoke(messages)
    tool_calls = response.tool_calls or []
    
    actions: List[Tuple[ActionType, Dict[str, Any], float]] = []
    for tool_call in tool_calls:
        action_type, payload, confidence = _parse_tool_call(tool_call)
        actions.append((action_type, payload, confidence))

    return actions
