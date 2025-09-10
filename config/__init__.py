"""
Simple Configuration Loader
Loads configuration from YAML file with environment variable support.
"""

import os
import yaml
from typing import Dict, Any


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    
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