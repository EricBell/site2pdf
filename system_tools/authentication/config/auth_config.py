#!/usr/bin/env python3
"""
Authentication Configuration Models
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

@dataclass
class FormConfig:
    """Configuration for login form detection"""
    username_field: Optional[str] = None
    password_field: Optional[str] = None
    submit_button: Optional[str] = None
    csrf_token: Optional[str] = None
    form_selector: Optional[str] = None
    additional_fields: Dict[str, str] = field(default_factory=dict)

@dataclass 
class SiteConfig:
    """Configuration for site-specific authentication"""
    domain: str
    plugin: str = "generic_form"
    login_url: Optional[str] = None
    form_config: Optional[FormConfig] = None
    success_indicators: List[str] = field(default_factory=list)
    failure_indicators: List[str] = field(default_factory=list)
    session_duration: str = "24h"
    multi_step_login: bool = False
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize form_config if not provided"""
        if self.form_config is None:
            self.form_config = FormConfig()

@dataclass
class AuthConfig:
    """Main authentication configuration"""
    enabled: bool = False
    cache_sessions: bool = True
    session_duration: str = "24h"
    sites: Dict[str, SiteConfig] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AuthConfig':
        """Create AuthConfig from dictionary"""
        auth_config = cls()
        auth_config.enabled = config_dict.get('enabled', False)
        auth_config.cache_sessions = config_dict.get('cache_sessions', True)
        auth_config.session_duration = config_dict.get('session_duration', '24h')
        auth_config.default_config = config_dict.get('default_config', {})
        
        # Parse site configurations
        sites_config = config_dict.get('sites', {})
        for domain, site_data in sites_config.items():
            # Parse form configuration
            form_data = site_data.get('form_selectors', {})
            form_config = FormConfig(
                username_field=form_data.get('username_field'),
                password_field=form_data.get('password_field'),
                submit_button=form_data.get('submit_button'),
                csrf_token=form_data.get('csrf_token'),
                form_selector=form_data.get('form_selector'),
                additional_fields=form_data.get('additional_fields', {})
            )
            
            # Create site configuration
            site_config = SiteConfig(
                domain=domain,
                plugin=site_data.get('plugin', 'generic_form'),
                login_url=site_data.get('login_url'),
                form_config=form_config,
                success_indicators=site_data.get('success_indicators', []),
                failure_indicators=site_data.get('failure_indicators', []),
                session_duration=site_data.get('session_duration', '24h'),
                multi_step_login=site_data.get('multi_step_login', False),
                custom_config=site_data.get('custom_config', {})
            )
            
            auth_config.sites[domain] = site_config
        
        return auth_config
    
    @classmethod
    def from_yaml_file(cls, file_path: Path) -> 'AuthConfig':
        """Load configuration from YAML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
            return cls.from_dict(config_dict.get('authentication', {}))
        except Exception as e:
            print(f"Warning: Failed to load auth config from {file_path}: {e}")
            return cls()  # Return default config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        sites_dict = {}
        for domain, site_config in self.sites.items():
            form_config = site_config.form_config
            sites_dict[domain] = {
                'plugin': site_config.plugin,
                'login_url': site_config.login_url,
                'form_selectors': {
                    'username_field': form_config.username_field,
                    'password_field': form_config.password_field,
                    'submit_button': form_config.submit_button,
                    'csrf_token': form_config.csrf_token,
                    'form_selector': form_config.form_selector,
                    'additional_fields': form_config.additional_fields
                },
                'success_indicators': site_config.success_indicators,
                'failure_indicators': site_config.failure_indicators,
                'session_duration': site_config.session_duration,
                'multi_step_login': site_config.multi_step_login,
                'custom_config': site_config.custom_config
            }
        
        return {
            'enabled': self.enabled,
            'cache_sessions': self.cache_sessions,
            'session_duration': self.session_duration,
            'sites': sites_dict,
            'default_config': self.default_config
        }
    
    def get_site_config(self, domain: str) -> Optional[SiteConfig]:
        """Get site configuration for domain"""
        return self.sites.get(domain)
    
    def add_site_config(self, site_config: SiteConfig):
        """Add site configuration"""
        self.sites[site_config.domain] = site_config