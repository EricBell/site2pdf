#!/usr/bin/env python3
"""
Base Authentication Plugin
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, NamedTuple
from bs4 import BeautifulSoup, Tag
import requests

class LoginForm(NamedTuple):
    """Represents a detected login form"""
    form_element: Tag
    action_url: str
    username_field: Optional[Tag] = None
    password_field: Optional[Tag] = None
    submit_button: Optional[Tag] = None
    csrf_token: Optional[str] = None
    method: str = 'POST'
    additional_fields: Dict[str, str] = {}

class AuthResult(NamedTuple):
    """Result of authentication attempt"""
    success: bool
    response: Optional[requests.Response] = None
    error_message: Optional[str] = None
    requires_additional_steps: bool = False
    next_step_url: Optional[str] = None

class BaseAuthPlugin(ABC):
    """Abstract base class for site-specific authentication plugins"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize plugin with configuration
        
        Args:
            config: Plugin-specific configuration dictionary
        """
        self.config = config or {}
    
    @abstractmethod
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """
        Detect and parse login form from page
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Current page URL for resolving relative URLs
            
        Returns:
            LoginForm object if found, None otherwise
        """
        pass
    
    @abstractmethod
    def perform_login(self, session: requests.Session, form: LoginForm, 
                     username: str, password: str) -> AuthResult:
        """
        Execute the login process
        
        Args:
            session: requests.Session to use
            form: Detected login form
            username: Username to login with
            password: Password to login with
            
        Returns:
            AuthResult indicating success/failure
        """
        pass
    
    @abstractmethod
    def validate_session(self, session: requests.Session, url: str) -> bool:
        """
        Check if session is still authenticated
        
        Args:
            session: requests.Session to validate
            url: URL to test authentication against
            
        Returns:
            True if session is valid, False otherwise
        """
        pass
    
    def get_login_url(self, base_url: str) -> str:
        """
        Get the login URL for the site
        
        Args:
            base_url: Base URL of the site
            
        Returns:
            Login URL (may be same as base_url or a different page)
        """
        # Default: assume login is on the same page
        return self.config.get('login_url', base_url)
    
    def get_success_indicators(self) -> List[str]:
        """
        Get CSS selectors that indicate successful login
        
        Returns:
            List of CSS selectors
        """
        return self.config.get('success_indicators', [
            '.user-menu',
            '.user-profile', 
            'a[href*="logout"]',
            'a[href*="sign-out"]',
            '.dashboard',
            '.welcome'
        ])
    
    def get_failure_indicators(self) -> List[str]:
        """
        Get CSS selectors that indicate failed login
        
        Returns:
            List of CSS selectors
        """
        return self.config.get('failure_indicators', [
            '.error',
            '.alert-danger',
            '.login-error', 
            '.error-message',
            '.invalid-feedback'
        ])
    
    def handle_multi_step_login(self, session: requests.Session, form: LoginForm,
                               username: str, password: str) -> AuthResult:
        """
        Handle multi-step login flows (e.g., username first, then password)
        
        Default implementation returns not implemented - override in subclasses
        
        Args:
            session: requests.Session to use
            form: Initial login form
            username: Username
            password: Password
            
        Returns:
            AuthResult for multi-step login
        """
        return AuthResult(
            success=False,
            error_message="Multi-step login not implemented for this plugin"
        )
    
    def extract_form_data(self, form: LoginForm, username: str, password: str) -> Dict[str, str]:
        """
        Extract form data for submission
        
        Args:
            form: Login form to process
            username: Username value
            password: Password value
            
        Returns:
            Dictionary of form fields and values
        """
        form_data = {}
        
        # Add username
        if form.username_field:
            field_name = form.username_field.get('name', 'username')
            form_data[field_name] = username
        
        # Add password
        if form.password_field:
            field_name = form.password_field.get('name', 'password')
            form_data[field_name] = password
        
        # Add CSRF token
        if form.csrf_token:
            # Try to find the token field name
            csrf_input = form.form_element.find('input', {'value': form.csrf_token})
            if csrf_input and csrf_input.get('name'):
                form_data[csrf_input.get('name')] = form.csrf_token
            else:
                # Fallback to common names
                form_data['_token'] = form.csrf_token
        
        # Add additional fields
        form_data.update(form.additional_fields)
        
        # Add any hidden fields
        hidden_inputs = form.form_element.find_all('input', {'type': 'hidden'})
        for hidden_input in hidden_inputs:
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name and name not in form_data:
                form_data[name] = value
        
        return form_data