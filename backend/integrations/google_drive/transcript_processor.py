"""
Transcript processing for Google Drive meeting transcripts.

Handles:
- Fetching transcript content from Drive
- Summarizing with LLM
- Creating context items
- Proposing follow-up actions
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from backend.orchestrator import process_new_context

from ...config import settings
from ...models import (
    ActionType,
    ContextItem,
    MeetingTranscript,
    ProposedAction,
    SourceType,
)
from ...storage import get_next_action_id, save_action
from ...context_storage import get_relevant_history, get_vector_store, save_context
from ...adapters import meeting_to_context
from ...llm import decide_actions_for_context
from .client import get_connected_drive


# --------------------------------------------------------------------------- #
# Pydantic Models for Structured Outputs
# --------------------------------------------------------------------------- #

class MeetingMetadata(BaseModel):
    """Structured metadata extracted from a meeting transcript."""
    title: str = Field(description="The meeting title or subject")
    participants: List[str] = Field(description="List of participant names mentioned in the transcript")
    meeting_datetime: str = Field(description="Meeting date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). Extract from transcript header or filename.")
    duration_mins: Optional[int] = Field(None, description="Meeting duration in minutes if mentioned")
    summary: str = Field(description="A concise 2-3 sentence summary of what the meeting was about")
    key_decisions: List[str] = Field(default_factory=list, description="Key decisions made during the meeting")
    action_items: List[str] = Field(default_factory=list, description="Action items with owners if mentioned")
    follow_up_topics: List[str] = Field(default_factory=list, description="Topics that need follow-up discussion")


# --------------------------------------------------------------------------- #
# LLM Analysis Prompts
# --------------------------------------------------------------------------- #

_ANALYSIS_SYSTEM_PROMPT = """\
You are a meeting transcript analyzer. Extract key information and metadata from meeting transcripts.

Your job is to:
1. Identify the meeting title/subject
2. Extract all participant names
3. Extract the meeting date and time (it's always present in the transcript header or filename)
4. Provide a concise summary
5. List key decisions, action items, and follow-up topics

Return the meeting date and time in ISO 8601 format: YYYY-MM-DDTHH:MM:SS
"""

_ANALYSIS_USER_TEMPLATE = """\
Analyze this meeting transcript and extract all relevant information:

FILENAME: {filename}

--- TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Extract:
- Meeting title (or infer from content)
- Meeting date and time in ISO 8601 format (REQUIRED - check filename and transcript header)
- All participant names
- A 2-3 sentence summary
- Key decisions made
- Action items with owners
- Topics needing follow-up
"""


# --------------------------------------------------------------------------- #
# Transcript Analysis with Structured Outputs
# --------------------------------------------------------------------------- #

def analyze_transcript(
    transcript_text: str,
    filename: str = "Meeting Transcript",
    model: str | None = None,
) -> MeetingMetadata:
    """
    Analyze a meeting transcript and extract structured metadata using LLM.
    
    Args:
        transcript_text: The raw transcript text
        filename: Original filename for context
        model: OpenAI model to use (defaults to settings.llm_model)
    
    Returns:
        MeetingMetadata with extracted information
    """
    model = model or settings.llm_model
    
    # Use structured output to get parsed metadata
    llm = ChatOpenAI(
        model=model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    ).with_structured_output(MeetingMetadata)
    
    # Build the prompt with filename hint
    user_prompt = _ANALYSIS_USER_TEMPLATE.format(transcript=transcript_text, filename=filename)
    
    messages = [
        SystemMessage(content=_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]
    
    metadata: MeetingMetadata = llm.invoke(messages)
    return metadata


def format_metadata_summary(metadata: MeetingMetadata) -> str:
    """
    Format the metadata into a readable summary string.
    
    Args:
        metadata: The extracted meeting metadata
    
    Returns:
        Formatted summary text
    """
    sections = []
    
    # Summary
    sections.append(f"## Summary\n{metadata.summary}")
    
    # Key Decisions
    if metadata.key_decisions:
        sections.append("## Key Decisions")
        sections.extend([f"- {decision}" for decision in metadata.key_decisions])
    
    # Action Items
    if metadata.action_items:
        sections.append("## Action Items")
        sections.extend([f"- {item}" for item in metadata.action_items])
    
    # Follow-up Topics
    if metadata.follow_up_topics:
        sections.append("## Follow-up Topics")
        sections.extend([f"- {topic}" for topic in metadata.follow_up_topics])
    
    return "\n\n".join(sections)




# --------------------------------------------------------------------------- #
# Full Processing Pipeline
# --------------------------------------------------------------------------- #

def process_new_transcript(
    file_id: str,
    skip_if_exists: bool = True,
) -> Optional[Tuple[ContextItem, List[ProposedAction]]]:
    """
    Process a new transcript file from Google Drive.
    
    Full pipeline:
    1. Check for duplicates
    2. Fetch transcript content from Drive
    3. Extract metadata and participants
    4. Summarize with LLM
    5. Create and save context item
    6. Run action decision LLM
    7. Save proposed actions
    
    Args:
        file_id: Google Drive file ID of the transcript
        skip_if_exists: If True, skip processing if already processed
    
    Returns:
        Tuple of (ContextItem, List[ProposedAction]) or None if skipped/error
    """
    # Check for duplicate
    store = get_vector_store()
    if skip_if_exists and store.check_exist(file_id, SourceType.MEETING_TRANSCRIPT):
        print(f"Skipping already processed transcript: {file_id}")
        return None
    
    # Get Drive client
    drive = get_connected_drive()
    if not drive:
        return None
    
    # Fetch file metadata
    metadata = drive.get_file_metadata(file_id)
    if not metadata:
        print(f"Could not fetch metadata for file: {file_id}")
        return None
    
    # Verify it's a Google Doc (transcript)
    if metadata.get("mimeType") != "application/vnd.google-apps.document":
        print(f"File is not a Google Doc: {metadata.get('mimeType')}")
        return None
    
    # Fetch transcript content
    transcript_text = drive.get_transcript_content(file_id)
    if not transcript_text or len(transcript_text) < 200: # checking that its not just the header that was added.
        print(f"Could not fetch transcript content for file: {file_id}")
        return None
    
    print(f"Metadata: {metadata}")
    print(f"Transcript text: {transcript_text[:200]}...")
    filename = metadata.get("name", "Meeting Transcript")
    
    # Analyze transcript with LLM to extract all metadata
    print(f"Analyzing transcript: {filename}")
    meeting_metadata = analyze_transcript(
        transcript_text=transcript_text,
        filename=filename,
    )
    
    # Parse the meeting datetime from LLM extraction
    try:
        # Try parsing ISO format first
        meeting_time = datetime.fromisoformat(meeting_metadata.meeting_datetime.replace("Z", "+00:00"))
    except Exception as e:
        # If parsing fails, fall back to file creation time as last resort
        print(f"Warning: Could not parse meeting_datetime '{meeting_metadata.meeting_datetime}', using file creation time")
        created_time = metadata.get("createdTime")
        if created_time:
            meeting_time = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        else:
            meeting_time = datetime.utcnow()
    
    # Format the summary
    summary = format_metadata_summary(meeting_metadata)
    
    # Create MeetingTranscript model with LLM-extracted metadata
    meeting = MeetingTranscript(
        id=file_id,
        title=meeting_metadata.title,
        participants=meeting_metadata.participants if meeting_metadata.participants else ["Unknown Participant"],
        transcript=transcript_text,
        meeting_time=meeting_time,
        duration_mins=meeting_metadata.duration_mins,
        summary=summary,
        drive_file_id=file_id,
        drive_link=metadata.get("webViewLink"),
    )
    
    # Convert to ContextItem using existing adapter
    context = meeting_to_context(meeting)
    created_actions = process_new_context(context)
    
    return context, created_actions


def process_recent_transcripts(
    max_files: int = 10,
    since_hours: int = 24,
) -> List[Tuple[ContextItem, List[ProposedAction]]]:
    """
    Process recent transcript files from the Meet Recordings folder.
    
    Args:
        max_files: Maximum number of files to process
        since_hours: Only process files modified in the last N hours
    
    Returns:
        List of (ContextItem, List[ProposedAction]) tuples for processed files
    """
    drive = get_connected_drive()
    if not drive:
        return []
    
    # Get recent files
    from datetime import timedelta
    modified_after = datetime.utcnow() - timedelta(hours=since_hours)
    
    files = drive.list_transcript_files(
        max_results=max_files,
        modified_after=modified_after,
    )

    print(f"Found {len(files)} files")
    
    results = []
    for file in files:
        result = process_new_transcript(file["id"])
        if result:
            results.append(result)
    
    return results

