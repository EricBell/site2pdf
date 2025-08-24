# Version Management System

A robust file-based version management system that automatically tracks changes and manages semantic versioning (major.minor.patch).

## Features

- **Automatic Change Detection**: Uses SHA256 file hashing to detect modifications
- **Semantic Versioning**: Supports major.minor.patch version format
- **Configurable File Tracking**: Customizable patterns for tracked files  
- **JSON Storage**: Simple JSON-based version and hash storage
- **CLI Interface**: Command-line tools for version management
- **Project Agnostic**: Easily portable to any Python project

## Installation

Copy the `versioning` package to your project or install as a standalone package:

```python
from system_tools.versioning import VersionManager
```

## Quick Start

```python
# Initialize version manager
vm = VersionManager("/path/to/your/project")

# Get current version
major, minor, patch = vm.get_current_version()
print(f"Current version: v{major}.{minor}.{patch}")

# Check for changes and auto-increment patch version
major, minor, patch, changed = vm.check_and_update_version()
if changed:
    print(f"Version updated to v{major}.{minor}.{patch}")

# Manual version control
vm.increment_major_version()  # 2.0.0
vm.increment_minor_version()  # 2.1.0  
vm.increment_patch_version()  # 2.1.1
```

## CLI Usage

```bash
# Show current version
python -m system_tools.versioning status

# Check for changes and update
python -m system_tools.versioning check

# Manual version increments
python -m system_tools.versioning major
python -m system_tools.versioning minor  
python -m system_tools.versioning patch

# Reset version
python -m system_tools.versioning reset
python -m system_tools.versioning reset 2 1 0  # Reset to v2.1.0
```

## Configuration

### Default File Patterns

The version manager tracks these file patterns by default:

- `*.py` - All Python files
- `templates/**/*.html` - HTML templates (recursive)
- `requirements.txt` - Python dependencies
- `*.spec` - Spec files

### Custom Configuration

```python
vm = VersionManager(
    project_root="/path/to/project",
    tracked_files=[
        "*.py",
        "src/**/*.js", 
        "config/*.yaml",
        "*.md"
    ]
)
```

### Excluded Directories

These directories are automatically excluded from tracking:
- `.git`, `.svn` (version control)
- `dist`, `build` (build artifacts)
- `__pycache__` (Python cache)
- `node_modules` (Node.js dependencies)
- Any directory starting with `.`

## Version Storage

Version information is stored in `version.json`:

```json
{
  "major": 1,
  "minor": 2, 
  "patch": 5,
  "file_hashes": {
    "src/main.py": "a1b2c3d4...",
    "config.yaml": "e5f6g7h8..."
  }
}
```

## Integration with CI/CD

```python
# In your build script
from system_tools.versioning import VersionManager

vm = VersionManager()
major, minor, patch, changed = vm.check_and_update_version()

if changed:
    print(f"::set-output name=version::v{major}.{minor}.{patch}")
    print(f"::set-output name=changed::true")
```

## Copying to Other Projects

To use in another project:

1. Copy the entire `system_tools/versioning/` directory
2. Update import paths if needed
3. Initialize with your project's root directory
4. Customize `tracked_files` patterns as needed

## API Reference

### VersionManager

#### Constructor
- `VersionManager(project_root=None)` - Initialize with optional project root

#### Methods
- `get_current_version()` - Returns (major, minor, patch) tuple
- `check_and_update_version()` - Returns (major, minor, patch, changed) tuple  
- `increment_major_version()` - Manually increment major version
- `increment_minor_version()` - Manually increment minor version
- `increment_patch_version()` - Manually increment patch version
- `get_version_string()` - Returns formatted "vX.Y.Z" string
- `reset_version(major=1, minor=0, patch=0)` - Reset to specific version

### Convenience Functions

- `get_version_string()` - Get version string using global instance
- `increment_major()` - Increment major version using global instance