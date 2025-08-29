# 🔐 Authentication Guide

This guide covers how to use the site2pdf authentication system to scrape protected websites that require login.

## Overview

The authentication system automatically detects login forms, handles credentials securely, and maintains sessions to avoid repeated logins. It works with most websites out of the box and supports advanced configurations for complex sites.

## Quick Start

### 1. Basic Authentication

**Command Line:**
```bash
# Direct credentials
./site2pdf https://protected-site.com --username myuser --password mypass

# Username only (password prompted securely)
./site2pdf https://protected-site.com --username myuser
```

**Environment Variables (Recommended):**
```bash
# Set credentials
export SITE2PDF_AUTH_USERNAME="your-username"
export SITE2PDF_AUTH_PASSWORD="your-password"

# Use authentication
./site2pdf https://protected-site.com --auth
```

### 2. Site-Specific Credentials

For multiple sites with different credentials:

```bash
# Site-specific environment variables (higher priority)
export SITE2PDF_DOCS_COMPANY_COM_USERNAME="work-user"
export SITE2PDF_DOCS_COMPANY_COM_PASSWORD="work-pass"
export SITE2PDF_GITHUB_COM_USERNAME="github-user"
export SITE2PDF_GITHUB_COM_PASSWORD="github-token"

# Scrape different sites with their specific credentials
./site2pdf https://docs.company.com --auth
./site2pdf https://github.com/private/repo --auth
```

## Advanced Configuration

### YAML Configuration

Add authentication configuration to `config.yaml`:

```yaml
authentication:
  enabled: true
  cache_sessions: true
  session_duration: "24h"
  
  sites:
    # Corporate intranet example
    intranet.company.com:
      plugin: "generic_form"
      login_url: "/auth/login"
      form_selectors:
        username_field: "input#employee-id"
        password_field: "input#password"
        submit_button: "button[type='submit']"
        csrf_token: "input[name='_csrf']"
      success_indicators:
        - ".user-profile"
        - "nav.authenticated"
      failure_indicators:
        - ".login-error"
        - ".auth-failed"
      session_duration: "8h"
    
    # Multi-step login example
    sso.company.com:
      plugin: "generic_form"
      multi_step_login: true
      form_selectors:
        username_field: "input[name='email']"
        password_field: "input[name='password']"
      success_indicators:
        - ".dashboard"
        - ".welcome-user"
```

### Session Management

Sessions are automatically cached to avoid repeated logins:

```bash
# First run - performs login and caches session
./site2pdf https://protected-site.com --auth

# Subsequent runs within 24h - reuses cached session
./site2pdf https://protected-site.com --auth

# Check session status (via verbose output)
./site2pdf https://protected-site.com --auth --verbose
```

## Common Use Cases

### 1. Corporate Intranets

```bash
# Set corporate credentials
export SITE2PDF_INTRANET_COMPANY_COM_USERNAME="employee.id"
export SITE2PDF_INTRANET_COMPANY_COM_PASSWORD="corporate-password"

# Scrape internal documentation
./site2pdf https://intranet.company.com/docs --auth --format markdown
```

### 2. GitHub Private Repositories

```bash
# Set GitHub credentials (use personal access token as password)
export SITE2PDF_GITHUB_COM_USERNAME="your-github-username"
export SITE2PDF_GITHUB_COM_PASSWORD="ghp_your_personal_access_token"

# Scrape private repository documentation
./site2pdf https://github.com/company/private-docs --auth
```

### 3. Confluence/Jira Sites

```bash
# Atlassian credentials
export SITE2PDF_COMPANY_ATLASSIAN_NET_USERNAME="your-email@company.com"
export SITE2PDF_COMPANY_ATLASSIAN_NET_PASSWORD="api-token"

# Scrape Confluence documentation
./site2pdf https://company.atlassian.net/wiki/spaces/DOCS --auth --format markdown
```

### 4. WordPress Sites

```bash
# WordPress admin credentials
export SITE2PDF_MYBLOG_COM_USERNAME="admin"
export SITE2PDF_MYBLOG_COM_PASSWORD="admin-password"

# Scrape protected WordPress content
./site2pdf https://myblog.com/protected-area --auth
```

## Security Best Practices

### 1. Environment Variables

**Recommended approach** - keeps credentials out of command history:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export SITE2PDF_AUTH_USERNAME="your-username"
export SITE2PDF_AUTH_PASSWORD="your-password"

# Or use a .env file (not committed to version control)
echo "SITE2PDF_AUTH_USERNAME=your-username" >> .env
echo "SITE2PDF_AUTH_PASSWORD=your-password" >> .env
```

### 2. Site-Specific Variables

Use site-specific variables for better security isolation:

```bash
# Convert domain to environment variable format:
# example.com -> SITE2PDF_EXAMPLE_COM_USERNAME
# docs.company.com -> SITE2PDF_DOCS_COMPANY_COM_USERNAME
# sub-domain.site.org -> SITE2PDF_SUB_DOMAIN_SITE_ORG_USERNAME

export SITE2PDF_DOCS_COMPANY_COM_USERNAME="work-user"
export SITE2PDF_DOCS_COMPANY_COM_PASSWORD="work-pass"
```

### 3. Interactive Prompts

For maximum security, provide only username and let the system prompt for password:

```bash
# Password will be prompted securely (hidden input)
./site2pdf https://sensitive-site.com --username secure-user
```

## Troubleshooting

### 1. Login Detection Issues

**Problem**: "Could not detect login form"

**Solutions:**
```bash
# Enable verbose logging to see what's happening
./site2pdf https://site.com --username user --verbose

# Check the actual login page URL
curl -I https://site.com/login

# Try specifying login URL in config
```

```yaml
authentication:
  sites:
    site.com:
      login_url: "/auth/signin"  # Exact login URL
```

### 2. Authentication Fails

**Problem**: Login appears successful but still can't access content

**Solutions:**
```bash
# Check session validation
./site2pdf https://site.com --auth --verbose

# Clear cached sessions and retry
rm -rf cache/auth_sessions/
./site2pdf https://site.com --auth
```

### 3. Multi-Step Login Issues

**Problem**: Site uses username-first, then password flow

**Solution:**
```yaml
authentication:
  sites:
    site.com:
      multi_step_login: true
      form_selectors:
        username_field: "input[name='email']"
        password_field: "input[name='password']"
```

### 4. Session Expires Quickly

**Problem**: Login session expires too fast

**Solutions:**
```yaml
# Extend session duration
authentication:
  session_duration: "48h"  # Longer duration
  sites:
    site.com:
      session_duration: "12h"  # Site-specific duration
```

### 5. Complex Login Forms

**Problem**: Site has unusual login form structure

**Solution:** Create custom configuration:

```yaml
authentication:
  sites:
    complex-site.com:
      plugin: "generic_form"
      form_selectors:
        form_selector: "form#custom-login"  # Specific form
        username_field: "input.user-email"  # CSS class selector
        password_field: "#pwd-input"        # ID selector
        submit_button: "button.login-btn"
        csrf_token: "meta[name='csrf-token']"  # Meta tag token
      success_indicators:
        - "#user-dashboard"
        - ".authenticated-header"
      failure_indicators:
        - ".error-container .message"
```

## Environment Variable Reference

### Format Pattern
```
SITE2PDF_[DOMAIN]_[FIELD]
```

**Domain Conversion Rules:**
- Replace dots (.) with underscores (_)
- Replace hyphens (-) with underscores (_)
- Convert to uppercase
- Remove protocols and paths

### Examples
| Domain | Username Variable | Password Variable |
|--------|------------------|-------------------|
| `example.com` | `SITE2PDF_EXAMPLE_COM_USERNAME` | `SITE2PDF_EXAMPLE_COM_PASSWORD` |
| `docs.company.com` | `SITE2PDF_DOCS_COMPANY_COM_USERNAME` | `SITE2PDF_DOCS_COMPANY_COM_PASSWORD` |
| `sub-domain.site.org` | `SITE2PDF_SUB_DOMAIN_SITE_ORG_USERNAME` | `SITE2PDF_SUB_DOMAIN_SITE_ORG_PASSWORD` |
| `company.atlassian.net` | `SITE2PDF_COMPANY_ATLASSIAN_NET_USERNAME` | `SITE2PDF_COMPANY_ATLASSIAN_NET_PASSWORD` |

### General Fallback Variables
- `SITE2PDF_AUTH_USERNAME` - General username (used if site-specific not found)
- `SITE2PDF_AUTH_PASSWORD` - General password (used if site-specific not found)

## Session Cache Management

### Cache Location
```
cache/auth_sessions/
├── example_com_auth_session.json.gz     # Cached session for example.com
├── github_com_auth_session.json.gz      # Cached session for github.com
└── company_com_auth_session.json.gz     # Cached session for company.com
```

### Manual Cache Management
```bash
# View cached sessions
ls -la cache/auth_sessions/

# Clear all authentication sessions
rm -rf cache/auth_sessions/

# Clear session for specific site
rm cache/auth_sessions/example_com_auth_session.json.gz

# View session expiry (requires jq)
zcat cache/auth_sessions/example_com_auth_session.json.gz | jq .expires_at
```

## Integration Examples

### Scheduled Scraping
```bash
#!/bin/bash
# daily-scrape.sh - Automated daily documentation scraping

# Set credentials (put in crontab or environment)
export SITE2PDF_DOCS_COMPANY_COM_USERNAME="automated-user"
export SITE2PDF_DOCS_COMPANY_COM_PASSWORD="api-token"

# Scrape with authentication and save with date
DATE=$(date +%Y-%m-%d)
./site2pdf https://docs.company.com \
  --auth \
  --format markdown \
  --output "company-docs-${DATE}.md" \
  --verbose

# Add to crontab:
# 0 6 * * * /path/to/daily-scrape.sh
```

### Multiple Sites Script
```bash
#!/bin/bash
# multi-site-scrape.sh - Scrape multiple authenticated sites

declare -A SITES=(
  ["https://intranet.company.com/docs"]="company-intranet"
  ["https://wiki.company.com"]="company-wiki"
  ["https://confluence.company.com/spaces/DOCS"]="confluence-docs"
)

for url in "${!SITES[@]}"; do
  output="${SITES[$url]}-$(date +%Y%m%d).md"
  echo "Scraping $url -> $output"
  
  ./site2pdf "$url" \
    --auth \
    --format markdown \
    --output "$output" \
    --chunk-size 5MB
done
```

## Support

### Getting Help

1. **Check verbose output** for authentication details:
   ```bash
   ./site2pdf https://site.com --username user --verbose
   ```

2. **Test with simple sites first** (like GitHub) to verify setup

3. **Check the authentication module documentation**:
   ```bash
   cat system_tools/authentication/README.md
   ```

4. **Examine site-specific configurations**:
   ```bash
   python -c "from system_tools.authentication.config.site_configs import get_predefined_site_configs; print(get_predefined_site_configs())"
   ```

### Common Issues Summary

| Issue | Symptom | Solution |
|-------|---------|----------|
| No login form detected | "Could not detect login form" | Check login URL, add custom selectors |
| Wrong credentials | "Login failed" message | Verify environment variables |
| Session expires | Asks for login repeatedly | Increase session duration |
| Multi-step login | Stuck after username entry | Enable multi_step_login |
| Complex forms | Form submission fails | Add custom form selectors |
| CSRF issues | Login fails silently | Check CSRF token selector |

For additional help, refer to the main README.md and system_tools/authentication/README.md documentation.