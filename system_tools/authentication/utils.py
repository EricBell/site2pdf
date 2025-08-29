#!/usr/bin/env python3
"""
Authentication Utility Functions
"""

import re
import urllib.parse
from typing import Optional, Dict, List
from bs4 import BeautifulSoup, Tag

def extract_domain(url: str) -> str:
    """Extract domain from URL for plugin matching"""
    parsed = urllib.parse.urlparse(url)
    return parsed.netloc.lower()

def normalize_url(url: str, base_url: str = None) -> str:
    """Normalize and resolve relative URLs"""
    if base_url and not url.startswith(('http://', 'https://')):
        return urllib.parse.urljoin(base_url, url)
    return url

def find_form_by_password(soup: BeautifulSoup) -> Optional[Tag]:
    """Find form containing password field"""
    password_inputs = soup.find_all('input', {'type': 'password'})
    
    for password_input in password_inputs:
        form = password_input.find_parent('form')
        if form:
            return form
    return None

def extract_csrf_token(soup: BeautifulSoup, form: Tag = None) -> Optional[str]:
    """Extract CSRF token from form or page"""
    # Common CSRF token patterns
    csrf_patterns = [
        'input[name*="csrf"]',
        'input[name*="token"]', 
        'input[name="_token"]',
        'input[name="authenticity_token"]',
        'meta[name="csrf-token"]'
    ]
    
    search_scope = form if form else soup
    
    for pattern in csrf_patterns:
        element = search_scope.select_one(pattern)
        if element:
            return element.get('value') or element.get('content')
    
    return None

def detect_username_field(form: Tag) -> Optional[Tag]:
    """Detect username/email field in form"""
    # Try common patterns in order of preference
    patterns = [
        'input[name="username"]',
        'input[name="email"]', 
        'input[name="login"]',
        'input[name="user"]',
        'input[type="email"]',
        'input[name*="user"]',
        'input[name*="email"]'
    ]
    
    for pattern in patterns:
        field = form.select_one(pattern)
        if field and field.get('type') != 'hidden':
            return field
    
    # Fallback: find first text input that's not password
    text_inputs = form.find_all('input', {'type': ['text', 'email']})
    if text_inputs:
        return text_inputs[0]
    
    return None

def detect_submit_button(form: Tag) -> Optional[Tag]:
    """Detect submit button in form"""
    # Try different submit button patterns
    patterns = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:not([type])',  # buttons without type default to submit
        'input[value*="login" i]',
        'input[value*="sign in" i]',
        'button:contains("Login")',
        'button:contains("Sign In")'
    ]
    
    for pattern in patterns:
        button = form.select_one(pattern)
        if button:
            return button
    
    return None

def extract_error_message(soup: BeautifulSoup) -> Optional[str]:
    """Extract error message from login response"""
    error_patterns = [
        '.error',
        '.alert-danger', 
        '.login-error',
        '.error-message',
        '.invalid-feedback',
        '[class*="error"]',
        '[id*="error"]'
    ]
    
    for pattern in error_patterns:
        error_element = soup.select_one(pattern)
        if error_element:
            text = error_element.get_text(strip=True)
            if text and len(text) > 5:  # Filter out empty or very short messages
                return text
    
    return None

def is_login_successful(soup: BeautifulSoup, success_indicators: List[str] = None) -> bool:
    """Check if login was successful based on page content"""
    if not success_indicators:
        success_indicators = [
            '.user-menu',
            '.user-profile',
            'a[href*="logout"]',
            'a[href*="sign-out"]',
            '.dashboard',
            '.welcome'
        ]
    
    for indicator in success_indicators:
        if soup.select_one(indicator):
            return True
    
    return False

def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def sanitize_session_id(url: str) -> str:
    """Create safe session ID from URL"""
    domain = extract_domain(url)
    # Replace special characters with underscores
    return re.sub(r'[^\w\-_.]', '_', domain)