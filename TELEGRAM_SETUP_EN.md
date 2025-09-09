# 📱 Telegram Bot Configuration Guide

This guide explains how to configure a Telegram bot to receive daily summaries from the Agent Orchestrator.

## 📋 Prerequisites

- Active Telegram account
- Telegram application installed (mobile or desktop)
- Agent Orchestrator already configured and working

## 🤖 Step 1: Create Bot on Telegram

### 1.1 Contact BotFather
1. Open Telegram
2. Search for **@BotFather** or access [t.me/BotFather](https://t.me/BotFather)
3. Start a conversation by clicking **"Start"**

### 1.2 Create New Bot
1. Send the command: `/newbot`
2. BotFather will ask for the bot name:
   ```
   Alright, a new bot. How are we going to call it? Please choose a name for your bot.
   ```
3. Enter a descriptive name (e.g., `Agent Orchestrator Bot`)

4. BotFather will ask for the bot username:
   ```
   Good. Now let's choose a username for your bot. It must end in 'bot'. Like this, for example: TetrisBot or tetris_bot.
   ```
5. Enter a unique username ending in "bot" (e.g., `MyAgentOrchestrator_bot`)

### 1.3 Save the Token
After creating the bot, you'll receive a message with the token:
```
Done! Congratulations on your new bot. You will find it at t.me/MyAgentOrchestrator_bot. 
You can now add a description, about section and profile picture for your bot.

Use this token to access the HTTP API:
123456789:ABCDEF1234567890abcdef1234567890ABC

Keep your token secure and store it safely, it can be used by anyone to control your bot.
```

**⚠️ IMPORTANT**: Copy and save this token in a secure location!

## 🆔 Step 2: Get Your Chat ID

### 2.1 Automatic Method (Recommended)
1. Search for **@userinfobot** on Telegram
2. Start a conversation
3. The bot will immediately show your information:
   ```
   👤 Name: Your Name
   🆔 ID: 123456789
   👤 Username: @your_username
   ```
4. Copy the **ID** number (e.g., `123456789`)

### 2.2 Manual Method (Alternative)
1. Start a conversation with your bot (search for the username you created)
2. Send any message to the bot (e.g., "Hello")
3. Open the following URL in your browser (replace `YOUR_TOKEN` with your bot token):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
4. Look for your `chat_id` in the JSON response

## ⚙️ Step 3: Configure Agent Orchestrator

### 3.1 Edit .env File
Open the `.env` file in the Agent Orchestrator directory:

```bash
# Telegram Configuration
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456789:ABCDEF1234567890abcdef1234567890ABC
TELEGRAM_CHAT_ID=123456789
```

### 3.2 Configure config.yaml (Optional)
For advanced settings, edit `config/config.yaml`:

```yaml
telegram:
  # Send daily summary automatically
  send_daily_summary: true
  # Send error notifications
  send_error_notifications: true
  # Send system status updates
  send_status_updates: false
  # Message format (html, markdown, text)
  message_format: "html"
```

## ✅ Step 4: Test Configuration

### 4.1 Check System Status
Run the command:
```bash
python main.py --status
```

You should see Telegram as "✅ Connected" in the status table.

### 4.2 Test Manual Sending
To test if the bot works, run:
```bash
python main.py --run-now
```

If everything is configured correctly, you'll receive a message on Telegram with the summary.

## 🔧 Troubleshooting

### ❌ "Bot token invalid"
- Check if you copied the token completely
- Make sure there are no extra spaces
- Token should have format: `123456789:ABC...`

### ❌ "Chat not found" or "Forbidden"
- Check if Chat ID is correct
- **IMPORTANT**: You must send at least one message to the bot first
- Start a conversation with the bot before testing

### ❌ "Telegram not configured"
- Make sure `TELEGRAM_ENABLED=true` in .env file
- Check that both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are defined

### ❌ Bot doesn't respond
- Confirm the bot is active (search for it on Telegram)
- Test manually by sending a message to the bot
- Use the `/start` command within the bot chat

## 📱 Customize Notifications

### Available Notification Types:
1. **Daily Summary**: Sent automatically or on demand
2. **Error Notifications**: When something fails in the system
3. **System Status**: Connectivity checks
4. **Scheduled Runs**: Start and completion of automated tasks

### Configure Notifications:
Edit `config/config.yaml`:

```yaml
telegram:
  send_daily_summary: true        # Daily summaries
  send_error_notifications: true  # System errors
  send_status_updates: false      # Status updates
```

## 🔐 Security

- **Never share the bot token** - anyone with access can control the bot
- Keep the `.env` file secure and don't commit it to public repositories
- Consider using a dedicated bot just for Agent Orchestrator
- If you suspect the token was compromised, create a new bot

## 📝 Example Message Received

When working correctly, you'll receive formatted messages like this:

```
🤖 Daily Summary - Agent Orchestrator
📅 2024-01-15

📧 Unread emails: 12
📩 Recent (3h): 3

📅 Meetings today: 4
💻 Virtual: 2
⏰ Total duration: 3.5h

📋 Daily Briefing:
Here's your day at a glance...

[Detailed summary generated by LLM]

Generated at 09:00
```

## 🆘 Support

If you continue having issues:
1. Check logs in `logs/orchestrator.log`
2. Run `python main.py --debug --status` for detailed information
3. Test connectivity manually with Telegram APIs
4. Consult the official Telegram Bot API documentation