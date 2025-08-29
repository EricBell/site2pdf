#!/usr/bin/env python3
"""
Predefined Site Configurations
"""

from typing import Dict
from .auth_config import SiteConfig, FormConfig

def get_predefined_site_configs() -> Dict[str, SiteConfig]:
    """Get predefined configurations for common sites"""
    
    configs = {}
    
    # GitHub configuration
    configs['github.com'] = SiteConfig(
        domain='github.com',
        plugin='generic_form',
        login_url='/login',
        form_config=FormConfig(
            username_field='input#login_field',
            password_field='input#password',
            submit_button='input[type="submit"]',
            csrf_token='input[name="authenticity_token"]'
        ),
        success_indicators=[
            '.Header-link--profile',
            'a[href="/settings/profile"]',
            '.user-profile-link'
        ],
        failure_indicators=[
            '.flash-error',
            '.js-flash-alert'
        ]
    )
    
    # WordPress (generic) configuration
    configs['wordpress'] = SiteConfig(
        domain='*',  # Wildcard for any WordPress site
        plugin='generic_form',
        login_url='/wp-admin',
        form_config=FormConfig(
            username_field='input#user_login',
            password_field='input#user_pass',
            submit_button='input#wp-submit'
        ),
        success_indicators=[
            '.wrap',
            '#wpadminbar',
            '.dashboard-widgets'
        ],
        failure_indicators=[
            '#login_error',
            '.login .message'
        ]
    )
    
    # Confluence configuration
    configs['confluence'] = SiteConfig(
        domain='*',
        plugin='generic_form',
        form_config=FormConfig(
            username_field='input#username',
            password_field='input#password',
            submit_button='input#login-submit'
        ),
        success_indicators=[
            '#user-menu-link',
            '.user-logo',
            '#header-menu-bar'
        ],
        failure_indicators=[
            '.error',
            '.aui-message-error'
        ]
    )
    
    # Jira configuration  
    configs['atlassian.net'] = SiteConfig(
        domain='*.atlassian.net',
        plugin='generic_form',
        form_config=FormConfig(
            username_field='input#username',
            password_field='input#password',
            submit_button='button[type="submit"]'
        ),
        success_indicators=[
            '[data-testid="global-navigation"]',
            '.css-w0rnml',
            '#jira'
        ],
        failure_indicators=[
            '[role="alert"]',
            '.css-1wqh8ic'
        ]
    )
    
    return configs

def load_site_config(domain: str) -> SiteConfig:
    """
    Load site configuration for domain
    
    Args:
        domain: Site domain
        
    Returns:
        SiteConfig for the domain or generic config
    """
    predefined = get_predefined_site_configs()
    
    # Exact match first
    if domain in predefined:
        return predefined[domain]
    
    # Check for wildcard matches
    for config_domain, config in predefined.items():
        if config_domain.startswith('*.'):
            # Wildcard match
            pattern = config_domain[2:]  # Remove '*.'
            if domain.endswith(pattern):
                return config
        elif config_domain == '*':
            # Universal match (like WordPress)
            return config
    
    # Return generic configuration
    return SiteConfig(
        domain=domain,
        plugin='generic_form',
        form_config=FormConfig(),
        success_indicators=[
            '.user-menu',
            '.user-profile',
            'a[href*="logout"]',
            'a[href*="sign-out"]',
            '.dashboard',
            '.welcome'
        ],
        failure_indicators=[
            '.error',
            '.alert-danger',
            '.login-error',
            '.error-message',
            '.invalid-feedback'
        ]
    )

# Example authentication configuration for config.yaml
EXAMPLE_AUTH_CONFIG = """
authentication:
  enabled: true
  cache_sessions: true
  session_duration: "24h"
  
  sites:
    example.com:
      plugin: "generic_form"
      login_url: "/login"
      form_selectors:
        username_field: "input[name='username']"
        password_field: "input[name='password']"
        submit_button: "input[type='submit']"
        csrf_token: "input[name='_token']"
      success_indicators:
        - ".user-menu"
        - "a[href*='logout']"
      failure_indicators:
        - ".error-message"
        - ".login-failed"
      session_duration: "24h"
      multi_step_login: false
      
    github.com:
      plugin: "generic_form"
      login_url: "/login"
      form_selectors:
        username_field: "input#login_field"
        password_field: "input#password"
        submit_button: "input[type='submit']"
        csrf_token: "input[name='authenticity_token']"
      success_indicators:
        - ".Header-link--profile"
        - "a[href='/settings/profile']"
      failure_indicators:
        - ".flash-error"
"""