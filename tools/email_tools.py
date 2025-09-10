"""
Email Tools for LLM
Provides email search, listing, and creation capabilities.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import base64
from email.mime.text import MIMEText

from services.tool_registry import BaseTool, ToolParameter, ToolResult

try:
    from services.google_auth import GoogleAuthManager
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GoogleAuthManager = None
    HttpError = Exception
    GOOGLE_AVAILABLE = False


class SearchEmailsTool(BaseTool):
    """Search for emails based on query and time range"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "search_emails"
    
    @property
    def description(self) -> str:
        return "Search for emails based on query, sender, time range, etc. Returns detailed email information."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("query", "string", "Search query (e.g., 'from:john subject:meeting', 'is:unread', 'after:2025/01/01')", required=False, default=""),
            ToolParameter("max_results", "integer", "Maximum number of emails to return", required=False, default=20),
            ToolParameter("days_back", "integer", "Search emails from N days back", required=False, default=7)
        ]
    
    def _get_service(self):
        """Get Gmail service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_gmail_service()
            except Exception as e:
                self.logger.error(f"Could not get Gmail service: {e}")
        return self._service
    
    async def execute(self, query: str = "", max_results: int = 20, days_back: int = 7) -> ToolResult:
        """Execute email search"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Gmail service not available")
        
        try:
            # Build search query
            search_query = query
            if days_back and not any(word in query.lower() for word in ['after:', 'before:']):
                cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')
                if search_query:
                    search_query += f" after:{cutoff_date}"
                else:
                    search_query = f"after:{cutoff_date}"
            
            self.logger.info(f"Searching emails with query: {search_query}")
            
            # Search for emails
            response = service.users().messages().list(
                userId='me',
                q=search_query,
                maxResults=min(max_results, 50)  # Safety limit
            ).execute()
            
            messages = response.get('messages', [])
            self.logger.info(f"Found {len(messages)} emails")
            
            # Get detailed information for each email
            emails = []
            for message in messages[:max_results]:
                try:
                    email_details = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Parse email details
                    headers = email_details['payload'].get('headers', [])
                    email_data = {
                        'id': message['id'],
                        'thread_id': email_details.get('threadId'),
                        'subject': '',
                        'from': '',
                        'to': '',
                        'date': '',
                        'snippet': email_details.get('snippet', ''),
                        'labels': email_details.get('labelIds', [])
                    }
                    
                    # Extract header information
                    for header in headers:
                        name = header['name'].lower()
                        value = header['value']
                        if name == 'subject':
                            email_data['subject'] = value
                        elif name == 'from':
                            email_data['from'] = value
                        elif name == 'to':
                            email_data['to'] = value
                        elif name == 'date':
                            email_data['date'] = value
                    
                    emails.append(email_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get details for email {message['id']}: {e}")
                    continue
            
            return ToolResult(
                success=True,
                data={
                    'emails': emails,
                    'total_found': len(messages),
                    'search_query': search_query
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error searching emails: {str(e)}"
            )


class GetUnreadEmailsTool(BaseTool):
    """Get list of unread emails"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "get_unread_emails"
    
    @property
    def description(self) -> str:
        return "Get list of unread emails. Shows the most recent unread emails with details."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("max_results", "integer", "Maximum number of unread emails to return", required=False, default=10)
        ]
    
    def _get_service(self):
        """Get Gmail service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_gmail_service()
            except Exception as e:
                self.logger.error(f"Could not get Gmail service: {e}")
        return self._service
    
    async def execute(self, max_results: int = 10) -> ToolResult:
        """Execute unread emails retrieval"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Gmail service not available")
        
        try:
            # Search for unread emails
            response = service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=min(max_results, 50)  # Safety limit
            ).execute()
            
            messages = response.get('messages', [])
            self.logger.info(f"Found {len(messages)} unread emails")
            
            # Get detailed information for each email
            emails = []
            for message in messages[:max_results]:
                try:
                    email_details = service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()
                    
                    # Parse email details
                    headers = email_details['payload'].get('headers', [])
                    email_data = {
                        'id': message['id'],
                        'thread_id': email_details.get('threadId'),
                        'subject': '',
                        'from': '',
                        'date': '',
                        'snippet': email_details.get('snippet', ''),
                        'is_unread': True
                    }
                    
                    # Extract header information
                    for header in headers:
                        name = header['name'].lower()
                        value = header['value']
                        if name == 'subject':
                            email_data['subject'] = value
                        elif name == 'from':
                            email_data['from'] = value
                        elif name == 'date':
                            email_data['date'] = value
                    
                    emails.append(email_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to get details for email {message['id']}: {e}")
                    continue
            
            return ToolResult(
                success=True,
                data={
                    'unread_emails': emails,
                    'total_unread': len(messages)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting unread emails: {str(e)}"
            )


class CreateEmailTool(BaseTool):
    """Create and send a new email"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        if GOOGLE_AVAILABLE:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    @property
    def name(self) -> str:
        return "create_email"
    
    @property
    def description(self) -> str:
        return "Create and send a new email. Specify recipient, subject, and message content."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter("to", "string", "Recipient email address", required=True),
            ToolParameter("subject", "string", "Email subject line", required=True),
            ToolParameter("body", "string", "Email message content", required=True),
            ToolParameter("cc", "string", "CC recipients (comma-separated)", required=False, default=""),
            ToolParameter("bcc", "string", "BCC recipients (comma-separated)", required=False, default="")
        ]
    
    def _get_service(self):
        """Get Gmail service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_gmail_service()
            except Exception as e:
                self.logger.error(f"Could not get Gmail service: {e}")
        return self._service
    
    def _create_message(self, to: str, subject: str, body: str, cc: str = "", bcc: str = ""):
        """Create email message"""
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        
        # Encode message
        raw = base64.urlsafe_b64encode(message.as_bytes())
        raw = raw.decode()
        return {'raw': raw}
    
    async def execute(self, to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> ToolResult:
        """Execute email creation and sending"""
        if not GOOGLE_AVAILABLE:
            return ToolResult(success=False, error="Google API not available")
        
        service = self._get_service()
        if not service:
            return ToolResult(success=False, error="Gmail service not available")
        
        try:
            # Create message
            message = self._create_message(to, subject, body, cc, bcc)
            
            # Send email
            sent_message = service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            self.logger.info(f"Email sent successfully: {sent_message['id']}")
            
            return ToolResult(
                success=True,
                data={
                    'message_id': sent_message['id'],
                    'to': to,
                    'subject': subject,
                    'status': 'sent'
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error sending email: {str(e)}"
            )


class GetCurrentTimeTool(BaseTool):
    """Get current date and time"""
    
    @property
    def name(self) -> str:
        return "get_current_time"
    
    @property
    def description(self) -> str:
        return "Get the current date and time. Useful for time-based queries and scheduling."
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self) -> ToolResult:
        """Execute current time retrieval"""
        now = datetime.now()
        
        return ToolResult(
            success=True,
            data={
                'current_datetime': now.isoformat(),
                'current_date': now.strftime('%Y-%m-%d'),
                'current_time': now.strftime('%H:%M:%S'),
                'current_weekday': now.strftime('%A'),
                'current_month_year': now.strftime('%B %Y'),
                'timestamp': now.timestamp()
            }
        )


def register_email_tools():
    """Register all email tools with the global registry"""
    from services.tool_registry import tool_registry
    
    tools = [
        SearchEmailsTool(),
        GetUnreadEmailsTool(),
        CreateEmailTool(),
        GetCurrentTimeTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)