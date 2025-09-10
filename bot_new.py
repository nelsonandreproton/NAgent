"""
NAgent - LLM-Driven Personal Assistant Bot
Minimal code - LLM makes ALL decisions about tool usage and responses.
"""

import os
import logging
import asyncio
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.llm_service import HuggingFaceInferenceService
from services.llm_orchestrator import LLMOrchestrator
from services.telegram_service import TelegramService, TelegramBotPoller
from config.settings import load_config


@dataclass
class BotResponse:
    """Simple response container"""
    content: str
    success: bool
    error: str = None


class NAgentBot:
    """Minimal LLM-driven bot - orchestrator does everything"""
    
    def __init__(self):
        self.config = load_config()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/bot.log') if not os.path.exists('logs') or os.makedirs('logs', exist_ok=True) else logging.FileHandler('logs/bot.log')
            ]
        )
        
        # Initialize LLM service
        self.llm = HuggingFaceInferenceService(self.config.get('llm', {}))
        
        # Register all available tools
        self._register_tools()
        
        # Initialize orchestrator - this is where the magic happens
        self.orchestrator = LLMOrchestrator(self.llm)
        
        # Initialize Telegram if needed
        self.telegram = TelegramService()
        
        self.logger.info("NAgent Bot initialized with LLM orchestration")
    
    def _register_tools(self):
        """Register all available tools"""
        try:
            # Import and register email tools
            from tools.email_tools import register_email_tools
            register_email_tools()
            
            # Import and register calendar tools  
            from tools.calendar_tools import register_calendar_tools
            register_calendar_tools()
            
            # Log available tools
            from services.tool_registry import tool_registry
            tool_names = list(tool_registry.tools.keys())
            self.logger.info(f"Registered tools: {tool_names}")
            
        except Exception as e:
            self.logger.error(f"Error registering tools: {e}")
            raise
    
    async def process_request(self, user_request: str, user_language: str = "pt") -> BotResponse:
        """
        Process any user request - LLM orchestrator handles everything
        
        This is the ONLY method needed! The orchestrator:
        - Understands user intent
        - Selects appropriate tools
        - Executes tools with right parameters
        - Formats natural response
        """
        try:
            self.logger.info(f"Processing request: {user_request}")
            
            # Let orchestrator handle everything
            response_content = await self.orchestrator.process_request(user_request, user_language)
            
            return BotResponse(
                content=response_content,
                success=True
            )
            
        except Exception as e:
            error_msg = f"Error processing request: {str(e)}"
            self.logger.error(error_msg)
            
            # Return error in appropriate language
            if user_language.startswith('pt'):
                error_response = f"Desculpe, encontrei um problema ao processar seu pedido."
            else:
                error_response = f"I apologize, but I encountered an issue processing your request."
            
            return BotResponse(
                content=error_response,
                success=False,
                error=error_msg
            )
    
    async def create_daily_summary(self) -> BotResponse:
        """Create daily summary by asking orchestrator"""
        summary_request = "Create a daily summary with my unread emails and upcoming events for today"
        return await self.process_request(summary_request, "pt")
    
    async def run_telegram_bot(self):
        """Run the Telegram bot"""
        try:
            if not self.telegram.is_configured():
                self.logger.error("Telegram not configured properly. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
                return
            
            # Test connection first
            connection_test = self.telegram.test_connection()
            if not connection_test['success']:
                self.logger.error(f"Telegram connection failed: {connection_test['error']}")
                return
            
            self.logger.info(f"Telegram bot connected: @{connection_test['bot_info'].get('username')}")
            
            async def handle_message(text: str, chat_id: str, user_id: str):
                """Handle incoming Telegram message"""
                try:
                    self.logger.info(f"Processing message from {user_id}: {text}")
                    
                    # Process request using orchestrator
                    response = await self.process_request(text, "pt")
                    
                    # Send response back
                    self.logger.info(f"Sending response to chat {chat_id}: {len(response.content)} characters")
                    send_success = await self.telegram.send_message_async(response.content, chat_id)
                    self.logger.info(f"Message send result: {send_success}")
                    
                except Exception as e:
                    self.logger.error(f"Error handling Telegram message: {e}")
                    # Send error message to user
                    await self.telegram.send_message_async(
                        "Desculpe, ocorreu um erro ao processar sua mensagem.",
                        chat_id
                    )
            
            # Create poller with proper parameters
            poller = TelegramBotPoller(self.telegram, handle_message)
            self.logger.info("Starting Telegram bot polling...")
            
            # Start polling
            await poller.start_polling()
            
        except Exception as e:
            self.logger.error(f"Error in Telegram bot: {e}")
    
    def check_system_status(self) -> dict:
        """Check system status"""
        from services.tool_registry import tool_registry
        
        return {
            'llm_model': self.config.get('llm', {}).get('model_name', 'Unknown'),
            'available_tools': list(tool_registry.tools.keys()),
            'orchestrator_ready': self.orchestrator is not None,
            'telegram_configured': bool(os.getenv('TELEGRAM_BOT_TOKEN'))
        }


async def main():
    """Main entry point for CLI testing"""
    bot = NAgentBot()
    
    print("🤖 NAgent Bot Ready!")
    print("Available commands:")
    print("- Any natural language request")
    print("- 'status' - Check system status")
    print("- 'quit' - Exit")
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == 'status':
                status = bot.check_system_status()
                print(f"Status: {status}")
                continue
            
            if not user_input:
                continue
            
            # Process request
            print("🤖 Processing...")
            response = await bot.process_request(user_input, "pt")
            
            print(f"Bot: {response.content}")
            if not response.success and response.error:
                print(f"Error: {response.error}")
            
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "telegram":
        # Run Telegram bot
        bot = NAgentBot()
        try:
            asyncio.run(bot.run_telegram_bot())
        except KeyboardInterrupt:
            print("\n👋 Telegram bot stopped")
    else:
        # Run CLI mode
        asyncio.run(main())