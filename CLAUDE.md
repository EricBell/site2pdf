# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

site2pdf is a sophisticated web scraping and document generation tool that converts websites into professional PDF and Markdown documents. It features intelligent content classification, human-like browsing behavior, modular authentication, and comprehensive caching systems.

## Core Architecture

### Entry Point and CLI
- **run.py**: Main entry point that sets up Python path and imports from src/cli.py
- **src/cli.py**: Click-based CLI with three main command groups: `scrape`, `todo`, `cache`
- Path setup imports: `generators/` and `system_tools/` packages added to Python path

### Main Processing Pipeline
1. **URL Discovery**: src/scraper.py orchestrates the crawling process
2. **Content Classification**: src/content_classifier.py categorizes pages (docs, content, navigation)
3. **Content Extraction**: src/extractor.py extracts and cleans HTML content
4. **Output Generation**: generators/ package creates PDF or Markdown
5. **Caching**: src/cache_manager.py handles session persistence

### Generator Architecture (Output Formats)
- **generators/__init__.py**: Base classes and validation
- **generators/pdf/pdf_generator.py**: WeasyPrint-based PDF generation
- **generators/markdown/markdown_generator.py**: HTML-to-Markdown conversion
- Each generator implements common interface with format-specific logic

### System Tools (Reusable Modules)
- **system_tools/authentication/**: Modular authentication system with plugins
- **system_tools/versioning/**: Version management utilities
- **system_tools/config/**: Configuration management
- **system_tools/logging/**: Logging utilities

## Key Development Commands

### Running the Application
```bash
# Basic scraping
python run.py scrape https://example.com

# With format options
python run.py scrape https://example.com --format markdown --output docs.md

# Authentication
python run.py scrape https://protected-site.com --username user --password pass

# Preview mode (interactive URL selection)
python run.py scrape https://example.com --preview

# Resume from cache
python run.py scrape https://example.com --resume session_id
```

### Todo Management
```bash
# Add todo
python run.py todo add "Fix bug" --priority high --category bug

# List todos
python run.py todo list --priority high

# Mark complete
python run.py todo done todo_id
```

### Cache Management
```bash
# List cached sessions
python run.py cache list --verbose

# Clean old sessions
python run.py cache clean --older-than 7d

# Export from cache
python run.py cache export session_id --format markdown
```

### Testing and Development
```bash
# Check syntax of all Python files
find . -name "*.py" -not -path "*/.venv/*" -exec python -m py_compile {} \;

# Verbose logging for debugging
python run.py scrape https://example.com --verbose

# Dry run (no actual scraping)
python run.py scrape https://example.com --dry-run
```

## Authentication System Architecture

The authentication system is modular and plugin-based:

### Core Components
- **auth_manager.py**: Main authentication orchestrator
- **session_store.py**: Session persistence and cookie management
- **credential_manager.py**: Secure credential handling
- **plugins/**: Site-specific authentication implementations

### Plugin System
- **email_otp.py**: Email OTP authentication with JavaScript automation
- **generic_form.py**: Generic form-based authentication
- **js_auth_mixin.py**: WebDriver automation utilities

### Authentication Methods Priority
1. **JavaScript automation**: Selenium WebDriver for complex forms
2. **Direct API**: Direct HTTP requests for simple forms
3. **Manual intervention**: User-guided authentication with automatic cookie extraction

### Configuration
Authentication is configured in config.yaml under `authentication:` section and uses environment variables for credentials (SITE2PDF_*_USERNAME/PASSWORD pattern).

## Content Processing Pipeline

### Intelligent Content Classification
- **Documentation pages**: /docs/, /help/, /guide/ patterns
- **Content pages**: /about/, /blog/, /features/ patterns  
- **Navigation pages**: Homepage, sitemaps, navigation
- **Excluded content**: Admin, API, login pages automatically filtered

### Human-Like Behavior Simulation
- **src/human_behavior.py**: Implements realistic delays and browsing patterns
- **Variable timing**: 2-8 second reading delays with decision time
- **Microsoft Edge simulation**: Realistic headers and user agents
- **Fatigue modeling**: Gradually slower behavior over time

### Path-Aware Scoping
- **src/path_scoping.py**: Keeps crawling within relevant website sections
- Automatically allows parent paths, homepage, and sibling sections
- Prevents crawling into unrelated areas (e.g., /blog when starting in /docs)

## Cache System Architecture

### Session-Based Caching
- **Cache structure**: cache/sessions/{session_id}/ with metadata and pages
- **Incremental saving**: Pages cached immediately as scraped
- **Resume capability**: Continue from exact interruption point
- **Format generation**: Create PDF/Markdown from cache without re-scraping

### Preview Session Persistence
- **cache/previews/**: Stores URL approval decisions
- **Interactive workflow**: Save user selections for later resume
- **Bulk operations**: Support for range selection (e.g., "1,3,5-8,12")

## Output Generation System

### Chunking System
- **src/chunk_manager.py**: Splits large outputs into manageable pieces
- **Size-based chunking**: Maximum file size (e.g., "5MB", "10MB")
- **Page-based chunking**: Maximum pages per chunk
- **Index generation**: Creates navigation between chunks

### Format-Specific Features
- **PDF**: WeasyPrint with table of contents, embedded images, professional styling
- **Markdown**: GitHub-compatible with TOC, proper image handling, multi-file support
- **Image handling**: Download/embed or replace with descriptive text for LLM compatibility

## Configuration Management

### Main Configuration (config.yaml)
- **Crawling settings**: max_depth, request_delay, max_pages
- **Content processing**: include_menus, include_images, remove_images
- **Output formats**: PDF and Markdown specific settings
- **Cache settings**: retention, compression, cleanup policies
- **Authentication**: Site-specific configuration

### Environment Variables (.env)
- **Credentials**: SITE2PDF_*_USERNAME/PASSWORD patterns
- **Proxy settings**: HTTP_PROXY support
- **Debug flags**: DEBUG_MODE for enhanced logging

## Important Implementation Details

### Error Handling
- **Selenium exceptions**: Extract clean error messages without verbose stacktraces
- **WebDriver management**: Proper cleanup and session restoration
- **Cache corruption**: Graceful handling with automatic recovery

### Manual Authentication Workflow
- **WebDriver reuse**: Creates non-headless browser for user interaction
- **Automatic cookie extraction**: Captures authentication cookies from browser session
- **Session validation**: Tests extracted cookies before proceeding
- **Cleanup**: Restores headless mode after manual authentication completes

### Path Setup and Imports
The project uses a specific import structure:
- Root-level packages (generators, system_tools) added to sys.path in run.py
- src/ modules accessed via relative imports
- Authentication plugins use relative imports within system_tools package

### Data Persistence
- **Todo storage**: YAML-based with metadata tracking
- **Cache compression**: gzip compression for efficient storage
- **Session metadata**: Comprehensive tracking of scraping state

## Development Patterns

### Adding New Output Formats
1. Create new package in generators/ (e.g., generators/epub/)
2. Implement base generator interface from generators/__init__.py
3. Register format in main CLI (src/cli.py)
4. Add format-specific configuration to config.yaml

### Adding Authentication Plugins
1. Create plugin in system_tools/authentication/plugins/
2. Inherit from base plugin classes in authentication/
3. Implement required methods: perform_login, validate_session
4. Register plugin in auth_manager.py plugin discovery

### Cache Session Extensions
1. Extend session metadata in cache_manager.py
2. Update session validation logic
3. Add CLI commands in cache_cli.py for new functionality
4. Ensure backward compatibility with existing sessions

This architecture enables modular development while maintaining clean separation of concerns between web scraping, content processing, output generation, and system utilities.