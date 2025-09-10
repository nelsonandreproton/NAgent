"""
NAgent - Intelligent Personal Assistant Bot
Routes user requests to appropriate agents using LLM intelligence.
"""

import os
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.llm_service import HuggingFaceInferenceService, LLMResponse
from services.telegram_service import TelegramService, TelegramBotPoller
from services.calendar_query_analyzer import CalendarQueryAnalyzer
from agents.gmail_agent import GmailAgent
from agents.calendar_agent import CalendarAgent
from config.settings import load_config


@dataclass
class BotResponse:
    """Response from the bot"""
    content: str
    success: bool
    error: Optional[str] = None
    agent_used: Optional[str] = None


class NAgentBot:
    """Intelligent personal assistant that routes requests to appropriate agents"""
    
    def __init__(self):
        self.config = load_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.llm = HuggingFaceInferenceService(self.config.get('llm', {}))
        
        self.telegram = TelegramService()
        
        # Initialize query analyzer
        self.calendar_query_analyzer = CalendarQueryAnalyzer(self.llm)
        
        # Initialize agents
        self.gmail_agent = GmailAgent()
        self.calendar_agent = CalendarAgent()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def process_request(self, user_request: str, user_id: str = None) -> BotResponse:
        """Process a user request intelligently"""
        
        try:
            # Check if LLM client is available
            if not self.llm.is_available():
                return BotResponse(
                    content="Sorry, I'm currently unavailable. Please check your Hugging Face token and try again later.",
                    success=False,
                    error="Inference client not available"
                )
            
            # Route the request using LLM
            routing_response = self.llm.route_user_request(user_request)
            
            if not routing_response.success:
                return BotResponse(
                    content="Sorry, I couldn't understand your request. Please try again.",
                    success=False,
                    error=routing_response.error
                )
            
            route = routing_response.content.strip().upper()
            self.logger.info(f"Request '{user_request}' routed to: {route}")
            
            # Handle based on route
            if route == "EMAIL":
                return await self._handle_email_request(user_request)
            elif route == "CALENDAR":
                return await self._handle_calendar_request(user_request)
            else:  # GENERAL
                return await self._handle_general_request(user_request)
                
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return BotResponse(
                content="Sorry, something went wrong. Please try again.",
                success=False,
                error=str(e)
            )
    
    async def _handle_email_request(self, user_request: str) -> BotResponse:
        """Handle email-related requests"""
        
        try:
            # Get emails from Gmail agent
            emails_result = await self.gmail_agent.get_unread_emails()
            
            if not emails_result['success']:
                # If Gmail fails, let LLM respond about the error
                general_response = self.llm.respond_to_general_request(
                    f"User asked about emails: '{user_request}', but there was an error accessing Gmail: {emails_result['error']}"
                )
                return BotResponse(
                    content=general_response.content if general_response.success else "Sorry, I can't access your emails right now.",
                    success=True,
                    agent_used="gmail",
                    error=emails_result['error']
                )
            
            # Let LLM analyze emails and respond
            analysis_response = self.llm.analyze_emails_for_user(emails_result['emails'], user_request)
            
            return BotResponse(
                content=analysis_response.content if analysis_response.success else "I couldn't analyze your emails right now.",
                success=analysis_response.success,
                agent_used="gmail",
                error=analysis_response.error
            )
            
        except Exception as e:
            self.logger.error(f"Error handling email request: {str(e)}")
            return BotResponse(
                content="Sorry, I had trouble accessing your emails.",
                success=False,
                agent_used="gmail",
                error=str(e)
            )
    
    async def _handle_calendar_request(self, user_request: str) -> BotResponse:
        """Handle calendar-related requests using intelligent query analysis"""
        
        try:
            # Use LLM to analyze the query and extract structured information
            calendar_query = self.calendar_query_analyzer.analyze_query(
                user_request, 
                user_timezone="Europe/Lisbon"  # TODO: Make this configurable per user
            )
            
            self.logger.info(f"Parsed calendar query: {calendar_query.query_type}, "
                           f"start: {calendar_query.start_datetime}, "
                           f"end: {calendar_query.end_datetime}, "
                           f"limit: {calendar_query.event_limit}")
            
            # Get events based on the analyzed query
            if calendar_query.query_type == "today":
                events_result = await self.calendar_agent.get_today_events()
            elif calendar_query.start_datetime and calendar_query.end_datetime:
                events_result = await self.calendar_agent.get_events_by_date_range(
                    calendar_query.start_datetime,
                    calendar_query.end_datetime
                )
            else:
                # Fallback to today's events
                events_result = await self.calendar_agent.get_today_events()
            
            if not events_result['success']:
                # If Calendar fails, let LLM respond about the error
                general_response = self.llm.respond_to_general_request(
                    f"User asked about calendar: '{user_request}', but there was an error accessing Calendar: {events_result['error']}"
                )
                return BotResponse(
                    content=general_response.content if general_response.success else "Sorry, I can't access your calendar right now.",
                    success=True,
                    agent_used="calendar",
                    error=events_result['error']
                )
            
            # Filter events if user asked for specific number (e.g., "next 5 events")
            events_to_analyze = events_result['events']
            if calendar_query.event_limit and len(events_to_analyze) > calendar_query.event_limit:
                events_to_analyze = events_to_analyze[:calendar_query.event_limit]
                self.logger.info(f"Limited events to {calendar_query.event_limit} as requested")
            
            # Let LLM analyze calendar and respond
            analysis_response = self.llm.analyze_calendar_for_user(events_to_analyze, user_request)
            
            return BotResponse(
                content=analysis_response.content if analysis_response.success else "I couldn't analyze your calendar right now.",
                success=analysis_response.success,
                agent_used="calendar",
                error=analysis_response.error
            )
            
        except Exception as e:
            self.logger.error(f"Error handling calendar request: {str(e)}")
            return BotResponse(
                content="Sorry, I had trouble accessing your calendar.",
                success=False,
                agent_used="calendar",
                error=str(e)
            )
    
    async def _handle_general_request(self, user_request: str) -> BotResponse:
        """Handle general requests"""
        
        try:
            # Let LLM respond to general request
            response = self.llm.respond_to_general_request(user_request)
            
            return BotResponse(
                content=response.content if response.success else "I'm not sure how to help with that.",
                success=response.success,
                agent_used="general",
                error=response.error
            )
            
        except Exception as e:
            self.logger.error(f"Error handling general request: {str(e)}")
            return BotResponse(
                content="Sorry, I had trouble understanding your request.",
                success=False,
                agent_used="general",
                error=str(e)
            )
    
    
    async def create_daily_summary(self, user_language_hint: str = "") -> BotResponse:
        """Create a comprehensive daily summary"""
        
        try:
            # Get data from both agents
            emails_result = await self.gmail_agent.get_unread_emails()
            events_result = await self.calendar_agent.get_today_events()
            
            emails = emails_result['emails'] if emails_result['success'] else []
            events = events_result['events'] if events_result['success'] else []
            
            # Create summary using LLM
            summary_response = self.llm.create_daily_summary_for_user(emails, events, user_language_hint)
            
            return BotResponse(
                content=summary_response.content if summary_response.success else "I couldn't create your daily summary right now.",
                success=summary_response.success,
                agent_used="daily_summary",
                error=summary_response.error
            )
            
        except Exception as e:
            self.logger.error(f"Error creating daily summary: {str(e)}")
            return BotResponse(
                content="Sorry, I couldn't create your daily summary.",
                success=False,
                agent_used="daily_summary", 
                error=str(e)
            )
    
    async def handle_telegram_message(self, text: str, chat_id: str, user_id: str):
        """Handle incoming Telegram message"""
        try:
            # Process the user request
            response = await self.process_request(text, user_id)
            
            # Format response for Telegram
            formatted_message = self.telegram.format_message_for_telegram(response.content)
            
            # Send response back to Telegram
            success = self.telegram.send_response_to_chat(chat_id, formatted_message)
            
            if not success:
                # Fallback: send simple error message
                self.telegram.send_response_to_chat(chat_id, "❌ Desculpe, ocorreu um erro. Tente novamente.")
                
        except Exception as e:
            self.logger.error(f"Error handling Telegram message: {str(e)}")
            self.telegram.send_error_notification(str(e), chat_id)
    
    async def start_telegram_bot(self):
        """Start the Telegram bot"""
        
        self.logger.info("Starting NAgent Telegram Bot...")
        
        if not self.telegram.is_configured():
            self.logger.error("Telegram not configured. Please check .env file.")
            return
        
        # Create and start the poller
        poller = TelegramBotPoller(self.telegram, self.handle_telegram_message)
        await poller.start_polling()


# Main function for running the bot
async def main():
    """Main entry point"""
    bot = NAgentBot()
    
    # Check services status
    print("🤖 NAgent Starting...")
    print(f"✅ Telegram Configured: {bot.telegram.is_configured()}")
    
    # Check Inference client
    if bot.llm.is_available():
        print("✅ Hugging Face Inference Client Ready")
    else:
        print("⚠️  Hugging Face client not available")
        print("   Make sure HUGGINGFACE_TOKEN is set in your .env file")
        print("   You can still use the bot with limited functionality")
    
    # Start the bot
    await bot.start_telegram_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 NAgent Bot stopped.")