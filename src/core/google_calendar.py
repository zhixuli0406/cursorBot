"""
Google Calendar Integration for CursorBot

Provides:
- OAuth2 authentication with Google
- Calendar listing
- Event querying and creation
- Event modification and deletion

Usage:
    from src.core.google_calendar import get_calendar_manager
    
    calendar = get_calendar_manager()
    
    # List calendars
    calendars = await calendar.list_calendars()
    
    # Get today's events
    events = await calendar.get_events_today()
    
    # Create event
    event = await calendar.create_event(
        title="Meeting",
        start="2026-01-27T10:00:00",
        end="2026-01-27T11:00:00",
    )
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
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


# OAuth2 scopes for Calendar
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    attendees: list[str] = field(default_factory=list)
    calendar_id: str = "primary"
    link: str = ""
    status: str = "confirmed"
    
    def __str__(self) -> str:
        time_str = self.start.strftime("%H:%M") if self.start else "N/A"
        return f"{time_str} - {self.title}"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "description": self.description,
            "location": self.location,
            "attendees": self.attendees,
            "calendar_id": self.calendar_id,
            "link": self.link,
            "status": self.status,
        }


@dataclass
class Calendar:
    """Represents a calendar."""
    id: str
    name: str
    description: str = ""
    primary: bool = False
    color: str = ""


class GoogleCalendarManager:
    """
    Manages Google Calendar integration.
    
    Handles OAuth2 authentication and provides methods for
    calendar and event operations.
    """
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        """
        Initialize the calendar manager.
        
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
        self.token_file = token_file or str(self.data_dir / "calendar_token.json")
        
        self._service = None
        self._credentials = None
        self._authenticated = False
    
    @property
    def is_available(self) -> bool:
        """Check if Google API is available."""
        return GOOGLE_API_AVAILABLE
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self._authenticated and self._service is not None
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from token file."""
        if not GOOGLE_API_AVAILABLE:
            return None
        
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                return creds
            except Exception as e:
                logger.warning(f"Failed to load calendar credentials: {e}")
        return None
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        try:
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
            logger.debug("Calendar credentials saved")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    async def authenticate(self, force_refresh: bool = False) -> bool:
        """
        Authenticate with Google Calendar API.
        
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
                logger.info("Refreshing calendar credentials...")
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
            self._service = build("calendar", "v3", credentials=creds)
            self._credentials = creds
            self._authenticated = True
            logger.info("Google Calendar authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Calendar authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def list_calendars(self) -> list[Calendar]:
        """
        List all calendars.
        
        Returns:
            List of Calendar objects
        """
        if not self.is_authenticated:
            logger.warning("Calendar not authenticated")
            return []
        
        try:
            result = self._service.calendarList().list().execute()
            calendars = []
            
            for item in result.get("items", []):
                calendars.append(Calendar(
                    id=item["id"],
                    name=item.get("summary", "Untitled"),
                    description=item.get("description", ""),
                    primary=item.get("primary", False),
                    color=item.get("backgroundColor", ""),
                ))
            
            return calendars
            
        except Exception as e:
            logger.error(f"Failed to list calendars: {e}")
            return []
    
    async def get_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime = None,
        time_max: datetime = None,
        max_results: int = 10,
        query: str = None,
    ) -> list[CalendarEvent]:
        """
        Get calendar events.
        
        Args:
            calendar_id: Calendar ID (default: primary)
            time_min: Start time filter
            time_max: End time filter
            max_results: Maximum number of events
            query: Search query
            
        Returns:
            List of CalendarEvent objects
        """
        if not self.is_authenticated:
            logger.warning("Calendar not authenticated")
            return []
        
        try:
            # Default to today if no time range
            if not time_min:
                time_min = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if not time_max:
                time_max = time_min + timedelta(days=1)
            
            params = {
                "calendarId": calendar_id,
                "timeMin": time_min.isoformat() + "Z",
                "timeMax": time_max.isoformat() + "Z",
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }
            
            if query:
                params["q"] = query
            
            result = self._service.events().list(**params).execute()
            events = []
            
            for item in result.get("items", []):
                # Parse start/end times
                start = item.get("start", {})
                end = item.get("end", {})
                
                start_dt = self._parse_datetime(start)
                end_dt = self._parse_datetime(end)
                
                # Extract attendees
                attendees = [
                    a.get("email", "") 
                    for a in item.get("attendees", [])
                ]
                
                events.append(CalendarEvent(
                    id=item["id"],
                    title=item.get("summary", "Untitled"),
                    start=start_dt,
                    end=end_dt,
                    description=item.get("description", ""),
                    location=item.get("location", ""),
                    attendees=attendees,
                    calendar_id=calendar_id,
                    link=item.get("htmlLink", ""),
                    status=item.get("status", "confirmed"),
                ))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    def _parse_datetime(self, dt_dict: dict) -> Optional[datetime]:
        """Parse datetime from Google Calendar format."""
        if not dt_dict:
            return None
        
        try:
            if "dateTime" in dt_dict:
                # Full datetime
                dt_str = dt_dict["dateTime"]
                # Remove timezone suffix for parsing
                if "+" in dt_str:
                    dt_str = dt_str.split("+")[0]
                elif dt_str.endswith("Z"):
                    dt_str = dt_str[:-1]
                return datetime.fromisoformat(dt_str)
            elif "date" in dt_dict:
                # All-day event
                return datetime.strptime(dt_dict["date"], "%Y-%m-%d")
        except Exception as e:
            logger.debug(f"Failed to parse datetime: {e}")
        
        return None
    
    async def get_events_today(self, calendar_id: str = "primary") -> list[CalendarEvent]:
        """Get today's events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return await self.get_events(calendar_id, today, tomorrow)
    
    async def get_events_week(self, calendar_id: str = "primary") -> list[CalendarEvent]:
        """Get this week's events."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today + timedelta(days=7)
        return await self.get_events(calendar_id, today, week_end, max_results=50)
    
    async def create_event(
        self,
        title: str,
        start: str,
        end: str = None,
        description: str = "",
        location: str = "",
        attendees: list[str] = None,
        calendar_id: str = "primary",
        all_day: bool = False,
    ) -> Optional[CalendarEvent]:
        """
        Create a new calendar event.
        
        Args:
            title: Event title
            start: Start time (ISO format or date)
            end: End time (ISO format or date)
            description: Event description
            location: Event location
            attendees: List of attendee emails
            calendar_id: Target calendar
            all_day: Whether this is an all-day event
            
        Returns:
            Created CalendarEvent or None
        """
        if not self.is_authenticated:
            logger.warning("Calendar not authenticated")
            return None
        
        try:
            # Parse start time
            start_dt = datetime.fromisoformat(start.replace("Z", ""))
            
            # Calculate end if not provided (1 hour default)
            if not end:
                end_dt = start_dt + timedelta(hours=1)
            else:
                end_dt = datetime.fromisoformat(end.replace("Z", ""))
            
            # Build event body
            event_body = {
                "summary": title,
                "description": description,
                "location": location,
            }
            
            if all_day:
                event_body["start"] = {"date": start_dt.strftime("%Y-%m-%d")}
                event_body["end"] = {"date": end_dt.strftime("%Y-%m-%d")}
            else:
                event_body["start"] = {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "UTC",
                }
                event_body["end"] = {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "UTC",
                }
            
            if attendees:
                event_body["attendees"] = [{"email": e} for e in attendees]
            
            # Create event
            result = self._service.events().insert(
                calendarId=calendar_id,
                body=event_body,
            ).execute()
            
            logger.info(f"Created event: {title}")
            
            return CalendarEvent(
                id=result["id"],
                title=title,
                start=start_dt,
                end=end_dt,
                description=description,
                location=location,
                attendees=attendees or [],
                calendar_id=calendar_id,
                link=result.get("htmlLink", ""),
            )
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None
    
    async def update_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
        title: str = None,
        start: str = None,
        end: str = None,
        description: str = None,
        location: str = None,
    ) -> bool:
        """
        Update an existing event.
        
        Args:
            event_id: Event ID
            calendar_id: Calendar ID
            title: New title (optional)
            start: New start time (optional)
            end: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            
        Returns:
            True if updated successfully
        """
        if not self.is_authenticated:
            return False
        
        try:
            # Get existing event
            event = self._service.events().get(
                calendarId=calendar_id,
                eventId=event_id,
            ).execute()
            
            # Update fields
            if title:
                event["summary"] = title
            if description is not None:
                event["description"] = description
            if location is not None:
                event["location"] = location
            if start:
                start_dt = datetime.fromisoformat(start.replace("Z", ""))
                event["start"] = {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "UTC",
                }
            if end:
                end_dt = datetime.fromisoformat(end.replace("Z", ""))
                event["end"] = {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "UTC",
                }
            
            # Update
            self._service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event,
            ).execute()
            
            logger.info(f"Updated event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return False
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary",
    ) -> bool:
        """
        Delete an event.
        
        Args:
            event_id: Event ID
            calendar_id: Calendar ID
            
        Returns:
            True if deleted successfully
        """
        if not self.is_authenticated:
            return False
        
        try:
            self._service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
            ).execute()
            
            logger.info(f"Deleted event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False
    
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
            import json
            
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
            import json
            
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
            self._service = build("calendar", "v3", credentials=creds)
            
            logger.info("Google Calendar authentication completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete auth: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# Global instance
_calendar_manager: Optional[GoogleCalendarManager] = None


def get_calendar_manager() -> GoogleCalendarManager:
    """Get the global calendar manager instance."""
    global _calendar_manager
    
    if _calendar_manager is None:
        _calendar_manager = GoogleCalendarManager()
    
    return _calendar_manager


__all__ = [
    "GoogleCalendarManager",
    "CalendarEvent",
    "Calendar",
    "get_calendar_manager",
    "GOOGLE_API_AVAILABLE",
]
