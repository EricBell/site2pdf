# Email OTP Authentication

The site2pdf scraper now supports email-based one-time passcode (OTP) authentication for sites that use passwordless email verification.

## How Email OTP Works

1. **Email Submission**: User enters their email address on the login page
2. **Code Delivery**: Site sends a verification code to the user's email
3. **Interactive Verification**: User retrieves the code from email and enters it
4. **Session Establishment**: Authentication completes and session is established

## Usage

### Command Line

```bash
# Use email OTP authentication
python run.py scrape https://example.com --auth email_otp --username your-email@example.com

# The scraper will:
# 1. Submit your email address
# 2. Wait for the verification code email
# 3. Prompt you to enter the code interactively
# 4. Complete authentication and start scraping
```

### Interactive Flow

When using email OTP authentication, you'll see prompts like:

```
📧 Verification code sent to your-email@example.com
📧 A verification code has been sent to your email. Please enter the code: 123456
```

### Error Handling

- **Invalid codes**: Up to 3 retry attempts with new code entry prompts
- **Timeout**: 5-minute default timeout for code entry (configurable)
- **Clear error messages**: Specific feedback for different failure scenarios

## Configuration

You can customize email OTP behavior in your configuration:

```yaml
authentication:
  email_otp:
    otp_timeout: 300        # Timeout in seconds (default: 5 minutes)
    max_retries: 3          # Maximum retry attempts (default: 3)
```

## Supported Sites

Email OTP authentication works with sites that:

- Have email-only login forms (no password field)
- Send verification codes via email
- Use standard form patterns for code submission
- Follow common email authentication flows

## Technical Details

### Form Detection

The plugin automatically detects:
- Email input fields (`<input type="email">` or name/placeholder containing "email")
- Absence of password fields (indicating email-only authentication)
- OTP verification forms (input fields for codes/tokens)
- CSRF tokens and hidden form fields

### Security Features

- **Session persistence**: Authenticated sessions are cached securely
- **CSRF protection**: Automatically handles CSRF tokens
- **Timeout management**: Prevents indefinite waiting for codes
- **Retry limits**: Prevents brute force attempts

### Plugin Architecture

Email OTP is implemented as a modular plugin that extends the base authentication system:

- **EmailOTPPlugin**: Handles email OTP-specific logic
- **BaseAuthPlugin**: Provides common authentication functionality
- **AuthenticationManager**: Coordinates different authentication types

## Example Sites

This authentication method works well with sites like:
- Documentation platforms
- SaaS applications
- Modern web applications using passwordless authentication
- Sites with "magic link" or "email verification" login flows

## Troubleshooting

### Code Not Received
- Check spam/junk folder
- Verify email address is correct
- Wait a few minutes for email delivery
- Try canceling and restarting authentication

### Invalid Code Errors
- Ensure code is entered exactly as received
- Check for extra spaces or characters
- Verify code hasn't expired
- Some codes are case-sensitive

### Form Detection Issues
- Plugin may fall back to generic form authentication
- Check that the site actually uses email OTP (no password field)
- Site may have non-standard form patterns