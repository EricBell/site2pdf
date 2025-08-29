#!/usr/bin/env python3
"""
Session Storage and Management for Authentication System
"""

import json
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from .exceptions import SessionExpiredError
from .utils import extract_domain, sanitize_session_id

class AuthSession:
    """Represents an authenticated session"""
    
    def __init__(self, site_url: str, session_data: Dict[str, Any] = None):
        self.site_url = site_url
        self.domain = extract_domain(site_url)
        self.session_id = sanitize_session_id(site_url)
        
        # Initialize from session data or create new
        if session_data:
            self.created_at = datetime.fromisoformat(session_data['created_at'])
            self.expires_at = datetime.fromisoformat(session_data['expires_at']) if session_data.get('expires_at') else None
            self.cookies = session_data.get('cookies', {})
            self.headers = session_data.get('headers', {})
            self.metadata = session_data.get('metadata', {})
        else:
            self.created_at = datetime.now()
            self.expires_at = None
            self.cookies = {}
            self.headers = {}
            self.metadata = {}
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def set_expiry(self, hours: int = 24):
        """Set session expiry time"""
        self.expires_at = datetime.now() + timedelta(hours=hours)
    
    def to_requests_session(self) -> requests.Session:
        """Create requests.Session with authentication data"""
        session = requests.Session()
        
        # Set cookies
        for name, value in self.cookies.items():
            session.cookies.set(name, value, domain=self.domain)
        
        # Set headers
        session.headers.update(self.headers)
        
        return session
    
    def update_from_response(self, response: requests.Response):
        """Update session data from response"""
        # Update cookies
        for cookie in response.cookies:
            self.cookies[cookie.name] = cookie.value
        
        # Store any important headers
        auth_headers = ['Authorization', 'X-CSRF-Token', 'X-Requested-With']
        for header in auth_headers:
            if header in response.headers:
                self.headers[header] = response.headers[header]
        
        # Update metadata
        self.metadata['last_updated'] = datetime.now().isoformat()
        self.metadata['last_response_status'] = response.status_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'site_url': self.site_url,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'cookies': self.cookies,
            'headers': self.headers,
            'metadata': self.metadata
        }

class SessionStore:
    """Manages authentication session persistence"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path.cwd() / 'cache'
        self.auth_cache_dir = self.cache_dir / 'auth_sessions'
        self.auth_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_file(self, site_url: str) -> Path:
        """Get session file path for site"""
        session_id = sanitize_session_id(site_url)
        return self.auth_cache_dir / f"{session_id}_auth_session.json.gz"
    
    def save_session(self, auth_session: AuthSession):
        """Save authentication session to cache"""
        session_file = self._get_session_file(auth_session.site_url)
        session_data = auth_session.to_dict()
        
        try:
            with gzip.open(session_file, 'wt', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Log error but don't fail - session caching is optional
            print(f"Warning: Failed to save session cache: {e}")
    
    def load_session(self, site_url: str) -> Optional[AuthSession]:
        """Load cached authentication session"""
        session_file = self._get_session_file(site_url)
        
        if not session_file.exists():
            return None
        
        try:
            with gzip.open(session_file, 'rt', encoding='utf-8') as f:
                session_data = json.load(f)
            
            auth_session = AuthSession(site_url, session_data)
            
            # Check if session is expired
            if auth_session.is_expired():
                self.delete_session(site_url)
                return None
            
            return auth_session
            
        except Exception as e:
            print(f"Warning: Failed to load session cache: {e}")
            # Remove corrupted session file
            try:
                session_file.unlink()
            except:
                pass
            return None
    
    def delete_session(self, site_url: str):
        """Delete cached session"""
        session_file = self._get_session_file(site_url)
        try:
            if session_file.exists():
                session_file.unlink()
        except Exception as e:
            print(f"Warning: Failed to delete session cache: {e}")
    
    def is_session_cached(self, site_url: str) -> bool:
        """Check if session is cached and valid"""
        session = self.load_session(site_url)
        return session is not None
    
    def cleanup_expired_sessions(self):
        """Remove all expired session files"""
        for session_file in self.auth_cache_dir.glob("*_auth_session.json.gz"):
            try:
                with gzip.open(session_file, 'rt', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                if session_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(session_data['expires_at'])
                    if datetime.now() > expires_at:
                        session_file.unlink()
                        
            except Exception:
                # Remove corrupted files
                try:
                    session_file.unlink()
                except:
                    pass
    
    def list_cached_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all cached sessions with metadata"""
        sessions = {}
        
        for session_file in self.auth_cache_dir.glob("*_auth_session.json.gz"):
            try:
                with gzip.open(session_file, 'rt', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                domain = extract_domain(session_data['site_url'])
                sessions[domain] = {
                    'site_url': session_data['site_url'],
                    'created_at': session_data['created_at'],
                    'expires_at': session_data.get('expires_at'),
                    'is_expired': False,
                    'metadata': session_data.get('metadata', {})
                }
                
                # Check if expired
                if session_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(session_data['expires_at'])
                    sessions[domain]['is_expired'] = datetime.now() > expires_at
                    
            except Exception:
                continue
        
        return sessions
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        sessions = self.list_cached_sessions()
        total_sessions = len(sessions)
        expired_sessions = sum(1 for s in sessions.values() if s['is_expired'])
        active_sessions = total_sessions - expired_sessions
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'cache_directory': str(self.auth_cache_dir),
            'cache_size_mb': self._get_cache_size_mb()
        }
    
    def _get_cache_size_mb(self) -> float:
        """Calculate total cache size in MB"""
        total_size = 0
        for session_file in self.auth_cache_dir.glob("*_auth_session.json.gz"):
            try:
                total_size += session_file.stat().st_size
            except:
                pass
        return round(total_size / (1024 * 1024), 2)