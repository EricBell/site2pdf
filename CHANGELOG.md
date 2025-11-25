# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Fixed syntax warning in `src/preview.py` - Changed regex pattern from `'[,\s]+'` to `r'[,\s]+'` to use raw string for proper escape sequence handling (Python 3.14+ compatibility)
- Fixed Python version requirement in `pyproject.toml` from `>=3.14` to `>=3.8` (Python 3.14 doesn't exist yet)
- Corrected package name in dependencies: `bs4` → `beautifulsoup4`

### Added
- **uv package manager support** - Added full support for uv as the recommended package manager
  - Organized optional dependencies into `[dev]` and `[auth]` groups
  - Added instructions for `uv sync` and `uv run` workflows
- **Comprehensive system dependency documentation**
  - Platform-specific installation instructions for WeasyPrint dependencies (Ubuntu/Debian, Fedora, macOS)
  - Detailed package name differences between Debian versions (Trixie vs older)
  - Note about `libgdk-pixbuf-2.0-0` vs `libgdk-pixbuf2.0-0` package naming
- **Enhanced troubleshooting documentation**
  - Added 8 common issues with detailed solutions in README.md
  - Added Common Issues section to CLAUDE.md for developers
  - Documented disk space cleanup procedures
  - Explained Selenium warning (it's not an error)
- **Improved pyproject.toml metadata**
  - Added MIT license specification
  - Added keywords for better discoverability
  - Added Python package classifiers
  - Added CLI entry point script definition
  - Added build system configuration (hatchling)
  - Added pytest and coverage tool configurations
- **Updated documentation structure**
  - Added "Running with uv" section in README.md
  - Added "Package Management" section in CLAUDE.md
  - Added "System Requirements" section in CLAUDE.md
  - Added verification commands for system library installation

### Changed
- Updated all core dependencies to latest compatible versions in `pyproject.toml`:
  - requests >=2.31.0
  - beautifulsoup4 >=4.12.0
  - weasyprint >=60.0
  - Pillow >=10.0.0
  - And others...
- Reorganized README installation section with both pip and uv methods
- Updated CLAUDE.md command examples to include uv alternatives
- Enhanced README troubleshooting section with specific error messages and solutions

### Documentation
- README.md: Added comprehensive installation, usage, and troubleshooting sections
- CLAUDE.md: Added system requirements, package management, and common issues sections
- Updated all command examples to mention both `python run.py` and `uv run python run.py` workflows

## [0.1.0] - Previous Release

Initial release with core features:
- Web scraping with intelligent content classification
- PDF and Markdown generation
- Human-like browsing behavior
- Modular authentication system
- Session-based caching
- Cache management with doctor functionality
- Todo management system
- JavaScript rendering support (optional)
- Path-aware scoping
- Preview mode with URL selection
