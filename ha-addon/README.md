# NAgent Bot - Home Assistant Add-on

LLM-Driven Personal Assistant Bot with Gmail and Calendar integration for Home Assistant.

## Installation

1. Copy this entire `ha-addon` folder to `/addons/local/nagent_bot/` in your Home Assistant
2. Refresh add-ons in HA: Settings > Add-ons > ⋮ > Reload
3. Install "NAgent Bot" from Local add-ons
4. Configure with your tokens
5. Start the add-on

## Configuration

Required settings:
- `telegram_bot_token`: Your Telegram bot token
- `telegram_chat_id`: Your chat ID  
- `huggingface_token`: Your Hugging Face token
- `google_credentials_base64`: Your Google credentials (base64 encoded)

## Usage

Send messages to your Telegram bot:
- "Do I have any unread emails?"
- "What's my schedule today?"
- "Hello!"