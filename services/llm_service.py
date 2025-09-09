"""
Ollama LLM Service Client
Handles communication with local Ollama instance for text summarization.
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM service"""
    content: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class OllamaService:
    """Client for Ollama LLM API"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "gemma2:2b"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.logger = logging.getLogger(__name__)
        
    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate text using Ollama API"""
        
        if not self.is_available():
            return LLMResponse(
                content="",
                success=False,
                error="Ollama service is not available"
            )
        
        # Prepare the request payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    success=True,
                    tokens_used=data.get("eval_count", 0)
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.logger.error(f"Ollama API error: {error_msg}")
                return LLMResponse(
                    content="",
                    success=False,
                    error=error_msg
                )
                
        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            self.logger.error(f"Ollama request error: {error_msg}")
            return LLMResponse(
                content="",
                success=False,
                error=error_msg
            )
    
    def summarize_emails(self, emails: List[Dict[str, Any]], detail_level: str = "medium", language: str = "pt-pt") -> LLMResponse:
        """Summarize a list of emails with language and format instructions"""
        
        if not emails:
            return LLMResponse(
                content=self._get_no_emails_message(language),
                success=True
            )
        
        # Build email summary context
        email_context = []
        for i, email in enumerate(emails[:20], 1):  # Limit to 20 emails to avoid token limits
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No Subject')
            preview = email.get('preview', '')
            
            email_context.append(f"{i}. From: {sender}\n   Subject: {subject}\n   Preview: {preview}\n")
        
        context = "\n".join(email_context)
        
        # Get language instructions
        lang_instructions = self._get_language_instructions(language)
        
        # Adjust prompt based on detail level
        if detail_level == "brief":
            prompt = f"""Analyze and summarize these unread emails in 2-3 sentences.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

Provide a brief overview of the key topics and urgent items. Focus on what requires immediate attention."""

        elif detail_level == "detailed":
            prompt = f"""Provide a detailed analysis and summary of these unread emails.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

For each important email or group of emails, mention:
1. Sender and subject
2. Key points or actions needed
3. Priority level (high/medium/low)
4. Group related emails by topic when possible
5. Suggest next actions if applicable"""

        else:  # medium
            prompt = f"""Analyze and summarize these unread emails with organized insights.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

Organize your summary by:
- Important/urgent items that need immediate attention
- Meeting invitations or calendar-related items
- General updates and notifications
- Action items or follow-ups required

Be informative but concise. Highlight what matters most for productivity."""

        system_prompt = f"You are an intelligent email assistant. Analyze emails and provide organized summaries in the requested language and format. Be contextually aware and focus on actionable insights."
        
        return self.generate(prompt, system_prompt, temperature=0.5)
    
    def summarize_calendar(self, events: List[Dict[str, Any]], detail_level: str = "medium", language: str = "pt-pt") -> LLMResponse:
        """Summarize calendar events with language and format instructions"""
        
        if not events:
            return LLMResponse(
                content=self._get_no_meetings_message(language),
                success=True
            )
        
        # Build calendar context
        event_context = []
        for i, event in enumerate(events, 1):
            title = event.get('title', 'No Title')
            start_time = event.get('start_time', '')
            end_time = event.get('end_time', '')
            attendees = event.get('attendees', [])
            location = event.get('location', '')
            
            event_str = f"{i}. {start_time} - {end_time}: {title}"
            if location:
                event_str += f" (Location: {location})"
            if attendees:
                event_str += f"\n   Attendees: {', '.join(attendees[:5])}"  # Limit attendee list
                if len(attendees) > 5:
                    event_str += f" and {len(attendees) - 5} more"
            event_str += "\n"
            
            event_context.append(event_str)
        
        context = "\n".join(event_context)
        
        # Get language instructions
        lang_instructions = self._get_language_instructions(language)
        
        # Adjust prompt based on detail level
        if detail_level == "brief":
            prompt = f"""Analyze and summarize today's calendar schedule in 2-3 sentences.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

Provide a concise overview mentioning the number of meetings and key appointments."""

        elif detail_level == "detailed":
            prompt = f"""Provide a comprehensive analysis of today's calendar schedule.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

For each meeting or group of meetings, include:
1. Time and duration analysis
2. Meeting titles and inferred purposes
3. Key attendees and their roles (if apparent)
4. Location details and meeting types (in-person/virtual)
5. Preparation recommendations or scheduling insights
6. Potential conflicts or optimization suggestions"""

        else:  # medium
            prompt = f"""Analyze and organize today's calendar schedule with practical insights.

{context}

LANGUAGE & FORMAT REQUIREMENTS:
{lang_instructions}

Structure your analysis by:
- Time periods (morning, afternoon, evening) with key meetings
- Meeting importance levels and types (internal vs external)
- Scheduling patterns, conflicts, or back-to-back meetings
- Virtual vs in-person meeting distribution
- Overall day structure and productivity recommendations

Be practical and focus on helping optimize the day."""

        system_prompt = f"You are an intelligent calendar assistant. Analyze schedules and provide organized summaries with actionable insights in the requested language and format."
        
        return self.generate(prompt, system_prompt, temperature=0.5)
    
    def create_daily_summary(self, email_summary: str, calendar_summary: str) -> LLMResponse:
        """Create a unified daily summary from email and calendar summaries"""
        
        prompt = f"""Create a comprehensive daily briefing from these summaries:

EMAIL SUMMARY:
{email_summary}

CALENDAR SUMMARY:
{calendar_summary}

Provide a unified daily briefing that:
1. Highlights the most important items from both emails and calendar
2. Identifies any connections between emails and meetings
3. Suggests priorities for the day
4. Notes any urgent items requiring immediate attention

Format the response as a professional daily briefing."""
        
        system_prompt = "You are an executive assistant providing a daily briefing. Be professional, concise, and actionable."
        
        return self.generate(prompt, system_prompt, temperature=0.3)