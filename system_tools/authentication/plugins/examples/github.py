#!/usr/bin/env python3
"""
GitHub Authentication Plugin Example
"""

from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests

from ..base_plugin import BaseAuthPlugin, LoginForm, AuthResult
from ...utils import extract_csrf_token, normalize_url

class GitHubAuthPlugin(BaseAuthPlugin):
    """GitHub-specific authentication plugin"""
    
    def get_login_url(self, base_url: str) -> str:
        """GitHub login URL"""
        return "https://github.com/login"
    
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """Detect GitHub login form"""
        
        # Look for the main login form
        form = soup.find('form', {'name': 'login'}) or soup.find('form', action='/session')
        if not form:
            return None
        
        # Get form action
        action = form.get('action', '/session')
        action_url = normalize_url(action, url)
        
        # Find form fields
        username_field = form.find('input', {'name': 'login'})
        password_field = form.find('input', {'name': 'password'})
        submit_button = form.find('input', {'type': 'submit'}) or form.find('button', {'type': 'submit'})
        
        # Extract CSRF token (GitHub uses authenticity_token)
        csrf_token = extract_csrf_token(soup, form)
        if not csrf_token:
            # GitHub specifically uses authenticity_token
            csrf_input = form.find('input', {'name': 'authenticity_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
        
        # Collect additional hidden fields
        additional_fields = {}
        hidden_inputs = form.find_all('input', {'type': 'hidden'})
        for hidden_input in hidden_inputs:
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name and name not in ['authenticity_token']:
                additional_fields[name] = value
        
        return LoginForm(
            form_element=form,
            action_url=action_url,
            username_field=username_field,
            password_field=password_field,
            submit_button=submit_button,
            csrf_token=csrf_token,
            method='POST',
            additional_fields=additional_fields
        )
    
    def perform_login(self, session: requests.Session, form: LoginForm, 
                     username: str, password: str) -> AuthResult:
        """Perform GitHub login"""
        
        # Prepare form data
        form_data = {
            'login': username,
            'password': password,
            'commit': 'Sign in'  # GitHub's submit button value
        }
        
        # Add CSRF token
        if form.csrf_token:
            form_data['authenticity_token'] = form.csrf_token
        
        # Add additional fields
        form_data.update(form.additional_fields)
        
        try:
            # Submit login form
            response = session.post(
                form.action_url,
                data=form_data,
                allow_redirects=True,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Check for success indicators
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # GitHub success indicators
            success_indicators = [
                '.Header-link--profile',    # Profile dropdown
                'a[href="/settings/profile"]',  # Settings link
                '.user-profile-link',       # User profile link
                '[data-ga-click*="Header"]'  # Header elements
            ]
            
            if any(soup.select_one(indicator) for indicator in success_indicators):
                return AuthResult(success=True, response=response)
            
            # Check for specific GitHub error indicators
            error_indicators = [
                '.flash-error',
                '.js-flash-alert',
                '#js-flash-container .flash',
                '.auth-form-body .flash'
            ]
            
            error_message = None
            for indicator in error_indicators:
                error_element = soup.select_one(indicator)
                if error_element:
                    error_message = error_element.get_text(strip=True)
                    break
            
            # Check if we're still on login page (failed)
            if soup.find('input', {'name': 'login'}):
                return AuthResult(
                    success=False,
                    response=response,
                    error_message=error_message or "Login failed - still on login page"
                )
            
            # If no clear success/failure indicators, assume success
            return AuthResult(success=True, response=response)
            
        except requests.exceptions.RequestException as e:
            return AuthResult(
                success=False,
                error_message=f"Network error during GitHub login: {str(e)}"
            )
    
    def validate_session(self, session: requests.Session, url: str) -> bool:
        """Validate GitHub session"""
        try:
            # Test with GitHub API or main page
            test_url = "https://github.com/"
            response = session.get(test_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for logged-in indicators
            success_indicators = [
                '.Header-link--profile',
                'a[href="/settings/profile"]', 
                '.user-profile-link'
            ]
            
            return any(soup.select_one(indicator) for indicator in success_indicators)
            
        except Exception:
            return False
    
    def get_success_indicators(self):
        """GitHub-specific success indicators"""
        return [
            '.Header-link--profile',
            'a[href="/settings/profile"]',
            '.user-profile-link',
            '[data-ga-click*="Header, click, Nav menu - item:profile"]'
        ]
    
    def get_failure_indicators(self):
        """GitHub-specific failure indicators"""
        return [
            '.flash-error',
            '.js-flash-alert',
            '#js-flash-container .flash-error',
            '.auth-form-body .flash-error'
        ]