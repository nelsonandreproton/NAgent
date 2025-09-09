#!/usr/bin/env python3
"""
Agent Orchestrator Main Module
Coordinates Gmail and Calendar agents to provide daily summaries.
"""

import os
import sys
import json
import yaml
import argparse
import logging
import schedule
import time
from datetime import datetime
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from dotenv import load_dotenv

# Import our services and agents
from services.google_auth import GoogleAuthManager
from services.llm_service import OllamaService
from services.telegram_service import TelegramService, TelegramNotifier
from agents.gmail_agent import GmailAgent
from agents.calendar_agent import CalendarAgent


class AgentOrchestrator:
    """Main orchestrator for Gmail and Calendar agents"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.console = Console()
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.auth_manager = None
        self.llm_service = None
        self.telegram_service = None
        self.telegram_notifier = None
        self.gmail_agent = None
        self.calendar_agent = None
        
        self._initialize_services()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Override with environment variables if they exist
            load_dotenv()
            
            # Update paths
            if os.getenv('GOOGLE_CREDENTIALS_PATH'):
                config['google_api']['credentials_path'] = os.getenv('GOOGLE_CREDENTIALS_PATH')
            if os.getenv('OLLAMA_BASE_URL'):
                config['ollama']['base_url'] = os.getenv('OLLAMA_BASE_URL')
            if os.getenv('OLLAMA_MODEL'):
                config['ollama']['model'] = os.getenv('OLLAMA_MODEL')
                
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        
        # Create logs directory if it doesn't exist
        log_file = log_config.get('file', 'logs/orchestrator.log')
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _initialize_services(self):
        """Initialize all services and agents"""
        try:
            # Initialize authentication manager
            google_config = self.config['google_api']
            self.auth_manager = GoogleAuthManager(
                credentials_path=google_config['credentials_path'],
                scopes=google_config['scopes']
            )
            
            # Initialize LLM service
            ollama_config = self.config['ollama']
            self.llm_service = OllamaService(
                base_url=ollama_config['base_url'],
                model=ollama_config['model']
            )
            
            # Initialize agents
            self.gmail_agent = GmailAgent(
                auth_manager=self.auth_manager,
                llm_service=self.llm_service,
                config=self.config['gmail']
            )
            
            self.calendar_agent = CalendarAgent(
                auth_manager=self.auth_manager,
                llm_service=self.llm_service,
                config=self.config['calendar']
            )
            
            # Initialize Telegram service if enabled
            telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
            if telegram_enabled:
                bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                chat_id = os.getenv('TELEGRAM_CHAT_ID')
                language = self.config.get('language', {}).get('default', 'pt-pt')
                
                if bot_token and chat_id:
                    self.telegram_service = TelegramService(bot_token, chat_id, language)
                    self.telegram_notifier = TelegramNotifier(self.telegram_service)
                    self.logger.info("Telegram service initialized successfully")
                else:
                    self.logger.warning("Telegram enabled but bot_token or chat_id missing")
            
            self.logger.info("All services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    def check_system_status(self) -> Dict[str, Any]:
        """Check the status of all system components"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'ollama': {'available': False, 'error': None},
            'google_auth': {'authenticated': False, 'error': None},
            'gmail': {'accessible': False, 'error': None},
            'calendar': {'accessible': False, 'error': None},
            'telegram': {'available': False, 'error': None}
        }
        
        # Check Ollama
        try:
            status['ollama']['available'] = self.llm_service.is_available()
            if not status['ollama']['available']:
                status['ollama']['error'] = "Ollama service not reachable"
        except Exception as e:
            status['ollama']['error'] = str(e)
        
        # Check Google authentication and services
        try:
            auth_results = self.auth_manager.test_connection()
            
            status['google_auth']['authenticated'] = auth_results['gmail']['success'] or auth_results['calendar']['success']
            status['gmail']['accessible'] = auth_results['gmail']['success']
            status['calendar']['accessible'] = auth_results['calendar']['success']
            
            if not status['gmail']['accessible']:
                status['gmail']['error'] = auth_results['gmail'].get('error')
            if not status['calendar']['accessible']:
                status['calendar']['error'] = auth_results['calendar'].get('error')
                
        except Exception as e:
            status['google_auth']['error'] = str(e)
        
        # Check Telegram
        if self.telegram_service:
            try:
                telegram_result = self.telegram_service.test_connection()
                status['telegram']['available'] = telegram_result['success']
                if not telegram_result['success']:
                    status['telegram']['error'] = telegram_result.get('error', 'Connection failed')
            except Exception as e:
                status['telegram']['error'] = str(e)
        else:
            status['telegram']['error'] = 'Telegram not configured or disabled'
        
        return status
    
    def generate_daily_summary(self, save_to_file: bool = True) -> Dict[str, Any]:
        """Generate a complete daily summary from both agents"""
        self.logger.info("Starting daily summary generation")
        
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().date().isoformat(),
            'email_summary': '',
            'calendar_summary': '',
            'unified_summary': '',
            'statistics': {},
            'errors': []
        }
        
        detail_level = self.config.get('summary', {}).get('detail_level', 'medium')
        
        try:
            # Generate email summary
            self.console.print("📧 Fetching and summarizing emails...", style="blue")
            email_summary = self.gmail_agent.generate_email_summary(
                self.gmail_agent.fetch_unread_emails(),
                detail_level=detail_level
            )
            summary_data['email_summary'] = email_summary
            
            # Get email statistics
            email_stats = self.gmail_agent.get_email_statistics()
            summary_data['statistics']['email'] = email_stats
            
        except Exception as e:
            error_msg = f"Failed to generate email summary: {e}"
            self.logger.error(error_msg)
            summary_data['errors'].append(error_msg)
            summary_data['email_summary'] = "Error generating email summary."
        
        try:
            # Generate calendar summary
            self.console.print("📅 Fetching and summarizing calendar...", style="blue")
            calendar_summary = self.calendar_agent.generate_calendar_summary(
                self.calendar_agent.fetch_today_events(),
                detail_level=detail_level
            )
            summary_data['calendar_summary'] = calendar_summary
            
            # Get calendar statistics
            calendar_stats = self.calendar_agent.get_calendar_statistics()
            summary_data['statistics']['calendar'] = calendar_stats
            
        except Exception as e:
            error_msg = f"Failed to generate calendar summary: {e}"
            self.logger.error(error_msg)
            summary_data['errors'].append(error_msg)
            summary_data['calendar_summary'] = "Error generating calendar summary."
        
        try:
            # Generate unified summary
            self.console.print("🤖 Creating unified summary...", style="blue")
            unified_response = self.llm_service.create_daily_summary(
                summary_data['email_summary'],
                summary_data['calendar_summary']
            )
            
            if unified_response.success:
                summary_data['unified_summary'] = unified_response.content
            else:
                summary_data['unified_summary'] = self._create_fallback_unified_summary(
                    summary_data['email_summary'],
                    summary_data['calendar_summary']
                )
                
        except Exception as e:
            error_msg = f"Failed to generate unified summary: {e}"
            self.logger.error(error_msg)
            summary_data['errors'].append(error_msg)
            summary_data['unified_summary'] = self._create_fallback_unified_summary(
                summary_data['email_summary'],
                summary_data['calendar_summary']
            )
        
        # Save to file if requested
        if save_to_file and self.config.get('summary', {}).get('save_to_file', True):
            self._save_summary_to_file(summary_data)
        
        # Send to Telegram if enabled
        if self.telegram_service and self.config.get('telegram', {}).get('send_daily_summary', True):
            try:
                self.telegram_service.send_daily_summary(summary_data)
                self.logger.info("Daily summary sent to Telegram")
            except Exception as e:
                error_msg = f"Failed to send summary to Telegram: {e}"
                self.logger.error(error_msg)
                summary_data['errors'].append(error_msg)
        
        self.logger.info("Daily summary generation completed")
        return summary_data
    
    def _create_fallback_unified_summary(self, email_summary: str, calendar_summary: str) -> str:
        """Create a basic unified summary without LLM"""
        sections = [
            "# Daily Briefing",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d at %H:%M')}",
            "",
            "## 📧 Email Summary",
            email_summary,
            "",
            "## 📅 Calendar Summary", 
            calendar_summary,
            "",
            "## 📝 Quick Notes",
            "• Review your email priorities for today",
            "• Prepare for upcoming meetings",
            "• Check for any scheduling conflicts"
        ]
        
        return "\n".join(sections)
    
    def _save_summary_to_file(self, summary_data: Dict[str, Any]):
        """Save summary data to file"""
        try:
            # Create output directory
            output_dir = self.config.get('summary', {}).get('output_directory', 'summaries')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Generate filename
            date_str = datetime.now().strftime('%Y-%m-%d')
            timestamp_str = datetime.now().strftime('%H-%M')
            
            output_format = self.config.get('summary', {}).get('output_format', 'json')
            
            if output_format == 'json':
                filename = f"{output_dir}/summary_{date_str}_{timestamp_str}.json"
                with open(filename, 'w') as f:
                    json.dump(summary_data, f, indent=2, default=str)
            elif output_format == 'text':
                filename = f"{output_dir}/summary_{date_str}_{timestamp_str}.txt"
                with open(filename, 'w') as f:
                    f.write(summary_data['unified_summary'])
            elif output_format == 'html':
                filename = f"{output_dir}/summary_{date_str}_{timestamp_str}.html"
                html_content = self._generate_html_summary(summary_data)
                with open(filename, 'w') as f:
                    f.write(html_content)
            
            self.logger.info(f"Summary saved to: {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save summary to file: {e}")
    
    def _generate_html_summary(self, summary_data: Dict[str, Any]) -> str:
        """Generate HTML formatted summary"""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Daily Summary - {summary_data['date']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f0f8ff; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .error {{ color: red; background: #ffe6e6; padding: 10px; border-radius: 3px; }}
                .stats {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Daily Summary</h1>
                <p>Generated on: {summary_data['timestamp']}</p>
            </div>
            
            <div class="section">
                <h2>📧 Email Summary</h2>
                <pre>{summary_data['email_summary']}</pre>
            </div>
            
            <div class="section">
                <h2>📅 Calendar Summary</h2>
                <pre>{summary_data['calendar_summary']}</pre>
            </div>
            
            <div class="section">
                <h2>🤖 Unified Summary</h2>
                <pre>{summary_data['unified_summary']}</pre>
            </div>
            
            <div class="section stats">
                <h2>📊 Statistics</h2>
                <pre>{json.dumps(summary_data['statistics'], indent=2)}</pre>
            </div>
            
            {f'<div class="error">Errors: {summary_data["errors"]}</div>' if summary_data['errors'] else ''}
        </body>
        </html>
        """
        return html_template
    
    def display_summary(self, summary_data: Dict[str, Any]):
        """Display summary using rich formatting"""
        # Main summary panel
        summary_panel = Panel(
            summary_data['unified_summary'],
            title="🤖 Daily Briefing",
            border_style="blue"
        )
        self.console.print(summary_panel)
        
        # Statistics table
        stats = summary_data.get('statistics', {})
        if stats:
            table = Table(title="📊 Daily Statistics")
            table.add_column("Category", style="cyan")
            table.add_column("Metric", style="magenta")
            table.add_column("Value", style="green")
            
            email_stats = stats.get('email', {})
            table.add_row("Email", "Unread Count", str(email_stats.get('total_unread', 0)))
            table.add_row("Email", "Recent (3h)", str(email_stats.get('recent_count', 0)))
            
            calendar_stats = stats.get('calendar', {})
            table.add_row("Calendar", "Total Events", str(calendar_stats.get('total_events', 0)))
            table.add_row("Calendar", "Virtual Meetings", str(calendar_stats.get('virtual_meetings', 0)))
            table.add_row("Calendar", "Duration (hours)", str(round(calendar_stats.get('total_duration_minutes', 0) / 60, 1)))
            
            self.console.print(table)
        
        # Errors if any
        if summary_data.get('errors'):
            error_text = Text("\n".join(summary_data['errors']), style="red")
            error_panel = Panel(error_text, title="⚠️  Errors", border_style="red")
            self.console.print(error_panel)
    
    def setup_scheduler(self):
        """Setup scheduled execution"""
        schedule_config = self.config.get('schedule', {})
        
        if not schedule_config.get('enabled', False):
            self.logger.info("Scheduling is disabled")
            return
        
        daily_time = schedule_config.get('daily_time', '09:00')
        schedule.every().day.at(daily_time).do(self._scheduled_run)
        
        self.logger.info(f"Scheduled daily summary at {daily_time}")
        
        self.console.print(f"⏰ Daily summary scheduled for {daily_time}")
        self.console.print("Press Ctrl+C to stop the scheduler")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.console.print("\n👋 Scheduler stopped")
    
    def _scheduled_run(self):
        """Run scheduled summary generation"""
        self.logger.info("Running scheduled daily summary")
        
        # Notify start if Telegram is enabled
        if self.telegram_notifier:
            self.telegram_notifier.notify_scheduled_run_started()
        
        try:
            summary_data = self.generate_daily_summary()
            self.display_summary(summary_data)
            
            # Notify completion if Telegram is enabled
            if self.telegram_notifier:
                self.telegram_notifier.notify_scheduled_run_completed()
                
        except Exception as e:
            error_msg = f"Scheduled run failed: {e}"
            self.logger.error(error_msg)
            
            # Send error notification if Telegram is enabled
            if self.telegram_notifier and self.config.get('telegram', {}).get('send_error_notifications', True):
                self.telegram_notifier.notify_system_error(error_msg)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Agent Orchestrator - Gmail and Calendar Summary")
    parser.add_argument('--config', default='config/config.yaml', help='Configuration file path')
    parser.add_argument('--run-now', action='store_true', help='Run summary generation immediately')
    parser.add_argument('--schedule', action='store_true', help='Run in scheduled mode')
    parser.add_argument('--status', action='store_true', help='Check system status')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(config_path=args.config)
        
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        
        if args.status:
            # Check system status
            status = orchestrator.check_system_status()
            console = Console()
            
            table = Table(title="🔍 System Status")
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="magenta")
            table.add_column("Details", style="yellow")
            
            for component, details in status.items():
                if component == 'timestamp':
                    continue
                    
                if component == 'ollama':
                    status_text = "✅ Available" if details['available'] else "❌ Unavailable"
                elif component == 'google_auth':
                    status_text = "✅ Authenticated" if details['authenticated'] else "❌ Not Authenticated"
                elif component == 'telegram':
                    status_text = "✅ Connected" if details['available'] else "❌ Disconnected"
                else:
                    status_text = "✅ Accessible" if details.get('accessible', False) else "❌ Not Accessible"
                
                error_text = details.get('error', '') or 'OK'
                table.add_row(component.title(), status_text, error_text)
            
            console.print(table)
        
        elif args.run_now:
            # Run summary immediately
            summary_data = orchestrator.generate_daily_summary()
            orchestrator.display_summary(summary_data)
        
        elif args.schedule:
            # Run in scheduled mode
            orchestrator.setup_scheduler()
        
        else:
            # Show help
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()