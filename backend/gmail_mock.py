from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from .models import EmailMessage


def fetch_recent_emails(limit: int = 5) -> List[EmailMessage]:
    """
    Mocked Gmail ingestion.
    Returns a small list of recent-looking emails with varied intents.
    """
    now = datetime.now(timezone.utc)
    emails = [
        EmailMessage(
            id="msg_1001",
            thread_id="thr_2001",
            from_email="recruiter@example.com",
            subject="Quick call this week?",
            body_text=(
                "Hi Vega,\n\nI saw your profile and would love to chat about an opportunity. "
                "Are you free Wed or Thu afternoon for a 30-minute call?\n\nBest,\nSam"
            ),
            received_at=now - timedelta(hours=2),
        ),
        EmailMessage(
            id="msg_1002",
            thread_id="thr_2002",
            from_email="teammate@example.com",
            subject="Please review the PR",
            body_text=(
                "Hey—could you review my PR #123 today? I need feedback on the API design. Thanks!"
            ),
            received_at=now - timedelta(hours=3),
        ),
        EmailMessage(
            id="msg_1003",
            thread_id="thr_2003",
            from_email="billing@example.com",
            subject="Invoice overdue notice",
            body_text=(
                "Your invoice INV-7782 is past due by 7 days. Please remit payment or contact support."
            ),
            received_at=now - timedelta(days=1, hours=1),
        ),
        EmailMessage(
            id="msg_1004",
            thread_id="thr_2004",
            from_email="friend@example.com",
            subject="Thanks!",
            body_text="Got it—thanks for sending the files. Talk soon.",
            received_at=now - timedelta(hours=6),
        ),
        EmailMessage(
            id="msg_1005",
            thread_id="thr_2005",
            from_email="events@example.com",
            subject="Webinar tomorrow",
            body_text="Reminder: Webinar is tomorrow at 9am PT. Join link inside.",
            received_at=now - timedelta(hours=10),
        ),
    ]
    return emails[:limit]


