#!/usr/bin/env python3
"""
Authentication Manager - Central coordinator for authentication system
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from .session_store import SessionStore, AuthSession
from .credential_manager import CredentialManager, Credentials
from .plugins.base_plugin import BaseAuthPlugin
from .plugins.generic_form import GenericFormPlugin
from .plugins.email_otp import EmailOTPPlugin
from .exceptions import AuthenticationError, LoginFailedError, SessionExpiredError
from .utils import extract_domain, normalize_url

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Central authentication coordinator"""
    
    def __init__(self, site_url: str, cache_dir: Path = None, config: Dict[str, Any] = None):
        """
        Initialize authentication manager
        
        Args:
            site_url: Target website URL
            cache_dir: Directory for session cache
            config: Authentication configuration
        """
        self.site_url = site_url.rstrip('/')
        self.domain = extract_domain(site_url)
        self.config = config or {}
        
        # Initialize components
        self.session_store = SessionStore(cache_dir)
        self.credential_manager = CredentialManager()
        
        # Plugin system
        self.plugins: Dict[str, BaseAuthPlugin] = {}
        self._register_default_plugins()
        
        # Current session state
        self._current_session: Optional[AuthSession] = None
        self._authenticated_requests_session: Optional[requests.Session] = None
    
    def _register_default_plugins(self):
        """Register default authentication plugins"""
        # Generic form plugin (fallback)
        self.plugins['generic_form'] = GenericFormPlugin(self.config.get('generic_form', {}))
        
        # Email OTP plugin
        self.plugins['email_otp'] = EmailOTPPlugin(self.config.get('email_otp', {}))
        
        # Site-specific plugins would be registered here
        # self.plugins['github.com'] = GitHubAuthPlugin()
    
    def register_plugin(self, domain: str, plugin: BaseAuthPlugin):
        """Register a site-specific authentication plugin"""
        self.plugins[domain] = plugin
    
    def _get_plugin(self, plugin_type: str = None) -> BaseAuthPlugin:
        """Get the appropriate plugin for the current site"""
        # If specific plugin type requested
        if plugin_type:
            if plugin_type in self.plugins:
                return self.plugins[plugin_type]
            else:
                raise AuthenticationError(f"Unknown plugin type: {plugin_type}")
        
        # Try site-specific plugin first
        if self.domain in self.plugins:
            return self.plugins[self.domain]
        
        # Fall back to generic form plugin
        return self.plugins['generic_form']
    
    def authenticate(self, username: str = None, password: str = None, auth_type: str = None) -> AuthSession:
        """
        Authenticate with the target site with enhanced pre-validation
        
        Args:
            username: Username (optional, will try to get from env/prompt)
            password: Password (optional, will try to get from env/prompt)  
            auth_type: Authentication type ('generic_form', 'email_otp', etc.)
            
        Returns:
            AuthSession object
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Check for cached session first
            if self.is_authenticated():
                logger.info(f"Using cached authentication for {self.domain}")
                print(f"🔐 Using cached authentication for {self.domain}")
                return self._current_session
            
            print(f"🔍 Starting authentication for {self.domain} using {auth_type or 'auto-detected'} method")
            
            # Pre-validation: Check if authentication is likely to be required
            auth_required = self._pre_validate_authentication_need(auth_type)
            if not auth_required['required']:
                if auth_required['reason'] == 'no_signup_no_login':
                    # Site appears to be fully public
                    print(f"🔍 Site appears to be public (no sign up or login indicators found)")
                    print(f"⚠️  Warning: You requested authentication, but the site may not require it")
                elif auth_required['reason'] == 'login_not_found':
                    # Site has signup but no accessible login path
                    error_msg = (
                        f"Authentication setup failed: {auth_required['details']}\n"
                        f"🔍 Site analysis:\n"
                        f"  - Sign up button: {'✅ Found' if auth_required.get('has_signup') else '❌ Not found'}\n"
                        f"  - Direct login: {'✅ Found' if auth_required.get('has_direct_login') else '❌ Not found'}\n"
                        f"  - Sign up → Login path: {'✅ Found' if auth_required.get('signup_to_login_path') else '❌ Not found'}\n"
                        f"💡 Suggestion: Verify the site requires authentication and check login flow manually"
                    )
                    raise AuthenticationError(error_msg)
            else:
                print(f"🔍 Authentication appears required: {auth_required['details']}")
            
            # Get credentials (for email OTP, password not required)
            require_password = auth_type != "email_otp"
            credentials = self.credential_manager.get_credentials(
                self.site_url, username, password, require_password=require_password
            )
            
            if not credentials.validate(require_password=require_password):
                if auth_type == "email_otp":
                    raise AuthenticationError("Email address is required for email OTP authentication")
                else:
                    raise AuthenticationError("Invalid or missing credentials")
            
            # Perform authentication
            auth_session = self._perform_authentication(credentials, auth_type)
            
            # Cache the session
            self.session_store.save_session(auth_session)
            self._current_session = auth_session
            
            # Invalidate old requests session to force recreation
            self._authenticated_requests_session = None
            
            logger.info(f"Authentication successful for {self.domain}")
            print(f"🔐 Authentication successful for {self.domain}")
            return auth_session
            
        except Exception as e:
            logger.error(f"Authentication failed for {self.domain}: {str(e)}")
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e
    
    def _pre_validate_authentication_need(self, auth_type: str = None) -> Dict[str, Any]:
        """
        Pre-validate whether authentication is likely to be needed for this site
        
        Args:
            auth_type: The authentication type being requested
            
        Returns:
            Dictionary with validation results:
            - required: bool - whether authentication appears necessary
            - reason: str - reason for the determination
            - details: str - human-readable explanation
            - has_signup: bool - whether site has signup indicators
            - has_direct_login: bool - whether site has direct login
            - signup_to_login_path: bool - whether signup->login path exists
        """
        try:
            print(f"🔍 Pre-validating authentication need for {self.site_url}")
            
            # Create a session to test the site
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            response = session.get(self.site_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for authentication indicators
            has_login_direct = self._has_direct_login_indicators(soup)
            has_signup = self._has_signup_indicators(soup)
            
            # If we have direct login, authentication is clearly supported
            if has_login_direct:
                return {
                    'required': True,
                    'reason': 'direct_login_found',
                    'details': 'Site has direct login indicators',
                    'has_signup': has_signup,
                    'has_direct_login': True,
                    'signup_to_login_path': False
                }
            
            # If we have signup, check if we can navigate to login
            if has_signup:
                print(f"🔍 Found signup indicators, checking for login navigation path...")
                plugin = self._get_plugin(auth_type)
                
                # Use the plugin's enhanced login discovery
                try:
                    discovered_login_url = plugin.get_login_url(self.site_url)
                    
                    # If we got back the original URL, login discovery failed
                    if discovered_login_url == self.site_url:
                        return {
                            'required': True,
                            'reason': 'login_not_found',
                            'details': 'Site has signup button but no accessible login path found',
                            'has_signup': True,
                            'has_direct_login': False,
                            'signup_to_login_path': False
                        }
                    else:
                        return {
                            'required': True,
                            'reason': 'signup_to_login_found',
                            'details': f'Found login path via signup navigation: {discovered_login_url}',
                            'has_signup': True,
                            'has_direct_login': False,
                            'signup_to_login_path': True
                        }
                except Exception as nav_error:
                    print(f"🔍 Login navigation test failed: {nav_error}")
                    return {
                        'required': True,
                        'reason': 'login_not_found', 
                        'details': f'Site has signup button but login navigation failed: {str(nav_error)}',
                        'has_signup': True,
                        'has_direct_login': False,
                        'signup_to_login_path': False
                    }
            
            # No clear authentication indicators
            return {
                'required': False,
                'reason': 'no_signup_no_login',
                'details': 'No authentication indicators found on the page',
                'has_signup': False,
                'has_direct_login': False,
                'signup_to_login_path': False
            }
            
        except Exception as e:
            print(f"🔍 Pre-validation failed: {e}")
            # If pre-validation fails, assume authentication might be needed
            return {
                'required': True,
                'reason': 'validation_failed',
                'details': f'Could not validate authentication need: {str(e)}',
                'has_signup': None,
                'has_direct_login': None,
                'signup_to_login_path': None
            }
    
    def _has_direct_login_indicators(self, soup: BeautifulSoup) -> bool:
        """Check if page has direct login indicators"""
        login_patterns = [
            r'login',
            r'sign.?in',
            r'log.?in',
            r'signin'
        ]
        
        for pattern in login_patterns:
            # Check href attributes
            if soup.find('a', href=re.compile(pattern, re.I)):
                return True
            # Check button/link text content
            if soup.find('a', string=re.compile(pattern, re.I)):
                return True
            # Check button elements
            if soup.find('button', string=re.compile(pattern, re.I)):
                return True
        
        return False
    
    def _has_signup_indicators(self, soup: BeautifulSoup) -> bool:
        """Check if page has signup indicators"""
        signup_patterns = [
            r'sign.?up',
            r'register',
            r'join',
            r'create.?account'
        ]
        
        for pattern in signup_patterns:
            # Check href attributes
            if soup.find('a', href=re.compile(pattern, re.I)):
                return True
            # Check button/link text content
            if soup.find('a', string=re.compile(pattern, re.I)):
                return True
            # Check button elements
            if soup.find('button', string=re.compile(pattern, re.I)):
                return True
        
        return False
    
    def _perform_authentication(self, credentials: Credentials, auth_type: str = None) -> AuthSession:
        """
        Perform the actual authentication process
        
        Args:
            credentials: User credentials
            auth_type: Authentication type to use
            
        Returns:
            AuthSession object
            
        Raises:
            LoginFailedError: If login fails
        """
        plugin = self._get_plugin(auth_type)
        
        # Create a new session
        session = requests.Session()
        
        # Set reasonable defaults
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Get login URL
        login_url = plugin.get_login_url(self.site_url)
        
        # Load login page
        response = session.get(login_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Detect login form
        login_form = plugin.detect_login_form(soup, login_url)
        
        # If we specifically requested email_otp but didn't find a form, log the issue
        if not login_form and auth_type == "email_otp":
            logger.warning("Email OTP authentication requested but no suitable form found. Available forms:")
            forms = soup.find_all('form')
            for i, form in enumerate(forms):
                logger.warning(f"  Form {i+1}: {form.get('action', 'no action')} - {len(form.find_all('input'))} inputs")
        
        if not login_form:
            # Try multi-step login detection
            # Look for username-only form first
            forms = soup.find_all('form')
            for form in forms:
                username_field = form.find('input', {'type': ['text', 'email']})
                if username_field and not form.find('input', {'type': 'password'}):
                    # This might be a multi-step form
                    from .plugins.base_plugin import LoginForm
                    from .utils import extract_csrf_token, normalize_url
                    
                    action = form.get('action', '')
                    action_url = normalize_url(action, login_url) if action else login_url
                    csrf_token = extract_csrf_token(soup, form)
                    
                    temp_form = LoginForm(
                        form_element=form,
                        action_url=action_url,
                        username_field=username_field,
                        password_field=None,
                        csrf_token=csrf_token
                    )
                    
                    # Try multi-step login
                    result = plugin.handle_multi_step_login(
                        session, temp_form, credentials.username, credentials.password
                    )
                    
                    if result.success:
                        # Create auth session from successful result
                        auth_session = AuthSession(self.site_url)
                        auth_session.update_from_response(result.response)
                        auth_session.set_expiry(24)  # 24 hours default
                        return auth_session
            
            raise LoginFailedError("Could not detect login form on the page")
        
        # Attempt login
        result = plugin.perform_login(
            session, login_form, credentials.username, credentials.password
        )
        
        # Debug: Log the result we received
        print(f"🔍 AuthManager: Received result from plugin: success={result.success}")
        if hasattr(result, 'error_message') and result.error_message:
            print(f"🔍 AuthManager: Error message: {result.error_message}")
        
        # Handle multi-step authentication (e.g., email OTP)
        if result.requires_additional_steps and result.step_type == "email_otp":
            # Handle email OTP flow
            verification_url = result.step_data.get('verification_url') or (result.response.url if result.response else result.next_step_url)
            email = result.step_data.get('email', credentials.username)
            
            import click
            click.echo(f"📧 Verification code sent to {email}")
            
            # Verify OTP code with interactive input
            verify_result = plugin.verify_email_otp(
                session, 
                code=None,  # Will prompt interactively
                verification_url=verification_url,
                form_data=result.step_data
            )
            
            if not verify_result.success:
                raise LoginFailedError(verify_result.error_message or "Email OTP verification failed")
            
            result = verify_result
        
        if not result.success:
            raise LoginFailedError(result.error_message or "Login failed")
        
        # Create auth session
        auth_session = AuthSession(self.site_url)
        auth_session.update_from_response(result.response)
        auth_session.set_expiry(24)  # 24 hours default
        
        return auth_session
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated
        
        Returns:
            True if authenticated, False otherwise
        """
        # Check cached session first
        if not self._current_session:
            self._current_session = self.session_store.load_session(self.site_url)
        
        if not self._current_session:
            return False
        
        if self._current_session.is_expired():
            self._current_session = None
            self.session_store.delete_session(self.site_url)
            return False
        
        # Validate session with the site
        try:
            plugin = self._get_plugin()
            requests_session = self._current_session.to_requests_session()
            
            if not plugin.validate_session(requests_session, self.site_url):
                # Session is invalid, clear it
                self._current_session = None
                self.session_store.delete_session(self.site_url)
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Session validation failed: {str(e)}")
            self._current_session = None
            return False
    
    def get_authenticated_session(self) -> requests.Session:
        """
        Get a requests.Session configured with authentication
        
        Returns:
            Authenticated requests.Session
            
        Raises:
            SessionExpiredError: If session is not valid
        """
        if not self.is_authenticated():
            raise SessionExpiredError("No valid authentication session")
        
        # Reuse existing session if available
        if self._authenticated_requests_session:
            return self._authenticated_requests_session
        
        # Create new authenticated session
        self._authenticated_requests_session = self._current_session.to_requests_session()
        
        # Set reasonable defaults
        self._authenticated_requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        return self._authenticated_requests_session
    
    def logout(self):
        """Clear authentication session"""
        self._current_session = None
        self._authenticated_requests_session = None
        self.session_store.delete_session(self.site_url)
        logger.info(f"Logged out from {self.domain}")
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about current session
        
        Returns:
            Session information dictionary or None
        """
        if not self._current_session:
            return None
        
        return {
            'site_url': self._current_session.site_url,
            'domain': self._current_session.domain,
            'created_at': self._current_session.created_at.isoformat(),
            'expires_at': self._current_session.expires_at.isoformat() if self._current_session.expires_at else None,
            'is_expired': self._current_session.is_expired(),
            'metadata': self._current_session.metadata
        }
    
    def get_credential_env_vars(self) -> Dict[str, str]:
        """Get the environment variable names for this site"""
        return self.credential_manager.get_env_var_names(self.site_url)