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
from .js_auth_mixin import JavaScriptAuthMixin


class EmailOTPPlugin(JavaScriptAuthMixin, BaseAuthPlugin):
    """Plugin for email-based OTP authentication"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        config = config or {}
        self.timeout_seconds = config.get('otp_timeout', 300)  # 5 minutes default
        self.max_retries = config.get('max_retries', 3)
    
    def get_login_url(self, base_url: str) -> str:
        """
        Get the login URL for the site, with auto-discovery
        
        First checks config, then tries to discover login links on the base page
        """
        # Check if login URL is explicitly configured
        if 'login_url' in self.config:
            return self.config['login_url']
        
        # Try to auto-discover login URL from the base page
        try:
            import requests
            from urllib.parse import urljoin
            
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            
            response = session.get(base_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for login links
            login_patterns = [
                r'login',
                r'sign.?in',
                r'log.?in',
                r'signin'
            ]
            
            for pattern in login_patterns:
                # Check href attributes
                link = soup.find('a', href=re.compile(pattern, re.I))
                if link:
                    href = link.get('href')
                    if href:
                        return urljoin(base_url, href)
                
                # Check button/link text content
                link = soup.find('a', string=re.compile(pattern, re.I))
                if link:
                    href = link.get('href')
                    if href:
                        return urljoin(base_url, href)
            
            # Fallback: try common login paths
            common_paths = ['/login', '/signin', '/sign-in', '/auth/login']
            for path in common_paths:
                try:
                    test_url = urljoin(base_url, path)
                    test_response = session.get(test_url, timeout=5)
                    if test_response.status_code == 200:
                        # Check if this page has login forms
                        test_soup = BeautifulSoup(test_response.text, 'html.parser')
                        forms = test_soup.find_all('form')
                        for form in forms:
                            # Look for email or username fields
                            if (form.find('input', {'type': 'email'}) or 
                                form.find('input', {'name': re.compile(r'email|username', re.I)}) or
                                form.find('input', {'type': 'text'})):
                                return test_url
                except:
                    continue
            
        except Exception as e:
            # If auto-discovery fails, fall back to base URL
            pass
        
        # Fallback to base URL
        return base_url
    
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """
        Detect email OTP login form
        
        Looks for forms with email input AND "Send One-Time Code" type button
        """
        forms = soup.find_all('form')
        print(f"🔍 EmailOTP: Found {len(forms)} forms on login page")
        
        for i, form in enumerate(forms):
            print(f"🔍 EmailOTP: Analyzing form {i+1}: action='{form.get('action', 'no action')}'")
            
            # Debug: show all inputs in this form
            inputs = form.find_all('input')
            print(f"  📝 Form {i+1} has {len(inputs)} inputs:")
            for inp in inputs:
                input_type = inp.get('type', 'text')
                input_name = inp.get('name', 'no name')
                input_placeholder = inp.get('placeholder', '')
                input_value = inp.get('value', '')
                print(f"    - type='{input_type}', name='{input_name}', placeholder='{input_placeholder}', value='{input_value}'")
            
            # Debug: show all buttons in this form  
            buttons = form.find_all(['button', 'input'])
            print(f"  🔘 Form {i+1} has {len(buttons)} buttons/inputs:")
            for btn in buttons:
                btn_type = btn.get('type', '')
                btn_text = btn.get_text(strip=True) if btn.name == 'button' else btn.get('value', '')
                btn_name = btn.get('name', '')
                print(f"    - type='{btn_type}', name='{btn_name}', text/value='{btn_text}'")
            print()
        
        print(f"🔍 EmailOTP: Finished analyzing all {len(forms)} forms on login page")
        print()
        
        for i, form in enumerate(forms):
            # Look for email input
            email_field = (
                form.find('input', {'type': 'email'}) or
                form.find('input', {'name': re.compile(r'email', re.I)}) or
                form.find('input', {'placeholder': re.compile(r'email', re.I)})
            )
            
            if email_field:
                print(f"  ✅ Found email field in form {i+1}")
                # Look for OTP-related buttons (regardless of password field presence)
                otp_button = self._find_otp_button(form)
                
                if otp_button:
                    print(f"  ✅ Found OTP button in form {i+1}: {otp_button.get_text(strip=True) if otp_button.name == 'button' else otp_button.get('value', '')}")
                else:
                    print(f"  ❌ No OTP button found in form {i+1}")
                
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
            print(f"🔍 EmailOTP: Form data extracted: {form_data}")
            
            # Look for additional hidden fields we might be missing
            hidden_inputs = form.form_element.find_all('input', {'type': 'hidden'})
            print(f"🔍 EmailOTP: Found {len(hidden_inputs)} hidden fields:")
            for hidden in hidden_inputs:
                name = hidden.get('name', 'no-name')
                value = hidden.get('value', '')
                print(f"  - {name} = '{value}'")
                if name not in form_data:
                    form_data[name] = value
                    print(f"    ✅ Added missing hidden field: {name}")
            
            # If we have a specific OTP button, add its name/value to form data
            if form.submit_button and form.submit_button.get('name'):
                button_name = form.submit_button.get('name')
                button_value = form.submit_button.get('value', '')
                form_data[button_name] = button_value
                print(f"🔍 EmailOTP: Added button data: {button_name}={button_value}")
            
            print(f"🔍 EmailOTP: Submitting to {form.action_url} with method {form.method}")
            print(f"🔍 EmailOTP: Final form data: {form_data}")
            
            # Add proper headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': form.action_url,
                'Origin': '/'.join(form.action_url.split('/')[:3])
            }
            
            response = session.request(
                method=form.method,
                url=form.action_url,
                data=form_data,
                headers=headers,
                allow_redirects=True
            )
            
            print(f"🔍 EmailOTP: Response status: {response.status_code}")
            print(f"🔍 EmailOTP: Response URL: {response.url}")
            
            # Check if we got redirected back to the same login page (indicates JavaScript dependency)
            if response.url == form.action_url:
                print("🔍 EmailOTP: ⚠️  Response redirected back to login page - likely JavaScript-only form")
                
                # Check if the page has JavaScript form handlers
                if self._has_javascript_form_handling(response.text):
                    print("🔍 EmailOTP: 🔄 Detected JavaScript-dependent form - trying browser automation fallback")
                    return self.perform_login_js(session, form, username, password)
            
            # Check if email was accepted and OTP was sent
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for OTP code input form
            print(f"🔍 EmailOTP: Checking response for OTP verification form...")
            
            # Debug: check if we got redirected or if there are any forms on the response page
            forms_in_response = soup.find_all('form')
            print(f"🔍 EmailOTP: Response has {len(forms_in_response)} forms")
            
            # Check for any error messages
            error_elements = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'error|alert|warning', re.I))
            if error_elements:
                print(f"🔍 EmailOTP: Found potential error messages:")
                for elem in error_elements[:3]:  # Limit to first 3
                    print(f"  - {elem.get_text(strip=True)}")
            
            otp_form = self._find_otp_verification_form(soup)
            
            if otp_form:
                print(f"🔍 EmailOTP: Found explicit OTP verification form")
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
                print(f"🔍 EmailOTP: No explicit OTP form found, but response was successful")
                print(f"🔍 EmailOTP: Response content preview (first 500 chars):")
                print(f"🔍 {response.text[:500]}...")
                
                # Look for success messages indicating email was sent
                success_indicators = [
                    r'code.{0,20}sent',
                    r'email.{0,20}sent',
                    r'verification.{0,20}sent',
                    r'check.{0,20}email',
                    r'sent.{0,20}email'
                ]
                
                response_text_lower = response.text.lower()
                email_sent = any(re.search(pattern, response_text_lower) for pattern in success_indicators)
                
                if email_sent:
                    print(f"🔍 EmailOTP: Found success indicators in response, email likely sent")
                    return AuthResult(
                        success=False,  # Not complete yet
                        response=response,
                        requires_additional_steps=True,
                        step_type="email_otp",
                        step_data={
                            "verification_url": response.url,
                            "form_action": "/login",  # Assume same endpoint
                            "email": username
                        }
                    )
                elif response.status_code == 200:
                    print(f"🔍 EmailOTP: No success indicators found - this may be an error")
                    # Check for error messages more thoroughly
                    error_msg = self._extract_error_message(soup)
                    if not error_msg:
                        # Look for any text that might indicate an error
                        form_text = soup.get_text()
                        error_keywords = ['error', 'invalid', 'incorrect', 'failed', 'not found']
                        for keyword in error_keywords:
                            if keyword in form_text.lower():
                                error_msg = f"Form submission may have failed (found '{keyword}' in response)"
                                break
                    
                    return AuthResult(
                        success=False,
                        response=response,
                        error_message=error_msg or "Email OTP submission unclear - no success indicators found in response"
                    )
                else:
                    # Check for error messages
                    error_msg = self._extract_error_message(soup)
                    return AuthResult(
                        success=False,
                        response=response,
                        error_message=error_msg or f"Email OTP submission failed (status: {response.status_code})"
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
    
    def _has_javascript_form_handling(self, html_content):
        """
        Check if the page uses JavaScript for form handling
        
        Args:
            html_content: HTML content as string
            
        Returns:
            bool: True if JavaScript form handling is detected
        """
        js_indicators = [
            r'addEventListener\s*\(\s*[\'"]submit[\'"]',
            r'onSubmit\s*=',
            r'preventDefault\s*\(\s*\)',
            r'event\.preventDefault',
            r'form\.submit\s*\(',
            r'fetch\s*\(',
            r'XMLHttpRequest',
            r'ajax',
            r'form\s*\.\s*addEventListener',
            r'document\.querySelector.*submit',
            r'e\.preventDefault'
        ]
        
        content_lower = html_content.lower()
        detected_patterns = []
        
        for pattern in js_indicators:
            if re.search(pattern, content_lower, re.IGNORECASE):
                detected_patterns.append(pattern)
        
        if detected_patterns:
            print(f"🔍 EmailOTP: JavaScript form handling patterns detected: {detected_patterns[:3]}")
            return True
        
        return False
    
    def perform_login_js(self, session, form, username: str, password: str) -> AuthResult:
        """
        Perform email OTP login using JavaScript/browser automation
        
        Args:
            session: requests.Session (not used for JS auth)
            form: LoginForm object from detect_login_form
            username: Email address
            password: Password (not used for email OTP)
            
        Returns:
            AuthResult indicating success/failure
        """
        print("🚀 EmailOTP: Starting JavaScript-based authentication")
        
        # Create WebDriver context
        with self as js_context:
            if not self.driver:
                return AuthResult(
                    success=False,
                    error_message="Failed to initialize browser automation. Please ensure Chrome browser is installed and JavaScript dependencies are available. Run: python install_js_deps.py"
                )
            
            try:
                # Navigate to login page
                print(f"🔍 EmailOTP: Navigating to {form.action_url}")
                self.driver.get(form.action_url)
                self._take_debug_screenshot("navigate_to_login", f"Navigated to {form.action_url}")
                
                # Find email input field
                email_selectors = [
                    'input[type="email"]',
                    'input[name*="email"]',
                    'input[id*="email"]',
                    'input[autocomplete="email"]',
                    'input[placeholder*="Email"]',
                    'input[placeholder*="EMAIL"]'
                ]
                
                email_input = self._find_element_by_selectors(email_selectors, timeout=10)
                if not email_input:
                    return AuthResult(
                        success=False,
                        error_message="Could not find email input field on the page"
                    )
                
                print(f"🔍 EmailOTP: Found email input field")
                self._take_debug_screenshot("found_email_field", "Located email input field")
                
                # Enter email address - try different interaction methods
                self._take_debug_screenshot("before_email_input", "About to enter email address")
                try:
                    # First try to scroll to element and make it visible
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", email_input)
                    time.sleep(1)
                    
                    # Try clicking to focus first
                    email_input.click()
                    email_input.clear()
                    email_input.send_keys(username)
                    print(f"🔍 EmailOTP: Entered email: {username}")
                    self._take_debug_screenshot("after_email_input_normal", f"Entered email normally: {username}")
                except Exception as interact_error:
                    print(f"🔍 EmailOTP: Normal interaction failed, trying JavaScript: {str(interact_error).split('Stacktrace:')[0].strip()}")
                    # Multiple JavaScript approaches to set email value
                    success = False
                    
                    # Approach 1: Direct value setting with multiple events
                    try:
                        self.driver.execute_script(f"""
                            arguments[0].value = '{username}';
                            arguments[0].focus();
                            arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                            arguments[0].blur();
                        """, email_input)
                        
                        # Verify the value was set
                        actual_value = self.driver.execute_script("return arguments[0].value;", email_input)
                        if actual_value == username:
                            success = True
                            print(f"🔍 EmailOTP: ✅ Email set successfully via JavaScript approach 1: {username}")
                        else:
                            print(f"🔍 EmailOTP: ⚠️ JavaScript approach 1 failed - got '{actual_value}', expected '{username}'")
                    except Exception as e:
                        print(f"🔍 EmailOTP: JavaScript approach 1 failed: {e}")
                    
                    # Approach 2: Character-by-character input simulation
                    if not success:
                        try:
                            self.driver.execute_script("arguments[0].value = '';", email_input)
                            self.driver.execute_script("arguments[0].focus();", email_input)
                            
                            for char in username:
                                self.driver.execute_script(f"""
                                    var event = new KeyboardEvent('keydown', {{ key: '{char}', bubbles: true }});
                                    arguments[0].dispatchEvent(event);
                                    arguments[0].value += '{char}';
                                    var inputEvent = new Event('input', {{ bubbles: true }});
                                    arguments[0].dispatchEvent(inputEvent);
                                """, email_input)
                                time.sleep(0.05)  # Small delay between characters
                            
                            self.driver.execute_script("arguments[0].blur();", email_input)
                            
                            # Verify
                            actual_value = self.driver.execute_script("return arguments[0].value;", email_input)
                            if actual_value == username:
                                success = True
                                print(f"🔍 EmailOTP: ✅ Email set successfully via JavaScript approach 2: {username}")
                            else:
                                print(f"🔍 EmailOTP: ⚠️ JavaScript approach 2 failed - got '{actual_value}', expected '{username}'")
                        except Exception as e:
                            print(f"🔍 EmailOTP: JavaScript approach 2 failed: {e}")
                    
                    # Approach 3: React/Vue component direct manipulation
                    if not success:
                        try:
                            self.driver.execute_script(f"""
                                // Try React approach
                                var input = arguments[0];
                                var lastValue = input.value;
                                input.value = '{username}';
                                var event = new Event('input', {{ target: input, bubbles: true }});
                                event.simulated = true;
                                var tracker = input._valueTracker;
                                if (tracker) {{
                                    tracker.setValue(lastValue);
                                }}
                                input.dispatchEvent(event);
                                
                                // Also try Vue approach
                                if (input.__vue__) {{
                                    input.__vue__.$emit('input', '{username}');
                                }}
                            """, email_input)
                            
                            # Verify
                            actual_value = self.driver.execute_script("return arguments[0].value;", email_input)
                            if actual_value == username:
                                success = True
                                print(f"🔍 EmailOTP: ✅ Email set successfully via JavaScript approach 3 (React/Vue): {username}")
                            else:
                                print(f"🔍 EmailOTP: ⚠️ JavaScript approach 3 failed - got '{actual_value}', expected '{username}'")
                        except Exception as e:
                            print(f"🔍 EmailOTP: JavaScript approach 3 failed: {e}")
                    
                    if not success:
                        print(f"🔍 EmailOTP: ❌ All JavaScript approaches failed to set email value")
                    
                    self._take_debug_screenshot("after_email_input_js", f"Email input attempts completed - success: {success}")
                
                # Find and click OTP button
                otp_button_selectors = [
                    'button:contains("Send One-Time Code")',
                    'button:contains("Send Code")',
                    'input[value*="One-Time Code"]',
                    'input[value*="Send Code"]',
                    'button:contains("Continue")',
                    'input[type="submit"]'
                ]
                
                # Convert jQuery-style :contains to XPath for Selenium
                xpath_selectors = [
                    '//button[contains(text(), "Send One-Time Code")]',
                    '//button[contains(text(), "Send Code")]', 
                    '//button[contains(text(), "Continue")]',
                    '//input[@value and contains(@value, "One-Time Code")]',
                    '//input[@value and contains(@value, "Send Code")]',
                    '//input[@type="submit"]'
                ]
                
                otp_button = None
                for xpath in xpath_selectors:
                    try:
                        from selenium.webdriver.common.by import By
                        otp_button = self.driver.find_element(By.XPATH, xpath)
                        print(f"🔍 EmailOTP: Found OTP button using xpath: {xpath}")
                        self._take_debug_screenshot("found_otp_button", f"Located OTP button: {xpath}")
                        break
                    except:
                        continue
                
                if not otp_button:
                    return AuthResult(
                        success=False,
                        error_message="Could not find 'Send One-Time Code' button on the page"
                    )
                
                # Click the OTP button
                current_url = self.driver.current_url
                print(f"🔍 EmailOTP: Clicking OTP button...")
                self._take_debug_screenshot("before_button_click", "About to click OTP button")
                
                button_clicked = False
                form_submitted = False
                
                try:
                    # Try normal click
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", otp_button)
                    time.sleep(0.5)
                    otp_button.click()
                    button_clicked = True
                    self._take_debug_screenshot("after_button_click_normal", "Clicked OTP button normally")
                    print(f"🔍 EmailOTP: ✅ Button clicked normally")
                except Exception as click_error:
                    print(f"🔍 EmailOTP: Normal button click failed, trying JavaScript: {str(click_error).split('Stacktrace:')[0].strip()}")
                
                # Multiple JavaScript approaches for button click and form submission
                if not button_clicked:
                    try:
                        # JavaScript click
                        self.driver.execute_script("arguments[0].click();", otp_button)
                        button_clicked = True
                        self._take_debug_screenshot("after_button_click_js", "Clicked OTP button via JavaScript")
                        print(f"🔍 EmailOTP: ✅ Button clicked via JavaScript")
                    except Exception as js_error:
                        print(f"🔍 EmailOTP: JavaScript button click failed: {js_error}")
                
                # Try multiple form submission approaches
                print(f"🔍 EmailOTP: Attempting form submission...")
                
                # Approach 1: Find and submit the form directly
                try:
                    form_element = self.driver.execute_script("""
                        var button = arguments[0];
                        var form = button.closest('form');
                        if (form) {
                            return form;
                        }
                        // Fallback - find any form on page
                        var forms = document.querySelectorAll('form');
                        return forms.length > 0 ? forms[0] : null;
                    """, otp_button)
                    
                    if form_element:
                        # Verify email value is set in form
                        email_value = self.driver.execute_script("""
                            var form = arguments[0];
                            var emailInput = form.querySelector('input[type="email"], input[name*="email"], input[placeholder*="email" i]');
                            return emailInput ? emailInput.value : null;
                        """, form_element)
                        
                        if email_value == username:
                            print(f"🔍 EmailOTP: ✅ Email value confirmed in form: {email_value}")
                        else:
                            print(f"🔍 EmailOTP: ⚠️ Email value in form: '{email_value}', expected: '{username}'")
                            # Try to set it again directly on the form
                            self.driver.execute_script(f"""
                                var form = arguments[0];
                                var emailInput = form.querySelector('input[type="email"], input[name*="email"], input[placeholder*="email" i]');
                                if (emailInput) {{
                                    emailInput.value = '{username}';
                                    emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    emailInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }}
                            """, form_element)
                        
                        # Submit the form
                        self.driver.execute_script("arguments[0].submit();", form_element)
                        form_submitted = True
                        print(f"🔍 EmailOTP: ✅ Form submitted directly")
                        self._take_debug_screenshot("after_form_submit", "Form submitted directly")
                        
                    else:
                        print(f"🔍 EmailOTP: ⚠️ No form element found for direct submission")
                except Exception as form_error:
                    print(f"🔍 EmailOTP: Form submission approach 1 failed: {form_error}")
                
                # Approach 2: Trigger button events manually  
                if not form_submitted:
                    try:
                        self.driver.execute_script("""
                            var button = arguments[0];
                            
                            // Trigger mouse events
                            var mouseDown = new MouseEvent('mousedown', { bubbles: true, cancelable: true });
                            var mouseUp = new MouseEvent('mouseup', { bubbles: true, cancelable: true });
                            var click = new MouseEvent('click', { bubbles: true, cancelable: true });
                            
                            button.dispatchEvent(mouseDown);
                            button.dispatchEvent(mouseUp);
                            button.dispatchEvent(click);
                            
                            // If button has onclick handler, try to call it
                            if (button.onclick) {
                                button.onclick();
                            }
                            
                            // Look for any form and submit it
                            var forms = document.querySelectorAll('form');
                            for (var i = 0; i < forms.length; i++) {
                                var form = forms[i];
                                var emailInput = form.querySelector('input[type="email"]');
                                if (emailInput && emailInput.value) {
                                    form.submit();
                                    break;
                                }
                            }
                        """, otp_button)
                        
                        form_submitted = True
                        print(f"🔍 EmailOTP: ✅ Form submission via event triggering completed")
                        self._take_debug_screenshot("after_event_submit", "Form submission via events")
                        
                    except Exception as event_error:
                        print(f"🔍 EmailOTP: Event-based form submission failed: {event_error}")
                
                # Approach 3: Look for AJAX/fetch calls
                if not form_submitted:
                    try:
                        result = self.driver.execute_script(f"""
                            // Try to find and trigger any fetch/AJAX calls
                            var button = arguments[0];
                            var form = button.closest('form');
                            
                            if (form) {{
                                var formData = new FormData(form);
                                
                                // Make sure email is in the form data
                                var emailFound = false;
                                for (var pair of formData.entries()) {{
                                    if (pair[0].toLowerCase().includes('email')) {{
                                        emailFound = true;
                                        break;
                                    }}
                                }}
                                
                                if (!emailFound) {{
                                    formData.append('email', '{username}');
                                }}
                                
                                // Try to submit via fetch to the same URL
                                fetch(window.location.href, {{
                                    method: 'POST',
                                    body: formData
                                }}).then(response => {{
                                    console.log('Manual fetch submitted', response.status);
                                }}).catch(err => {{
                                    console.log('Manual fetch failed', err);
                                }});
                                
                                return 'Manual fetch attempted';
                            }}
                            
                            return 'No form found for manual fetch';
                        """, otp_button)
                        
                        print(f"🔍 EmailOTP: Manual fetch result: {result}")
                        form_submitted = True
                        self._take_debug_screenshot("after_manual_fetch", "Manual fetch submission attempted")
                        
                    except Exception as fetch_error:
                        print(f"🔍 EmailOTP: Manual fetch submission failed: {fetch_error}")
                
                if not form_submitted:
                    print(f"🔍 EmailOTP: ❌ All form submission approaches failed")
                else:
                    print(f"🔍 EmailOTP: ✅ Form submission completed successfully")
                
                # Wait for response (either success message or URL change)
                print("🔍 EmailOTP: Waiting for page response", end="", flush=True)
                for i in range(10):  # 5 seconds with progress dots
                    time.sleep(0.5)
                    print(".", end="", flush=True)
                    if i == 5:  # Take a mid-wait screenshot
                        self._take_debug_screenshot("wait_progress_midpoint", "Mid-wait progress check")
                print()  # New line after dots
                print("🔍 EmailOTP: Checking for success indicators...")
                self._take_debug_screenshot("final_page_state", "Final page state after wait")
                
                # Check for success indicators
                success_selectors = [
                    'div:contains("code sent")',
                    'div:contains("email sent")', 
                    'div:contains("check your email")',
                    'input[placeholder*="code" i]',
                    'input[placeholder*="verification" i]'
                ]
                
                # More specific success indicators - avoid generic terms
                success_xpaths = [
                    '//*[contains(text(), "code sent")]',
                    '//*[contains(text(), "email sent")]', 
                    '//*[contains(text(), "check your email")]',
                    '//*[contains(text(), "verification code")]',
                    '//*[contains(text(), "one-time code")]',
                    '//*[contains(text(), "magic link")]',
                    '//*[contains(text(), "sent you")]',
                    '//*[contains(text(), "check your inbox")]',
                    '//input[contains(@placeholder, "verification code" )]',
                    '//input[contains(@placeholder, "enter code")]',
                    '//input[contains(@placeholder, "6-digit")]',
                    '//input[@type="text" and @maxlength="6"]',
                    '//input[@type="number" and @maxlength="6"]',
                    '//div[contains(@class, "success")]',
                    '//div[contains(@class, "sent")]'
                ]
                
                found_success = False
                for xpath in success_xpaths:
                    try:
                        element = self.driver.find_element(By.XPATH, xpath)
                        print(f"🔍 EmailOTP: Found success indicator: {element.text or element.get_attribute('placeholder')}")
                        found_success = True
                        break
                    except:
                        continue
                
                if found_success:
                    print("🔍 EmailOTP: ✅ Email OTP request appears successful!")
                    return AuthResult(
                        success=True,
                        requires_additional_steps=True,
                        step_type='email_otp',
                        next_step_url=self.driver.current_url,
                        response=None,  # Explicitly set None for JS-based auth
                        step_data={
                            'email': username,
                            'verification_method': 'javascript'
                        }
                    )
                else:
                    # Check if URL changed to something meaningful (not just same page reload)
                    current_page_url = self.driver.current_url
                    if current_page_url != current_url and not current_page_url.endswith('/login'):
                        print(f"🔍 EmailOTP: URL changed from {current_url} to {current_page_url} - indicates success")
                        return AuthResult(
                            success=True,
                            requires_additional_steps=True,
                            step_type='email_otp',
                            next_step_url=current_page_url,
                            response=None,  # Explicitly set None for JS-based auth
                            step_data={
                                'email': username,
                                'verification_method': 'javascript'
                            }
                        )
                    
                    # Check if page content significantly changed (not just a reload)
                    page_title = self.driver.title
                    page_text_sample = self.driver.execute_script("""
                        return document.body ? document.body.innerText.substring(0, 200) : '';
                    """)
                    
                    # Look for specific changes that indicate we moved past the login form
                    if ('Welcome back!' not in page_text_sample and 
                        'Enter your email' not in page_text_sample and
                        len(page_text_sample.strip()) > 50):
                        print(f"🔍 EmailOTP: Page content changed significantly - indicates success")
                        print(f"🔍 EmailOTP: New page title: {page_title}")
                        print(f"🔍 EmailOTP: New page sample: {page_text_sample[:100]}...")
                        return AuthResult(
                            success=True,
                            requires_additional_steps=True,
                            step_type='email_otp',
                            next_step_url=current_page_url,
                            response=None,  # Explicitly set None for JS-based auth
                            step_data={
                                'email': username,
                                'verification_method': 'javascript'
                            }
                        )
                    
                    # No clear success indicators found - check for error messages
                    error_xpaths = [
                        '//*[contains(text(), "error")]',
                        '//*[contains(text(), "invalid")]',
                        '//*[contains(text(), "incorrect")]',
                        '//*[contains(text(), "failed")]',
                        '//*[contains(text(), "not found")]',
                        '//*[contains(@class, "error")]',
                        '//*[contains(@class, "alert")]'
                    ]
                    
                    found_error = False
                    for xpath in error_xpaths:
                        try:
                            element = self.driver.find_element(By.XPATH, xpath)
                            print(f"🔍 EmailOTP: Found error indicator: {element.text}")
                            found_error = True
                            break
                        except:
                            continue
                    
                    if not found_error:
                        # No error messages found, assume success and continue
                        print("🔍 EmailOTP: ✅ No error messages found, assuming email submission was successful")
                        return AuthResult(
                            success=True,
                            requires_additional_steps=True,
                            step_type='email_otp',
                            next_step_url=self.driver.current_url,
                            response=None,  # Explicitly set None for JS-based auth
                            step_data={
                                'email': username,
                                'verification_method': 'javascript'
                            }
                        )
                    else:
                        # Found error messages
                        page_source_preview = self.driver.page_source[:500] if self.driver.page_source else "No content"
                        return AuthResult(
                            success=False,
                            error_message=f"Email OTP submission failed - error messages found on page. Page preview: {page_source_preview}"
                        )
                    
            except Exception as e:
                print(f"🔍 EmailOTP: ❌ JavaScript authentication error: {str(e).split('Stacktrace:')[0].strip()}")
                return AuthResult(
                    success=False,
                    error_message=f"JavaScript authentication failed: {str(e).split('Stacktrace:')[0].strip()}"
                )
    
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
            print("📧 Verification code sent to your email!")
            print("🕒 Please check your email and enter the verification code below...")
            prompt_text = "📧 A verification code has been sent to your email. Please enter the code"
        
        code = click.prompt(prompt_text, type=str, default="", show_default=False)
        return code.strip()