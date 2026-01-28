"""
Gmail Integration for CursorBot

Provides:
- OAuth2 authentication with Google
- Email reading and searching
- Email sending
- Label management
- Pub/Sub webhook triggers

Usage:
    from src.core.gmail import get_gmail_manager
    
    gmail = get_gmail_manager()
    
    # List recent emails
    emails = await gmail.list_emails(max_results=10)
    
    # Search emails
    results = await gmail.search_emails("from:example@gmail.com")
    
    # Send email
    await gmail.send_email(
        to="recipient@example.com",
        subject="Hello",
        body="This is a test email.",
    )
"""

import os
import base64
import json
import asyncio
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from ..utils.logger import logger

# Try to import Google API client
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Credentials = None
    Request = None
    InstalledAppFlow = None
    build = None


# OAuth2 scopes for Gmail
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


@dataclass
class EmailMessage:
    """Represents an email message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    to: list[str]
    cc: list[str] = field(default_factory=list)
    date: datetime = None
    snippet: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    is_read: bool = True
    attachments: list[dict] = field(default_factory=list)
    
    def __str__(self) -> str:
        date_str = self.date.strftime("%Y-%m-%d %H:%M") if self.date else "N/A"
        return f"[{date_str}] {self.sender}: {self.subject}"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "subject": self.subject,
            "sender": self.sender,
            "to": self.to,
            "cc": self.cc,
            "date": self.date.isoformat() if self.date else None,
            "snippet": self.snippet,
            "body": self.body,
            "labels": self.labels,
            "is_read": self.is_read,
            "attachments": self.attachments,
        }


@dataclass
class GmailLabel:
    """Represents a Gmail label."""
    id: str
    name: str
    type: str = "user"
    message_count: int = 0
    unread_count: int = 0


class GmailManager:
    """
    Manages Gmail integration.
    
    Handles OAuth2 authentication and provides methods for
    email operations.
    """
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        """
        Initialize the Gmail manager.
        
        Args:
            credentials_file: Path to OAuth2 client credentials JSON
            token_file: Path to store/load user token
        """
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "google"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = credentials_file or os.getenv(
            "GOOGLE_CREDENTIALS_FILE",
            str(self.data_dir / "credentials.json")
        )
        self.token_file = token_file or str(self.data_dir / "gmail_token.json")
        
        self._service = None
        self._credentials = None
        self._authenticated = False
        self._user_email = None
    
    @property
    def is_available(self) -> bool:
        """Check if Google API is available."""
        return GOOGLE_API_AVAILABLE
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._authenticated and self._service is not None
    
    @property
    def user_email(self) -> Optional[str]:
        """Get authenticated user's email."""
        return self._user_email
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        if not GOOGLE_API_AVAILABLE:
            return None
        
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                return creds
            except Exception as e:
                logger.warning(f"Failed to load Gmail credentials: {e}")
        return None
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        try:
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
            logger.debug("Gmail credentials saved")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    async def authenticate(self, force_refresh: bool = False) -> bool:
        """
        Authenticate with Gmail API.
        
        Args:
            force_refresh: Force re-authentication
            
        Returns:
            True if authenticated successfully
        """
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API client not installed. Run: pip install google-api-python-client google-auth-oauthlib")
            return False
        
        try:
            creds = self._load_credentials()
            
            # Refresh or get new credentials
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail credentials...")
                creds.refresh(Request())
                self._save_credentials(creds)
            elif not creds or force_refresh:
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    logger.info("Download OAuth2 credentials from Google Cloud Console")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
                self._save_credentials(creds)
            
            # Build service
            self._service = build("gmail", "v1", credentials=creds)
            self._credentials = creds
            self._authenticated = True
            
            # Get user email
            profile = self._service.users().getProfile(userId="me").execute()
            self._user_email = profile.get("emailAddress")
            
            logger.info(f"Gmail authenticated as: {self._user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def list_emails(
        self,
        max_results: int = 10,
        label_ids: list[str] = None,
        query: str = None,
        include_body: bool = False,
    ) -> list[EmailMessage]:
        """
        List emails from inbox.
        
        Args:
            max_results: Maximum number of emails
            label_ids: Filter by label IDs (default: INBOX)
            query: Gmail search query
            include_body: Whether to fetch full body
            
        Returns:
            List of EmailMessage objects
        """
        if not self.is_authenticated:
            logger.warning("Gmail not authenticated")
            return []
        
        try:
            params = {
                "userId": "me",
                "maxResults": max_results,
            }
            
            if label_ids:
                params["labelIds"] = label_ids
            else:
                params["labelIds"] = ["INBOX"]
            
            if query:
                params["q"] = query
            
            result = self._service.users().messages().list(**params).execute()
            messages = result.get("messages", [])
            
            emails = []
            for msg in messages:
                email = await self._get_email_details(msg["id"], include_body)
                if email:
                    emails.append(email)
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to list emails: {e}")
            return []
    
    async def _get_email_details(
        self,
        message_id: str,
        include_body: bool = False,
    ) -> Optional[EmailMessage]:
        """Get detailed email information."""
        try:
            msg = self._service.users().messages().get(
                userId="me",
                id=message_id,
                format="full" if include_body else "metadata",
                metadataHeaders=["From", "To", "Cc", "Subject", "Date"],
            ).execute()
            
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            
            # Parse date
            date = None
            if "Date" in headers:
                try:
                    from email.utils import parsedate_to_datetime
                    date = parsedate_to_datetime(headers["Date"])
                except Exception:
                    pass
            
            # Parse recipients
            to = self._parse_addresses(headers.get("To", ""))
            cc = self._parse_addresses(headers.get("Cc", ""))
            
            # Get body if requested
            body = ""
            if include_body:
                body = self._extract_body(msg.get("payload", {}))
            
            # Check attachments
            attachments = self._get_attachments(msg.get("payload", {}))
            
            # Check read status
            labels = msg.get("labelIds", [])
            is_read = "UNREAD" not in labels
            
            return EmailMessage(
                id=msg["id"],
                thread_id=msg.get("threadId", ""),
                subject=headers.get("Subject", "(No Subject)"),
                sender=headers.get("From", ""),
                to=to,
                cc=cc,
                date=date,
                snippet=msg.get("snippet", ""),
                body=body,
                labels=labels,
                is_read=is_read,
                attachments=attachments,
            )
            
        except Exception as e:
            logger.error(f"Failed to get email details: {e}")
            return None
    
    def _parse_addresses(self, address_str: str) -> list[str]:
        """Parse email addresses from header string."""
        if not address_str:
            return []
        return [a.strip() for a in address_str.split(",")]
    
    def _extract_body(self, payload: dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    if "body" in part and part["body"].get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break
                elif part.get("mimeType") == "text/html" and not body:
                    if "body" in part and part["body"].get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
        
        return body
    
    def _get_attachments(self, payload: dict) -> list[dict]:
        """Extract attachment information from payload."""
        attachments = []
        
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    attachments.append({
                        "filename": part["filename"],
                        "mimeType": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": part.get("body", {}).get("attachmentId", ""),
                    })
        
        return attachments
    
    async def search_emails(
        self,
        query: str,
        max_results: int = 20,
        include_body: bool = False,
    ) -> list[EmailMessage]:
        """
        Search emails using Gmail query syntax.
        
        Args:
            query: Gmail search query (e.g., "from:example@gmail.com")
            max_results: Maximum number of results
            include_body: Whether to fetch full body
            
        Returns:
            List of matching EmailMessage objects
        """
        return await self.list_emails(
            max_results=max_results,
            label_ids=None,
            query=query,
            include_body=include_body,
        )
    
    async def get_email(self, message_id: str) -> Optional[EmailMessage]:
        """
        Get a specific email by ID.
        
        Args:
            message_id: Email message ID
            
        Returns:
            EmailMessage or None
        """
        return await self._get_email_details(message_id, include_body=True)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: list[str] = None,
        bcc: list[str] = None,
        html: bool = False,
        reply_to: str = None,
    ) -> Optional[str]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            html: Whether body is HTML
            reply_to: Message ID to reply to
            
        Returns:
            Sent message ID or None
        """
        if not self.is_authenticated:
            logger.warning("Gmail not authenticated")
            return None
        
        try:
            # Create message
            if html:
                message = MIMEMultipart("alternative")
                message.attach(MIMEText(body, "plain"))
                message.attach(MIMEText(body, "html"))
            else:
                message = MIMEText(body)
            
            message["to"] = to
            message["subject"] = subject
            message["from"] = self._user_email or "me"
            
            if cc:
                message["cc"] = ", ".join(cc)
            if bcc:
                message["bcc"] = ", ".join(bcc)
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            body_data = {"raw": raw}
            if reply_to:
                body_data["threadId"] = reply_to
            
            # Send
            result = self._service.users().messages().send(
                userId="me",
                body=body_data,
            ).execute()
            
            logger.info(f"Email sent to {to}: {subject}")
            return result.get("id")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return None
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read."""
        return await self._modify_labels(message_id, remove_labels=["UNREAD"])
    
    async def mark_as_unread(self, message_id: str) -> bool:
        """Mark an email as unread."""
        return await self._modify_labels(message_id, add_labels=["UNREAD"])
    
    async def archive(self, message_id: str) -> bool:
        """Archive an email (remove from inbox)."""
        return await self._modify_labels(message_id, remove_labels=["INBOX"])
    
    async def trash(self, message_id: str) -> bool:
        """Move an email to trash."""
        if not self.is_authenticated:
            return False
        
        try:
            self._service.users().messages().trash(
                userId="me",
                id=message_id,
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to trash email: {e}")
            return False
    
    async def _modify_labels(
        self,
        message_id: str,
        add_labels: list[str] = None,
        remove_labels: list[str] = None,
    ) -> bool:
        """Modify email labels."""
        if not self.is_authenticated:
            return False
        
        try:
            body = {}
            if add_labels:
                body["addLabelIds"] = add_labels
            if remove_labels:
                body["removeLabelIds"] = remove_labels
            
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body=body,
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to modify labels: {e}")
            return False
    
    async def list_labels(self) -> list[GmailLabel]:
        """List all Gmail labels."""
        if not self.is_authenticated:
            return []
        
        try:
            result = self._service.users().labels().list(userId="me").execute()
            labels = []
            
            for item in result.get("labels", []):
                # Get label details
                label_info = self._service.users().labels().get(
                    userId="me",
                    id=item["id"],
                ).execute()
                
                labels.append(GmailLabel(
                    id=item["id"],
                    name=item.get("name", ""),
                    type=item.get("type", "user"),
                    message_count=label_info.get("messagesTotal", 0),
                    unread_count=label_info.get("messagesUnread", 0),
                ))
            
            return labels
            
        except Exception as e:
            logger.error(f"Failed to list labels: {e}")
            return []
    
    async def get_unread_count(self) -> int:
        """Get count of unread emails in inbox."""
        if not self.is_authenticated:
            return 0
        
        try:
            result = self._service.users().labels().get(
                userId="me",
                id="INBOX",
            ).execute()
            return result.get("messagesUnread", 0)
        except Exception as e:
            logger.error(f"Failed to get unread count: {e}")
            return 0
    
    def get_auth_url(self) -> Optional[str]:
        """
        Get OAuth2 authorization URL for manual auth flow.
        
        Returns:
            Authorization URL or None
        """
        if not GOOGLE_API_AVAILABLE:
            return None
        
        if not os.path.exists(self.credentials_file):
            return None
        
        try:
            # Read client credentials
            with open(self.credentials_file, "r") as f:
                creds_data = json.load(f)
            
            # Get client info (handle both 'installed' and 'web' types)
            client_info = creds_data.get("installed") or creds_data.get("web", {})
            client_id = client_info.get("client_id", "")
            
            if not client_id:
                logger.error("No client_id found in credentials file")
                return None
            
            # Build OAuth URL manually with all required parameters
            import urllib.parse
            
            redirect_uri = "http://localhost:8080"
            
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "access_type": "offline",
                "prompt": "consent",
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
            
            # Store redirect_uri for later use
            self._redirect_uri = redirect_uri
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to get auth URL: {e}")
            return None
    
    async def complete_auth_with_code(self, code: str) -> bool:
        """
        Complete OAuth with authorization code.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            True if successful
        """
        if not GOOGLE_API_AVAILABLE:
            return False
        
        if not os.path.exists(self.credentials_file):
            return False
        
        try:
            # Read client credentials
            with open(self.credentials_file, "r") as f:
                creds_data = json.load(f)
            
            client_info = creds_data.get("installed") or creds_data.get("web", {})
            client_id = client_info.get("client_id", "")
            client_secret = client_info.get("client_secret", "")
            
            redirect_uri = getattr(self, "_redirect_uri", "http://localhost:8080")
            
            # Exchange code for tokens using httpx
            import httpx
            
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                return False
            
            token_data = response.json()
            
            # Create credentials object
            creds = Credentials(
                token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
            
            # Save credentials
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
            
            self._credentials = creds
            self._service = build("gmail", "v1", credentials=creds)
            
            logger.info("Gmail authentication completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete auth: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# Global instance
_gmail_manager: Optional[GmailManager] = None


def get_gmail_manager() -> GmailManager:
    """Get the global Gmail manager instance."""
    global _gmail_manager
    
    if _gmail_manager is None:
        _gmail_manager = GmailManager()
    
    return _gmail_manager


__all__ = [
    "GmailManager",
    "EmailMessage",
    "GmailLabel",
    "get_gmail_manager",
    "GOOGLE_API_AVAILABLE",
]
