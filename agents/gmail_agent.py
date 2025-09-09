"""
Gmail Agent
Handles fetching and processing unread emails from Gmail API.
"""

import base64
import email
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from googleapiclient.errors import HttpError

from services.google_auth import GoogleAuthManager
from services.llm_service import OllamaService


class GmailAgent:
    """Agent for Gmail operations and email summarization"""
    
    def __init__(self, auth_manager: GoogleAuthManager, llm_service: OllamaService, config: Dict[str, Any]):
        self.auth_manager = auth_manager
        self.llm_service = llm_service
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._service = None
    
    def _get_service(self):
        """Get Gmail service instance"""
        if not self._service:
            self._service = self.auth_manager.get_gmail_service()
        return self._service
    
    def fetch_unread_emails(self) -> List[Dict[str, Any]]:
        """Fetch unread emails from Gmail"""
        try:
            service = self._get_service()
            
            # Build query for unread emails
            query_parts = ['is:unread']
            
            # Add time filter if configured
            max_age_hours = self.config.get('max_age_hours', 24)
            if max_age_hours:
                cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
                date_str = cutoff_date.strftime('%Y/%m/%d')
                query_parts.append(f'after:{date_str}')
            
            # Add label filters if configured
            labels = self.config.get('labels', [])
            for label in labels:
                query_parts.append(f'label:{label}')
            
            # Add sender exclusions if configured
            exclude_senders = self.config.get('exclude_senders', [])
            for sender in exclude_senders:
                query_parts.append(f'-from:{sender}')
            
            query = ' '.join(query_parts)
            self.logger.info(f"Gmail query: {query}")
            
            # Get list of unread emails
            result = service.users().messages().list(
                userId=self.config.get('user_id', 'me'),
                q=query,
                maxResults=self.config.get('max_results', 50)
            ).execute()
            
            messages = result.get('messages', [])
            self.logger.info(f"Found {len(messages)} unread emails")
            
            if not messages:
                return []
            
            # Fetch email details
            emails = []
            for message in messages:
                try:
                    email_data = self._get_email_details(service, message['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    self.logger.warning(f"Failed to fetch email {message['id']}: {e}")
                    continue
            
            return emails
            
        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error fetching emails: {e}")
            return []
    
    def _get_email_details(self, service, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific email"""
        try:
            message = service.users().messages().get(
                userId=self.config.get('user_id', 'me'),
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
                # Create preview (first N characters)
                preview_length = self.config.get('preview_max_length', 200)
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
        
        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    # Use HTML as fallback if no plain text
                    if 'data' in part['body']:
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                        body = body.replace('&nbsp;', ' ').replace('&amp;', '&')
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        # Clean up the body text
        body = body.strip()
        # Remove excessive whitespace
        body = ' '.join(body.split())
        
        return body
    
    def generate_email_summary(self, emails: List[Dict[str, Any]], detail_level: str = "medium") -> str:
        """Generate summary of emails using LLM"""
        if not emails:
            return "No unread emails found."
        
        try:
            # Sort emails by date (newest first)
            emails_sorted = sorted(emails, key=lambda x: x.get('internal_date', 0), reverse=True)
            
            self.logger.info(f"Generating summary for {len(emails_sorted)} emails with detail level: {detail_level}")
            
            # Use LLM service to generate summary
            response = self.llm_service.summarize_emails(emails_sorted, detail_level)
            
            if response.success:
                return response.content
            else:
                self.logger.error(f"LLM summarization failed: {response.error}")
                return self._create_fallback_summary(emails_sorted)
                
        except Exception as e:
            self.logger.error(f"Error generating email summary: {e}")
            return self._create_fallback_summary(emails)
    
    def _create_fallback_summary(self, emails: List[Dict[str, Any]]) -> str:
        """Create a simple summary without LLM"""
        if not emails:
            return "No unread emails found."
        
        summary_parts = [f"You have {len(emails)} unread emails:"]
        
        # Group emails by sender
        sender_counts = {}
        important_emails = []
        
        for email in emails[:10]:  # Limit to first 10
            sender = email.get('sender', 'Unknown')
            # Extract email address from sender
            import re
            match = re.search(r'<(.+?)>', sender)
            if match:
                sender_email = match.group(1)
            else:
                sender_email = sender
            
            sender_counts[sender_email] = sender_counts.get(sender_email, 0) + 1
            
            # Mark potentially important emails
            subject = email.get('subject', '').lower()
            if any(word in subject for word in ['urgent', 'important', 'action required', 'asap', 'deadline']):
                important_emails.append(email)
        
        # Add sender summary
        if sender_counts:
            summary_parts.append("\nTop senders:")
            for sender, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                summary_parts.append(f"  • {sender}: {count} email{'s' if count > 1 else ''}")
        
        # Add important emails
        if important_emails:
            summary_parts.append("\nPotentially important emails:")
            for email in important_emails[:3]:
                sender = email.get('sender', 'Unknown')
                subject = email.get('subject', 'No Subject')
                summary_parts.append(f"  • {sender}: {subject}")
        
        return '\n'.join(summary_parts)
    
    def get_email_statistics(self) -> Dict[str, Any]:
        """Get statistics about emails"""
        try:
            emails = self.fetch_unread_emails()
            
            stats = {
                'total_unread': len(emails),
                'senders': {},
                'labels': {},
                'recent_count': 0  # emails from last 3 hours
            }
            
            cutoff = datetime.now() - timedelta(hours=3)
            cutoff_timestamp = int(cutoff.timestamp() * 1000)
            
            for email in emails:
                # Count by sender
                sender = email.get('sender', 'Unknown')
                stats['senders'][sender] = stats['senders'].get(sender, 0) + 1
                
                # Count by labels
                for label in email.get('labels', []):
                    stats['labels'][label] = stats['labels'].get(label, 0) + 1
                
                # Count recent emails
                if email.get('internal_date', 0) > cutoff_timestamp:
                    stats['recent_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting email statistics: {e}")
            return {'total_unread': 0, 'senders': {}, 'labels': {}, 'recent_count': 0}