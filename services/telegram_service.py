"""
Telegram Service
Handles Telegram bot interactions including sending/receiving messages.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
import requests
import json
from datetime import datetime


class TelegramService:
    """Service for Telegram bot communication"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.logger = logging.getLogger(__name__)
        
        # Base API URL
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"
    
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_id)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Telegram bot connection"""
        result = {
            'success': False,
            'bot_info': {},
            'chat_accessible': False,
            'error': None
        }
        
        if not self.is_configured():
            result['error'] = "Bot token or chat ID not configured"
            return result
        
        try:
            # Test bot token
            response = requests.get(f"{self.api_base}/getMe", timeout=10)
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
            
            # Test chat access
            test_message = "🤖 Bot connection test - ignore this message"
            test_result = self.send_message(test_message)
            result['chat_accessible'] = test_result
            result['success'] = test_result
            
            if not test_result:
                result['error'] = f"Cannot access chat {self.chat_id}"
                
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Telegram connection test failed: {e}")
        
        return result
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Send a message to Telegram chat"""
        if not self.is_configured():
            self.logger.error("Telegram not configured")
            return False
            
        try:
            response = requests.post(
                f"{self.api_base}/sendMessage",
                json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': True
                },
                timeout=30
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
    
    def get_updates(self, offset: int = 0, timeout: int = 30) -> List[Dict]:
        """Get updates from Telegram"""
        if not self.is_configured():
            return []
            
        try:
            response = requests.get(
                f"{self.api_base}/getUpdates",
                params={
                    'offset': offset,
                    'timeout': timeout
                },
                timeout=timeout + 5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('result', [])
            else:
                self.logger.error(f"Failed to get updates: {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error getting Telegram updates: {e}")
            return []
    
    def send_typing_action(self, chat_id: str = None) -> bool:
        """Send typing action to show bot is processing"""
        if not self.is_configured():
            return False
            
        target_chat = chat_id or self.chat_id
        
        try:
            response = requests.post(
                f"{self.api_base}/sendChatAction",
                json={
                    'chat_id': target_chat,
                    'action': 'typing'
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error sending typing action: {e}")
            return False
    
    def send_response_to_chat(self, chat_id: str, message: str) -> bool:
        """Send response to a specific chat"""
        if not self.is_configured():
            return False
            
        try:
            response = requests.post(
                f"{self.api_base}/sendMessage",
                json={
                    'chat_id': chat_id,
                    'text': message,
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True
                },
                timeout=30
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Error sending response to chat {chat_id}: {e}")
            return False
    
    async def send_message_async(self, message: str, chat_id: str = None, parse_mode: str = 'HTML') -> bool:
        """Async version of send_message"""
        # For now, just call the sync version in an executor
        # In a production app, you'd use aiohttp
        return await asyncio.get_event_loop().run_in_executor(
            None, 
            self.send_response_to_chat if chat_id else self.send_message,
            chat_id or message if chat_id else message
        )
    
    def format_message_for_telegram(self, content: str, title: str = None, emoji: str = "🤖") -> str:
        """Format message for Telegram with proper HTML"""
        
        # Escape HTML special characters in content
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # But allow basic formatting
        content = content.replace('**', '<b>', 1).replace('**', '</b>', 1)  # Bold
        content = content.replace('*', '<i>', 1).replace('*', '</i>', 1)    # Italic
        
        if title:
            message = f"{emoji} <b>{title}</b>\n\n{content}"
        else:
            message = f"{emoji} {content}"
        
        # Ensure message isn't too long for Telegram (4096 char limit)
        if len(message) > 4000:
            message = message[:3900] + "\n\n<i>... (mensagem truncada)</i>"
        
        return message
    
    def send_error_notification(self, error_message: str, chat_id: str = None) -> bool:
        """Send error notification"""
        formatted_message = self.format_message_for_telegram(
            error_message, 
            "Erro", 
            "❌"
        )
        
        if chat_id:
            return self.send_response_to_chat(chat_id, formatted_message)
        else:
            return self.send_message(formatted_message)


class TelegramBotPoller:
    """Handles Telegram bot polling and message processing"""
    
    def __init__(self, telegram_service: TelegramService, message_handler):
        self.telegram_service = telegram_service
        self.message_handler = message_handler
        self.logger = logging.getLogger(__name__)
        self.last_update_id = 0
        self.running = False
    
    async def start_polling(self):
        """Start polling for Telegram messages"""
        if not self.telegram_service.is_configured():
            self.logger.error("Cannot start polling: Telegram not configured")
            return
        
        self.running = True
        self.logger.info("Starting Telegram bot polling...")
        
        while self.running:
            try:
                # Get updates from Telegram
                updates = self.telegram_service.get_updates(
                    offset=self.last_update_id + 1,
                    timeout=30
                )
                
                for update in updates:
                    await self._process_update(update)
                    self.last_update_id = update['update_id']
                
                # Small delay to avoid overwhelming the API
                if not updates:
                    await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error in polling loop: {str(e)}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _process_update(self, update: Dict):
        """Process a single update from Telegram"""
        try:
            if 'message' in update and 'text' in update['message']:
                message = update['message']
                user_id = str(message['from']['id'])
                chat_id = str(message['chat']['id'])
                text = message['text']
                
                self.logger.info(f"Received message from {user_id}: {text}")
                
                # Send typing indicator
                self.telegram_service.send_typing_action(chat_id)
                
                # Process the message
                if self.message_handler:
                    await self.message_handler(text, chat_id, user_id)
        
        except Exception as e:
            self.logger.error(f"Error processing update: {str(e)}")
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.running = False
        self.logger.info("Stopping Telegram bot polling...")


# Convenience functions for the new bot architecture
def init_telegram_from_env() -> TelegramService:
    """Initialize Telegram service from environment variables"""
    return TelegramService()


def send_telegram_message(message: str) -> bool:
    """Quick function to send a message to Telegram"""
    telegram = init_telegram_from_env()
    if telegram.is_configured():
        return telegram.send_message(message)
    return False