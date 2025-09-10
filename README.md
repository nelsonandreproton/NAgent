# NAgent - LLM-Driven Personal Assistant

A **minimal, intelligent** personal assistant bot that uses **Qwen2.5-7B-Instruct** to understand natural language and intelligently select tools for email and calendar management.

## 🧠 Revolutionary LLM-Driven Architecture

**True AI Intelligence**: The bot uses minimal code - the LLM makes **ALL decisions** about:
- 🎯 **Tool Selection**: Understands user intent and picks the right tool
- 🔧 **Parameter Extraction**: Automatically extracts parameters from natural language  
- 💬 **Response Formatting**: Generates natural Portuguese responses

## ✨ Key Features

- **🤖 LLM-Driven Intelligence**: Qwen2.5-7B-Instruct model makes all decisions
- **🇵🇹 Portuguese Native**: Superior Portuguese understanding and responses
- **📱 Telegram Integration**: Real-time chat interface 
- **📧 Gmail Integration**: Search, list, create emails intelligently
- **📅 Calendar Integration**: Manage events with natural language
- **⚡ Minimal Code**: 80% less code than traditional bot architectures
- **🛠️ Tool Ecosystem**: 7 intelligent tools for comprehensive assistance

## 🏗️ Architecture

```
User Input (Portuguese) 
    ↓
🧠 LLM Orchestrator (Qwen2.5-7B-Instruct)
    ↓ (Intelligent Decision Making)
🔧 Tool Registry (Dynamic Discovery)
    ↓ (Smart Tool Selection)
┌─────────────┬─────────────────┬─────────────┐
│ Email Tools │ Calendar Tools  │ Utility Tools│
└─────────────┴─────────────────┴─────────────┘
    ↓
📊 Natural Language Response
```

**The LLM does ALL the thinking** - no hardcoded routing logic!

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Hugging Face account and token (free)
- Google API credentials (for Gmail/Calendar access)
- Telegram bot token (for Telegram interface)

### 2. Install Dependencies

```bash
# Install dependencies (much lighter now!)
pip install -r requirements.txt

# Verify installation
python -c "from huggingface_hub import InferenceClient; print('✅ Hugging Face Hub ready')"
```

### 3. Get Hugging Face Token

```bash
# 1. Go to https://huggingface.co/settings/tokens
# 2. Create a new token (read access is sufficient)
# 3. Copy your token (starts with hf_...)
```

**Note**: Without this token, you'll see authentication errors. The token is required for cloud AI processing.

### 4. Configure Environment

Create `.env` file:
```bash
# Hugging Face Token (required for AI processing)
HUGGINGFACE_TOKEN=hf_your_token_here

# Telegram Bot Configuration (required for Telegram interface)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Google API Credentials Path
GOOGLE_CREDENTIALS_PATH=credentials/credentials.json
```

### 5. Configure API Settings (Optional)

Edit `config/config.yaml` for advanced configuration:

```yaml
llm:
  model_name: "google/gemma-2-2b-it"
  
  # API settings
  api:
    timeout: 30
    max_retries: 3
    retry_delay: 1
  
  # Generation settings
  generation:
    max_new_tokens: 1024
    temperature: 0.7
    top_p: 0.9
```

### 6. Test the Bot (Recommended: Safe Startup)

**Safe startup script (prevents conflicts):**
```bash
# Telegram bot (recommended)
python start_bot.py telegram

# CLI mode for testing
python start_bot.py cli
```

**Alternative direct startup:**
```bash
# Telegram mode
python bot_new.py telegram

# CLI mode  
python bot_new.py
```

**Test with CLI commands:**
```bash
# Test the orchestrator intelligence
python test_orchestrator.py
```

## ⚙️ Configuration Options

### API Configuration

**Default setup (recommended):**
```yaml
llm:
  model_name: "google/gemma-2-2b-it"
  api:
    timeout: 30
    max_retries: 3
```

**High-throughput setup:**
```yaml
llm:
  model_name: "google/gemma-2-2b-it"
  api:
    timeout: 60      # Longer timeout for complex requests
    max_retries: 5   # More retries for reliability
    retry_delay: 2   # Longer delay between retries
```

**Fast response setup:**
```yaml
llm:
  model_name: "google/gemma-2-2b-it"
  api:
    timeout: 15      # Shorter timeout for quick responses
    max_retries: 1   # Fewer retries for speed
  generation:
    max_new_tokens: 512  # Shorter responses
    temperature: 0.5     # More deterministic
```

## 💬 Usage Examples

### Email Questions
- "Do I have any unread emails?"
- "What emails did I receive today?"
- "Show me the most important emails"
- "Any urgent messages?"

### Calendar Questions  
- "What meetings do I have today?"
- "What's my schedule like?"
- "Do I have any conflicts today?"
- "What's next on my calendar?"

### General Questions
- "Hello!" 
- "What can you help me with?"
- "How are you?"
- "What are your capabilities?"

### Multi-language Support
The bot automatically detects and responds in your language:
- "Tenho emails por ler?" (Portuguese)
- "¿Tengo reuniones hoy?" (Spanish)  
- "Ai-je des réunions aujourd'hui ?" (French)

## 🔧 Configuration

Edit `config/config.yaml` to customize:

```yaml
# NAgent Bot Configuration
bot:
  mode: "telegram"          # telegram or cli
  auto_daily_summary: false

# Hugging Face LLM Configuration
llm:
  model_name: "google/gemma-2-2b-it"
  device: "auto"           # auto, cpu, cuda, mps
  cache_dir: "models/"
  
# Agent Configuration
agents:
  gmail:
    max_results: 20
    max_age_hours: 24
  calendar:
    max_results: 20
```

## 📁 Project Structure

```
NAgent/
├── bot.py                 # Main bot orchestrator
├── test.py               # CLI testing interface
├── config/
│   ├── config.yaml       # Configuration file
│   └── settings.py       # Settings loader
├── services/
│   ├── llm_service.py    # Hugging Face Inference API integration & request routing
│   └── telegram_service.py # Telegram bot integration
├── agents/
│   ├── gmail_agent.py    # Gmail API integration
│   └── calendar_agent.py # Calendar API integration
└── credentials/          # Google API credentials
```

## 🤖 How It Works

1. **Request Reception**: User sends message via Telegram or CLI
2. **Language Detection**: LLM detects the user's language automatically
3. **Intent Classification**: LLM categorizes request (EMAIL/CALENDAR/GENERAL)
4. **Agent Routing**: Request routed to appropriate agent
5. **Data Retrieval**: Agent fetches relevant data (emails/events)
6. **LLM Analysis**: LLM analyzes data and generates natural response
7. **Response Delivery**: Answer sent back in user's original language

## 🔐 Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API and Calendar API
4. Create credentials (OAuth 2.0 Client ID)
5. Download credentials.json to `credentials/` folder
6. First run will open browser for authentication

## 📱 Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create new bot with `/newbot`
3. Get your bot token
4. Add token to `.env` file
5. Get your chat ID (message the bot, check logs, or use [@userinfobot](https://t.me/userinfobot))

## 🛠️ Development

### Testing Different Components

```bash
# Test LLM routing
python -c "
from services.llm_service import OllamaService
llm = OllamaService()
response = llm.route_user_request('do I have emails?')
print(response.content)
"

# Test Gmail agent
python -c "
import asyncio
from agents.gmail_agent import GmailAgent
agent = GmailAgent()
result = asyncio.run(agent.get_unread_emails())
print(f'Found {result[\"count\"]} emails')
"
```

### Adding New Languages

The LLM handles translations automatically, but you can add language-specific instructions by editing the `_get_language_instructions()` method in `services/llm_service.py`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `python test.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Inference API not working:**
```bash
# Check Hugging Face Hub installation
python -c "from huggingface_hub import InferenceClient; print('✅ Hub available')"

# Test your token
python -c "
import os
from huggingface_hub import InferenceClient
token = os.getenv('HUGGINGFACE_TOKEN')
if not token:
    print('❌ HUGGINGFACE_TOKEN not found in environment')
else:
    print(f'✅ Token found: {token[:10]}...')
    client = InferenceClient(token=token)
    print('✅ Client initialized successfully')
"

# Test API access
python -c "
import os
from huggingface_hub import InferenceClient
client = InferenceClient(token=os.getenv('HUGGINGFACE_TOKEN'))
try:
    response = client.text_generation('Hello', model='google/gemma-2-2b-it', max_new_tokens=10)
    print('✅ API working:', response[:50])
except Exception as e:
    print('❌ API error:', str(e))
"
```

**Rate limiting:**
- Free accounts have limited requests per hour
- Upgrade to Hugging Face Pro for higher limits
- The bot implements automatic retry with exponential backoff

**Google API authentication:**
- Ensure credentials.json is in credentials/ folder
- Check Google Cloud Console for API limits
- Re-run authentication if tokens expire

**Telegram not working:**
- Verify bot token and chat ID in .env
- Check if bot is added to your chat
- Ensure bot has permission to send messages

**No emails/events found:**
- Check Google API scopes in config.yaml
- Verify authentication with Google services
- Check the time filters (max_age_hours)

## 🌟 What's Different

This bot is designed to be **conversational and intelligent** rather than just a scheduled automation tool. Key differences:

- **Natural Language Processing**: Ask questions naturally in any language
- **Context-Aware**: Understands what you're really asking for
- **Interactive**: Real-time responses via Telegram chat
- **Zero Setup**: No model downloads or GPU requirements - uses Hugging Face cloud inference
- **Flexible**: Works with development testing and production deployment

Perfect for busy professionals who want to interact with their email and calendar through natural conversation! 🚀