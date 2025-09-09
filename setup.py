#!/usr/bin/env python3
"""
Setup script for Agent Orchestrator
Handles initial setup and configuration
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Check Python version compatibility"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    else:
        print(f"✅ Python version: {sys.version.split()[0]}")
        return True

def check_ollama():
    """Check if Ollama is installed and accessible"""
    try:
        result = subprocess.run(['ollama', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama not working properly")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        print("Please install Ollama from: https://ollama.ai/")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def setup_ollama_model():
    """Pull the required Ollama model"""
    print("\n🤖 Setting up Ollama model...")
    try:
        subprocess.run(['ollama', 'pull', 'gemma2:2b'], check=True)
        print("✅ gemma2:2b model downloaded")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to download gemma2:2b model")
        return False

def create_env_file():
    """Create .env file from template if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.template'):
            shutil.copy('.env.template', '.env')
            print("✅ Created .env file from template")
            print("📝 Please edit .env file with your settings")
            return True
        else:
            print("❌ .env.template not found")
            return False
    else:
        print("✅ .env file already exists")
        return True

def create_credentials_dir():
    """Ensure credentials directory exists"""
    if not os.path.exists('credentials'):
        os.makedirs('credentials')
        print("✅ Created credentials directory")
    else:
        print("✅ Credentials directory exists")
    
    # Create placeholder for credentials.json
    creds_path = 'credentials/credentials.json'
    if not os.path.exists(creds_path):
        placeholder_content = '''
{
  "_comment": "Replace this file with your Google API credentials",
  "_instructions": [
    "1. Go to Google Cloud Console",
    "2. Enable Gmail and Calendar APIs", 
    "3. Create OAuth 2.0 credentials (Desktop Application)",
    "4. Download as credentials.json and replace this file"
  ]
}
'''
        with open(creds_path, 'w') as f:
            f.write(placeholder_content)
        print(f"📝 Created placeholder: {creds_path}")

def print_next_steps():
    """Print final setup instructions"""
    print("\n🎉 Setup completed!")
    print("\n📋 Next steps:")
    print("1. Set up Google API credentials:")
    print("   - Go to https://console.cloud.google.com/")
    print("   - Enable Gmail and Calendar APIs")
    print("   - Create OAuth 2.0 credentials (Desktop Application)")  
    print("   - Download as 'credentials.json' and place in credentials/ directory")
    print()
    print("2. Configure your settings:")
    print("   - Edit .env file with your preferences")
    print("   - Optionally edit config/config.yaml for advanced settings")
    print()
    print("3. Test the system:")
    print("   - python main.py --status")
    print("   - python main.py --run-now")
    print()
    print("4. Set up scheduled runs:")
    print("   - python main.py --schedule")

def main():
    """Main setup routine"""
    print("🚀 Agent Orchestrator Setup\n")
    
    # Check prerequisites
    if not check_python_version():
        return False
    
    if not check_ollama():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup Ollama model
    if not setup_ollama_model():
        return False
    
    # Create configuration files
    if not create_env_file():
        return False
    
    create_credentials_dir()
    
    print_next_steps()
    return True

if __name__ == '__main__':
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)