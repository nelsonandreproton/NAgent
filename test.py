#!/usr/bin/env python3
"""
NAgent Test Interface
Simple command-line interface to test the bot without Telegram.

Usage: python test.py "your question here"
Example: python test.py "do I have any unread emails?"
"""

import sys
import asyncio
from dotenv import load_dotenv
from bot import NAgentBot

# Load environment variables
load_dotenv()


async def test_request(request: str):
    """Test a single request"""
    
    print(f"🤖 Processing: '{request}'")
    print("-" * 50)
    
    # Initialize bot
    bot = NAgentBot()
    
    # Check Inference client status
    if bot.llm.is_available():
        print("✅ Hugging Face Inference Client Ready")
    else:
        print("❌ Hugging Face client not available")
        print("   Make sure HUGGINGFACE_TOKEN is set in your .env file")
        print("   Continuing with limited functionality...")
    
    print(f"API Ready: {'✅' if bot.llm.is_available() else '⚠️'}")
    
    try:
        # Process request
        response = await bot.process_request(request)
        
        print(f"\n📝 Response (Agent: {response.agent_used or 'unknown'}):")
        print(response.content)
        
        if not response.success and response.error:
            print(f"\n⚠️  Error: {response.error}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_daily_summary():
    """Test daily summary generation"""
    
    print("🌅 Generating Daily Summary...")
    print("-" * 50)
    
    bot = NAgentBot()
    
    # Check Inference client
    if not bot.llm.is_available():
        print("❌ Hugging Face client not available")
        print("   Make sure HUGGINGFACE_TOKEN is set in your .env file")
        print("   Continuing with limited functionality...")
    
    try:
        response = await bot.create_daily_summary()
        
        print("📋 Daily Summary:")
        print(response.content)
        
        if not response.success and response.error:
            print(f"\n⚠️  Error: {response.error}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def show_help():
    """Show help message"""
    print("""
🤖 NAgent Test Interface

Usage:
  python test.py "your question"     - Ask a specific question
  python test.py summary            - Generate daily summary
  python test.py help               - Show this help

Examples:
  python test.py "do I have any unread emails?"
  python test.py "what meetings do I have today?"
  python test.py "what's my schedule like?"
  python test.py "hello, how are you?"
  python test.py summary

The bot will automatically detect if your question is about:
- EMAIL: questions about emails, inbox, messages
- CALENDAR: questions about meetings, schedule, appointments
- GENERAL: general questions or greetings
""")


async def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("❌ Please provide a request to test.")
        show_help()
        return
    
    request = sys.argv[1]
    
    if request.lower() in ['help', '--help', '-h']:
        show_help()
        return
    elif request.lower() == 'summary':
        await test_daily_summary()
    else:
        await test_request(request)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test stopped.")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")