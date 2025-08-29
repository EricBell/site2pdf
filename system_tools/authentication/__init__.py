#!/usr/bin/env python3
"""
Authentication System for Site2PDF
==================================

A modular authentication system that handles login flows for various websites.
Designed to be reusable across projects with a plugin-based architecture.

Features:
- Session persistence and management
- Generic form-based authentication
- Site-specific plugin support
- Secure credential handling
- CSRF token handling
- Multi-step form support

Usage:
    from system_tools.authentication import create_auth_manager
    
    # Quick setup
    auth = create_auth_manager("https://example.com")
    session = await auth.authenticate("username", "password")
    
    # Advanced usage
    auth_manager = AuthenticationManager("https://site.com")
    if auth_manager.is_authenticated():
        session = auth_manager.get_authenticated_session()
"""

from .auth_manager import AuthenticationManager
from .session_store import SessionStore, AuthSession
from .credential_manager import CredentialManager, Credentials
from .plugins.base_plugin import BaseAuthPlugin
from .plugins.generic_form import GenericFormPlugin
from .exceptions import AuthenticationError, SessionExpiredError, LoginFailedError

__version__ = "1.0.0"
__author__ = "Site2PDF Team"

__all__ = [
    'AuthenticationManager',
    'SessionStore',
    'AuthSession',
    'CredentialManager', 
    'Credentials',
    'BaseAuthPlugin',
    'GenericFormPlugin',
    'AuthenticationError',
    'SessionExpiredError',
    'LoginFailedError',
    'create_auth_manager'
]

def create_auth_manager(site_url: str, cache_dir=None, **kwargs) -> AuthenticationManager:
    """
    Factory function for easy authentication setup
    
    Args:
        site_url: The target website URL
        cache_dir: Directory for session cache (optional)
        **kwargs: Additional configuration options
    
    Returns:
        Configured AuthenticationManager instance
    """
    return AuthenticationManager(site_url, cache_dir=cache_dir, **kwargs)