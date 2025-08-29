#!/usr/bin/env python3
"""
Email OTP Authentication Plugin

Handles email-based one-time passcode authentication flows where:
1. User enters email address
2. Site sends verification code to email
3. User enters code to complete authentication
"""

import re
import time
import click
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

from .base_plugin import BaseAuthPlugin, LoginForm, AuthResult


class EmailOTPPlugin(BaseAuthPlugin):
    """Plugin for email-based OTP authentication"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        config = config or {}
        self.timeout_seconds = config.get('otp_timeout', 300)  # 5 minutes default
        self.max_retries = config.get('max_retries', 3)
    
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """
        Detect email OTP login form
        
        Looks for forms with email input AND "Send One-Time Code" type button
        """
        forms = soup.find_all('form')
        
        for form in forms:
            # Look for email input
            email_field = (
                form.find('input', {'type': 'email'}) or
                form.find('input', {'name': re.compile(r'email', re.I)}) or
                form.find('input', {'placeholder': re.compile(r'email', re.I)})
            )
            
            if email_field:
                # Look for OTP-related buttons (regardless of password field presence)
                otp_button = self._find_otp_button(form)
                
                if otp_button:
                    # This is an email OTP form with dedicated OTP button
                    action = form.get('action', '')
                    if action:
                        action_url = urljoin(url, action)
                    else:
                        action_url = url
                    
                    # Look for CSRF token
                    csrf_token = self._extract_csrf_token(form)
                    
                    # Get additional hidden fields
                    additional_fields = {}
                    hidden_inputs = form.find_all('input', {'type': 'hidden'})
                    for hidden_input in hidden_inputs:
                        name = hidden_input.get('name')
                        value = hidden_input.get('value', '')
                        if name and name != 'csrf_token' and name != '_token':
                            additional_fields[name] = value
                    
                    return LoginForm(
                        form_element=form,
                        action_url=action_url,
                        username_field=email_field,
                        password_field=None,  # Not used for OTP flow
                        submit_button=otp_button,  # Use the OTP button specifically
                        csrf_token=csrf_token,
                        method=form.get('method', 'POST').upper(),
                        additional_fields=additional_fields
                    )
                else:
                    # Check for email-only form (legacy detection)
                    password_field = form.find('input', {'type': 'password'})
                    
                    if not password_field:
                        # This looks like an email-only OTP form
                        action = form.get('action', '')
                        if action:
                            action_url = urljoin(url, action)
                        else:
                            action_url = url
                        
                        # Look for CSRF token
                        csrf_token = self._extract_csrf_token(form)
                        
                        # Find submit button
                        submit_button = (
                            form.find('input', {'type': 'submit'}) or
                            form.find('button', {'type': 'submit'}) or
                            form.find('button')
                        )
                        
                        # Get additional hidden fields
                        additional_fields = {}
                        hidden_inputs = form.find_all('input', {'type': 'hidden'})
                        for hidden_input in hidden_inputs:
                            name = hidden_input.get('name')
                            value = hidden_input.get('value', '')
                            if name and name != 'csrf_token' and name != '_token':
                                additional_fields[name] = value
                        
                        return LoginForm(
                            form_element=form,
                            action_url=action_url,
                            username_field=email_field,
                            password_field=None,
                            submit_button=submit_button,
                            csrf_token=csrf_token,
                            method=form.get('method', 'POST').upper(),
                            additional_fields=additional_fields
                        )
        
        return None
    
    def perform_login(self, session: requests.Session, form: LoginForm, 
                     username: str, password: str) -> AuthResult:
        """
        Perform email OTP login - submit email and wait for code
        
        Args:
            session: requests.Session to use
            form: Detected login form
            username: Email address
            password: Ignored for email OTP
        """
        try:
            # Submit email address with OTP button click
            form_data = self.extract_form_data(form, username, "")
            
            # If we have a specific OTP button, add its name/value to form data
            if form.submit_button and form.submit_button.get('name'):
                button_name = form.submit_button.get('name')
                button_value = form.submit_button.get('value', '')
                form_data[button_name] = button_value
            
            response = session.request(
                method=form.method,
                url=form.action_url,
                data=form_data,
                allow_redirects=True
            )
            
            # Check if email was accepted and OTP was sent
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for OTP code input form
            otp_form = self._find_otp_verification_form(soup)
            
            if otp_form:
                return AuthResult(
                    success=False,  # Not complete yet
                    response=response,
                    requires_additional_steps=True,
                    step_type="email_otp",
                    step_data={
                        "verification_url": response.url,
                        "form_action": otp_form.get('action', ''),
                        "email": username
                    }
                )
            else:
                # Check for error messages
                error_msg = self._extract_error_message(soup)
                return AuthResult(
                    success=False,
                    response=response,
                    error_message=error_msg or "Email OTP submission failed"
                )
                
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Email OTP error: {str(e)}"
            )
    
    def handle_email_otp(self, session: requests.Session, email: str, 
                        previous_response: requests.Response = None) -> AuthResult:
        """
        Handle email OTP submission
        
        Args:
            session: requests.Session to use
            email: Email address for OTP
            previous_response: Previous response if continuing flow
        """
        try:
            # If we don't have a previous response, we need to get the login page first
            if not previous_response:
                # This should have been called from perform_login with form data
                return AuthResult(
                    success=False,
                    error_message="Email OTP requires initial form submission"
                )
            
            # Parse the current page to find email form
            soup = BeautifulSoup(previous_response.text, 'html.parser')
            form = self.detect_login_form(soup, previous_response.url)
            
            if not form:
                return AuthResult(
                    success=False,
                    error_message="Could not find email OTP form"
                )
            
            # Submit email address
            form_data = self.extract_form_data(form, email, "")
            
            response = session.request(
                method=form.method,
                url=form.action_url,
                data=form_data,
                allow_redirects=True
            )
            
            # Check if email was accepted and OTP was sent
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for OTP code input form
            otp_form = self._find_otp_verification_form(soup)
            
            if otp_form:
                return AuthResult(
                    success=False,  # Not complete yet
                    response=response,
                    requires_additional_steps=True,
                    step_type="email_otp",
                    step_data={
                        "verification_url": response.url,
                        "form_action": otp_form.get('action', ''),
                        "email": email
                    }
                )
            else:
                # Check for error messages
                error_msg = self._extract_error_message(soup)
                return AuthResult(
                    success=False,
                    response=response,
                    error_message=error_msg or "Email OTP submission failed"
                )
                
        except Exception as e:
            return AuthResult(
                success=False,
                error_message=f"Email OTP error: {str(e)}"
            )
    
    def verify_email_otp(self, session: requests.Session, code: str, 
                        verification_url: str = None, form_data: Dict[str, Any] = None) -> AuthResult:
        """
        Verify email OTP code with interactive retry
        """
        retries = 0
        
        while retries <= self.max_retries:
            try:
                # If no code provided, prompt user interactively
                if not code:
                    code = self._prompt_for_otp_code(retries > 0)
                    if not code:
                        return AuthResult(
                            success=False,
                            error_message="No OTP code provided"
                        )
                
                # Get current page to find verification form
                response = session.get(verification_url)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                otp_form = self._find_otp_verification_form(soup)
                if not otp_form:
                    return AuthResult(
                        success=False,
                        error_message="Could not find OTP verification form"
                    )
                
                # Prepare form submission
                action = otp_form.get('action', '')
                action_url = urljoin(verification_url, action) if action else verification_url
                method = otp_form.get('method', 'POST').upper()
                
                # Build form data
                otp_form_data = {}
                
                # Find OTP code input
                code_field = (
                    otp_form.find('input', {'name': re.compile(r'code|otp|token', re.I)}) or
                    otp_form.find('input', {'type': 'text'}) or
                    otp_form.find('input', {'type': 'number'})
                )
                
                if code_field:
                    field_name = code_field.get('name', 'code')
                    otp_form_data[field_name] = code
                
                # Add CSRF token if present
                csrf_token = self._extract_csrf_token(otp_form)
                if csrf_token:
                    csrf_input = otp_form.find('input', {'value': csrf_token})
                    if csrf_input and csrf_input.get('name'):
                        otp_form_data[csrf_input.get('name')] = csrf_token
                    else:
                        otp_form_data['_token'] = csrf_token
                
                # Add hidden fields
                hidden_inputs = otp_form.find_all('input', {'type': 'hidden'})
                for hidden_input in hidden_inputs:
                    name = hidden_input.get('name')
                    value = hidden_input.get('value', '')
                    if name and name not in otp_form_data:
                        otp_form_data[name] = value
                
                # Add any additional form data passed in
                if form_data:
                    otp_form_data.update(form_data)
                
                # Submit verification
                verify_response = session.request(
                    method=method,
                    url=action_url,
                    data=otp_form_data,
                    allow_redirects=True
                )
                
                # Check if authentication succeeded
                if self.validate_session(session, verify_response.url):
                    return AuthResult(
                        success=True,
                        response=verify_response
                    )
                
                # Check for specific error messages
                verify_soup = BeautifulSoup(verify_response.text, 'html.parser')
                error_msg = self._extract_error_message(verify_soup)
                
                # If code was invalid and we have retries left, try again
                if error_msg and ("invalid" in error_msg.lower() or "incorrect" in error_msg.lower()) and retries < self.max_retries:
                    click.echo(f"❌ {error_msg}")
                    code = None  # Reset code to prompt again
                    retries += 1
                    continue
                
                return AuthResult(
                    success=False,
                    response=verify_response,
                    error_message=error_msg or "OTP verification failed"
                )
                
            except Exception as e:
                return AuthResult(
                    success=False,
                    error_message=f"OTP verification error: {str(e)}"
                )
        
        return AuthResult(
            success=False,
            error_message=f"OTP verification failed after {self.max_retries} attempts"
        )
    
    def validate_session(self, session: requests.Session, url: str) -> bool:
        """
        Check if session is authenticated by looking for success indicators
        """
        try:
            response = session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for success indicators
            for selector in self.get_success_indicators():
                if soup.select(selector):
                    return True
            
            # Check for absence of failure indicators  
            for selector in self.get_failure_indicators():
                if soup.select(selector):
                    return False
                    
            # If we can't find clear indicators, assume success if no login form
            login_form = self.detect_login_form(soup, url)
            return login_form is None
            
        except Exception:
            return False
    
    def _find_otp_verification_form(self, soup: BeautifulSoup) -> Optional[Any]:
        """Find form for OTP code verification"""
        forms = soup.find_all('form')
        
        for form in forms:
            # Look for code/otp/token input fields
            code_field = (
                form.find('input', {'name': re.compile(r'code|otp|token|verify', re.I)}) or
                form.find('input', {'placeholder': re.compile(r'code|otp|verification', re.I)})
            )
            
            if code_field:
                return form
        
        return None
    
    def _extract_csrf_token(self, form) -> Optional[str]:
        """Extract CSRF token from form"""
        # Look for common CSRF token patterns
        csrf_input = (
            form.find('input', {'name': '_token'}) or
            form.find('input', {'name': 'csrf_token'}) or
            form.find('input', {'name': re.compile(r'csrf|token', re.I)})
        )
        
        if csrf_input:
            return csrf_input.get('value')
        
        return None
    
    def _extract_error_message(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract error message from page"""
        for selector in self.get_failure_indicators():
            error_elem = soup.select_one(selector)
            if error_elem:
                return error_elem.get_text(strip=True)
        
        return None
    
    def _find_otp_button(self, form) -> Optional[Any]:
        """Find OTP-related button in form"""
        # Look for buttons with OTP-related text
        otp_keywords = [
            'send one-time code', 'send code', 'one-time code', 
            'magic link', 'email code', 'verification code',
            'send link', 'email login', 'passwordless'
        ]
        
        # Check button elements
        buttons = form.find_all('button')
        for button in buttons:
            button_text = button.get_text(strip=True).lower()
            if any(keyword in button_text for keyword in otp_keywords):
                return button
        
        # Check input submit buttons
        submit_inputs = form.find_all('input', {'type': 'submit'})
        for submit_input in submit_inputs:
            value = (submit_input.get('value') or '').lower()
            if any(keyword in value for keyword in otp_keywords):
                return submit_input
        
        # Check for buttons with specific IDs or names that suggest OTP
        otp_selectors = [
            '[id*="otp"]', '[id*="code"]', '[id*="magic"]',
            '[name*="otp"]', '[name*="code"]', '[name*="magic"]'
        ]
        
        for selector in otp_selectors:
            button = form.select_one(f'button{selector}, input[type="submit"]{selector}')
            if button:
                return button
        
        return None
    
    def _prompt_for_otp_code(self, is_retry: bool = False) -> str:
        """Interactive prompt for OTP code"""
        if is_retry:
            prompt_text = "❓ Please enter the verification code from your email (or press Enter to cancel)"
        else:
            prompt_text = "📧 A verification code has been sent to your email. Please enter the code"
        
        code = click.prompt(prompt_text, type=str, default="", show_default=False)
        return code.strip()