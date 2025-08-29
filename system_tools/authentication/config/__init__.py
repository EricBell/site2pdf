#!/usr/bin/env python3
"""
Authentication Configuration Management
"""

from .auth_config import AuthConfig, SiteConfig, FormConfig
from .site_configs import get_predefined_site_configs, load_site_config

__all__ = [
    'AuthConfig',
    'SiteConfig', 
    'FormConfig',
    'get_predefined_site_configs',
    'load_site_config'
]