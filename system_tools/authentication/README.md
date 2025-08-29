# 🔐 Authentication System

A modular, reusable authentication system for web scraping that handles login flows across different websites. Designed as a standalone module within the `system_tools` package.

## Features

- **🎯 Generic Form Detection**: Automatically detects and handles common login forms
- **🔌 Plugin Architecture**: Site-specific authentication plugins for complex flows  
- **💾 Session Persistence**: Caches authentication sessions to avoid repeated logins
- **🔒 Secure Credentials**: Multiple credential sources with environment variable support
- **⚙️ Configurable**: YAML-based configuration for site-specific settings
- **🛡️ CSRF Protection**: Automatic CSRF token detection and handling
- **🔄 Multi-Step Support**: Handles username-first then password login flows
- **📊 Session Validation**: Checks session validity before each use

## Quick Start

### Basic Usage

```python
from system_tools.authentication import create_auth_manager

# Simple authentication
auth = create_auth_manager("https://example.com")
session = await auth.authenticate("username", "password")

# Use authenticated session
authenticated_requests = auth.get_authenticated_session()
response = authenticated_requests.get("https://example.com/protected")
```

### Environment Variable Setup

```bash
# Site-specific credentials (recommended)
export SITE2PDF_EXAMPLE_COM_USERNAME="your-username"
export SITE2PDF_EXAMPLE_COM_PASSWORD="your-password"

# General credentials (fallback)
export SITE2PDF_AUTH_USERNAME="your-username"  
export SITE2PDF_AUTH_PASSWORD="your-password"
```

### CLI Integration

```bash
# With username/password
./site2pdf https://example.com --username myuser --password mypass

# With environment variables
./site2pdf https://example.com --auth

# Username provided, password prompted
./site2pdf https://example.com --username myuser
```

## Architecture

### Core Components

```
authentication/
├── auth_manager.py         # Central coordinator
├── session_store.py        # Session persistence  
├── credential_manager.py   # Secure credential handling
├── plugins/                # Authentication plugins
│   ├── base_plugin.py     # Abstract base class
│   ├── generic_form.py    # Generic form handler
│   └── examples/          # Site-specific examples
├── config/                # Configuration management
│   ├── auth_config.py     # Configuration models
│   └── site_configs.py    # Predefined site configs
├── utils.py               # Utility functions
└── exceptions.py          # Custom exceptions
```

### Plugin System

The authentication system uses a plugin architecture where each site can have specific authentication logic:

```python
class BaseAuthPlugin(ABC):
    @abstractmethod
    def detect_login_form(self, soup: BeautifulSoup, url: str) -> Optional[LoginForm]:
        """Detect and parse login form"""
        
    @abstractmethod  
    def perform_login(self, session: requests.Session, form: LoginForm, 
                     username: str, password: str) -> AuthResult:
        """Execute login process"""
        
    @abstractmethod
    def validate_session(self, session: requests.Session, url: str) -> bool:
        """Check if session is still valid"""
```

## Configuration

### YAML Configuration

Add to your `config.yaml`:

```yaml
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
```

### Predefined Site Configurations

The system includes predefined configurations for common sites:

- **GitHub**: Complete OAuth and form-based login
- **WordPress**: Standard wp-admin login
- **Confluence**: Atlassian login flows
- **Jira**: Atlassian cloud authentication

## Advanced Usage

### Custom Plugin Development

```python
from system_tools.authentication.plugins import BaseAuthPlugin

class MyCustomPlugin(BaseAuthPlugin):
    def detect_login_form(self, soup, url):
        # Custom form detection logic
        pass
        
    def perform_login(self, session, form, username, password):
        # Custom login implementation  
        pass
        
    def validate_session(self, session, url):
        # Custom session validation
        pass

# Register custom plugin
auth_manager.register_plugin("mysite.com", MyCustomPlugin())
```

### Session Management

```python
# Check authentication status
if auth_manager.is_authenticated():
    session = auth_manager.get_authenticated_session()
    
# Get session information
session_info = auth_manager.get_session_info()
print(f"Session expires: {session_info['expires_at']}")

# Manual logout
auth_manager.logout()
```

### Credential Management

```python
# Get environment variable names for a site
env_vars = auth_manager.get_credential_env_vars()
print(f"Set: {env_vars['site_specific_username']}")
print(f"Set: {env_vars['site_specific_password']}")

# Cache credentials for reuse
credentials = Credentials("username", "password")  
auth_manager.credential_manager.cache_credentials(site_url, credentials)
```

## Security Features

### Credential Security
- **No credential storage**: Only session tokens are cached
- **Environment variable priority**: Secure credential sourcing
- **Interactive prompts**: Fallback for missing credentials
- **Memory clearing**: Credentials cleared from memory after use

### Session Security
- **Automatic expiration**: Configurable session timeouts
- **Session validation**: Checks validity before each use
- **Secure storage**: Sessions compressed and isolated by site
- **CSRF protection**: Automatic token extraction and submission

### Network Security
- **Realistic headers**: Mimics real browser behavior
- **Request rate limiting**: Respects server limits
- **Error handling**: Graceful failure without exposure

## Error Handling

```python
from system_tools.authentication.exceptions import (
    AuthenticationError,
    LoginFailedError, 
    SessionExpiredError
)

try:
    auth_session = auth_manager.authenticate()
except LoginFailedError as e:
    print(f"Login failed: {e}")
except SessionExpiredError as e:
    print(f"Session expired: {e}")
except AuthenticationError as e:
    print(f"Authentication error: {e}")
```

## Integration Examples

### With Web Scraper

```python
from system_tools.authentication import AuthenticationManager

class WebScraper:
    def __init__(self, base_url, auth_enabled=False):
        self.auth_manager = None
        if auth_enabled:
            self.auth_manager = AuthenticationManager(base_url)
    
    def get_session(self):
        if self.auth_manager and self.auth_manager.is_authenticated():
            return self.auth_manager.get_authenticated_session()
        return requests.Session()
```

### Standalone Script

```python
#!/usr/bin/env python3
import asyncio
from system_tools.authentication import create_auth_manager

async def scrape_protected_site():
    auth = create_auth_manager("https://example.com")
    
    # Authenticate (will use env vars or prompt)
    await auth.authenticate()
    
    # Get authenticated session
    session = auth.get_authenticated_session()
    
    # Use session for scraping
    response = session.get("https://example.com/protected-data")
    return response.json()

if __name__ == "__main__":
    data = asyncio.run(scrape_protected_site())
    print(data)
```

## Troubleshooting

### Common Issues

1. **Form Detection Fails**
   ```python
   # Enable verbose logging to see detection details
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Session Expires Quickly**
   ```yaml
   # Adjust session duration in config
   authentication:
     session_duration: "48h"  # Longer duration
   ```

3. **Multi-Step Login Issues**
   ```yaml
   # Enable multi-step login for sites that need it
   sites:
     example.com:
       multi_step_login: true
   ```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('system_tools.authentication').setLevel(logging.DEBUG)

# Check what's happening during authentication
auth_manager = AuthenticationManager(site_url, config={'debug': True})
```

## Dependencies

The authentication module has minimal external dependencies:

- `requests`: HTTP client for authentication requests
- `beautifulsoup4`: HTML parsing for form detection  
- `PyYAML`: Configuration file support (optional)

All other functionality uses Python standard library.

## Reusability

This module is designed to be easily portable to other projects:

1. **Copy the entire `authentication/` directory**
2. **Install dependencies**: `pip install -r authentication/requirements.txt`
3. **Import and use**: `from authentication import create_auth_manager`

## Contributing

When adding new authentication plugins:

1. **Create plugin class** extending `BaseAuthPlugin`
2. **Add predefined config** in `site_configs.py`
3. **Test with real sites** to ensure reliability
4. **Document specific requirements** in plugin docstring

## License

This module follows the same license as the parent project. See LICENSE file for details.