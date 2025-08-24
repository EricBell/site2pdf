#!/usr/bin/env python3
"""
System Tools Package
===================

A collection of reusable system utilities for Python projects.

Available subpackages:
- versioning: Version management with file hashing
- logging: Enhanced logging utilities (future)
- config: Configuration management (future)  
- monitoring: System monitoring tools (future)
"""

# Import main classes for convenience
from .versioning import VersionManager, get_version_string, increment_major

__version__ = "1.0.0"
__author__ = "Site2PDF Team"

__all__ = [
    'VersionManager',
    'get_version_string', 
    'increment_major'
]