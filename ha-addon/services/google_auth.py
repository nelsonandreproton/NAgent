"""
Google API Authentication Manager
Handles OAuth 2.0 flow and Service Account authentication for Gmail and Calendar APIs.
"""

import os
import json
import logging
from typing import Optional, List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleAuthManager:
    """Manages Google API authentication and service creation"""
    
    def __init__(self, credentials_path: str, scopes: List[str]):
        self.credentials_path = credentials_path
        self.token_path = os.path.join(os.path.dirname(credentials_path), "token.json")
        self.scopes = scopes
        self.logger = logging.getLogger(__name__)
        self._credentials: Optional[Credentials] = None
    
    def authenticate(self) -> bool:
        """Authenticate with Google APIs using OAuth 2.0 or Service Account"""
        
        self.logger.info(f"Starting authentication with credentials path: {self.credentials_path}")
        
        # Check if this is a service account credential file
        if self._is_service_account_file():
            try:
                self._credentials = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path, scopes=self.scopes
                )
                self.logger.info("Loaded service account credentials")
                return True
            except Exception as e:
                self.logger.error(f"Failed to load service account credentials: {e}")
                return False
        
        # Check if we have existing valid OAuth credentials
        if os.path.exists(self.token_path):
            try:
                self._credentials = Credentials.from_authorized_user_file(
                    self.token_path, self.scopes
                )
                self.logger.info("Loaded existing OAuth credentials")
            except Exception as e:
                self.logger.warning(f"Failed to load existing OAuth credentials: {e}")
        
        # If credentials are not valid or don't exist, get new ones
        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                try:
                    self._credentials.refresh(Request())
                    self.logger.info("Refreshed expired credentials")
                except Exception as e:
                    self.logger.warning(f"Failed to refresh credentials: {e}")
                    self._credentials = None
            
            # If still no valid credentials, start OAuth flow
            if not self._credentials or not self._credentials.valid:
                if not os.path.exists(self.credentials_path):
                    self.logger.error(f"Credentials file not found: {self.credentials_path}")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.scopes
                    )
                    self._credentials = flow.run_local_server(port=0)
                    self.logger.info("Completed OAuth flow")
                except Exception as e:
                    self.logger.error(f"OAuth flow failed: {e}")
                    return False
        
        # Save credentials for next run
        try:
            with open(self.token_path, 'w') as token_file:
                token_file.write(self._credentials.to_json())
            self.logger.info("Saved credentials to token file")
        except Exception as e:
            self.logger.warning(f"Failed to save credentials: {e}")
        
        return True
    
    def _is_service_account_file(self) -> bool:
        """Check if the credentials file is a service account file"""
        self.logger.info(f"Checking if file is service account: {self.credentials_path}")
        
        if not os.path.exists(self.credentials_path):
            self.logger.error(f"Credentials file does not exist: {self.credentials_path}")
            return False
        
        try:
            with open(self.credentials_path, 'r') as f:
                data = json.load(f)
            is_service_account = data.get('type') == 'service_account'
            self.logger.info(f"Credentials file content - type: {data.get('type', 'unknown')}, is_service_account: {is_service_account}")
            
            # Also log the project_id to verify we're reading the right file
            if 'project_id' in data:
                self.logger.info(f"Service account project_id: {data['project_id']}")
            
            return is_service_account
        except Exception as e:
            self.logger.error(f"Failed to read credentials file {self.credentials_path}: {e}")
            return False
    
    def get_gmail_service(self):
        """Get authenticated Gmail service"""
        if not self._credentials:
            if not self.authenticate():
                raise Exception("Failed to authenticate with Google APIs")
        
        try:
            service = build('gmail', 'v1', credentials=self._credentials)
            self.logger.info("Created Gmail service")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create Gmail service: {e}")
            raise
    
    def get_calendar_service(self):
        """Get authenticated Calendar service"""
        if not self._credentials:
            if not self.authenticate():
                raise Exception("Failed to authenticate with Google APIs")
        
        try:
            service = build('calendar', 'v3', credentials=self._credentials)
            self.logger.info("Created Calendar service")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create Calendar service: {e}")
            raise
    
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials"""
        return self._credentials is not None and self._credentials.valid
    
    def revoke_credentials(self):
        """Revoke and remove stored credentials"""
        if self._credentials:
            try:
                self._credentials.revoke(Request())
                self.logger.info("Revoked credentials")
            except Exception as e:
                self.logger.warning(f"Failed to revoke credentials: {e}")
        
        # Remove token file
        if os.path.exists(self.token_path):
            try:
                os.remove(self.token_path)
                self.logger.info("Removed token file")
            except Exception as e:
                self.logger.warning(f"Failed to remove token file: {e}")
        
        self._credentials = None
    
    def test_connection(self) -> dict:
        """Test connection to both Gmail and Calendar APIs"""
        results = {
            'gmail': {'success': False, 'error': None},
            'calendar': {'success': False, 'error': None}
        }
        
        # Test Gmail
        try:
            gmail_service = self.get_gmail_service()
            # Try to get user profile
            profile = gmail_service.users().getProfile(userId='me').execute()
            results['gmail']['success'] = True
            results['gmail']['email'] = profile.get('emailAddress')
            self.logger.info(f"Gmail connection successful for {profile.get('emailAddress')}")
        except Exception as e:
            results['gmail']['error'] = str(e)
            self.logger.error(f"Gmail connection failed: {e}")
        
        # Test Calendar
        try:
            calendar_service = self.get_calendar_service()
            # Try to get calendar list
            calendar_list = calendar_service.calendarList().list(maxResults=1).execute()
            results['calendar']['success'] = True
            results['calendar']['calendars_count'] = len(calendar_list.get('items', []))
            self.logger.info("Calendar connection successful")
        except Exception as e:
            results['calendar']['error'] = str(e)
            self.logger.error(f"Calendar connection failed: {e}")
        
        return results