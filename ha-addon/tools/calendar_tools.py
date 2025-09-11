"""
Calendar Tools for LLM
Provides calendar search, listing, and creation capabilities.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from services.tool_registry import BaseTool, ToolParameter, ToolResult

try:
    from services.google_auth import GoogleAuthManager
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GoogleAuthManager = None
    HttpError = Exception
    GOOGLE_AVAILABLE = False


class SearchCalendarEventsTool(BaseTool):
    """Search for calendar events based on query, date range, etc."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "search_calendar_events"
    
    @property
    def description(self) -> str:
        return "Search for calendar events in a specific date range. Use for finding events on specific dates or time periods."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("start_date", "string", "Start date for search (YYYY-MM-DD format)", required=False),
            ToolParameter("end_date", "string", "End date for search (YYYY-MM-DD format)", required=False),
            ToolParameter("query", "string", "Text to search in event titles/descriptions", required=False, default=""),
            ToolParameter("max_results", "integer", "Maximum number of events to return", required=False, default=20)
        ]
    
    def _get_service(self):
        """Get Calendar service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_calendar_service()
            except Exception as e:
                self.logger.error(f"Could not get Calendar service: {e}")
        return self._service
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        try:
            return datetime.fromisoformat(date_str)
        except:
            return datetime.strptime(date_str, '%Y-%m-%d')
    
    async def execute(self, start_date: str = None, end_date: str = None, query: str = "", max_results: int = 20) -> ToolResult:
        """Execute calendar event search"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Calendar service not available")
        
        try:
            # Set default date range if not provided with timezone awareness
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if not start_date:
                start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                start_dt = self._parse_date(start_date)
            
            if not end_date:
                end_dt = start_dt + timedelta(days=30)  # Default to 30 days
            else:
                end_dt = self._parse_date(end_date)
                end_dt = end_dt.replace(hour=23, minute=59, second=59)
            
            time_min = start_dt.isoformat().replace('+00:00', 'Z')
            time_max = end_dt.isoformat().replace('+00:00', 'Z')
            
            self.logger.info(f"Searching calendar events from {time_min} to {time_max}")
            
            # Search calendar events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=min(max_results, 100),  # Safety limit
                singleEvents=True,
                orderBy='startTime',
                q=query if query else None
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} events")
            
            # Process events
            processed_events = []
            for event in events:
                try:
                    # Parse start/end times
                    start_info = event.get('start', {})
                    end_info = event.get('end', {})
                    
                    event_data = {
                        'id': event.get('id'),
                        'title': event.get('summary', 'No Title'),
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'start_time': '',
                        'end_time': '',
                        'start_date': '',
                        'end_date': '',
                        'is_all_day': False,
                        'attendees': [],
                        'creator': event.get('creator', {}).get('email', ''),
                        'status': event.get('status', '')
                    }
                    
                    # Parse start/end times
                    if 'dateTime' in start_info:
                        # Timed event
                        start_dt = datetime.fromisoformat(start_info['dateTime'].replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_info['dateTime'].replace('Z', '+00:00'))
                        event_data['start_time'] = start_dt.strftime('%H:%M')
                        event_data['end_time'] = end_dt.strftime('%H:%M')
                        event_data['start_date'] = start_dt.strftime('%Y-%m-%d')
                        event_data['end_date'] = end_dt.strftime('%Y-%m-%d')
                    elif 'date' in start_info:
                        # All-day event
                        event_data['is_all_day'] = True
                        event_data['start_date'] = start_info['date']
                        event_data['end_date'] = end_info.get('date', start_info['date'])
                        event_data['start_time'] = 'All day'
                        event_data['end_time'] = 'All day'
                    
                    # Parse attendees
                    attendees = event.get('attendees', [])
                    for attendee in attendees:
                        name = attendee.get('displayName', attendee.get('email', 'Unknown'))
                        event_data['attendees'].append({
                            'name': name,
                            'email': attendee.get('email', ''),
                            'status': attendee.get('responseStatus', 'unknown')
                        })
                    
                    processed_events.append(event_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process event: {e}")
                    continue
            
            return ToolResult(
                success=True,
                data={
                    'events': processed_events,
                    'total_found': len(events),
                    'search_period': f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
                    'query': query
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error searching calendar events: {str(e)}"
            )


class GetUpcomingEventsTool(BaseTool):
    """Get upcoming events starting from current time"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "get_upcoming_events"
    
    @property
    def description(self) -> str:
        return "Get upcoming events starting from now. Perfect for 'next event', 'upcoming meetings', etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("max_results", "integer", "Maximum number of events to return", required=False, default=10),
            ToolParameter("days_ahead", "integer", "Look for events in the next N days", required=False, default=30)
        ]
    
    def _get_service(self):
        """Get Calendar service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_calendar_service()
            except Exception as e:
                self.logger.error(f"Could not get Calendar service: {e}")
        return self._service
    
    async def execute(self, max_results: int = 10, days_ahead: int = 30) -> ToolResult:
        """Execute upcoming events retrieval"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Calendar service not available")
        
        try:
            # Get current time and future range with timezone awareness
            from datetime import timezone
            now = datetime.now(timezone.utc)
            future = now + timedelta(days=days_ahead)
            
            time_min = now.isoformat().replace('+00:00', 'Z')
            time_max = future.isoformat().replace('+00:00', 'Z')
            
            self.logger.info(f"Getting upcoming events from {time_min} to {time_max}")
            
            # Get upcoming events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=min(max_results, 50),  # Safety limit
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} upcoming events")
            
            # Process events (similar to search)
            processed_events = []
            for event in events:
                try:
                    start_info = event.get('start', {})
                    end_info = event.get('end', {})
                    
                    event_data = {
                        'id': event.get('id'),
                        'title': event.get('summary', 'No Title'),
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                        'start_time': '',
                        'end_time': '',
                        'start_date': '',
                        'end_date': '',
                        'is_all_day': False,
                        'attendees': [],
                        'creator': event.get('creator', {}).get('email', ''),
                        'status': event.get('status', '')
                    }
                    
                    # Parse start/end times
                    if 'dateTime' in start_info:
                        start_dt = datetime.fromisoformat(start_info['dateTime'].replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_info['dateTime'].replace('Z', '+00:00'))
                        event_data['start_time'] = start_dt.strftime('%H:%M')
                        event_data['end_time'] = end_dt.strftime('%H:%M')
                        event_data['start_date'] = start_dt.strftime('%Y-%m-%d')
                        event_data['end_date'] = end_dt.strftime('%Y-%m-%d')
                        
                        # Calculate time until event
                        time_until = start_dt - now
                        if time_until.days > 0:
                            event_data['time_until'] = f"{time_until.days} days"
                        elif time_until.seconds > 3600:
                            hours = time_until.seconds // 3600
                            event_data['time_until'] = f"{hours} hours"
                        else:
                            minutes = time_until.seconds // 60
                            event_data['time_until'] = f"{minutes} minutes"
                    elif 'date' in start_info:
                        event_data['is_all_day'] = True
                        event_data['start_date'] = start_info['date']
                        event_data['end_date'] = end_info.get('date', start_info['date'])
                        event_data['start_time'] = 'All day'
                        event_data['end_time'] = 'All day'
                    
                    # Parse attendees
                    attendees = event.get('attendees', [])
                    for attendee in attendees:
                        name = attendee.get('displayName', attendee.get('email', 'Unknown'))
                        event_data['attendees'].append({
                            'name': name,
                            'email': attendee.get('email', ''),
                            'status': attendee.get('responseStatus', 'unknown')
                        })
                    
                    processed_events.append(event_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process event: {e}")
                    continue
            
            return ToolResult(
                success=True,
                data={
                    'upcoming_events': processed_events,
                    'total_found': len(events),
                    'search_period': f"Next {days_ahead} days",
                    'current_time': now.isoformat()
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting upcoming events: {str(e)}"
            )


class CreateCalendarEventTool(BaseTool):
    """Create a new calendar event"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "create_calendar_event"
    
    @property
    def description(self) -> str:
        return "Create a new calendar event. Specify title, start/end times, description, attendees, etc."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("title", "string", "Event title/summary", required=True),
            ToolParameter("start_datetime", "string", "Start date and time (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD for all-day)", required=True),
            ToolParameter("end_datetime", "string", "End date and time (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD for all-day)", required=True),
            ToolParameter("description", "string", "Event description", required=False, default=""),
            ToolParameter("location", "string", "Event location", required=False, default=""),
            ToolParameter("attendees", "string", "Attendee emails (comma-separated)", required=False, default="")
        ]
    
    def _get_service(self):
        """Get Calendar service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_calendar_service()
            except Exception as e:
                self.logger.error(f"Could not get Calendar service: {e}")
        return self._service
    
    def _parse_datetime(self, datetime_str: str) -> Dict[str, str]:
        """Parse datetime string for Google Calendar API"""
        try:
            # Check if it's a date-only string (YYYY-MM-DD)
            if len(datetime_str) == 10:
                return {'date': datetime_str}
            else:
                # Parse as datetime
                dt = datetime.fromisoformat(datetime_str)
                return {'dateTime': dt.isoformat(), 'timeZone': 'Europe/Lisbon'}
        except Exception as e:
            self.logger.error(f"Error parsing datetime '{datetime_str}': {e}")
            raise ValueError(f"Invalid datetime format: {datetime_str}")
    
    async def execute(self, title: str, start_datetime: str, end_datetime: str, 
                     description: str = "", location: str = "", attendees: str = "") -> ToolResult:
        """Execute calendar event creation"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Calendar service not available")
        
        try:
            # Parse start/end times
            start = self._parse_datetime(start_datetime)
            end = self._parse_datetime(end_datetime)
            
            # Create event object
            event = {
                'summary': title,
                'start': start,
                'end': end
            }
            
            if description:
                event['description'] = description
            
            if location:
                event['location'] = location
            
            # Parse attendees
            if attendees:
                attendee_list = []
                for email in attendees.split(','):
                    email = email.strip()
                    if email:
                        attendee_list.append({'email': email})
                if attendee_list:
                    event['attendees'] = attendee_list
            
            # Create the event
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            self.logger.info(f"Calendar event created successfully: {created_event.get('id')}")
            
            return ToolResult(
                success=True,
                data={
                    'event_id': created_event.get('id'),
                    'title': title,
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime,
                    'status': 'created',
                    'html_link': created_event.get('htmlLink'),
                    'attendees_count': len(attendees.split(',')) if attendees else 0
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error creating calendar event: {str(e)}"
            )


def register_calendar_tools():
    """Register all calendar tools with the global registry"""
    from services.tool_registry import tool_registry
    
    tools = [
        SearchCalendarEventsTool(),
        GetUpcomingEventsTool(),
        CreateCalendarEventTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)