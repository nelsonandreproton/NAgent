#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting NAgent Bot..."

# Get configuration from Home Assistant
export TELEGRAM_BOT_TOKEN="$(bashio::config 'telegram_bot_token')"
export TELEGRAM_CHAT_ID="$(bashio::config 'telegram_chat_id')"
export HUGGINGFACE_TOKEN="$(bashio::config 'huggingface_token')"
export GOOGLE_CREDENTIALS_BASE64="$(bashio::config 'google_credentials_base64')"
export LOG_LEVEL="$(bashio::config 'log_level')"

# Validate required config
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    bashio::log.fatal "Telegram bot token is required!"
    bashio::exit.nok
fi

if [ -z "$TELEGRAM_CHAT_ID" ]; then
    bashio::log.fatal "Telegram chat ID is required!"
    bashio::exit.nok
fi

if [ -z "$HUGGINGFACE_TOKEN" ]; then
    bashio::log.fatal "Hugging Face token is required!"
    bashio::exit.nok
fi

if [ -z "$GOOGLE_CREDENTIALS_BASE64" ]; then
    bashio::log.fatal "Google credentials (base64) are required!"
    bashio::exit.nok
fi

# Setup Google credentials
mkdir -p /tmp/credentials
echo "$GOOGLE_CREDENTIALS_BASE64" | base64 -d > /tmp/credentials/credentials.json
export GOOGLE_CREDENTIALS_PATH="/tmp/credentials/credentials.json"

# Verify credentials file was created and show details for debugging
if [ -f "/tmp/credentials/credentials.json" ]; then
    bashio::log.info "Credentials file created successfully"
    FILE_SIZE=$(wc -c < /tmp/credentials/credentials.json)
    bashio::log.info "Credentials file size: ${FILE_SIZE} bytes"
    
    # Show first few characters to verify content
    head -c 100 /tmp/credentials/credentials.json > /tmp/cred_preview.txt
    PREVIEW=$(cat /tmp/cred_preview.txt)
    bashio::log.info "Credentials file preview: ${PREVIEW}..."
    rm -f /tmp/cred_preview.txt
else
    bashio::log.error "Failed to create credentials file!"
fi

bashio::log.info "Configuration loaded successfully"
bashio::log.info "Starting NAgent Bot with Telegram integration..."

# Change to app directory
cd /app

# Start the bot
exec python3 main.py