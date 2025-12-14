"""
Adapters for converting source-specific data into generic ContextItem.

Each adapter transforms a specific input type (email, slack message, etc.)
into a unified ContextItem that can be processed by the LLM.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from .models import ContextItem, EmailMessage, MeetingTranscript, SlackMessage, SourceType


def email_to_context(email: EmailMessage) -> ContextItem:
    """
    Convert an EmailMessage to a generic ContextItem.
    
    The content dict preserves email-specific fields that the LLM
    and executors may need for taking actions.
    """
    # Pre-format the context text for LLM prompts
    context_text = (
        f"[EMAIL]\n"
        f"From: {email.from_email}\n"
        f"Subject: {email.subject}\n"
        f"Received: {email.received_at.isoformat()}\n"
        f"Body:\n{email.body_text}"
    )
    
    return ContextItem(
        id=str(uuid4()),
        source_type=SourceType.EMAIL,
        source_id=email.id,  # Used for deduplication
        timestamp=email.received_at,
        content={
            "from_email": email.from_email,
            "subject": email.subject,
            "body_text": email.body_text,
            "thread_id": email.thread_id,
        },
        context_text=context_text,
        sender=email.from_email,
        summary=f"{email.subject}: {email.body_text[:120]}...".replace("\n", " ") 
                if len(email.body_text) > 120 
                else f"{email.subject}: {email.body_text}".replace("\n", " "),
    )


def slack_to_context(message: SlackMessage) -> ContextItem:
    """
    Convert a SlackMessage to a generic ContextItem.
    """
    display_channel = message.channel_name or message.channel_id
    
    # Pre-format the context text for LLM prompts
    context_text = (
        f"[SLACK MESSAGE]\n"
        f"Channel: {display_channel}\n"
        f"From: {message.user_name}\n"
        f"Time: {message.timestamp.isoformat()}\n"
        f"Message:\n{message.text}"
    )
    
    return ContextItem(
        id=str(uuid4()),
        source_type=SourceType.SLACK,
        source_id=message.id,
        timestamp=message.timestamp,
        content={
            "channel_id": message.channel_id,
            "channel_name": message.channel_name,
            "user_id": message.user_id,
            "user_name": message.user_name,
            "message": message.text,
            "thread_ts": message.thread_ts,
        },
        context_text=context_text,
        sender=message.user_name,
        summary=f"[{display_channel}] {message.text[:120]}...".replace("\n", " ")
                if len(message.text) > 120
                else f"[{display_channel}] {message.text}".replace("\n", " "),
    )


def meeting_to_context(meeting: MeetingTranscript) -> ContextItem:
    """
    Convert a MeetingTranscript to a generic ContextItem.
    """
    participants_str = ", ".join(meeting.participants[:3])
    if len(meeting.participants) > 3:
        participants_str += f" +{len(meeting.participants) - 3} others"
    
    all_participants_str = ", ".join(meeting.participants)
    
    # Pre-format the context text for LLM prompts
    context_text = (
        f"[MEETING TRANSCRIPT]\n"
        f"Title: {meeting.title}\n"
        f"Participants: {all_participants_str}\n"
        f"Time: {meeting.meeting_time.isoformat()}\n"
        f"Duration: {meeting.duration_mins} minutes\n"
        f"Transcript:\n{meeting.transcript}"
    )
    
    return ContextItem(
        id=str(uuid4()),
        source_type=SourceType.MEETING_TRANSCRIPT,
        source_id=meeting.id,
        timestamp=meeting.meeting_time,
        content={
            "title": meeting.title,
            "participants": meeting.participants,
            "transcript": meeting.transcript,
            "duration_mins": meeting.duration_mins,
        },
        context_text=context_text,
        sender=participants_str,
        summary=f"Meeting: {meeting.title} ({participants_str})",
    )


def calendar_event_to_context(
    event_id: str,
    title: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    attendees: Optional[list[str]] = None,
    location: Optional[str] = None,
) -> ContextItem:
    """
    Convert a calendar event to a generic ContextItem.
    
    This is a placeholder for future calendar integration.
    """
    attendees = attendees or []
    attendees_str = ", ".join(attendees[:3]) if attendees else "No attendees"
    if len(attendees) > 3:
        attendees_str += f" +{len(attendees) - 3} others"
    
    all_attendees_str = ", ".join(attendees) if attendees else "No attendees"
    
    # Pre-format the context text for LLM prompts
    context_text = (
        f"[CALENDAR EVENT]\n"
        f"Title: {title}\n"
        f"Time: {start_time.isoformat()} - {end_time.isoformat()}\n"
        f"Location: {location or 'Not specified'}\n"
        f"Attendees: {all_attendees_str}\n"
        f"Description:\n{description}"
    )
    
    return ContextItem(
        id=str(uuid4()),
        source_type=SourceType.CALENDAR_EVENT,
        source_id=event_id,
        timestamp=start_time,
        content={
            "title": title,
            "description": description,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "attendees": attendees,
            "location": location,
        },
        context_text=context_text,
        sender=attendees_str,
        summary=f"Event: {title} ({attendees_str})",
    )


# --------------------------------------------------------------------------- #
# Helper to format context for LLM prompts
# --------------------------------------------------------------------------- #

def format_context_for_prompt(context: ContextItem) -> str:
    """
    Get the pre-formatted context text for LLM prompts.
    
    Returns the context_text attribute which is set by the adapter
    when the ContextItem is created.
    """
    return context.context_text
