"""
Hugging Face Inference Client Service
Handles text generation using Hugging Face's Inference API for intelligent request routing and responses.
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from huggingface_hub import InferenceClient
    HUGGINGFACE_AVAILABLE = True
except ImportError as e:
    HUGGINGFACE_AVAILABLE = False
    IMPORT_ERROR = str(e)


@dataclass
class LLMResponse:
    """Response from LLM service"""
    content: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class HuggingFaceInferenceService:
    """Hugging Face Inference API service"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Check if huggingface_hub is available
        if not HUGGINGFACE_AVAILABLE:
            self.logger.error(f"Hugging Face Hub not available: {IMPORT_ERROR}")
            self.client = None
            return
        
        # Get Hugging Face token from environment
        self.hf_token = os.getenv('HUGGINGFACE_TOKEN')
        if not self.hf_token:
            self.logger.warning("HUGGINGFACE_TOKEN not found in environment variables")
            self.logger.info("Will attempt to use public inference (with rate limits)")
        
        # Model configuration
        self.model_name = config.get('model_name', 'google/gemma-2-2b-it')
        
        # API settings
        api_config = config.get('api', {})
        self.timeout = api_config.get('timeout', 30)
        self.max_retries = api_config.get('max_retries', 3)
        self.retry_delay = api_config.get('retry_delay', 1)
        
        # Generation config
        self.generation_config = config.get('generation', {})
        
        # Initialize client
        try:
            self.client = InferenceClient(token=self.hf_token)
            self.logger.info(f"Initialized Hugging Face Inference client for model: {self.model_name}")
            if self.hf_token:
                self.logger.info("✅ Using authenticated API (higher rate limits)")
            else:
                self.logger.info("⚠️  Using public API (limited rate limits)")
        except Exception as e:
            self.logger.error(f"Failed to initialize Inference client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Inference client is available"""
        return HUGGINGFACE_AVAILABLE and self.client is not None
    
    def _format_prompt(self, user_prompt: str, system_prompt: str = None) -> str:
        """Format prompt for Gemma instruction-tuned model"""
        if system_prompt:
            return (
                f"<start_of_turn>system\n{system_prompt}<end_of_turn>\n"
                f"<start_of_turn>user\n{user_prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )
        else:
            return (
                f"<start_of_turn>user\n{user_prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """Generate text using Hugging Face Inference API"""
        
        if not HUGGINGFACE_AVAILABLE:
            return LLMResponse(
                content="",
                success=False,
                error="Hugging Face Hub not available"
            )
        
        if not self.is_available():
            return LLMResponse(
                content="",
                success=False,
                error="Inference client not initialized"
            )
        
        # Create messages for chat completion
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare generation parameters
        gen_params = self.generation_config.copy()
        if temperature is not None:
            gen_params['temperature'] = temperature
        if max_tokens is not None:
            gen_params['max_tokens'] = max_tokens
        
        # Remove parameters that might not be supported by the API
        supported_params = {
            'max_tokens': gen_params.get('max_tokens', gen_params.get('max_new_tokens', 1024)),
            'temperature': gen_params.get('temperature', 0.7),
            'top_p': gen_params.get('top_p', 0.9),
        }
        
        # Attempt generation with retries
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Generating text (attempt {attempt + 1}/{self.max_retries})")
                
                response = self.client.chat_completion(
                    model=self.model_name,
                    messages=messages,
                    **supported_params
                )
                
                # Extract content from response
                if hasattr(response, 'choices') and response.choices:
                    response_text = response.choices[0].message.content.strip()
                elif hasattr(response, 'generated_text'):
                    response_text = response.generated_text.strip()
                else:
                    # If response is a string, use it directly
                    response_text = str(response).strip()
                
                return LLMResponse(
                    content=response_text,
                    success=True,
                    tokens_used=len(response_text.split())  # Approximate token count
                )
                
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"Generation attempt {attempt + 1} failed: {error_msg}")
                
                # If this is a task support error, try fallback to text generation
                if "not supported for task" in error_msg.lower() and attempt == 0:
                    try:
                        # Fallback to text generation
                        formatted_prompt = self._format_prompt(prompt, system_prompt)
                        response = self.client.text_generation(
                            model=self.model_name,
                            prompt=formatted_prompt,
                            max_new_tokens=supported_params['max_tokens'],
                            temperature=supported_params['temperature']
                        )
                        
                        if isinstance(response, str):
                            response_text = response.strip()
                        else:
                            response_text = str(response).strip()
                        
                        return LLMResponse(
                            content=response_text,
                            success=True,
                            tokens_used=len(response_text.split())
                        )
                    except Exception as fallback_e:
                        self.logger.warning(f"Fallback to text_generation also failed: {fallback_e}")
                        error_msg = str(fallback_e)
                
                # Check for specific error types
                if "rate limit" in error_msg.lower():
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        self.logger.info(f"Rate limited, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                elif "model" in error_msg.lower() and "loading" in error_msg.lower():
                    if attempt < self.max_retries - 1:
                        wait_time = 10 * (attempt + 1)  # Model loading can take time
                        self.logger.info(f"Model loading, waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                # If it's the last attempt or an unrecoverable error, return failure
                if attempt == self.max_retries - 1:
                    return LLMResponse(
                        content="",
                        success=False,
                        error=f"Failed after {self.max_retries} attempts: {error_msg}"
                    )
                
                # Wait before next attempt
                time.sleep(self.retry_delay)
        
        return LLMResponse(
            content="",
            success=False,
            error="Maximum retries exceeded"
        )
    
    def generate_chat(self, messages: List[Dict[str, str]]) -> LLMResponse:
        """Generate response using chat completion format"""
        
        if not self.is_available():
            return LLMResponse(
                content="",
                success=False,
                error="Inference client not initialized"
            )
        
        try:
            # Try to use chat completion if available
            response = self.client.chat_completion(
                model=self.model_name,
                messages=messages,
                max_tokens=self.generation_config.get('max_new_tokens', 1024),
                temperature=self.generation_config.get('temperature', 0.7)
            )
            
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                response_text = response.choices[0].message.content.strip()
            else:
                response_text = str(response).strip()
            
            return LLMResponse(
                content=response_text,
                success=True,
                tokens_used=len(response_text.split())
            )
            
        except Exception as e:
            # Fallback to text generation if chat completion fails
            self.logger.debug(f"Chat completion failed: {e}, falling back to text generation")
            
            # Convert messages to simple prompt
            if messages:
                last_message = messages[-1]
                if last_message.get('role') == 'user':
                    return self.generate(last_message['content'])
            
            return LLMResponse(
                content="",
                success=False,
                error=f"Chat generation failed: {str(e)}"
            )
    
    # Keep the same method names for backward compatibility with existing code
    def route_user_request(self, user_request: str) -> LLMResponse:
        """Analyze user request and determine which agent to use"""
        
        prompt = f"""User request: "{user_request}"

Analyze this request and categorize it. Respond with ONLY one of these options:
- EMAIL: if the request is about emails, unread messages, inbox, senders, etc.
- CALENDAR: if the request is about meetings, schedule, appointments, events, calendar, today's agenda, etc.
- GENERAL: if the request is a general question, greeting, or not specifically about email/calendar

Respond with just the category word (EMAIL, CALENDAR, or GENERAL)."""
        
        system_prompt = "You are a request classifier. Analyze the user's intent and respond with the appropriate category."
        
        return self.generate(prompt, system_prompt, temperature=0.1)
    
    def analyze_emails_for_user(self, emails: List[Dict[str, Any]], user_request: str) -> LLMResponse:
        """Analyze emails based on user's natural language request"""
        
        if not emails:
            prompt = f"""User asked: "{user_request}"
            
There are currently no unread emails.

Respond to the user's request in the same language they used, letting them know there are no unread emails at this time."""
        else:
            # Build email summary context
            email_context = []
            for i, email in enumerate(emails[:15], 1):  # Limit to 15 emails to avoid API limits
                sender = email.get('sender', 'Unknown')
                subject = email.get('subject', 'No Subject')
                preview = email.get('preview', '')
                date = email.get('date', '')
                
                email_context.append(f"{i}. From: {sender}\n   Subject: {subject}\n   Date: {date}\n   Preview: {preview}\n")
            
            context = "\n".join(email_context)
            
            prompt = f"""User asked: "{user_request}"
            
Here are the {len(emails)} unread emails:
{context}

IMPORTANT: Respond in the EXACT same language as the user's question. 
If they asked in Portuguese, reply in Portuguese.
If they asked in English, reply in English.
If they asked in Spanish, reply in Spanish.

Analyze the emails and respond to the user's request. 
Provide helpful, organized information that directly addresses what they asked for.
Use clear formatting and be conversational yet informative."""

        system_prompt = "You are a helpful email assistant. ALWAYS respond in the same language the user used in their question. If they asked in Portuguese, you MUST reply in Portuguese. Be natural and focus on what the user actually asked for."
        
        return self.generate(prompt, system_prompt, temperature=0.6)
    
    def analyze_calendar_for_user(self, events: List[Dict[str, Any]], user_request: str) -> LLMResponse:
        """Analyze calendar events based on user's natural language request"""
        
        if not events:
            prompt = f"""User asked: "{user_request}"
            
There are no meetings or events scheduled for today.

Respond to the user's request in the same language they used, letting them know there are no meetings scheduled."""
        else:
            # Build calendar context
            event_context = []
            for i, event in enumerate(events, 1):
                title = event.get('title', 'No Title')
                start_time = event.get('start_time', '')
                end_time = event.get('end_time', '')
                start_date = event.get('start_date', '')
                attendees = event.get('attendees', [])
                location = event.get('location', '')
                
                # Format date and time together
                if start_date and start_time and start_time != 'All day':
                    datetime_str = f"{start_date} {start_time}"
                    if end_time:
                        datetime_str += f" - {end_time}"
                elif start_date and start_time == 'All day':
                    datetime_str = f"{start_date} (All day)"
                else:
                    datetime_str = f"{start_time} - {end_time}" if start_time and end_time else "Time unknown"
                
                event_str = f"{i}. {datetime_str}: {title}"
                if location:
                    event_str += f" (Location: {location})"
                if attendees:
                    event_str += f"\n   Attendees: {', '.join(attendees[:5])}"  # Limit attendee list
                    if len(attendees) > 5:
                        event_str += f" and {len(attendees) - 5} more"
                event_str += "\n"
                
                event_context.append(event_str)
            
            context = "\n".join(event_context)
            
            prompt = f"""User asked: "{user_request}"
            
Here are the calendar events:
{context}

IMPORTANT: Respond in the EXACT same language as the user's question. 
If they asked in Portuguese, reply in Portuguese.
If they asked in English, reply in English.
If they asked in Spanish, reply in Spanish.

IMPORTANT: If the user asked for a specific number of events (like "next 5 events", "próximos 5 eventos"), only show that exact number of events in chronological order, not all events found.

Analyze the calendar and respond to the user's request.
Provide helpful, organized information that directly addresses what they asked for.
Use clear formatting and be conversational yet informative."""

        system_prompt = "You are a helpful calendar assistant. ALWAYS respond in the same language the user used in their question. If they asked in Portuguese, you MUST reply in Portuguese. Be natural and focus on what the user actually asked for."
        
        return self.generate(prompt, system_prompt, temperature=0.6)
    
    def respond_to_general_request(self, user_request: str) -> LLMResponse:
        """Respond to general requests not related to email or calendar"""
        
        prompt = f"""User asked: "{user_request}"
        
This is a general request not specifically about emails or calendar.
Respond helpfully in the same language the user used.
Be conversational, friendly, and informative.
        
If they're asking about your capabilities, let them know you can help with:
- Checking and analyzing emails
- Reviewing calendar and meetings
- General questions and assistance"""
        
        system_prompt = "You are a helpful personal assistant. Respond naturally in the user's language and be conversational yet professional."
        
        return self.generate(prompt, system_prompt, temperature=0.7)
    
    def create_daily_summary_for_user(self, emails: List[Dict[str, Any]], events: List[Dict[str, Any]], user_language_hint: str = "") -> LLMResponse:
        """Create a unified daily summary in user's preferred language"""
        
        # Build context
        email_context = "No unread emails."
        if emails:
            email_list = []
            for email in emails[:8]:  # Limit for API efficiency
                sender = email.get('sender', 'Unknown')
                subject = email.get('subject', 'No Subject')
                email_list.append(f"- From: {sender}, Subject: {subject}")
            email_context = "\n".join(email_list)
        
        event_context = "No meetings scheduled for today."
        if events:
            event_list = []
            for event in events[:8]:  # Limit for API efficiency
                title = event.get('title', 'No Title')
                start_time = event.get('start_time', '')
                event_list.append(f"- {start_time}: {title}")
            event_context = "\n".join(event_list)
        
        language_instruction = ""
        if user_language_hint:
            language_instruction = f"Respond in the same language as this example: '{user_language_hint}'"
        else:
            language_instruction = "Respond in Portuguese (Portugal) as default, but adapt to user's language if context suggests otherwise."
        
        prompt = f"""Create a comprehensive daily briefing from this information:

EMAILS:
{email_context}

CALENDAR:
{event_context}

{language_instruction}

Provide a unified daily briefing that:
1. Highlights the most important items from both emails and calendar
2. Identifies any connections between emails and meetings  
3. Suggests priorities for the day
4. Notes any urgent items requiring immediate attention

Be conversational, organized, and helpful."""
        
        system_prompt = "You are a helpful personal assistant providing daily briefings. Be natural, organized, and focus on actionable insights."
        
        return self.generate(prompt, system_prompt, temperature=0.4)
    
    def analyze_calendar_query_with_context(self, user_request: str, temporal_context: dict) -> LLMResponse:
        """Analyze a calendar query with full temporal context and return structured data"""
        
        # Format temporal context for the LLM
        context_info = f"""CURRENT TEMPORAL CONTEXT:
- Current date/time: {temporal_context['current_datetime']}
- Current date: {temporal_context['current_date']}
- Current time: {temporal_context['current_time']}
- Today is: {temporal_context['current_weekday']}
- Current month: {temporal_context['current_month_year']}
- Tomorrow: {temporal_context['tomorrow']}
- Start of this week: {temporal_context['start_of_week']}
- End of this week: {temporal_context['end_of_week']}
- End of this month: {temporal_context['end_of_month']}
- Timezone: {temporal_context['timezone']}"""

        prompt = f"""{context_info}

User calendar query: "{user_request}"

Analyze this calendar query and return a JSON response with the following structure:

{{
  "query_type": "date_range" | "next_events" | "specific_date" | "today",
  "start_datetime": "ISO datetime or relative like 'now', 'today'",
  "end_datetime": "ISO datetime or relative like 'end_of_month', '+90days'",
  "event_limit": number (only if user asked for specific count like "next 5 events"),
  "time_context": "descriptive label like 'this_week', 'end_of_month', 'next_events'",
  "language": "pt" | "en" | "es" | "fr" (detected language),
  "needs_clarification": false (set to true only if query is genuinely ambiguous),
  "ambiguity_reason": "explanation if needs_clarification is true"
}}

IMPORTANT RULES:
1. For "next N events" queries, use "now" as start_datetime (current exact time) and "+90days" as end_datetime
2. For date range queries like "até fim do mês", use current datetime as start and actual end date
3. Always return valid JSON only, no additional text
4. If user asks for specific number of events, set event_limit to that number
5. If user asks for singular "next event" (próximo evento, next event), set event_limit to 1
6. Language detection should be accurate based on the query

EXAMPLES:
Query: "próximos 5 eventos"
Response: {{"query_type": "next_events", "start_datetime": "now", "end_datetime": "+90days", "event_limit": 5, "time_context": "next_events", "language": "pt"}}

Query: "qual o meu próximo evento?" (singular)
Response: {{"query_type": "next_events", "start_datetime": "now", "end_datetime": "+90days", "event_limit": 1, "time_context": "next_event", "language": "pt"}}

Query: "tenho algo até ao fim do mês?"
Response: {{"query_type": "date_range", "start_datetime": "now", "end_datetime": "end_of_month", "time_context": "end_of_month", "language": "pt"}}

Query: "what meetings do I have today?"
Response: {{"query_type": "today", "start_datetime": "today", "end_datetime": "today", "time_context": "today", "language": "en"}}

Query: "what's my next meeting?" (singular)
Response: {{"query_type": "next_events", "start_datetime": "now", "end_datetime": "+90days", "event_limit": 1, "time_context": "next_event", "language": "en"}}"""

        system_prompt = "You are a calendar query analyzer. Return only valid JSON with the exact structure requested. Be precise with datetime handling and language detection."
        
        return self.generate(prompt, system_prompt, temperature=0.1)


# For backward compatibility, create an alias
HuggingFaceLLMService = HuggingFaceInferenceService