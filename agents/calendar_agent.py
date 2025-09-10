"""
Calendar Agent
Simplified Calendar agent for the new bot architecture.
"""

import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from googleapiclient.errors import HttpError
    from services.google_auth import GoogleAuthManager
except ImportError:
    GoogleAuthManager = None
    HttpError = Exception


class CalendarAgent:
    """Simplified Calendar agent for chat responses"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        # Initialize auth manager if available
        if GoogleAuthManager:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/calendar.readonly'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    def _get_service(self):
        """Get Calendar service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_calendar_service()
            except Exception as e:
                self.logger.error(f"Could not get Calendar service: {e}")
        return self._service
    
    async def get_today_events(self, max_results: int = 20) -> Dict[str, Any]:
        """Get today's calendar events (async wrapper)"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._fetch_today_events_sync,
            max_results
        )
    
    def _fetch_today_events_sync(self, max_results: int = 20) -> Dict[str, Any]:
        """Fetch today's calendar events synchronously"""
        result = {
            'success': False,
            'events': [],
            'count': 0,
            'error': None
        }
        
        try:
            service = self._get_service()
            
            if not service:
                result['error'] = "Calendar service not available. Please check authentication."
                return result
            
            # Define time range (today)
            now = datetime.now()
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Convert to RFC3339 format
            time_min = start_of_day.isoformat() + 'Z'
            time_max = end_of_day.isoformat() + 'Z'
            
            self.logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Call the Calendar API
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} events for today")
            
            if not events:
                result['success'] = True
                return result
            
            # Process events
            processed_events = []
            for event in events:
                processed_event = self._process_event(event)
                if processed_event:
                    processed_events.append(processed_event)
            
            result['events'] = processed_events
            result['count'] = len(processed_events)
            result['success'] = True
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching calendar events: {str(e)}"
            self.logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a calendar event into a simplified format"""
        try:
            # Extract basic info
            event_data = {
                'id': event.get('id', ''),
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_time': '',
                'end_time': '',
                'start_date': '',
                'end_date': '',
                'attendees': [],
                'is_all_day': False,
                'meeting_url': ''
            }
            
            # Parse start/end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            if 'dateTime' in start:
                # Timed event
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                event_data['start_time'] = start_dt.strftime('%H:%M')
                event_data['end_time'] = end_dt.strftime('%H:%M')
                event_data['start_date'] = start_dt.strftime('%Y-%m-%d')
                event_data['end_date'] = end_dt.strftime('%Y-%m-%d')
            elif 'date' in start:
                # All-day event
                event_data['is_all_day'] = True
                event_data['start_time'] = 'All day'
                event_data['end_time'] = 'All day'
                # Parse date for all-day events
                try:
                    start_date = datetime.fromisoformat(start['date'])
                    event_data['start_date'] = start_date.strftime('%Y-%m-%d')
                    if 'date' in end:
                        end_date = datetime.fromisoformat(end['date'])
                        event_data['end_date'] = end_date.strftime('%Y-%m-%d')
                    else:
                        event_data['end_date'] = event_data['start_date']
                except:
                    event_data['start_date'] = 'Unknown'
                    event_data['end_date'] = 'Unknown'
            
            # Extract attendees
            attendees = event.get('attendees', [])
            for attendee in attendees[:10]:  # Limit to 10 attendees
                email = attendee.get('email', '')
                name = attendee.get('displayName', email.split('@')[0] if email else 'Unknown')
                event_data['attendees'].append(name)
            
            # Look for meeting URLs in description or location
            description = event_data['description'].lower()
            location = event_data['location'].lower()
            
            if any(url_hint in description for url_hint in ['meet.google.com', 'zoom.us', 'teams.microsoft.com']):
                event_data['meeting_url'] = 'Virtual meeting (check description)'
            elif any(url_hint in location for url_hint in ['meet.google.com', 'zoom.us', 'teams.microsoft.com']):
                event_data['meeting_url'] = 'Virtual meeting (check location)'
            
            return event_data
            
        except Exception as e:
            self.logger.warning(f"Error processing event {event.get('id', 'unknown')}: {e}")
            return None
    
    async def get_events_by_timeframe(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Get events for the next N hours (async wrapper)"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._fetch_events_by_timeframe_sync,
            hours_ahead
        )
    
    def _fetch_events_by_timeframe_sync(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Fetch events for the next N hours synchronously"""
        result = {
            'success': False,
            'events': [],
            'count': 0,
            'error': None
        }
        
        try:
            service = self._get_service()
            
            if not service:
                result['error'] = "Calendar service not available. Please check authentication."
                return result
            
            # Define time range
            now = datetime.now()
            future = now + timedelta(hours=hours_ahead)
            
            # Convert to RFC3339 format
            time_min = now.isoformat() + 'Z'
            time_max = future.isoformat() + 'Z'
            
            self.logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Call the Calendar API
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} events in the next {hours_ahead} hours")
            
            # Process events
            processed_events = []
            for event in events:
                processed_event = self._process_event(event)
                if processed_event:
                    processed_events.append(processed_event)
            
            result['events'] = processed_events
            result['count'] = len(processed_events)
            result['success'] = True
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching calendar events: {str(e)}"
            self.logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def is_available(self) -> bool:
        """Check if Calendar service is available"""
        try:
            service = self._get_service()
            return service is not None
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Calendar agent status"""
        result = {
            'available': False,
            'authenticated': False,
            'error': None
        }
        
        try:
            if not self._auth_manager:
                result['error'] = "Google Auth Manager not available"
                return result
            
            service = self._get_service()
            if service:
                # Test with a simple API call
                calendar_list = service.calendarList().list(maxResults=1).execute()
                result['available'] = True
                result['authenticated'] = True
                calendars = calendar_list.get('items', [])
                if calendars:
                    result['primary_calendar'] = calendars[0].get('summary', 'Unknown')
            else:
                result['error'] = "Could not create Calendar service"
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def get_events_by_date_range(self, start_date: datetime = None, end_date: datetime = None, max_results: int = 50) -> Dict[str, Any]:
        """Get events for a custom date range (async wrapper)"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._fetch_events_by_date_range_sync,
            start_date,
            end_date,
            max_results
        )
    
    def _fetch_events_by_date_range_sync(self, start_date: datetime = None, end_date: datetime = None, max_results: int = 50) -> Dict[str, Any]:
        """Fetch events for a custom date range synchronously"""
        result = {
            'success': False,
            'events': [],
            'count': 0,
            'error': None
        }
        
        try:
            service = self._get_service()
            
            if not service:
                result['error'] = "Calendar service not available. Please check authentication."
                return result
            
            # Use defaults if not provided
            if start_date is None:
                start_date = datetime.now()
            if end_date is None:
                end_date = datetime.now() + timedelta(days=7)  # Default to one week
            
            # Convert to RFC3339 format
            time_min = start_date.isoformat() + 'Z'
            time_max = end_date.isoformat() + 'Z'
            
            self.logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Call the Calendar API
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} events in date range")
            
            # Process events and filter future events from current time
            processed_events = []
            now = datetime.now()
            self.logger.info(f"Current time for filtering: {now}")
            
            for event in events:
                try:
                    event_data = self._process_event(event)
                    if event_data:
                        event_title = event_data.get('title', 'Unknown')
                        event_start_str = event_data.get('start_time', '')
                        event_start = self._parse_event_datetime(event_start_str)
                        
                        self.logger.info(f"Event: '{event_title}' at '{event_start_str}' -> parsed as {event_start}")
                        
                        # Only include events that start after current time
                        if event_start and event_start > now:
                            self.logger.info(f"✅ Including future event: '{event_title}' at {event_start}")
                            processed_events.append(event_data)
                        elif not event_start:
                            # If we can't parse the time, include it (all-day events, etc.)
                            self.logger.info(f"✅ Including unparseable/all-day event: '{event_title}'")
                            processed_events.append(event_data)
                        else:
                            self.logger.info(f"❌ Skipping past event: '{event_title}' at {event_start} (before {now})")
                except Exception as e:
                    self.logger.warning(f"Failed to process event: {e}")
                    continue
            
            # Sort processed events by start time to ensure chronological order
            processed_events.sort(key=lambda event: self._parse_event_datetime(event.get('start_time', '')) or datetime.max)
            
            self.logger.info(f"After sorting, first few events: {[(e.get('title'), e.get('start_time')) for e in processed_events[:3]]}")
            
            result['events'] = processed_events
            result['count'] = len(processed_events)
            result['success'] = True
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching events by date range: {str(e)}"
            self.logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _parse_event_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse event time string to datetime object"""
        if not time_str or time_str in ['All Day', '']:
            return None
            
        try:
            # Try parsing common formats
            for fmt in [
                '%H:%M',       # "14:30"
                '%H:%M:%S',    # "14:30:00"
                '%Y-%m-%d %H:%M:%S',  # "2025-09-10 14:30:00"
                '%Y-%m-%dT%H:%M:%S',  # ISO format
                '%Y-%m-%dT%H:%M:%SZ'  # ISO with Z
            ]:
                try:
                    if fmt.startswith('%H'):
                        # For time-only formats, assume today's date
                        time_part = datetime.strptime(time_str, fmt).time()
                        return datetime.combine(datetime.now().date(), time_part)
                    else:
                        return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
                    
            # Try ISO format parsing
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
        except Exception as e:
            self.logger.debug(f"Could not parse event time '{time_str}': {e}")
            return None