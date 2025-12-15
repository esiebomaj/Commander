"""
Gmail integration for Commander.

Provides OAuth authentication, email reading, sending, and push notifications
for new emails.

Setup:
1. Create a Google Cloud project and enable Gmail API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download the credentials JSON and save as 'data/gmail_credentials.json'
4. Run the OAuth flow to authorize the application
"""
from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ...models import EmailMessage
from .cleaning import html_to_text, sanitize_body_text
from ..token_storage import (
    get_token,
    save_token,
    delete_token,
    has_token,
    save_gmail_history_id,
    get_gmail_history_id,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

from ...config import settings

DEFAULT_CREDENTIALS_FILE = settings.gmail_credentials_path

# Gmail API scopes - read and send emails
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",  # For marking as read
]


# --------------------------------------------------------------------------- #
# Gmail Integration Class
# --------------------------------------------------------------------------- #

class GmailIntegration:
    """
    Gmail integration for reading and sending emails.
    
    Usage:
        gmail = GmailIntegration()
        
        # Check if connected
        if not gmail.is_connected():
            auth_url = gmail.get_auth_url()
            # User visits URL and authorizes
            gmail.complete_auth(authorization_code)
        
        # Fetch recent emails
        emails = gmail.fetch_recent_emails(max_results=10)
        
        # Send an email
        gmail.send_email(to="user@example.com", subject="Hello", body="Hi there!")
    """
    
    def __init__(self, credentials_file: Union[str, Path]):
        """
        Initialize Gmail integration.
        
        Args:
            credentials_file: Path to the OAuth credentials JSON file.
        
        Raises:
            FileNotFoundError: If credentials file doesn't exist
        """
        self._credentials_file = Path(credentials_file)
        if not self._credentials_file.exists():
            raise FileNotFoundError(
                f"Gmail credentials file not found at {self._credentials_file}. "
                "Please download OAuth credentials from Google Cloud Console."
            )
        
        self._service = None
        self._credentials: Optional[Credentials] = None
        self._flow: Optional[InstalledAppFlow] = None
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if the Gmail integration is connected and has valid credentials."""
        if not has_token("gmail"):
            return False
        
        try:
            creds = self._get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False
    
    def get_user_email(self) -> Optional[str]:
        """Get the email address of the connected user."""
        if not self.is_connected():
            return None
        
        try:
            service = self._get_service()
            profile = service.users().getProfile(userId="me").execute()
            return profile.get("emailAddress")
        except Exception:
            return None
    
    # ----------------------------------------------------------------------- #
    # OAuth Flow
    # ----------------------------------------------------------------------- #
    
    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """
        Get the OAuth authorization URL for the user to visit.
        
        Args:
            redirect_uri: The redirect URI for OAuth. Use "urn:ietf:wg:oauth:2.0:oob" 
                         for copy/paste flow, or a web callback URL for web apps.
        
        Returns:
            The authorization URL for the user to visit
        """
        self._flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_file),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        
        auth_url, _ = self._flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        
        return auth_url
    
    def complete_auth(self, authorization_code: str) -> bool:
        """
        Complete the OAuth flow with the authorization code.
        
        Args:
            authorization_code: The code returned after user authorization
        
        Returns:
            True if authentication was successful
        """
        if self._flow is None:
            raise ValueError("Must call get_auth_url() first to start the OAuth flow")
        
        try:
            self._flow.fetch_token(code=authorization_code)
            creds = self._flow.credentials
            
            # Save credentials
            save_token("gmail", {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            })
            
            self._credentials = creds
            self._service = None  # Reset service to use new credentials
            self._flow = None
            
            return True
        except Exception as e:
            print(f"Error completing OAuth: {e}")
            return False
    
    def run_local_auth_flow(self, port: int = 8080) -> bool:
        """
        Run the complete OAuth flow locally (opens browser).
        
        This is a convenience method for command-line usage.
        
        Args:
            port: Local port for the OAuth callback
        
        Returns:
            True if authentication was successful
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._credentials_file),
                scopes=SCOPES,
            )
            creds = flow.run_local_server(port=port)
            
            # Save credentials
            save_token("gmail", {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            })
            
            self._credentials = creds
            self._service = None
            
            print(f"Successfully authenticated as {self.get_user_email()}")
            return True
        except Exception as e:
            print(f"Error during OAuth flow: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect Gmail by removing stored credentials.
        
        Returns:
            True if credentials were removed
        """
        self._credentials = None
        self._service = None
        return delete_token("gmail")
    
    # ----------------------------------------------------------------------- #
    # Private: Credentials & Service
    # ----------------------------------------------------------------------- #
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Gmail credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        token_data = get_token("gmail")
        if not token_data:
            return None
        
        try:
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", SCOPES),
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                save_token("gmail", {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else SCOPES,
                })
            
            self._credentials = creds
            return creds
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _get_service(self):
        """Get the Gmail API service, initializing if needed."""
        if self._service:
            return self._service
        
        creds = self._get_credentials()
        if not creds:
            raise ValueError("Not authenticated. Call run_local_auth_flow() or complete_auth() first.")
        
        self._service = build("gmail", "v1", credentials=creds)
        return self._service
    
    # ----------------------------------------------------------------------- #
    # Email Reading
    # ----------------------------------------------------------------------- #
    
    def fetch_recent_emails(
        self,
        max_results: int = 10,
        query: str = "is:important",
        include_spam_trash: bool = False,
    ) -> List[EmailMessage]:
        """
        Fetch recent emails from the user's inbox.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., "is:unread", "from:example.com")
            include_spam_trash: Whether to include spam and trash
        
        Returns:
            List of EmailMessage objects
        """
        service = self._get_service()
        emails: List[EmailMessage] = []
        
        try:
            # List message IDs
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                q=query,
                includeSpamTrash=include_spam_trash,
            ).execute()
            
            messages = results.get("messages", [])
            
            # Fetch full message details
            for msg_meta in messages:
                msg_id = msg_meta["id"]
                email = self._fetch_email_by_id(msg_id)
                if email:
                    emails.append(email)
            
            # Update history ID for incremental sync
            if messages:
                # Get current history ID
                profile = service.users().getProfile(userId="me").execute()
                history_id = profile.get("historyId")
                if history_id:
                    save_gmail_history_id(history_id)
            
            return emails
            
        except HttpError as e:
            print(f"Error fetching emails: {e}")
            return []
    
    def _fetch_email_by_id(self, msg_id: str) -> Optional[EmailMessage]:
        """Fetch a single email by ID and convert to EmailMessage."""
        service = self._get_service()
        
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full",
            ).execute()
            
            return self._parse_message(msg)
        except HttpError as e:
            print(f"Error fetching email {msg_id}: {e}")
            return None
    
    def _parse_message(self, msg: Dict[str, Any]) -> EmailMessage:
        """Parse a Gmail API message into an EmailMessage."""
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        
        # Extract body
        body_text = self._extract_body(msg.get("payload", {}))
        
        # Parse received time
        internal_date = msg.get("internalDate")
        if internal_date:
            received_at = datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        else:
            received_at = datetime.now(timezone.utc)
        
        return EmailMessage(
            id=msg["id"],
            thread_id=msg.get("threadId", msg["id"]),
            from_email=headers.get("from", "unknown@unknown.com"),
            subject=headers.get("subject", "(no subject)"),
            body_text=body_text,
            received_at=received_at,
            labels=msg.get("labelIds", []),
        )
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract the plain text body from a message payload."""
        # Try to get plain text directly
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                return sanitize_body_text(raw)
        
        # Check parts for multipart messages
        parts = payload.get("parts", [])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    raw = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    return sanitize_body_text(raw)
            
            # Recurse into nested parts
            if part.get("parts"):
                body = self._extract_body(part)
                if body:
                    return body
        
        # Fallback: try to get HTML and strip it
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    return sanitize_body_text(html_to_text(html))
        
        return ""
    
    # ----------------------------------------------------------------------- #
    # Incremental Sync (New Emails)
    # ----------------------------------------------------------------------- #
    
    def fetch_new_emails(self) -> List[EmailMessage]:
        """
        Fetch new emails since last sync using Gmail History API.
        
        This uses the stored history ID to only fetch emails that arrived
        since the last call to fetch_recent_emails() or fetch_new_emails().
        
        Returns:
            List of new EmailMessage objects
        """
        history_id = get_gmail_history_id()
        
        if not history_id:
            # No history ID - do a full fetch instead
            print("No history ID found. Performing full fetch.")
            return self.fetch_recent_emails(max_results=10)
        
        service = self._get_service()
        new_emails: List[EmailMessage] = []
        seen_ids: set = set()
        
        try:
            # Get history since last sync
            results = service.users().history().list(
                userId="me",
                startHistoryId=history_id,
                historyTypes=["messageAdded"],
                labelId="IMPORTANT",
            ).execute()
            
            history_records = results.get("history", [])
            
            # Extract new message IDs 
            for record in history_records:
                for msg_added in record.get("messagesAdded", []):
                    message = msg_added.get("message", {})
                    msg_id = message.get("id")
     
                    if msg_id and msg_id not in seen_ids:
                        seen_ids.add(msg_id)
                        email = self._fetch_email_by_id(msg_id)
                        if email:
                            new_emails.append(email)
            
            # Update history ID
            new_history_id = results.get("historyId")
            if new_history_id:
                save_gmail_history_id(new_history_id)
            
            return new_emails
            
        except HttpError as e:
            if e.resp.status == 404:
                # History ID is too old, do a full fetch
                print("History ID expired. Performing full fetch.")
                return self.fetch_recent_emails(max_results=10)
            print(f"Error fetching new emails: {e}")
            return []
    
    # ----------------------------------------------------------------------- #
    # Push Notifications (Webhook Setup)
    # ----------------------------------------------------------------------- #
    
    def setup_push_notifications(
        self,
        topic_name: str,
        label_ids: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Set up Gmail push notifications via Google Cloud Pub/Sub.
        
        Prerequisites:
        1. Create a Google Cloud Pub/Sub topic
        2. Give gmail-api-push@system.gserviceaccount.com publish rights to the topic
        3. Create a subscription to receive messages
        
        Args:
            topic_name: Full Pub/Sub topic name (e.g., "projects/my-project/topics/gmail-notifications")
            label_ids: Optional list of label IDs to watch (default: ["INBOX"])
        
        Returns:
            Watch response with historyId and expiration, or None on error
        """
        service = self._get_service()
        
        try:
            request_body = {
                "topicName": topic_name,
                "labelIds": label_ids or ["IMPORTANT"],
            }
            
            print("--------------------------------")
            print(request_body)
            print("--------------------------------")
            response = service.users().watch(
                userId="me",
                body=request_body,
            ).execute()

            print(response)
            
            # Save the history ID for incremental sync
            history_id = response.get("historyId")
            if history_id:
                save_gmail_history_id(history_id)
            
            return response
            
        except HttpError as e:
            print(f"Error setting up push notifications: {e}")
            return None
    

    def stop_push_notifications(self) -> bool:
        """Stop Gmail push notifications."""
        service = self._get_service()
        
        try:
            service.users().stop(userId="me").execute()
            return True
        except HttpError as e:
            print(f"Error stopping push notifications: {e}")
            return False
    
    # ----------------------------------------------------------------------- #
    # Email Sending
    # ----------------------------------------------------------------------- #
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional thread ID to reply to an existing thread
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
        
        Returns:
            Sent message metadata or None on error
        """
        service = self._get_service()
        
        try:
            # Create message
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            
            if cc:
                message["cc"] = ", ".join(cc)
            if bcc:
                message["bcc"] = ", ".join(bcc)
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            body_data: Dict[str, Any] = {"raw": raw}
            if thread_id:
                body_data["threadId"] = thread_id
            
            # Send message
            sent = service.users().messages().send(
                userId="me",
                body=body_data,
            ).execute()
            
            return sent
            
        except HttpError as e:
            print(f"Error sending email: {e}")
            return None
    
    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create an email draft.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            thread_id: Optional thread ID for a reply draft
        
        Returns:
            Draft metadata or None on error
        """
        service = self._get_service()
        
        try:
            # Create message
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            draft_body: Dict[str, Any] = {
                "message": {"raw": raw}
            }
            if thread_id:
                draft_body["message"]["threadId"] = thread_id
            
            # Create draft
            draft = service.users().drafts().create(
                userId="me",
                body=draft_body,
            ).execute()
            
            return draft
            
        except HttpError as e:
            print(f"Error creating draft: {e}")
            return None


# --------------------------------------------------------------------------- #
# Singleton Instance
# --------------------------------------------------------------------------- #

# Global instance for easy access
_gmail_instance: Optional[GmailIntegration] = None


def get_gmail(credentials_file: Union[str, Path] = DEFAULT_CREDENTIALS_FILE) -> GmailIntegration:
    """
    Get the global Gmail integration instance.
    
    Args:
        credentials_file: Path to credentials file. Only used when
                         creating a new instance (first call).
                         Defaults to 'data/gmail_credentials.json'.
    """
    global _gmail_instance
    if _gmail_instance is None:
        _gmail_instance = GmailIntegration(credentials_file=credentials_file)
    return _gmail_instance
