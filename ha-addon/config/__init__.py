"""
Simple Configuration Loader
Loads configuration from YAML file with environment variable support.
"""

import os
import yaml
import base64
import json
from typing import Dict, Any


def setup_google_credentials():
    """Setup Google credentials from environment variables for cloud hosting"""
    
    # Method 1: Base64 encoded credentials (preferred for Pella)
    if os.getenv('GOOGLE_CREDENTIALS_BASE64'):
        try:
            creds_data = base64.b64decode(os.getenv('GOOGLE_CREDENTIALS_BASE64'))
            os.makedirs('/tmp', exist_ok=True)
            with open('/tmp/credentials.json', 'wb') as f:
                f.write(creds_data)
            os.environ['GOOGLE_CREDENTIALS_PATH'] = '/tmp/credentials.json'
            return
        except Exception as e:
            print(f"Warning: Failed to decode base64 credentials: {e}")
    
    # Method 2: JSON string credentials
    if os.getenv('GOOGLE_CREDENTIALS_JSON'):
        try:
            os.makedirs('/tmp', exist_ok=True)
            with open('/tmp/credentials.json', 'w') as f:
                f.write(os.getenv('GOOGLE_CREDENTIALS_JSON'))
            os.environ['GOOGLE_CREDENTIALS_PATH'] = '/tmp/credentials.json'
            return
        except Exception as e:
            print(f"Warning: Failed to write JSON credentials: {e}")


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    
    # Setup Google credentials from environment first
    setup_google_credentials()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # Add environment variables for sensitive data
        if not config.get('telegram'):
            config['telegram'] = {}
        
        config['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
        config['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
        
        # Override Google credentials path from env if provided
        if os.getenv('GOOGLE_CREDENTIALS_PATH'):
            if not config.get('google_api'):
                config['google_api'] = {}
            config['google_api']['credentials_path'] = os.getenv('GOOGLE_CREDENTIALS_PATH')
        
        return config
        
    except Exception as e:
        raise RuntimeError(f"Error loading config file {config_path}: {e}")