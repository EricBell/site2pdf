# JavaScript Authentication Support

This document describes the JavaScript-enabled authentication feature that allows the scraper to handle websites that require JavaScript for form submission.

## Overview

Some modern websites (like ideabrowser.com) use JavaScript for form submission instead of standard HTML form POST requests. When the scraper detects such sites, it automatically falls back to browser automation using Selenium WebDriver.

## Features

- **Automatic Detection**: The system detects when JavaScript is required and switches to browser automation
- **Seamless Fallback**: No changes needed to existing commands - JavaScript support is automatic
- **Headless Operation**: Runs Chrome in headless mode by default (no GUI required)
- **Optional Dependency**: Only installs when needed, doesn't bloat the main application

## Installation

### 1. Install JavaScript Dependencies

```bash
python install_js_deps.py
```

This installs:
- `selenium>=4.15.0` - WebDriver automation library
- `webdriver-manager>=4.0.0` - Automatic ChromeDriver management

### 2. Install Chrome Browser

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y google-chrome-stable
```

**Windows:**
Download and install from: https://www.google.com/chrome/

**macOS:**
```bash
brew install --cask google-chrome
```

## Usage

Once installed, JavaScript authentication works automatically:

```bash
# This command will automatically use JavaScript if needed
python run.py scrape --auth email_otp --username your@email.com https://example.com
```

## How It Works

1. **Standard HTTP First**: The system first tries normal HTTP form submission
2. **JavaScript Detection**: If the response redirects back to the login page, it scans for JavaScript form handlers
3. **Browser Fallback**: If JavaScript is detected, it launches a Chrome browser to handle the form
4. **Form Interaction**: The browser navigates to the page, fills the email field, and clicks the OTP button
5. **Success Detection**: Looks for success indicators or URL changes to confirm the email was sent

## Configuration

JavaScript behavior can be configured via plugin config:

```python
config = {
    'javascript': {
        'enabled': True,          # Enable/disable JavaScript fallback
        'headless': True,         # Run browser in headless mode
        'timeout': 30,           # Page load timeout in seconds
        'implicit_wait': 10,     # Element wait timeout
        'window_size': (1920, 1080),  # Browser window size
        'user_agent': 'Mozilla/5.0...'  # Custom user agent
    }
}
```

## Supported Sites

The JavaScript authentication has been designed to work with sites like:
- ideabrowser.com (email OTP)
- Any site using JavaScript form submission
- Modern SPA applications with AJAX authentication

## Troubleshooting

### Chrome Not Found
```
Error: cannot find Chrome binary
```
**Solution**: Install Google Chrome browser (see Installation section)

### Dependencies Not Installed
```
Error: Failed to initialize browser automation
```
**Solution**: Run `python install_js_deps.py`

### Timeout Issues
```
Error: TimeoutException
```
**Solution**: Increase timeout in configuration or check network connectivity

### Element Not Found
```
Error: Could not find email input field
```
**Solution**: The site may have changed its HTML structure. Update selectors in the plugin.

## Technical Details

### Architecture

- **JavaScriptAuthMixin**: Base mixin class providing browser automation capabilities
- **EmailOTPPlugin**: Extended to inherit JavaScript capabilities
- **Automatic Detection**: Uses regex patterns to detect JavaScript form handlers
- **Context Management**: Proper WebDriver cleanup using context managers

### Element Detection

The system looks for email inputs using multiple selectors:
- `input[type="email"]`
- `input[name*="email"]`
- `input[id*="email"]`
- `input[autocomplete="email"]`

### Success Detection

After form submission, it looks for:
- Success messages containing "code sent", "email sent", etc.
- URL changes indicating successful submission
- Verification code input fields appearing on the page

## Limitations

1. **Chrome Dependency**: Requires Chrome browser installation
2. **Performance**: Slower than HTTP-only authentication due to browser overhead
3. **Detection Accuracy**: May occasionally miss JavaScript requirements or false-positive detect them
4. **Site Changes**: May need updates if target sites change their HTML structure

## Development

### Adding New JavaScript Authentication

1. Extend your plugin with `JavaScriptAuthMixin`
2. Implement `perform_login_js()` method
3. Add site-specific element selectors
4. Test with the target website

### Example Implementation

```python
from .js_auth_mixin import JavaScriptAuthMixin
from .base_plugin import BaseAuthPlugin

class MyPlugin(JavaScriptAuthMixin, BaseAuthPlugin):
    def perform_login_js(self, session, form, username, password):
        with self as js_context:
            if not self.driver:
                return AuthResult(success=False, error_message="Browser not available")
            
            # Navigate and interact with page
            self.driver.get(form.action_url)
            # ... implement site-specific logic
            
            return AuthResult(success=True)
```

## Contributing

When adding support for new sites:
1. Test both HTTP and JavaScript paths
2. Add appropriate success/failure detection
3. Update documentation with new supported sites
4. Include error handling for common failures