"""
Calendar Agent
Handles fetching and processing calendar events from Google Calendar API.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from googleapiclient.errors import HttpError

from services.google_auth import GoogleAuthManager
from services.llm_service import OllamaService


class CalendarAgent:
    """Agent for Calendar operations and event summarization"""
    
    def __init__(self, auth_manager: GoogleAuthManager, llm_service: OllamaService, config: Dict[str, Any]):
        self.auth_manager = auth_manager
        self.llm_service = llm_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._service = None
    
    def _get_service(self):
        """Get Calendar service instance"""
        if not self._service:
            self._service = self.auth_manager.get_calendar_service()
        return self._service
    
    def fetch_today_events(self) -> List[Dict[str, Any]]:
        """Fetch calendar events for today"""
        return self.fetch_events_for_date(datetime.now().date())
    
    def fetch_events_for_date(self, target_date: datetime.date) -> List[Dict[str, Any]]:
        """Fetch calendar events for a specific date"""
        try:
            service = self._get_service()
            
            # Set time range for the target date
            start_time = datetime.combine(target_date, datetime.min.time())
            end_time = start_time + timedelta(days=1)
            
            # Convert to RFC3339 format
            time_min = start_time.isoformat() + 'Z'
            time_max = end_time.isoformat() + 'Z'
            
            self.logger.info(f"Fetching events from {time_min} to {time_max}")
            
            # Get events from the calendar
            events_result = service.events().list(
                calendarId=self.config.get('calendar_id', 'primary'),
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            self.logger.info(f"Found {len(events)} events for {target_date}")
            
            if not events:
                return []
            
            # Process events
            processed_events = []
            for event in events:
                try:
                    event_data = self._process_event(event)
                    if event_data and self._should_include_event(event_data):
                        processed_events.append(event_data)
                except Exception as e:
                    self.logger.warning(f"Failed to process event {event.get('id', 'unknown')}: {e}")
                    continue
            
            return processed_events
            
        except HttpError as e:
            self.logger.error(f"Calendar API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching events: {e}")
            return []
    
    def _process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a raw calendar event into structured data"""
        try:
            # Extract basic information
            event_data = {
                'id': event.get('id'),
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'status': event.get('status', 'confirmed'),
                'is_all_day': False,
                'start_time': '',
                'end_time': '',
                'duration_minutes': 0,
                'attendees': [],
                'organizer': '',
                'created': event.get('created', ''),
                'updated': event.get('updated', ''),
                'html_link': event.get('htmlLink', '')
            }
            
            # Process start and end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            if 'date' in start:  # All-day event
                event_data['is_all_day'] = True
                event_data['start_time'] = start['date']
                event_data['end_time'] = end.get('date', start['date'])
                event_data['duration_minutes'] = 1440  # Full day
            else:  # Timed event
                start_dt = self._parse_datetime(start.get('dateTime', ''))
                end_dt = self._parse_datetime(end.get('dateTime', ''))
                
                if start_dt and end_dt:
                    event_data['start_time'] = start_dt.strftime('%H:%M')
                    event_data['end_time'] = end_dt.strftime('%H:%M')
                    event_data['duration_minutes'] = int((end_dt - start_dt).total_seconds() / 60)
                    event_data['start_datetime'] = start_dt
                    event_data['end_datetime'] = end_dt
            
            # Process attendees
            attendees = event.get('attendees', [])
            for attendee in attendees:
                email = attendee.get('email', '')
                display_name = attendee.get('displayName', email)
                status = attendee.get('responseStatus', 'needsAction')
                
                event_data['attendees'].append({
                    'email': email,
                    'name': display_name,
                    'status': status,
                    'optional': attendee.get('optional', False)
                })
            
            # Process organizer
            organizer = event.get('organizer', {})
            event_data['organizer'] = organizer.get('displayName', organizer.get('email', ''))
            
            # Determine meeting type
            event_data['meeting_type'] = self._determine_meeting_type(event_data)
            
            return event_data
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return None
    
    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string from Google Calendar API"""
        if not datetime_str:
            return None
        
        try:
            # Remove timezone info for simplicity
            datetime_str = datetime_str.split('+')[0].split('-')[0].rstrip('Z')
            return datetime.fromisoformat(datetime_str.replace('T', ' '))
        except Exception as e:
            self.logger.warning(f"Failed to parse datetime {datetime_str}: {e}")
            return None
    
    def _determine_meeting_type(self, event_data: Dict[str, Any]) -> str:
        """Determine the type of meeting based on event data"""
        title = event_data.get('title', '').lower()
        description = event_data.get('description', '').lower()
        location = event_data.get('location', '').lower()
        
        # Check for virtual meeting indicators
        virtual_indicators = ['zoom', 'meet', 'teams', 'webex', 'skype', 'virtual', 'online', 'video']
        if any(indicator in title or indicator in description or indicator in location for indicator in virtual_indicators):
            return 'virtual'
        
        # Check for in-person indicators
        if location and not any(virtual in location for virtual in virtual_indicators):
            return 'in-person'
        
        # Check for common meeting types
        if any(word in title for word in ['standup', 'daily', 'scrum']):
            return 'standup'
        elif any(word in title for word in ['1:1', 'one-on-one', '1-on-1']):
            return 'one-on-one'
        elif any(word in title for word in ['interview', 'candidate']):
            return 'interview'
        elif any(word in title for word in ['all-hands', 'company', 'town hall']):
            return 'company-wide'
        
        return 'meeting'
    
    def _should_include_event(self, event_data: Dict[str, Any]) -> bool:
        """Determine if an event should be included in the summary"""
        # Skip cancelled events
        if event_data.get('status') == 'cancelled':
            return False
        
        # Check minimum duration
        min_duration = self.config.get('min_duration_minutes', 5)
        if event_data.get('duration_minutes', 0) < min_duration:
            return False
        
        # Check if all-day events should be included
        if event_data.get('is_all_day') and not self.config.get('include_all_day', True):
            return False
        
        return True
    
    def generate_calendar_summary(self, events: List[Dict[str, Any]], detail_level: str = "medium") -> str:
        """Generate summary of calendar events using LLM"""
        if not events:
            return "No meetings scheduled for today."
        
        try:
            # Sort events by start time
            events_sorted = sorted(events, key=lambda x: x.get('start_datetime', datetime.min))
            
            self.logger.info(f"Generating summary for {len(events_sorted)} events with detail level: {detail_level}")
            
            # Use LLM service to generate summary
            response = self.llm_service.summarize_calendar(events_sorted, detail_level)
            
            if response.success:
                return response.content
            else:
                self.logger.error(f"LLM summarization failed: {response.error}")
                return self._create_fallback_summary(events_sorted)
                
        except Exception as e:
            self.logger.error(f"Error generating calendar summary: {e}")
            return self._create_fallback_summary(events)
    
    def _create_fallback_summary(self, events: List[Dict[str, Any]]) -> str:
        """Create a simple summary without LLM"""
        if not events:
            return "No meetings scheduled for today."
        
        summary_parts = [f"You have {len(events)} meeting{'s' if len(events) > 1 else ''} today:"]
        
        # Group events by time periods
        morning_events = []
        afternoon_events = []
        evening_events = []
        all_day_events = []
        
        for event in events:
            if event.get('is_all_day'):
                all_day_events.append(event)
            else:
                start_time = event.get('start_datetime')
                if start_time:
                    hour = start_time.hour
                    if hour < 12:
                        morning_events.append(event)
                    elif hour < 17:
                        afternoon_events.append(event)
                    else:
                        evening_events.append(event)
        
        # Add all-day events first
        if all_day_events:
            summary_parts.append("\nAll-day events:")
            for event in all_day_events:
                summary_parts.append(f"  • {event.get('title')}")
        
        # Add timed events by period
        for period_name, period_events in [
            ("Morning", morning_events),
            ("Afternoon", afternoon_events), 
            ("Evening", evening_events)
        ]:
            if period_events:
                summary_parts.append(f"\n{period_name}:")
                for event in period_events:
                    title = event.get('title')
                    start_time = event.get('start_time')
                    end_time = event.get('end_time')
                    duration = event.get('duration_minutes', 0)
                    
                    event_line = f"  • {start_time}-{end_time}: {title}"
                    if duration >= 60:
                        hours = duration // 60
                        minutes = duration % 60
                        if minutes > 0:
                            event_line += f" ({hours}h {minutes}m)"
                        else:
                            event_line += f" ({hours}h)"
                    elif duration > 0:
                        event_line += f" ({duration}m)"
                    
                    summary_parts.append(event_line)
        
        # Add statistics
        virtual_count = sum(1 for e in events if e.get('meeting_type') == 'virtual')
        in_person_count = sum(1 for e in events if e.get('meeting_type') == 'in-person')
        
        if virtual_count > 0 or in_person_count > 0:
            summary_parts.append(f"\nMeeting breakdown: {virtual_count} virtual, {in_person_count} in-person")
        
        return '\n'.join(summary_parts)
    
    def get_calendar_statistics(self) -> Dict[str, Any]:
        """Get statistics about calendar events"""
        try:
            events = self.fetch_today_events()
            
            stats = {
                'total_events': len(events),
                'virtual_meetings': 0,
                'in_person_meetings': 0,
                'all_day_events': 0,
                'total_duration_minutes': 0,
                'meeting_types': {},
                'busiest_hour': None
            }
            
            hour_counts = {}
            
            for event in events:
                # Count by meeting type
                meeting_type = event.get('meeting_type', 'unknown')
                stats['meeting_types'][meeting_type] = stats['meeting_types'].get(meeting_type, 0) + 1
                
                if meeting_type == 'virtual':
                    stats['virtual_meetings'] += 1
                elif meeting_type == 'in-person':
                    stats['in_person_meetings'] += 1
                
                # Count all-day events
                if event.get('is_all_day'):
                    stats['all_day_events'] += 1
                else:
                    # Add to total duration
                    stats['total_duration_minutes'] += event.get('duration_minutes', 0)
                    
                    # Count events per hour
                    start_dt = event.get('start_datetime')
                    if start_dt:
                        hour = start_dt.hour
                        hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Find busiest hour
            if hour_counts:
                busiest_hour = max(hour_counts.items(), key=lambda x: x[1])
                stats['busiest_hour'] = f"{busiest_hour[0]:02d}:00 ({busiest_hour[1]} events)"
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting calendar statistics: {e}")
            return {
                'total_events': 0,
                'virtual_meetings': 0,
                'in_person_meetings': 0,
                'all_day_events': 0,
                'total_duration_minutes': 0,
                'meeting_types': {},
                'busiest_hour': None
            }