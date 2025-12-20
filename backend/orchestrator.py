from __future__ import annotations

from typing import List, Literal, Optional

from .adapters import email_to_context, meeting_to_context, slack_to_context
from .context_storage import (
    get_relevant_history,
    get_vector_store,
    save_context,
)
from .executors import execute_action
from .gmail_mock import fetch_recent_emails
from .meeting_mock import fetch_recent_meeting_transcripts
from .slack_mock import fetch_recent_slack_messages
from .llm import decide_actions_for_context
from .models import ActionType, ContextItem, ProposedAction
from .storage import (
    get_action,
    get_next_action_id,
    list_actions,
    save_action,
    update_action_status,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Default number of historical context items to include in LLM prompts
DEFAULT_HISTORY_LIMIT = 10


def _process_contexts(
    contexts: List[ContextItem],
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> List[ProposedAction]:
    """
    Process a list of context items through the LLM and persist results.
    
    Args:
        contexts: List of ContextItem objects to process
        history_limit: Number of recent context items to include in LLM prompt
    
    Returns:
        List of newly created proposed actions
    """
    created: List[ProposedAction] = []
    store = get_vector_store()

    for context in contexts:
        # Check for duplicate (by source_id from the source system)
        if store.check_exist(context.source_id, context.source_type):
            print(f"Skipping duplicate context: {context.source_id}")
            continue
        
        # Save the context first 
        save_context(context)
        
        # Get relevant history for LLM context (semantic + recent)
        similar_history, recent_history = get_relevant_history(
            current_context=context,
            semantic_limit=history_limit // 2,
            recent_limit=history_limit // 2,
        )
        
        # Get LLM decisions with history
        actions = decide_actions_for_context(
            context, 
            similar_history=similar_history,
            recent_history=recent_history
        )
        
        # Create and save proposed actions
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
            created.append(proposed)
        
        # Mark context as processed
        store.update_processed(context.id)

    return created

SourceType = Literal["gmail", "slack", "meeting", "all"]


def run_ingest_and_decide(
    source: SourceType = "all",
    limit: int = 5,
    history_limit: int = DEFAULT_HISTORY_LIMIT,
) -> List[ProposedAction]:
    """
    Fetch and process contexts from specified source.
    
    Args:
        source: Which source to ingest (SourceType)
        limit: Maximum number of items to fetch per source
        history_limit: Number of recent context items to include in LLM prompt
    
    Returns:
        List of newly created proposed actions
    """
    
    contexts: List[ContextItem] = []

    if source in ("gmail", "all"):
        contexts.extend([email_to_context(email) for email in fetch_recent_emails(limit=limit)])
    if source in ("slack", "all"):
        contexts.extend([slack_to_context(msg) for msg in fetch_recent_slack_messages(limit=limit)])
    if source in ("meeting", "all"):
        contexts.extend([meeting_to_context(t) for t in fetch_recent_meeting_transcripts(limit=limit)])

    return _process_contexts(contexts, history_limit)



def get_actions(status: Optional[str] = None) -> List[ProposedAction]:
    """
    List actions with optional status filter.
    
    Args:
        status: Filter by status (pending, executed, skipped, error)
    """
    return list_actions(status=status)


def get_action_by_id(action_id: int) -> Optional[ProposedAction]:
    """Get an action by its ID."""
    return get_action(action_id)


def approve_action(action_id: int) -> ProposedAction:
    """
    Approve and execute an action.
    
    Args:
        action_id: The ID of the action to approve
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    if action.status not in ("pending", "error"):
        return action  # no-op if already handled
    
    result = execute_action(action)

    updated = update_action_status(action_id, result.status)
    return updated or action


def skip_action(action_id: int) -> ProposedAction:
    """
    Skip an action (mark it as skipped without executing).
    
    Args:
        action_id: The ID of the action to skip
    
    Returns:
        The updated action
    
    Raises:
        ValueError: If the action is not found
    """
    action = get_action(action_id)
    if not action:
        raise ValueError(f"Action {action_id} not found")
    
    updated = update_action_status(action_id, "skipped")
    return updated or action


