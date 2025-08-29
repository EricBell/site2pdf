#!/usr/bin/env python3
"""
Authentication Exception Classes
"""

class AuthenticationError(Exception):
    """Base exception for authentication errors"""
    pass

class SessionExpiredError(AuthenticationError):
    """Raised when authentication session has expired"""
    pass

class LoginFailedError(AuthenticationError):
    """Raised when login attempt fails"""
    pass

class FormDetectionError(AuthenticationError):
    """Raised when login form cannot be detected or parsed"""
    pass

class CredentialError(AuthenticationError):
    """Raised when credentials are invalid or missing"""
    pass

class PluginError(AuthenticationError):
    """Raised when authentication plugin encounters an error"""
    pass