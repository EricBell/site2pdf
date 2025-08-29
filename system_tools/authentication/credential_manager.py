#!/usr/bin/env python3
"""
Credential Management for Authentication System
"""

import os
import getpass
from typing import Optional, Dict, NamedTuple
from urllib.parse import urlparse
from .exceptions import CredentialError
from .utils import extract_domain

class Credentials(NamedTuple):
    """Authentication credentials"""
    username: str
    password: str
    
    def validate(self) -> bool:
        """Validate credentials are not empty"""
        return bool(self.username and self.password)

class CredentialManager:
    """Secure credential management with multiple sources"""
    
    def __init__(self):
        self._cached_credentials: Dict[str, Credentials] = {}
    
    def get_credentials(self, site_url: str, username: str = None, password: str = None) -> Credentials:
        """
        Get credentials from multiple sources in priority order:
        1. Direct parameters
        2. Environment variables (site-specific)
        3. Environment variables (general)
        4. Interactive prompt
        
        Args:
            site_url: Target website URL
            username: Direct username (highest priority)
            password: Direct password (highest priority)
            
        Returns:
            Credentials object
            
        Raises:
            CredentialError: If credentials cannot be obtained
        """
        domain = extract_domain(site_url)
        
        # Check cache first
        cache_key = f"{domain}:{username}" if username else domain
        if cache_key in self._cached_credentials:
            return self._cached_credentials[cache_key]
        
        # Priority 1: Direct parameters
        if username and password:
            credentials = Credentials(username, password)
            self._cached_credentials[cache_key] = credentials
            return credentials
        
        # Priority 2: Site-specific environment variables
        env_username = username or self._get_site_env_var(domain, 'USERNAME')
        env_password = password or self._get_site_env_var(domain, 'PASSWORD')
        
        if env_username and env_password:
            credentials = Credentials(env_username, env_password)
            self._cached_credentials[cache_key] = credentials
            return credentials
        
        # Priority 3: General environment variables
        general_username = env_username or os.getenv('SITE2PDF_AUTH_USERNAME')
        general_password = env_password or os.getenv('SITE2PDF_AUTH_PASSWORD')
        
        if general_username and general_password:
            credentials = Credentials(general_username, general_password)
            self._cached_credentials[cache_key] = credentials
            return credentials
        
        # Priority 4: Interactive prompt (if in TTY)
        if os.isatty(0):  # Check if running in terminal
            try:
                prompt_username = env_username or general_username or input(f"Username for {domain}: ")
                prompt_password = env_password or general_password or getpass.getpass(f"Password for {domain}: ")
                
                if prompt_username and prompt_password:
                    credentials = Credentials(prompt_username, prompt_password)
                    self._cached_credentials[cache_key] = credentials
                    return credentials
            except (KeyboardInterrupt, EOFError):
                raise CredentialError("Authentication cancelled by user")
        
        raise CredentialError(f"No credentials found for {domain}. Set environment variables or provide via CLI.")
    
    def _get_site_env_var(self, domain: str, var_type: str) -> Optional[str]:
        """Get site-specific environment variable"""
        # Convert domain to valid env var name (replace dots/hyphens with underscores)
        domain_var = domain.replace('.', '_').replace('-', '_').upper()
        var_name = f"SITE2PDF_{domain_var}_{var_type}"
        return os.getenv(var_name)
    
    def clear_cache(self):
        """Clear cached credentials"""
        self._cached_credentials.clear()
    
    def cache_credentials(self, site_url: str, credentials: Credentials, username_key: str = None):
        """Cache credentials for future use"""
        domain = extract_domain(site_url)
        cache_key = f"{domain}:{username_key}" if username_key else domain
        self._cached_credentials[cache_key] = credentials
    
    def has_cached_credentials(self, site_url: str, username: str = None) -> bool:
        """Check if credentials are cached for site"""
        domain = extract_domain(site_url)
        cache_key = f"{domain}:{username}" if username else domain
        return cache_key in self._cached_credentials
    
    def get_env_var_names(self, site_url: str) -> Dict[str, str]:
        """Get the environment variable names that would be used for this site"""
        domain = extract_domain(site_url)
        domain_var = domain.replace('.', '_').replace('-', '_').upper()
        
        return {
            'site_specific_username': f"SITE2PDF_{domain_var}_USERNAME",
            'site_specific_password': f"SITE2PDF_{domain_var}_PASSWORD", 
            'general_username': 'SITE2PDF_AUTH_USERNAME',
            'general_password': 'SITE2PDF_AUTH_PASSWORD'
        }