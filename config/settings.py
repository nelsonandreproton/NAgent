"""
Configuration Settings Loader
Loads configuration from YAML file and environment variables.
"""

import os
import yaml
from typing import Dict, Any


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    
    # Default configuration
    default_config = {
        'bot': {
            'mode': 'telegram',
            'auto_daily_summary': False,
            'daily_time': '09:00'
        },
        'llm': {
            'base_url': 'http://localhost:11434',
            'model': 'gemma2:2b',
            'timeout': 60,
            'temperature': 0.7
        },
        'google_api': {
            'credentials_path': 'credentials/credentials.json',
            'scopes': [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/calendar.readonly'
            ]
        },
        'agents': {
            'gmail': {
                'max_results': 20,
                'max_age_hours': 24
            },
            'calendar': {
                'max_results': 20
            }
        },
        'response': {
            'max_message_length': 4000,
            'truncate_long_responses': True
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'logs/orchestrator.log'
        }
    }
    
    # Try to load from YAML file
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Merge configurations (file config overrides defaults)
                    default_config = merge_configs(default_config, file_config)
        else:
            print(f"Warning: Config file {config_path} not found, using defaults")
    except Exception as e:
        print(f"Warning: Error loading config file {config_path}: {e}")
        print("Using default configuration")
    
    return default_config


def merge_configs(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two configuration dictionaries"""
    result = default.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def get_env_config() -> Dict[str, Any]:
    """Get configuration from environment variables"""
    return {
        'telegram': {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID')
        },
        'google_api': {
            'credentials_path': os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
        }
    }


def load_full_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from both YAML file and environment variables"""
    
    # Load base configuration
    config = load_config(config_path)
    
    # Merge with environment variables
    env_config = get_env_config()
    config = merge_configs(config, env_config)
    
    return config