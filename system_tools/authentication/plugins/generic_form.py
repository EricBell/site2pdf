#!/usr/bin/env python3
"""
Generic Form-Based Authentication Plugin
"""

from typing import Optional, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests
import time

from .base_plugin import BaseAuthPlugin, LoginForm, AuthResult
from ..utils import (
    find_form_by_password, 
    extract_csrf_token, 
    detect_username_field,
    detect_submit_button,
    extract_error_message,
    is_login_successful,
    normalize_url
)
from ..exceptions import FormDetectionError, LoginFailedError

class GenericFormPlugin(BaseAuthPlugin):
    """Generic form-based authentication that works with most sites"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.max_retries = config.get('max_retries', 3) if config else 3
        self.retry_delay = config.get('retry_delay', 2.0) if config else 2.0
    
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """
        Detect login form using generic patterns
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Current page URL for resolving relative URLs
            
        Returns:
            LoginForm object if found, None otherwise
        """
        # First try to find form with password field
        form = find_form_by_password(soup)
        if not form:
            return None
        
        # Extract form details
        action = form.get('action', '')
        action_url = normalize_url(action, url) if action else url
        method = form.get('method', 'POST').upper()
        
        # Find username field
        username_field = detect_username_field(form)
        
        # Find password field
        password_field = form.find('input', {'type': 'password'})
        
        # Find submit button
        submit_button = detect_submit_button(form)
        
        # Extract CSRF token
        csrf_token = extract_csrf_token(soup, form)
        
        # Collect any additional hidden fields
        additional_fields = {}
        hidden_inputs = form.find_all('input', {'type': 'hidden'})
        for hidden_input in hidden_inputs:
            name = hidden_input.get('name')
            value = hidden_input.get('value', '')
            if name and not any(token_name in name.lower() 
                              for token_name in ['csrf', 'token', '_token']):
                additional_fields[name] = value
        
        return LoginForm(
            form_element=form,
            action_url=action_url,
            username_field=username_field,
            password_field=password_field,
            submit_button=submit_button,
            csrf_token=csrf_token,
            method=method,
            additional_fields=additional_fields
        )
    
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
        # Prepare form data
        form_data = self.extract_form_data(form, username, password)
        
        # Attempt login with retries
        for attempt in range(self.max_retries):
            try:
                # Submit login form
                response = session.request(
                    method=form.method,
                    url=form.action_url,
                    data=form_data,
                    allow_redirects=True,
                    timeout=30
                )
                
                response.raise_for_status()
                
                # Parse response to check for success/failure
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for success indicators
                success_indicators = self.get_success_indicators()
                if any(soup.select_one(indicator) for indicator in success_indicators):
                    return AuthResult(
                        success=True,
                        response=response
                    )
                
                # Check for failure indicators
                failure_indicators = self.get_failure_indicators()
                error_elements = [soup.select_one(indicator) for indicator in failure_indicators]
                error_elements = [elem for elem in error_elements if elem]
                
                if error_elements:
                    error_message = extract_error_message(soup)
                    return AuthResult(
                        success=False,
                        response=response,
                        error_message=error_message or "Login failed (error detected on page)"
                    )
                
                # If no clear indicators, check if we're still on a login page
                # (presence of password field usually indicates login page)
                if soup.find('input', {'type': 'password'}):
                    # Still on login page - likely failed
                    error_message = extract_error_message(soup)
                    if attempt < self.max_retries - 1:
                        # Retry with delay
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return AuthResult(
                            success=False,
                            response=response,
                            error_message=error_message or "Login failed (still on login page)"
                        )
                else:
                    # No password field found - likely successful
                    return AuthResult(
                        success=True,
                        response=response
                    )
                
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    return AuthResult(
                        success=False,
                        error_message=f"Network error during login: {str(e)}"
                    )
            except Exception as e:
                return AuthResult(
                    success=False,
                    error_message=f"Unexpected error during login: {str(e)}"
                )
        
        return AuthResult(
            success=False,
            error_message=f"Login failed after {self.max_retries} attempts"
        )
    
    def validate_session(self, session: requests.Session, url: str) -> bool:
        """
        Check if session is still authenticated
        
        Args:
            session: requests.Session to validate
            url: URL to test authentication against
            
        Returns:
            True if session is valid, False otherwise
        """
        try:
            # Make a request to the protected area
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for success indicators (user menu, logout links, etc.)
            success_indicators = self.get_success_indicators()
            if any(soup.select_one(indicator) for indicator in success_indicators):
                return True
            
            # Check if we're redirected to login page
            if soup.find('input', {'type': 'password'}):
                return False  # Back on login page
            
            # Check for failure indicators
            failure_indicators = self.get_failure_indicators()
            if any(soup.select_one(indicator) for indicator in failure_indicators):
                return False
            
            # Default to True if no clear indicators (conservative)
            return True
            
        except Exception:
            # If we can't validate, assume session is invalid
            return False
    
    def handle_multi_step_login(self, session: requests.Session, form: LoginForm,
                               username: str, password: str) -> AuthResult:
        """
        Handle multi-step login flows (username first, then password)
        
        Args:
            session: requests.Session to use
            form: Initial login form
            username: Username
            password: Password
            
        Returns:
            AuthResult for multi-step login
        """
        try:
            # Step 1: Submit username only
            username_data = {}
            if form.username_field:
                field_name = form.username_field.get('name', 'username')
                username_data[field_name] = username
            
            # Add CSRF token and hidden fields
            if form.csrf_token:
                csrf_input = form.form_element.find('input', {'value': form.csrf_token})
                if csrf_input and csrf_input.get('name'):
                    username_data[csrf_input.get('name')] = form.csrf_token
            
            # Add hidden fields
            for name, value in form.additional_fields.items():
                username_data[name] = value
            
            # Submit username
            response = session.request(
                method=form.method,
                url=form.action_url,
                data=username_data,
                allow_redirects=True,
                timeout=30
            )
            
            response.raise_for_status()
            
            # Step 2: Look for password form
            soup = BeautifulSoup(response.text, 'html.parser')
            password_form = self.detect_login_form(soup, response.url)
            
            if not password_form or not password_form.password_field:
                return AuthResult(
                    success=False,
                    response=response,
                    error_message="Could not find password form in multi-step login"
                )
            
            # Step 3: Submit password
            return self.perform_login(session, password_form, username, password)
            
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Multi-step login error: {str(e)}"
            )