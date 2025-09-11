#!/usr/bin/env python3
"""
NAgent Bot - Main entry point for Pella hosting
Simplified entry point for cloud deployment
"""

import asyncio
import logging
import os
from bot_new import NAgentBot

# Setup basic logging for Pella
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Main entry point for NAgent bot"""
    try:
        # Initialize bot
        bot = NAgentBot()
        
        # Start Telegram bot
        await bot.run_telegram_bot()
        
    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())