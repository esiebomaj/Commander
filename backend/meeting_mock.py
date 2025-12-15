from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from .models import MeetingTranscript


def fetch_recent_meeting_transcripts(limit: int = 3) -> List[MeetingTranscript]:
    """
    Mocked meeting transcript ingestion.
    Returns a small list of recent meeting transcripts with varied content.
    """
    now = datetime.now(timezone.utc)
    transcripts = [
        MeetingTranscript(
            id="meeting_001",
            title="Sprint Planning - Week 50",
            participants=["vega", "alice", "bob", "charlie"],
            transcript=(
                "Alice: Alright, let's go through the backlog for this sprint.\n"
                "Bob: I think we should prioritize the payment integration. Customer X is waiting.\n"
                "Vega: Agreed. I can take the API endpoints if someone handles the frontend.\n"
                "Charlie: I'll do the frontend. Should take about 3 days.\n"
                "Alice: Great. Let's also add the bug fixes from last week. Vega, can you create tickets for those?\n"
                "Vega: Sure, I'll have them ready by EOD.\n"
                "Alice: Perfect. Let's sync again on Wednesday to check progress."
            ),
            meeting_time=now - timedelta(hours=6),
            duration_mins=45,
        ),
        MeetingTranscript(
            id="meeting_002",
            title="1:1 with Manager",
            participants=["vega", "manager_mike"],
            transcript=(
                "Mike: How's everything going? Any blockers?\n"
                "Vega: Things are good. The payment integration is on track.\n"
                "Mike: Excellent. I wanted to discuss the upcoming performance review cycle.\n"
                "Vega: Sure, what do I need to prepare?\n"
                "Mike: Just gather some examples of your key achievements this quarter. "
                "I'd also like you to think about your goals for next quarter.\n"
                "Vega: Got it. I'll put together a doc and share it before our next 1:1.\n"
                "Mike: Sounds good. Also, there's a tech lead opportunity opening up. Interested?\n"
                "Vega: Definitely interested. Let's discuss more next time."
            ),
            meeting_time=now - timedelta(days=1, hours=2),
            duration_mins=30,
        ),
        MeetingTranscript(
            id="meeting_003",
            title="Customer Feedback Review",
            participants=["vega", "alice", "eve", "product_lead"],
            transcript=(
                "Eve: I've compiled the survey results. Top complaints are slow load times and confusing navigation.\n"
                "Product Lead: We knew about the performance issues. What's the plan?\n"
                "Alice: Engineering is already working on optimizations. Should ship next sprint.\n"
                "Vega: For navigation, I think we need a UX audit. The current flow has too many steps.\n"
                "Eve: Agreed. I'll schedule a session with the design team.\n"
                "Product Lead: Let's create action items. Vega, can you draft a proposal for the UX improvements?\n"
                "Vega: Sure, I'll have something ready by Friday.\n"
                "Product Lead: Great. Let's reconvene next week with updates."
            ),
            meeting_time=now - timedelta(days=2),
            duration_mins=60,
        ),
    ]
    return transcripts[:limit]
