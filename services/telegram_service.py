"""
Telegram Service
Handles sending messages and notifications to Telegram via bot API.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import telegram
from telegram.error import TelegramError
import requests
from datetime import datetime

from services.translations import TranslationService


class TelegramService:
    """Service for sending messages via Telegram bot"""
    
    def __init__(self, bot_token: str, chat_id: str, language: str = "pt-pt"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.language = language
        self.logger = logging.getLogger(__name__)
        self._bot = None
        
        # Initialize translation service
        self.translator = TranslationService(language)
    
    def _get_bot(self):
        """Get Telegram bot instance"""
        if not self._bot:
            self._bot = telegram.Bot(token=self.bot_token)
        return self._bot
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Telegram bot connection"""
        result = {
            'success': False,
            'bot_info': {},
            'chat_accessible': False,
            'error': None
        }
        
        try:
            # Test bot token
            bot = self._get_bot()
            
            # Use requests for synchronous call to avoid asyncio issues
            response = requests.get(f"https://api.telegram.org/bot{self.bot_token}/getMe")
            if response.status_code == 200:
                bot_info = response.json()['result']
                result['bot_info'] = {
                    'username': bot_info.get('username'),
                    'first_name': bot_info.get('first_name'),
                    'id': bot_info.get('id')
                }
                self.logger.info(f"Bot connected: @{bot_info.get('username')}")
            else:
                result['error'] = f"Invalid bot token: {response.text}"
                return result
            
            # Test chat access by sending a test message
            test_response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': f'🤖 {self.translator.get("test_connection")}',
                    'parse_mode': 'HTML'
                }
            )
            
            if test_response.status_code == 200:
                result['chat_accessible'] = True
                result['success'] = True
                self.logger.info(f"Test message sent to chat {self.chat_id}")
            else:
                error_data = test_response.json()
                result['error'] = f"Cannot access chat {self.chat_id}: {error_data.get('description', 'Unknown error')}"
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Telegram connection test failed: {e}")
        
        return result
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to Telegram chat"""
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': True
                }
            )
            
            if response.status_code == 200:
                self.logger.info("Message sent successfully to Telegram")
                return True
            else:
                error_data = response.json()
                self.logger.error(f"Failed to send Telegram message: {error_data.get('description')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Send formatted daily summary to Telegram"""
        try:
            # Create formatted message
            message = self._format_summary_message(summary_data)
            
            # Send message
            success = self.send_message(message)
            
            if success:
                self.logger.info("Daily summary sent to Telegram")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending daily summary to Telegram: {e}")
            return False
    
    def _format_summary_message(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data into Telegram message"""
        timestamp = summary_data.get('timestamp', '')
        date = summary_data.get('date', '')
        
        # Parse timestamp for proper formatting
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = self.translator.format_time(dt)
        except:
            time_str = timestamp.split('T')[1][:5] if 'T' in timestamp else ''
        
        # Get statistics
        stats = summary_data.get('statistics', {})
        email_stats = stats.get('email', {})
        calendar_stats = stats.get('calendar', {})
        
        # Format header
        lines = [
            f"🤖 <b>{self.translator.get('daily_summary_title')}</b>",
            f"📅 <i>{date}</i>",
            ""
        ]
        
        # Email statistics
        total_emails = email_stats.get('total_unread', 0)
        recent_emails = email_stats.get('recent_count', 0)
        
        if total_emails > 0:
            lines.extend([
                f"📧 <b>{self.translator.get('unread_emails')}:</b> {total_emails}",
                f"📩 <b>{self.translator.get('recent_emails')}:</b> {recent_emails}",
                ""
            ])
        
        # Calendar statistics  
        total_events = calendar_stats.get('total_events', 0)
        virtual_meetings = calendar_stats.get('virtual_meetings', 0)
        duration_hours = round(calendar_stats.get('total_duration_minutes', 0) / 60, 1)
        
        if total_events > 0:
            lines.extend([
                f"📅 <b>{self.translator.get('meetings_today')}:</b> {total_events}",
                f"💻 <b>{self.translator.get('virtual_meetings')}:</b> {virtual_meetings}",
                f"⏰ <b>{self.translator.get('total_duration')}:</b> {duration_hours}{self.translator.get('hours')}",
                ""
            ])
        
        # Add unified summary (truncated for Telegram)
        unified_summary = summary_data.get('unified_summary', '')
        if unified_summary:
            # Limit message length for Telegram (4096 chars max)
            if len(unified_summary) > 2000:
                unified_summary = unified_summary[:2000] + "..."
            
            lines.extend([
                f"<b>{self.translator.get('unified_summary_title')}:</b>",
                f"<pre>{unified_summary}</pre>",
                ""
            ])
        
        # Add errors if any
        errors = summary_data.get('errors', [])
        if errors:
            lines.extend([
                f"⚠️ <b>{self.translator.get('warnings')}:</b>",
                f"<i>{'; '.join(errors[:2])}</i>",  # Limit to 2 errors
                ""
            ])
        
        # Footer
        lines.append(f"<i>{self.translator.get('generated_at')} {time_str}</i>")
        
        return '\n'.join(lines)
    
    def send_notification(self, title: str, message: str, emoji: str = "🔔") -> bool:
        """Send a simple notification to Telegram"""
        formatted_message = f"{emoji} <b>{title}</b>\n\n{message}"
        return self.send_message(formatted_message)
    
    def send_error_notification(self, error_message: str) -> bool:
        """Send error notification to Telegram"""
        message = f"❌ <b>{self.translator.get('error_notification_title')}</b>\n\n<pre>{error_message}</pre>"
        return self.send_message(message)
    
    def send_status_update(self, status_data: Dict[str, Any]) -> bool:
        """Send system status update to Telegram"""
        lines = [
            f"🔍 <b>{self.translator.get('system_status_title')}</b>",
            ""
        ]
        
        # Check each component
        components = {
            'ollama': 'Ollama LLM',
            'gmail': 'Gmail API', 
            'calendar': 'Calendar API',
            'telegram': 'Telegram Bot'
        }
        
        for key, name in components.items():
            if key in status_data:
                component_status = status_data[key]
                is_working = (component_status.get('success', False) or 
                             component_status.get('accessible', False) or 
                             component_status.get('available', False) or
                             component_status.get('authenticated', False))
                
                if is_working:
                    lines.append(f"✅ <b>{name}:</b> OK")
                else:
                    error = component_status.get('error', 'Erro desconhecido')
                    lines.append(f"❌ <b>{name}:</b> {error}")
        
        # Parse timestamp
        timestamp = status_data.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = self.translator.format_time(dt)
        except:
            time_str = timestamp
        
        lines.append(f"\n<i>{self.translator.get('connection_test')}: {time_str}</i>")
        
        message = '\n'.join(lines)
        return self.send_message(message)


class TelegramNotifier:
    """Simple wrapper for common Telegram notifications"""
    
    def __init__(self, telegram_service: TelegramService):
        self.telegram_service = telegram_service
        self.logger = logging.getLogger(__name__)
    
    def notify_summary_generated(self, summary_data: Dict[str, Any]) -> bool:
        """Notify that daily summary was generated"""
        return self.telegram_service.send_daily_summary(summary_data)
    
    def notify_system_error(self, error: str) -> bool:
        """Notify about system errors"""
        return self.telegram_service.send_error_notification(error)
    
    def notify_scheduled_run_started(self) -> bool:
        """Notify that scheduled run started"""
        return self.telegram_service.send_notification(
            self.telegram_service.translator.get("scheduled_run_started"),
            self.telegram_service.translator.get("scheduled_run_started_msg"),
            "⏰"
        )
    
    def notify_scheduled_run_completed(self) -> bool:
        """Notify that scheduled run completed"""
        return self.telegram_service.send_notification(
            self.telegram_service.translator.get("scheduled_run_completed"),
            self.telegram_service.translator.get("scheduled_run_completed_msg"),
            "✅"
        )
    
    def notify_system_status(self, status_data: Dict[str, Any]) -> bool:
        """Notify about system status"""
        return self.telegram_service.send_status_update(status_data)