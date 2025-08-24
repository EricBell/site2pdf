#!/usr/bin/env python3
"""
Versioning System Tools
======================

Automatic version management based on file changes with SHA256 hashing.

Features:
- Automatic patch version increments on file changes
- Manual major/minor version control
- File hash tracking for change detection
- Configurable file patterns
- JSON-based version storage

Usage:
    from system_tools.versioning import VersionManager
    
    vm = VersionManager()
    version_string = vm.get_version_string()
    major, minor, patch = vm.get_current_version()
"""

from .version_manager import (
    VersionManager,
    get_version_string,
    increment_major
)

__all__ = [
    'VersionManager',
    'get_version_string',
    'increment_major'
]