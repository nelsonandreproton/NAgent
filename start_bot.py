#!/usr/bin/env python3
"""
Safe Bot Starter - Ensures no conflicts with existing bot processes
"""

import os
import sys
import signal
import subprocess
import time
import psutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_bot_processes():
    """Find all running bot processes"""
    bot_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'])
            if 'python' in proc.info['name'].lower() and 'bot_new.py' in cmdline:
                bot_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return bot_processes

def kill_existing_bots():
    """Kill any existing bot processes"""
    processes = find_bot_processes()
    if processes:
        print(f"🔄 Found {len(processes)} existing bot process(es), terminating...")
        for proc in processes:
            try:
                print(f"   Killing PID {proc.pid}: {' '.join(proc.cmdline())}")
                proc.terminate()
                proc.wait(timeout=5)  # Wait up to 5 seconds for graceful termination
            except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                try:
                    proc.kill()  # Force kill if graceful termination fails
                except psutil.NoSuchProcess:
                    pass
        
        # Wait a moment for processes to fully terminate
        time.sleep(2)
        
        # Verify all processes are gone
        remaining = find_bot_processes()
        if remaining:
            print(f"⚠️ Warning: {len(remaining)} process(es) still running")
            for proc in remaining:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
        else:
            print("✅ All existing bot processes terminated")
    else:
        print("✅ No existing bot processes found")

def start_bot(mode='telegram'):
    """Start the bot in specified mode"""
    print(f"🚀 Starting NAgent Bot in {mode} mode...")
    
    # Change to bot directory
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(bot_dir)
    
    # Build command
    if mode == 'telegram':
        cmd = [sys.executable, 'bot_new.py', 'telegram']
    else:
        cmd = [sys.executable, 'bot_new.py']
    
    # Start the bot
    try:
        if mode == 'telegram':
            print("📱 Telegram bot starting... (Press Ctrl+C to stop)")
            subprocess.run(cmd)
        else:
            print("💻 CLI bot starting...")
            subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

def main():
    """Main entry point"""
    print("🤖 NAgent Bot Safe Starter")
    print("=" * 40)
    
    # Parse command line arguments
    mode = 'telegram'
    if len(sys.argv) > 1:
        if sys.argv[1] in ['cli', 'telegram']:
            mode = sys.argv[1]
        else:
            print("Usage: python start_bot.py [cli|telegram]")
            sys.exit(1)
    
    # Kill any existing processes
    kill_existing_bots()
    
    # Wait a moment for Telegram API to clear any conflicts
    if mode == 'telegram':
        print("⏳ Waiting for Telegram API to clear conflicts...")
        time.sleep(5)
    
    # Start the bot
    start_bot(mode)

if __name__ == "__main__":
    main()