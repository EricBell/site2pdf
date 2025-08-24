# System Tools Package

A comprehensive collection of reusable system utilities for Python projects. Each subpackage is designed to be independently usable and easily portable to other projects.

## Available Subpackages

### 🔄 Versioning (`system_tools.versioning`)
**Status: ✅ Complete**

Automatic version management with file-based change detection:
- SHA256 file hashing for change detection
- Semantic versioning (major.minor.patch)
- CLI interface for version control
- JSON-based storage

```python
from system_tools.versioning import VersionManager
vm = VersionManager()
print(vm.get_version_string())  # v1.2.3
```

### 📝 Logging (`system_tools.logging`) 
**Status: 🚧 Planned**

Enhanced logging utilities:
- Structured JSON logging
- Log rotation and archiving  
- Performance monitoring
- Custom formatters and handlers

### ⚙️ Configuration (`system_tools.config`)
**Status: 🚧 Planned**

Configuration management tools:
- YAML/JSON validation
- Environment variable management
- Configuration inheritance
- Schema validation

### 📊 Monitoring (`system_tools.monitoring`)
**Status: 🚧 Planned**

System monitoring and health checks:
- Performance metrics collection
- Health check endpoints
- Resource usage monitoring
- Alert systems

## Installation

### In Current Project
```python
from system_tools import VersionManager
from system_tools.versioning import get_version_string
```

### Copy to Another Project
1. Copy entire `system_tools/` directory
2. Update imports if needed
3. Install dependencies listed in each subpackage

## Design Principles

- **Independence**: Each subpackage works standalone
- **Reusability**: Easy to copy to other projects
- **Minimal Dependencies**: Only essential external dependencies
- **Clear APIs**: Well-documented interfaces
- **Extensibility**: Plugin-friendly architecture

## Dependencies by Subpackage

### Versioning
- **Standard Library Only**: `json`, `hashlib`, `pathlib`, `logging`
- **External**: None

### Future Subpackages
Dependencies will be documented in each subpackage's README.

## Usage Examples

### Quick Start
```python
# Version management
from system_tools import VersionManager
vm = VersionManager()
current = vm.get_current_version()  # (1, 2, 3)

# Check for changes and auto-increment
major, minor, patch, changed = vm.check_and_update_version()
```

### CLI Usage
```bash
# Version management
python -m system_tools.versioning status
python -m system_tools.versioning check
python -m system_tools.versioning major
```

## Contributing

When adding new system tools:

1. Create new subpackage directory
2. Add `__init__.py` with clear exports
3. Include comprehensive README.md
4. Update main `system_tools/__init__.py`
5. Document dependencies and usage
6. Ensure standalone functionality

## License

Each subpackage maintains its own license. Check individual README files for details.