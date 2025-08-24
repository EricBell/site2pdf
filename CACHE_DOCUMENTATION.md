# Cache System Documentation

## Overview

The site2pdf caching system provides robust data persistence and recovery capabilities to prevent data loss during scraping operations and enable efficient workflow management. The system consists of two main components: **Session Caching** for scraped content and **Preview Caching** for URL approval decisions.

## Architecture

### Core Components

1. **CacheManager** (`src/cache_manager.py`)
   - Manages scraped content caching and session lifecycle
   - Provides incremental page saving and loading capabilities
   - Handles session metadata and resume functionality

2. **PreviewCache** (`src/preview_cache.py`)
   - Manages preview session persistence
   - Stores URL approval/exclusion decisions
   - Enables resuming URL selection workflows

3. **Cache CLI** (`src/cache_cli.py`)
   - Command-line interface for cache management
   - Provides operations for listing, cleaning, and exporting cached data
   - Includes diagnostic and maintenance tools

### Directory Structure

```
cache/
├── sessions/                    # Scraped content cache
│   └── [session_id]/
│       ├── session.json         # Session metadata
│       └── pages/               # Cached page content
│           ├── page_001.json
│           ├── page_002.json
│           └── ...
└── previews/                    # Preview session cache
    └── [preview_id]/
        └── preview.json         # URL approval decisions
```

## Session Caching

### Session Lifecycle

1. **Creation**: New session created when scraping starts
2. **Population**: Pages incrementally saved as they're scraped
3. **Completion**: Session marked as completed when scraping finishes
4. **Resume**: Interrupted sessions can be resumed from last saved state
5. **Cleanup**: Old sessions automatically cleaned based on configuration

### Session Metadata Format

```json
{
  "session_id": "a1b2c3d4-5678-90ab-cdef-123456789012",
  "base_url": "https://docs.example.com",
  "status": "completed",
  "created_at": "2025-08-24T10:30:00Z",
  "last_modified": "2025-08-24T11:45:00Z",
  "pages_scraped": 25,
  "pages_total": 30,
  "config_hash": "abc123def456",
  "exclude_patterns": ["/admin", "/api"],
  "cache_size": 2048576
}
```

### Page Cache Format

```json
{
  "url": "https://docs.example.com/getting-started",
  "title": "Getting Started Guide",
  "content": "<html>...</html>",
  "text_content": "Getting Started...",
  "metadata": {
    "description": "Learn how to get started",
    "keywords": ["guide", "tutorial"],
    "author": "Example Team"
  },
  "images": [
    {
      "src": "https://example.com/image.png",
      "local_path": "temp/image_001.png",
      "alt": "Example diagram"
    }
  ],
  "links": ["https://docs.example.com/api"],
  "timestamp": "2025-08-24T10:35:00Z",
  "word_count": 450,
  "content_type": "documentation"
}
```

## Preview Caching

### Preview Session Format

```json
{
  "session_id": "b2c3d4e5-6789-01bc-def1-234567890123",
  "base_url": "https://docs.example.com",
  "status": "completed",
  "created_at": "2025-08-24T10:00:00Z",
  "last_modified": "2025-08-24T10:25:00Z",
  "urls_discovered": 45,
  "urls_approved": 25,
  "urls_excluded": 20,
  "approved_urls": [
    "https://docs.example.com/",
    "https://docs.example.com/getting-started",
    "https://docs.example.com/api-reference"
  ],
  "excluded_urls": [
    "https://docs.example.com/admin",
    "https://docs.example.com/login"
  ],
  "user_decisions": {
    "https://docs.example.com/getting-started": "approved",
    "https://docs.example.com/admin": "excluded"
  },
  "classifications": {
    "https://docs.example.com/getting-started": "documentation",
    "https://docs.example.com/admin": "admin"
  }
}
```

## Configuration

### Cache Settings (config.yaml)

```yaml
cache:
  enabled: true                  # Enable caching system
  directory: cache               # Cache directory location
  compression: true              # Compress cached data
  compression_level: 6           # Compression level (1-9)
  max_sessions: 100              # Maximum cached sessions
  auto_cleanup: true             # Automatic cleanup of old sessions
  cleanup_settings:
    max_age_days: 30             # Auto-remove sessions older than this
    keep_completed: 10           # Always keep recent completed sessions
  save_frequency: 5              # Save every N pages during scraping
  session_timeout_hours: 24      # Consider sessions stale after this time
```

## CLI Usage

### Basic Cache Operations

```bash
# List all cached sessions
python run.py cache list

# List with status filter
python run.py cache list --status completed

# Show detailed information
python run.py cache list --verbose

# View cache statistics
python run.py cache stats

# Show specific session details
python run.py cache show a1b2c3d4
```

### Cache Cleanup

```bash
# Clean old sessions (dry run first)
python run.py cache clean --older-than 7d --dry-run

# Actually clean old sessions
python run.py cache clean --older-than 7d

# Keep specific number of completed sessions
python run.py cache clean --older-than 30d --keep-completed 5

# Force deletion without confirmation
python run.py cache delete a1b2c3d4 --force
```

### Cache Export

```bash
# Export cached session to PDF
python run.py cache export a1b2c3d4 --format pdf

# Export to Markdown with custom filename
python run.py cache export a1b2c3d4 --format markdown --output docs.md

# Export to Markdown (alternative syntax)
python run.py cache export a1b2c3d4 --format md --output documentation.md
```

### Preview Session Management

```bash
# List preview sessions
python run.py cache previews

# List with status filter
python run.py cache previews --status completed
```

## Scraping with Cache

### Resume Scraping

```bash
# Normal scraping (creates cache automatically)
python run.py scrape https://docs.example.com

# Resume interrupted session
python run.py scrape https://docs.example.com --resume a1b2c3d4

# Generate output from cache without re-scraping
python run.py scrape --from-cache a1b2c3d4 --format pdf
python run.py scrape --from-cache a1b2c3d4 --format markdown
```

### Preview Session Resume

```bash
# Start preview mode (creates preview cache)
python run.py scrape https://docs.example.com --preview

# Resume preview session
python run.py scrape https://docs.example.com --resume-preview b2c3d4e5
```

## Advanced Features

### Session ID Format

Session IDs are generated using the following format:
- UUID4 format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- Based on: Base URL + timestamp + config hash
- Example: `a1b2c3d4-5678-90ab-cdef-123456789012`

### Compression

- **Enabled by default** for space efficiency
- Uses gzip compression with configurable level (1-9)
- Transparent compression/decompression during read/write operations
- Reduces disk usage by ~60-80% for typical web content

### Data Integrity

- **JSON validation** on all cached data
- **Timestamp verification** for session consistency
- **URL validation** for cached pages
- **Status consistency checks** between metadata and actual data

## Troubleshooting

### Common Issues

1. **Cache Directory Permissions**
   ```bash
   # Fix permissions
   chmod 755 cache/
   chmod -R 644 cache/sessions/
   chmod -R 644 cache/previews/
   ```

2. **Corrupted Cache Files**
   ```bash
   # Validate specific session
   python run.py cache show a1b2c3d4
   
   # If corrupted, delete and restart
   python run.py cache delete a1b2c3d4 --force
   ```

3. **Disk Space Issues**
   ```bash
   # Check cache size
   python run.py cache stats
   
   # Clean old sessions
   python run.py cache clean --older-than 7d
   ```

4. **Session Resume Failures**
   ```bash
   # Check session status
   python run.py cache show a1b2c3d4
   
   # Force resume if session appears active
   python run.py scrape https://example.com --resume a1b2c3d4 --verbose
   ```

### Debug Mode

Enable verbose logging to troubleshoot cache issues:

```bash
# Enable verbose mode for detailed cache operations
python run.py scrape https://example.com --verbose

# Check logs for cache-related messages
cat logs/scraper.log | grep -i cache
```

### Manual Cache Operations

For advanced users, cache files can be manually inspected:

```bash
# View session metadata
cat cache/sessions/a1b2c3d4-5678-90ab-cdef-123456789012/session.json

# List cached pages
ls cache/sessions/a1b2c3d4-5678-90ab-cdef-123456789012/pages/

# View specific page cache
cat cache/sessions/a1b2c3d4-5678-90ab-cdef-123456789012/pages/page_001.json
```

## Performance Considerations

### Optimization Tips

1. **Regular Cleanup**: Configure automatic cleanup to prevent unlimited growth
2. **Compression**: Enable compression to reduce disk usage
3. **Session Limits**: Set reasonable max_sessions limit based on available disk space
4. **Save Frequency**: Adjust save_frequency based on system performance and reliability needs

### Resource Usage

- **Disk Space**: ~1-5MB per page depending on content and compression
- **Memory**: Minimal overhead during normal operations
- **Performance**: <1% impact on scraping speed with incremental saving

## Security Considerations

### Data Protection

- Cache files contain scraped web content - ensure appropriate file permissions
- Cache directory should not be web-accessible
- Consider encryption for sensitive content
- Regular cleanup prevents accumulation of potentially sensitive data

### Best Practices

1. **Set appropriate file permissions** on cache directory
2. **Regular cleanup** of old cached sessions
3. **Monitor disk usage** to prevent system issues
4. **Backup important cache sessions** before major cleanups
5. **Review cached content** before sharing or archiving projects

This documentation provides comprehensive coverage of the caching system's capabilities, configuration options, and best practices for effective use.