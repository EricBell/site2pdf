# site2pdf 📄

A powerful Python CLI application that intelligently scrapes websites, generates comprehensive PDF documents with human-like behavior, and includes a full-featured todo management system for project organization.

## Features

### 🧠 **Intelligent Scraping**
- 🎯 **Path-Aware Discovery**: Stays focused on relevant sections (e.g., `/docs/*` only)
- 🏷️ **Content Classification**: Distinguishes documentation, content, navigation, and technical pages
- 🔍 **Smart URL Filtering**: Automatically excludes admin pages, APIs, and irrelevant content
- 📊 **Quality Assessment**: Analyzes page content quality and skips low-value pages

### 🕵️ **Human-Like Behavior** 
- 🎭 **Microsoft Edge Simulation**: Realistic browser headers and user agent
- ⏱️ **Variable Delays**: Human-like reading and decision times (2-8s per page)
- 🍪 **Session Management**: Proper cookie handling and referrer tracking
- 📈 **Adaptive Behavior**: Detects rate limiting and adjusts automatically
- 😴 **Fatigue Simulation**: Gradually slower over time like real users

### 📄 **Multi-Format Output Generation**
- 📖 **PDF Generation**: Professional PDFs with documentation focus
- 📝 **Markdown Export**: Clean, structured markdown with HTML-to-markdown conversion
- 🖼️ **Image Embedding**: Downloads and includes images with proper formatting
- 📚 **Table of Contents**: Automatic TOC generation with page/anchor links
- 🎨 **Professional Layout**: Clean, readable formatting with proper structure
- 📁 **Multi-File Support**: Single document or individual files per page

### 🔧 **Powerful Configuration**
- 🎮 **Interactive Preview**: Tree-view URL selection with approval system
- 💾 **URL List Persistence**: Save and reuse approved URL lists
- ⚙️ **Extensive Options**: Fine-tune crawling, delays, content filtering, and output
- 🚫 **Menu Exclusion**: Configurable removal of navigation menus from PDFs

### 💾 **Advanced Caching System**
- 🗄️ **Session-Based Caching**: Automatic caching of scraped pages to prevent data loss
- 🔄 **Resume Functionality**: Continue interrupted scraping sessions from where they left off
- 🎯 **Preview Session Persistence**: Save and resume URL approval decisions across sessions
- 📦 **Multi-Format Export**: Generate different output formats from cached data without re-scraping
- 🧹 **Cache Management**: CLI commands for listing, cleaning, and managing cached sessions
- ⚡ **Performance**: Avoid re-scraping when generating multiple output formats

### 📝 **Todo Management System**
- 📋 **YAML-Based Storage**: All todos stored in structured `todos.yaml` format
- 🎨 **Rich CLI Interface**: Beautiful icons, colors, and formatting
- 🎯 **Priority System**: Low, Medium, High, Urgent with visual indicators
- 📊 **Status Tracking**: Pending, In Progress, Completed, Cancelled
- 📂 **Categories**: Organize todos by type (bugs, features, documentation)
- 📅 **Due Dates**: Smart date parsing (today, tomorrow, specific dates)
- 💭 **Notes System**: Add timestamped notes to any todo
- 🔍 **Full-Text Search**: Search across descriptions, categories, and notes
- 📈 **Statistics Dashboard**: Track progress and completion rates

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd site2pdf
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Basic Usage

#### Website Scraping
```bash
# Scrape a website and generate PDF (default)
python run.py scrape https://example.com

# Generate markdown instead of PDF
python run.py scrape https://example.com --format markdown

# With custom options
python run.py scrape https://example.com --output my-site.pdf --max-depth 3 --verbose

# Export to markdown with custom filename
python run.py scrape https://example.com --format md --output my-site.md

# Exclude navigation menus from output (default)
python run.py scrape https://example.com

# Include navigation menus in output
python run.py scrape https://example.com --include-menus

# Dry run to see what would be scraped
python run.py scrape https://example.com --dry-run
```

#### Todo Management
```bash
# Add a new todo
python run.py todo add "Fix PDF generation bug" --priority high --due today --category bug

# List todos
python run.py todo list

# Mark as completed
python run.py todo done [todo_id]

# Search todos
python run.py todo search "menu"

# View statistics
python run.py todo stats
```

### Command Line Options

#### Scraping Commands (`python run.py scrape [options] <url>`)
- `base_url` (required): The starting URL to scrape
- `--output, -o`: Output filename (PDF or Markdown)
- `--format, -f`: Output format (pdf, markdown, md) - default: pdf
- `--max-depth, -d`: Maximum crawl depth
- `--max-pages, -p`: Maximum number of pages to scrape
- `--delay`: Delay between requests (seconds)
- `--config, -c`: Configuration file path
- `--verbose, -v`: Enable verbose logging
- `--dry-run`: Show what would be scraped without doing it
- `--preview`: Interactive URL selection with tree view
- `--exclude`: URL patterns to exclude (can use multiple times)
- `--save-approved`: Save approved URLs to file for reuse
- `--load-approved`: Load previously approved URLs from file
- `--include-menus`: Include navigation menus in output (default: exclude)
- `--resume`: Resume from cached session ID
- `--resume-preview`: Resume from cached preview session ID
- `--from-cache`: Generate output from cached session (no scraping)

#### Todo Management Commands (`python run.py todo <command>`)
- `add <description>`: Add a new todo item
- `list`: List todo items with filtering options
- `update <id>`: Update an existing todo
- `delete <id>`: Delete a todo item
- `done <id>`: Mark a todo as completed
- `show <id>`: Show detailed information about a todo
- `note <id> <note>`: Add a note to a todo
- `search <term>`: Search todos by text
- `stats`: Show todo statistics

#### Cache Management Commands (`python run.py cache <command>`)
- `list`: List cached scraping sessions with filtering options
- `clean`: Clean up old cache sessions
- `stats`: Show cache statistics and usage information
- `export <session_id>`: Export cached session data to different formats
- `show <session_id>`: Show detailed information about a cached session
- `delete <session_id>`: Delete a cached session
- `previews`: List cached preview sessions

#### Todo Options
- `--priority, -p`: Set priority (low, medium, high, urgent)
- `--due, -d`: Set due date (today, tomorrow, next week, YYYY-MM-DD)
- `--category, -c`: Set category (bug, feature, documentation, etc.)
- `--status, -s`: Set status (pending, in_progress, completed, cancelled)
- `--completed`: Show completed todos in list

#### Cache Management Options
- `--status`: Filter sessions by status (active, completed, failed)
- `--verbose, -v`: Show detailed session information
- `--older-than`: Remove sessions older than specified time (e.g., 7d, 24h)
- `--keep-completed`: Keep this many recent completed sessions
- `--dry-run`: Show what would be cleaned without doing it
- `--force`: Force deletion without confirmation
- `--format, -f`: Output format for cache export (pdf, markdown, md)
- `--output, -o`: Output filename for cache export

## Configuration

### Configuration File (config.yaml)

The application uses `config.yaml` for public configuration:

```yaml
crawling:
  max_depth: 5
  request_delay: 2.0
  max_pages: 1000

content:
  include_menus: false        # Exclude navigation menus
  include_images: true
  include_metadata: true

pdf:
  output_filename: "scraped_website.pdf"
  page_size: "A4"
  include_toc: true

markdown:
  output_filename: "scraped_website.md"
  multi_file: false          # Single file vs multiple files
  include_toc: true          # Include table of contents

cache:
  enabled: true              # Enable caching system
  directory: cache           # Cache directory location
  compression: true          # Compress cached data
  max_sessions: 100          # Maximum cached sessions
  auto_cleanup: true         # Automatic cleanup of old sessions
  cleanup_settings:
    max_age_days: 30         # Auto-remove sessions older than this
    keep_completed: 10       # Always keep recent completed sessions

# ... see config.yaml for full options
```

### Environment Variables (.env)

Private configuration goes in `.env`:

```bash
# Proxy settings
HTTP_PROXY=http://proxy.company.com:8080

# Custom delays
CRAWL_DELAY_OVERRIDE=3

# Debug mode
DEBUG_MODE=true
```

## Project Structure

```
site2pdf/
├── requirements.md          # Detailed requirements
├── .env                    # Private configuration
├── config.yaml             # Public configuration
├── todos.yaml              # Todo management storage (created automatically)
├── requirements.txt        # Python dependencies
├── run.py                  # Main entry point
├── src/
│   ├── cli.py             # Click CLI interface
│   ├── scraper.py         # Web scraping logic
│   ├── extractor.py       # Content extraction
│   ├── cache_manager.py   # Caching system for scraped content
│   ├── cache_cli.py       # Cache management CLI commands
│   ├── preview_cache.py   # Preview session persistence
│   ├── todo_manager.py    # Todo management logic
│   ├── todo_cli.py        # Todo CLI commands
│   └── utils.py           # Utility functions
├── generators/             # Output format generators (NEW)
│   ├── __init__.py        # Base classes and validation
│   ├── pdf/               # PDF generation package
│   │   └── pdf_generator.py
│   └── markdown/          # Markdown generation package (NEW)
│       └── markdown_generator.py
├── system_tools/           # Reusable system utilities (NEW)
│   └── versioning/        # Version management
├── cache/                 # Cached scraping sessions and preview data
│   ├── sessions/          # Scraped content cache by session ID
│   └── previews/          # Preview session states
├── output/                # Generated files (PDF, Markdown)
├── temp/                  # Temporary files (images)
└── logs/                  # Log files
```

## Examples

### Website Scraping Examples

#### Basic Website Scraping
```bash
# PDF output (default)
python run.py scrape https://docs.python.org

# Markdown output
python run.py scrape https://docs.python.org --format markdown
```

#### Limited Depth Scraping
```bash
python run.py scrape https://example.com --max-depth 2 --max-pages 50 --format md
```

#### Custom Configuration
```bash
# PDF with custom filename
python run.py scrape https://example.com --config custom-config.yaml --output custom-name.pdf

# Markdown with custom filename
python run.py scrape https://example.com --format markdown --output docs.md
```

#### Verbose Mode with Custom Delay
```bash
python run.py scrape https://example.com --verbose --delay 3 --format markdown
```

#### Menu Exclusion Examples
```bash
# Default behavior - exclude menus (works for both PDF and Markdown)
python run.py scrape https://docs.example.com --format markdown

# Include menus for sites where navigation is important
python run.py scrape https://docs.example.com --include-menus --format md
```

#### Markdown-Specific Examples
```bash
# Generate single markdown file (default)
python run.py scrape https://example.com/docs --format markdown

# Configure for multi-file output (modify config.yaml: markdown.multi_file: true)
# Creates directory with README.md index and individual page files
python run.py scrape https://example.com/docs --format markdown

# Markdown with table of contents (default)
python run.py scrape https://example.com/docs --format md --output documentation.md
```

### Todo Management Examples

#### Basic Todo Operations
```bash
# Add todos with different priorities
python run.py todo add "Fix PDF generation crash" --priority urgent --due today --category bug
python run.py todo add "Add dark mode support" --priority medium --category feature
python run.py todo add "Update API documentation" --priority low --due "next week" --category docs

# List and filter todos
python run.py todo list                         # Active todos only
python run.py todo list --completed            # Include completed
python run.py todo list --priority high        # High priority only
python run.py todo list --category bug         # Bug category only

# Work with specific todos
python run.py todo show a1b2c3d4               # Show details
python run.py todo note a1b2c3d4 "Added logging for better debugging"
python run.py todo update a1b2c3d4 --status in_progress
python run.py todo done a1b2c3d4               # Mark completed
```

#### Advanced Todo Management
```bash
# Search across all content
python run.py todo search "PDF generation"     # Find related todos
python run.py todo search "menu"               # Search notes too

# Project tracking
python run.py todo stats                       # View project status
python run.py todo list --status in_progress   # See active work
python run.py todo list --due today            # Today's deadlines
```

## Advanced Features

### 🎮 Interactive Preview Mode
Preview and approve URLs before scraping with a tree-view interface:

```bash
# Interactive preview with approval
python run.py scrape https://example.com/docs/ --preview

# Preview with URL filtering
python run.py scrape https://example.com --preview --exclude "/admin" --exclude "/api"

# Save approved URLs for reuse
python run.py scrape https://example.com --preview --save-approved approved_urls.json
```

**Preview Features:**
- 📊 Content type indicators (📖 Documentation, 📄 Content, 🧭 Navigation)
- 🎯 Path scoping information showing allowed/blocked sections  
- 🌳 Hierarchical tree view of discovered URLs
- ✅ Interactive approval with exclude/include commands
- 💾 Save/load approved URL lists for repeated scraping

### 🎯 Path-Aware Scoping
Automatically stays within relevant sections of websites:

```bash
# Starting from documentation section
python run.py scrape https://example.com/docs/getting-started/

# Will scrape:
# ✅ /docs/api-reference/     (same section)
# ✅ /docs/                   (parent section) 
# ✅ /                        (homepage)

# Will ignore:
# ❌ /blog/                   (different section)
# ❌ /admin/                  (admin area)
# ❌ /xmlrpc.php             (technical file)
```

**Configuration:**
```yaml
path_scoping:
  enabled: true                    # Enable path-based scoping
  allow_parent_levels: 1           # Allow 1 level up from starting path
  allow_homepage: true             # Always allow homepage
  allow_siblings: true             # Allow sibling paths in same section
  allow_navigation: "limited"      # Navigation link policy
```

### 🕵️ Human-Like Behavior
Mimics real user browsing patterns to avoid detection:

```bash
# Enable human-like delays and behavior
python run.py scrape https://example.com --verbose
```

**Behavioral Features:**
- 🎭 **Microsoft Edge simulation** with realistic headers
- ⏱️ **Variable delays**: 2-8 seconds reading + 1-3 seconds decision time
- 📈 **Adaptive timing**: Slower for complex pages, faster for simple ones
- 😴 **Fatigue simulation**: Gradually slower over long sessions
- 🍪 **Session management**: Proper cookies and referrer tracking
- 📊 **Rate limit detection**: Automatically backs off when detected

**Configuration:**
```yaml
human_behavior:
  delays:
    base_reading_time: [2, 8]      # Time to "read" page content
    navigation_decision: [1, 3]    # Time to "decide" next action
    variance_percent: 30           # Random timing variation
  browsing:
    session_break_after: 50        # Break every N pages
    weekend_factor: 1.2            # 20% slower on weekends
```

### 🔍 Smart Content Classification
Automatically identifies and prioritizes different types of content:

- 📖 **Documentation**: `/docs/`, `/help/`, `/guide/`, `/tutorial/`
- 📄 **Content Pages**: `/about/`, `/blog/`, `/features/`, `/examples/`
- 🧭 **Navigation**: Homepage, sitemaps, main navigation
- ❌ **Excluded**: Admin pages, APIs, technical files, login forms

**Quality Assessment:**
- Word count and content depth analysis
- Heading structure evaluation  
- Image and multimedia content detection
- Low-quality page filtering (too sparse or too navigation-heavy)

### 🚫 Smart Menu Exclusion
Intelligently removes navigation menus from PDF output for cleaner documents:

```bash
# Default behavior - menus are excluded
python run.py scrape https://docs.example.com

# Include menus when navigation context is important
python run.py scrape https://docs.example.com --include-menus
```

**Menu Detection Features:**
- 🎯 **Multi-Pattern Detection**: Finds menus by CSS classes (`.menu`, `.nav`, `.sidebar`)
- 🏷️ **Semantic Recognition**: Detects `<nav>` elements and ARIA navigation roles
- 🧠 **Heuristic Analysis**: Identifies menu-like structures (high link-to-text ratios)
- 📍 **Position Awareness**: Handles left, right, top, and bottom navigation layouts
- ⚙️ **Configurable**: Control via `--include-menus` flag or `config.yaml`

**Configuration:**
```yaml
content:
  include_menus: false          # Default: exclude menus for cleaner PDFs
```

### 💾 Advanced Caching System
Comprehensive caching system that prevents data loss and enables efficient workflows:

**Core Features:**
- 🗄️ **Session-Based Storage**: Each scraping run creates a unique cached session
- 📦 **Incremental Saving**: Pages are cached immediately as they're scraped
- 🔄 **Resume Capability**: Continue interrupted scraping from exact point of failure
- 🎯 **Preview Persistence**: Save and restore URL approval decisions across sessions
- ⚡ **Multi-Format Export**: Generate PDF, Markdown from cached data without re-scraping
- 🧹 **Automatic Cleanup**: Configurable cleanup policies for old sessions

**Cache Structure:**
```
cache/
├── sessions/
│   └── a1b2c3d4-5678-90ab-cdef-123456789012/
│       ├── session.json        # Session metadata
│       └── pages/              # Individual cached pages
│           ├── page_001.json
│           └── page_002.json
└── previews/
    └── b2c3d4e5-6789-01bc-def1-234567890123/
        └── preview.json        # URL approval decisions
```

**Usage Examples:**
```bash
# Automatic caching during normal scraping
python run.py scrape https://docs.example.com

# Resume interrupted session
python run.py scrape https://docs.example.com --resume a1b2c3d4

# Generate different formats from cache
python run.py scrape --from-cache a1b2c3d4 --format markdown
python run.py scrape --from-cache a1b2c3d4 --format pdf

# Preview session management
python run.py scrape https://example.com --preview
python run.py scrape https://example.com --resume-preview b2c3d4e5

# Cache management
python run.py cache list                      # View all sessions
python run.py cache stats                     # Cache statistics
python run.py cache clean --older-than 7d     # Cleanup old sessions
```

### 🛡️ Robust PDF Generation
Enhanced error handling and recovery for reliable PDF creation:

**Robustness Features:**
- 🔍 **Data Validation**: Validates all page data before PDF generation
- 🧹 **HTML Sanitization**: Repairs malformed HTML using BeautifulSoup
- 🎯 **Progressive Fallbacks**: Multiple content generation strategies
- 📊 **Detailed Logging**: Comprehensive error reporting and debugging info
- 🔄 **Graceful Recovery**: Continues processing even when individual pages fail

**Error Handling:**
- Corrupted page data → Skip with warning
- Malformed HTML → Sanitize and repair automatically  
- Missing content → Generate from text + metadata
- WeasyPrint errors → Enhanced error context and recovery

## Output

The application generates:

- **PDF Document**: Comprehensive PDF with all scraped content (--format pdf)
- **Markdown Files**: Clean, structured markdown documents (--format markdown)
  - Single file: All content in one markdown document with TOC
  - Multi-file: Directory with README.md index and individual page files
- **Cache Files**: Scraped content and preview sessions stored in `cache/`
  - Session cache: Incremental page storage with metadata for resume capability
  - Preview cache: URL approval decisions for session persistence
- **Log Files**: Detailed crawling and processing logs in `logs/`
- **Temporary Files**: Downloaded images stored in `temp/` during processing
- **Todo Database**: YAML-based todo storage in `todos.yaml` (when using todo features)

## 📝 Todo Management System

The integrated todo management system helps you track development tasks, bugs, and project progress using a structured YAML format.

### Todo Features

**🎨 Visual Interface:**
- Beautiful CLI with icons and colors
- Priority indicators: 🚨 Urgent, 🔴 High, 🟡 Medium, 🟢 Low
- Status tracking: ⏳ Pending, 🔄 In Progress, ✅ Completed, ❌ Cancelled
- Due date alerts: 🔥 Overdue, 📅 Due today/tomorrow

**📊 Organization:**
- Categories (bugs, features, documentation, etc.)
- Priority levels with visual indicators
- Due date management with smart parsing
- Timestamped notes for each todo
- Full-text search across all content

**💾 Data Storage:**
```yaml
# todos.yaml structure
metadata:
  created: '2025-08-23T22:23:33.477485'
  last_modified: '2025-08-23T22:25:03.648130'
  version: '1.0'
todos:
  a1b2c3d4:
    description: Fix PDF generation error
    status: completed
    priority: high
    category: bug
    created: '2025-08-23T22:23:33.477531'
    due_date: '2025-08-23'
    completed: '2025-08-23T22:24:37.225425'
    notes:
    - text: Added debug logging to identify root cause
      timestamp: '2025-08-23T22:25:03.648101'
```

### Todo Workflow Examples

**📋 Project Management:**
```bash
# Sprint planning
python run.py todo add "Implement user authentication" --priority high --due "2024-09-01" --category feature
python run.py todo add "Fix mobile responsive layout" --priority medium --category bug
python run.py todo add "Write API documentation" --priority low --due "next week" --category docs

# Daily standup
python run.py todo list --status in_progress    # What you're working on
python run.py todo list --due today            # Today's deadlines
python run.py todo stats                       # Overall progress

### Cache Management Examples

#### Basic Cache Operations
```bash
# List all cached sessions
python run.py cache list

# View detailed cache statistics
python run.py cache stats

# Clean up old sessions (dry run first)
python run.py cache clean --older-than 7d --dry-run
python run.py cache clean --older-than 7d

# Show specific session details
python run.py cache show a1b2c3d4

# Export cached data to different formats
python run.py cache export a1b2c3d4 --format markdown --output cached-docs.md
python run.py cache export a1b2c3d4 --format pdf
```

#### Resume and Cache Workflow
```bash
# Start scraping (creates cache automatically)
python run.py scrape https://docs.example.com --max-pages 100

# If interrupted, resume from cache
python run.py scrape https://docs.example.com --resume a1b2c3d4

# Generate different formats from cache without re-scraping
python run.py scrape https://docs.example.com --from-cache a1b2c3d4 --format markdown
python run.py scrape https://docs.example.com --from-cache a1b2c3d4 --format pdf

# Preview with session persistence
python run.py scrape https://docs.example.com --preview
# ... make selections and exit
python run.py scrape https://docs.example.com --resume-preview b2c3d4e5
```

**🐛 Bug Tracking:**
```bash
# Report and track bugs
python run.py todo add "PDF generation crashes on large images" --priority urgent --category bug
python run.py todo note a1b2c3d4 "Reproduced with 10MB+ images, investigating memory usage"
python run.py todo update a1b2c3d4 --status in_progress
python run.py todo done a1b2c3d4               # Mark as fixed
```

**📈 Progress Monitoring:**
```bash
# View project status
python run.py todo stats
# Output:
# 📊 Todo Statistics
# ══════════════════════════════
# Total todos:     15
# ⏳ Pending:       8
# 🔄 In Progress:   3
# ✅ Completed:     4
# ❌ Cancelled:     0
# 🔥 Overdue:       1
```

## Output Format Features

### PDF Features
- ✅ Table of contents with page links
- ✅ Preserved content structure and formatting
- ✅ Embedded images with captions
- ✅ Page numbers and metadata
- ✅ Professional styling and layout
- ✅ Link references for each page

### Markdown Features
- ✅ Clean HTML-to-Markdown conversion
- ✅ Table of contents with anchor links
- ✅ Preserved content structure and formatting
- ✅ Links and images properly converted
- ✅ Single-file or multi-file output modes
- ✅ GitHub-compatible markdown syntax
- ✅ Configurable via YAML settings

## Compliance & Ethics

- 🤖 Respects robots.txt files
- ⏱️ Implements configurable crawl delays
- 🚫 Filters out admin and login pages
- 📊 Reasonable default limits
- 🔒 Handles HTTP errors gracefully

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure output directories are writable
2. **Network Timeouts**: Increase timeout in config.yaml
3. **Memory Issues**: Reduce max_pages for large sites
4. **PDF Generation Fails**: Check WeasyPrint dependencies

### Debugging

Enable verbose mode and check logs:
```bash
python run.py https://example.com --verbose
cat logs/scraper.log
```

## Dependencies

- **requests**: HTTP requests and web scraping
- **beautifulsoup4**: HTML parsing and sanitization
- **click**: Command-line interface and todo management
- **weasyprint**: PDF generation
- **python-dotenv**: Environment variables
- **PyYAML**: Configuration files and todo storage
- **tqdm**: Progress bars
- **Pillow**: Image processing
- **uuid**: Unique todo ID generation

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the logs in `logs/scraper.log`
- Review configuration in `config.yaml`
- Refer to `requirements.md` for detailed specifications