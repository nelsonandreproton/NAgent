"""
Gmail Agent
Simplified Gmail agent for the new bot architecture.
"""

import base64
import email
import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

try:
    from googleapiclient.errors import HttpError
    from services.google_auth import GoogleAuthManager
except ImportError:
    GoogleAuthManager = None
    HttpError = Exception


class GmailAgent:
    """Simplified Gmail agent for chat responses"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._auth_manager = None
        self._service = None
        
        # Initialize auth manager if available
        if GoogleAuthManager:
            try:
                credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials/credentials.json')
                scopes = [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/calendar.readonly'
                ]
                self._auth_manager = GoogleAuthManager(credentials_path, scopes)
            except Exception as e:
                self.logger.warning(f"Could not initialize Google Auth: {e}")
    
    def _get_service(self):
        """Get Gmail service instance"""
        if not self._service and self._auth_manager:
            try:
                self._service = self._auth_manager.get_gmail_service()
            except Exception as e:
                self.logger.error(f"Could not get Gmail service: {e}")
        return self._service
    
    async def get_unread_emails(self, max_results: int = 20, max_age_hours: int = 24) -> Dict[str, Any]:
        """Get unread emails (async wrapper)"""
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._fetch_unread_emails_sync,
            max_results,
            max_age_hours
        )
    
    def _fetch_unread_emails_sync(self, max_results: int = 20, max_age_hours: int = 24) -> Dict[str, Any]:
        """Fetch unread emails synchronously"""
        result = {
            'success': False,
            'emails': [],
            'count': 0,
            'error': None
        }
        
        try:
            service = self._get_service()
            
            if not service:
                result['error'] = "Gmail service not available. Please check authentication."
                return result
            
            # Build query for unread emails
            query_parts = ['is:unread']
            
            # Add time filter
            if max_age_hours:
                cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
                date_str = cutoff_date.strftime('%Y/%m/%d')
                query_parts.append(f'after:{date_str}')
            
            query = ' '.join(query_parts)
            self.logger.info(f"Gmail query: {query}")
            
            # Get list of unread emails
            response = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = response.get('messages', [])
            self.logger.info(f"Found {len(messages)} unread emails")
            
            if not messages:
                result['success'] = True
                return result
            
            # Fetch email details
            emails = []
            for message in messages[:max_results]:  # Extra safety limit
                try:
                    email_data = self._get_email_details(service, message['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch email {message['id']}: {e}")
                    continue
            
            result['emails'] = emails
            result['count'] = len(emails)
            result['success'] = True
            
            return result
            
        except Exception as e:
            error_msg = f"Error fetching emails: {str(e)}"
            self.logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _get_email_details(self, service, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific email"""
        try:
            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract basic information
            email_data = {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'sender': '',
                'subject': '',
                'date': '',
                'preview': '',
                'labels': message.get('labelIds', [])
            }
            
            # Parse headers
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'from':
                    email_data['sender'] = value
                elif name == 'subject':
                    email_data['subject'] = value
                elif name == 'date':
                    email_data['date'] = value
            
            # Extract email body/preview
            body = self._extract_email_body(message['payload'])
            if body:
                # Create preview (first 200 characters)
                preview_length = 200
                email_data['preview'] = body[:preview_length]
                if len(body) > preview_length:
                    email_data['preview'] += '...'
            
            # Add timestamp for sorting
            email_data['internal_date'] = int(message.get('internalDate', 0))
            
            return email_data
            
        except Exception as e:
            self.logger.error(f"Error getting email details for {message_id}: {e}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract text content from email payload"""
        body = ""
        
        try:
            if 'parts' in payload:
                # Multipart message
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
                    elif part.get('mimeType') == 'text/html' and not body:
                        # Fallback to HTML if no plain text
                        data = part['body'].get('data')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            # Simple HTML to text conversion
                            body = body.replace('<br>', '\n').replace('<br/>', '\n')
                            body = body.replace('<p>', '\n').replace('</p>', '\n')
                            # Remove HTML tags (basic)
                            import re
                            body = re.sub('<[^<]+?>', '', body)
            else:
                # Single part message
                if payload.get('mimeType') == 'text/plain':
                    data = payload['body'].get('data')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif payload.get('mimeType') == 'text/html':
                    data = payload['body'].get('data') 
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        body = body.replace('<br>', '\n').replace('<br/>', '\n')
                        import re
                        body = re.sub('<[^<]+?>', '', body)
        
        except Exception as e:
            self.logger.warning(f"Error extracting email body: {e}")
        
        # Clean up whitespace
        body = body.strip()
        # Replace multiple newlines with single newlines
        body = '\n'.join(line.strip() for line in body.split('\n') if line.strip())
        
        return body
    
    def is_available(self) -> bool:
        """Check if Gmail service is available"""
        try:
            service = self._get_service()
            return service is not None
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Gmail agent status"""
        result = {
            'available': False,
            'authenticated': False,
            'error': None
        }
        
        try:
            if not self._auth_manager:
                result['error'] = "Google Auth Manager not available"
                return result
            
            service = self._get_service()
            if service:
                # Test with a simple API call
                profile = service.users().getProfile(userId='me').execute()
                result['available'] = True
                result['authenticated'] = True
                result['email_address'] = profile.get('emailAddress', 'unknown')
            else:
                result['error'] = "Could not create Gmail service"
        
        except Exception as e:
            result['error'] = str(e)
        
        return result