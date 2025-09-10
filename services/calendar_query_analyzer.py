"""
Calendar Query Analyzer
Uses LLM to understand natural language calendar queries and convert them to structured data.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass
from functools import lru_cache

try:
    import pytz
except ImportError:
    pytz = None


@dataclass
class CalendarQuery:
    """Structured representation of a calendar query"""
    query_type: str  # "date_range", "next_events", "specific_date", "today"
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    event_limit: Optional[int] = None
    time_context: str = ""  # "today", "this_week", "end_of_month", "next_events"
    language: str = "en"
    original_query: str = ""
    needs_clarification: bool = False
    ambiguity_reason: str = ""


class CalendarQueryAnalyzer:
    """Analyzes natural language calendar queries using LLM with temporal context"""
    
    def __init__(self, llm_service):
        self.llm = llm_service
        self.logger = logging.getLogger(__name__)
        
    def analyze_query(self, user_request: str, user_timezone: str = "UTC") -> CalendarQuery:
        """Analyze a user's calendar query and return structured information"""
        try:
            # Generate temporal context with precise current time
            context = self._generate_temporal_context(user_timezone)
            
            # Call LLM with context and query
            llm_response = self.llm.analyze_calendar_query_with_context(user_request, context)
            
            if not llm_response.success:
                self.logger.warning(f"LLM query analysis failed: {llm_response.error}")
                return self._fallback_to_default(user_request)
            
            # Parse LLM response
            query = self._parse_llm_response(llm_response.content, user_request, context)
            
            # Validate and apply safety checks
            return self._validate_and_sanitize(query, context)
            
        except Exception as e:
            self.logger.error(f"Error analyzing calendar query: {e}")
            return self._fallback_to_default(user_request)
    
    def _generate_temporal_context(self, timezone: str = "UTC") -> Dict[str, Any]:
        """Generate comprehensive temporal context for the LLM"""
        if pytz and timezone != "UTC":
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except:
                now = datetime.now()
        else:
            now = datetime.now()
        
        # Calculate common date boundaries
        start_of_week = now - timedelta(days=now.weekday())
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        if now.month == 12:
            end_of_month = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_of_month = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        end_of_month = end_of_month.replace(hour=23, minute=59, second=59)
        
        tomorrow = now + timedelta(days=1)
        
        return {
            "current_datetime": now.isoformat(),
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M:%S"),
            "current_weekday": now.strftime("%A"),
            "current_month_year": now.strftime("%B %Y"),
            "today": now.strftime("%Y-%m-%d"),
            "tomorrow": tomorrow.strftime("%Y-%m-%d"),
            "start_of_week": start_of_week.strftime("%Y-%m-%d"),
            "end_of_week": end_of_week.strftime("%Y-%m-%d"),
            "end_of_month": end_of_month.strftime("%Y-%m-%d"),
            "timezone": timezone,
            "iso_week_number": now.isocalendar()[1],
            "_datetime_obj": now  # Keep for internal use
        }
    
    def _parse_llm_response(self, llm_content: str, original_query: str, context: Dict[str, Any]) -> CalendarQuery:
        """Parse LLM response into CalendarQuery object"""
        try:
            # Try to extract JSON from LLM response
            response_data = self._extract_json_from_response(llm_content)
            
            if not response_data:
                self.logger.warning("No valid JSON found in LLM response")
                return self._fallback_to_default(original_query)
            
            # Parse datetime strings
            start_datetime = self._parse_datetime_from_response(
                response_data.get("start_datetime") or response_data.get("start_date"),
                context
            )
            end_datetime = self._parse_datetime_from_response(
                response_data.get("end_datetime") or response_data.get("end_date"),
                context
            )
            
            return CalendarQuery(
                query_type=response_data.get("query_type", "today"),
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                event_limit=response_data.get("event_limit"),
                time_context=response_data.get("time_context", ""),
                language=response_data.get("language", "en"),
                original_query=original_query,
                needs_clarification=response_data.get("needs_clarification", False),
                ambiguity_reason=response_data.get("ambiguity_reason", "")
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return self._fallback_to_default(original_query)
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response, handling various formats"""
        # Try direct JSON parsing first
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON within the response
        import re
        json_matches = re.findall(r'\{[^}]+\}', content, re.DOTALL)
        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
                
        return None
    
    def _parse_datetime_from_response(self, date_str: str, context: Dict[str, Any]) -> Optional[datetime]:
        """Parse datetime from LLM response, handling relative and absolute dates"""
        if not date_str:
            return None
            
        date_str = date_str.strip().lower()
        now = context["_datetime_obj"]
        
        # Handle relative dates
        if date_str == "now":
            return now
        elif date_str == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str == "tomorrow":
            return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str == "end_of_month":
            end_month_str = context["end_of_month"]
            return datetime.fromisoformat(end_month_str + "T23:59:59")
        elif date_str == "end_of_week":
            end_week_str = context["end_of_week"]
            return datetime.fromisoformat(end_week_str + "T23:59:59")
        elif date_str.startswith("+"):
            # Handle "+90days", "+1week" etc
            try:
                if "day" in date_str:
                    days = int(date_str.replace("+", "").replace("days", "").replace("day", ""))
                    return now + timedelta(days=days)
                elif "week" in date_str:
                    weeks = int(date_str.replace("+", "").replace("weeks", "").replace("week", ""))
                    return now + timedelta(weeks=weeks)
            except ValueError:
                pass
        
        # Handle absolute dates (ISO format)
        try:
            if "T" in date_str:
                return datetime.fromisoformat(date_str)
            else:
                # Just a date, assume start of day
                return datetime.fromisoformat(date_str + "T00:00:00")
        except ValueError:
            pass
            
        return None
    
    def _validate_and_sanitize(self, query: CalendarQuery, context: Dict[str, Any]) -> CalendarQuery:
        """Validate and apply safety checks to the parsed query"""
        now = context["_datetime_obj"]
        
        # Set defaults for missing start/end times
        if query.query_type == "next_events" and not query.start_datetime:
            query.start_datetime = now  # Start from current exact time
            
        if query.query_type == "next_events" and not query.end_datetime:
            # For "next events", search far enough to find events
            query.end_datetime = now + timedelta(days=90)
            
        if query.query_type == "today" and not query.start_datetime:
            query.start_datetime = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query.end_datetime = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Ensure start is before end
        if query.start_datetime and query.end_datetime:
            if query.start_datetime > query.end_datetime:
                query.start_datetime, query.end_datetime = query.end_datetime, query.start_datetime
        
        # Set reasonable event limits
        if query.event_limit and query.event_limit > 50:
            query.event_limit = 50  # Safety limit
            
        return query
    
    def _fallback_to_default(self, original_query: str) -> CalendarQuery:
        """Fallback to default query when LLM analysis fails"""
        now = datetime.now()
        return CalendarQuery(
            query_type="today",
            start_datetime=now.replace(hour=0, minute=0, second=0, microsecond=0),
            end_datetime=now.replace(hour=23, minute=59, second=59, microsecond=999999),
            time_context="today",
            language="pt",  # Default to Portuguese
            original_query=original_query
        )