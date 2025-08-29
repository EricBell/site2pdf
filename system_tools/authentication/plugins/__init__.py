#!/usr/bin/env python3
"""
Authentication Plugins Package
"""

from .base_plugin import BaseAuthPlugin, LoginForm, AuthResult
from .generic_form import GenericFormPlugin
from .email_otp import EmailOTPPlugin

__all__ = [
    'BaseAuthPlugin',
    'LoginForm', 
    'AuthResult',
    'GenericFormPlugin',
    'EmailOTPPlugin'
]