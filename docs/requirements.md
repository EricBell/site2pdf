# Website Scraping to PDF Application - Requirements

> **📜 Historical Document**: This file represents the original project requirements and specifications from the initial planning phase. For current features, usage instructions, and comprehensive documentation, please refer to [README.md](../README.md) in the root directory. This document is maintained for reference, development planning, and tracking how the project has evolved beyond its original scope.

## Project Overview
Create a Python CLI application that scrapes a website and all its subpages, then generates a single PDF document containing all the content with embedded images. The application also includes comprehensive todo management for project organization and tracking.

## Functional Requirements

### Core Functionality
- **Web Scraping**: Crawl starting from a base URL and discover all internal links/subpages
- **Content Extraction**: Extract text, headings, structure, and images from each page
- **PDF Generation**: Create a single PDF document with all scraped content
- **Image Handling**: Download and embed images into the PDF output
- **CLI Interface**: Accept base URL as command-line argument using Click

### User Interface
- Command-line interface with base URL as primary argument
- Progress reporting during scraping and PDF generation
- Error reporting and logging
- Configurable options (depth, output filename, etc.)
- **Preview Mode**: Interactive URL discovery and approval before scraping
- **URL Filtering**: Exclude specific URL patterns or paths
- **Approval Persistence**: Save and reuse approved URL lists

### Content Processing
- Preserve content structure and hierarchy
- Maintain readable formatting in PDF output
- Handle various HTML elements (headings, paragraphs, lists, etc.)
- Download and store images locally for PDF embedding
- Respect website structure and navigation

### Crawling Behavior
- Discover and follow only internal links (same domain)
- Avoid infinite loops through duplicate URL detection
- Track visited pages to prevent re-scraping
- Implement rate limiting and respectful crawling practices
- Check and respect robots.txt when possible

## Technical Requirements

### Dependencies
- **requests**: HTTP requests and web scraping
- **beautifulsoup4**: HTML parsing and content extraction
- **click**: Command-line interface framework
- **weasyprint** or **reportlab**: PDF generation
- **python-dotenv**: Environment variable management
- **pyyaml**: Configuration file handling

### Project Structure
```

site2pdf/
├── requirements.md          # This file  
├── .env                    # Private configuration
├── config.yaml             # Public configuration
├── todos.yaml              # Todo management storage (created automatically)
├── .gitignore             # Version control exclusions
├── package.json           # Project metadata
├── requirements.txt       # Python dependencies
├── run.py                 # Main entry point
├── src/
│   ├── __init__.py
│   ├── cli.py            # Click CLI interface
│   ├── scraper.py        # Web scraping logic
│   ├── extractor.py      # Content extraction with menu exclusion
│   ├── pdf_generator.py  # Robust PDF creation
│   ├── preview.py        # URL preview and approval system
│   ├── todo_manager.py   # Todo management logic (NEW)
│   ├── todo_cli.py       # Todo CLI commands (NEW)
│   └── utils.py          # Utility functions
├── output/               # Generated PDFs
├── temp/                 # Temporary files (images)
└── logs/                 # Log files
```

### Configuration Management
- **Private (.env)**: API keys, proxy settings, authentication tokens
- **Public (config.yaml)**: Crawl settings, timeouts, user agents, output preferences

### Error Handling
- Graceful handling of network errors
- Robust error recovery during crawling
- Comprehensive logging system
- Progress tracking and reporting

### Version Control
- Git repository initialization
- Proper .gitignore for Python projects
- Exclude sensitive files (.env, output files)
- Include package.json for project versioning

## Input/Output Specifications

### Input
- **Base URL**: Starting point for website crawling
- **Configuration**: Optional settings via config files or CLI flags
- **URL Patterns**: Optional exclude patterns for filtering unwanted content
- **Approved URLs**: Optional pre-approved URL lists for targeted scraping

### Output
- **PDF File**: Single document containing all scraped content
- **Log Files**: Detailed crawling and processing logs
- **Asset Directory**: Downloaded images and resources
- **Approved URL Lists**: JSON files containing approved URLs for reuse

## Performance Requirements
- Handle websites with hundreds of pages
- Implement reasonable rate limiting (1-2 seconds between requests)
- Memory-efficient processing of large content
- Progress reporting for long-running operations

## Compliance and Ethics
- Respect robots.txt files
- Implement crawl delays between requests
- Use appropriate User-Agent strings
- Avoid overwhelming target servers
- Handle HTTP status codes properly (429, 403, etc.)

## Implemented Advanced Features

### Path-Aware URL Scoping
- **Intelligent path boundaries**: Automatically limits crawling to relevant sections
- **Configurable scope rules**: Parent levels, siblings, navigation policies
- **Homepage allowance**: Optional inclusion of root page even outside scope
- **Smart filtering**: Blocks admin pages, APIs, technical files automatically

### Human-Like Browsing Simulation  
- **Microsoft Edge emulation**: Realistic browser headers and user agents
- **Variable timing**: Human-like reading (2-8s) and decision delays (1-3s)
- **Behavioral patterns**: Fatigue simulation, session breaks, adaptive delays
- **Anti-detection**: Rate limit monitoring, cookie handling, referrer tracking

### Content Classification & Quality Assessment
- **Automatic categorization**: Documentation, content, navigation, technical
- **Quality scoring**: Word count, structure, heading analysis
- **Priority-based crawling**: Focus on high-value documentation content
- **Low-quality filtering**: Skip sparse or navigation-heavy pages

### Interactive Preview System
- **Tree-view interface**: Hierarchical URL display with content types
- **Approval workflow**: Interactive exclude/include commands
- **URL list persistence**: Save and reuse approved URL sets
- **Scope visualization**: Shows path boundaries and filtering rules

### Smart Menu Exclusion (NEW)
- **Configurable menu removal**: Default exclusion of navigation menus from PDFs
- **Multi-pattern detection**: CSS selectors, semantic elements, heuristic analysis
- **Position-aware handling**: Supports left, right, top, bottom navigation layouts
- **Override capability**: `--include-menus` flag to preserve navigation when needed

### Robust PDF Generation (NEW)  
- **Data validation**: Comprehensive validation of scraped content before PDF creation
- **HTML sanitization**: Automatic repair of malformed HTML using BeautifulSoup
- **Progressive fallbacks**: Multiple content generation strategies for reliability
- **Enhanced error handling**: Graceful recovery from WeasyPrint and content issues

### Integrated Todo Management System (NEW)
- **YAML-based storage**: Structured todo database in `todos.yaml`
- **Rich CLI interface**: Beautiful icons, colors, and visual indicators
- **Priority system**: Low, Medium, High, Urgent with visual feedback
- **Status tracking**: Pending, In Progress, Completed, Cancelled workflows
- **Category organization**: Flexible categorization (bugs, features, documentation)
- **Due date management**: Smart date parsing and overdue alerts
- **Note system**: Timestamped notes for detailed task tracking
- **Search capabilities**: Full-text search across descriptions, categories, notes
- **Statistics dashboard**: Progress tracking and project insights

## Future Enhancements
- Support for JavaScript-rendered content
- Multiple output formats (HTML, EPUB, etc.)
- Parallel crawling capabilities
- Custom CSS styling for PDF output
- AI-powered content relevance scoring

## Usage Examples

### Website Scraping Usage  
```bash
# Simple scraping
python run.py scrape https://example.com

# With custom output filename  
python run.py scrape https://example.com --output my-site.pdf

# Exclude menus from PDF (default behavior)
python run.py scrape https://example.com  

# Include menus in PDF
python run.py scrape https://example.com --include-menus

# Dry run to see what would be scraped
python run.py scrape https://example.com --dry-run
```

### Todo Management Usage
```bash  
# Add todos with priorities and due dates
python run.py todo add "Fix PDF generation crash" --priority urgent --due today --category bug
python run.py todo add "Implement user auth" --priority high --due "2024-09-01" --category feature

# List and manage todos
python run.py todo list                    # Show active todos
python run.py todo list --completed       # Include completed  
python run.py todo list --priority high   # Filter by priority
python run.py todo done [todo_id]         # Mark completed

# Advanced todo operations
python run.py todo search "PDF"           # Search todos
python run.py todo note [id] "Added debug logging for investigation"
python run.py todo stats                  # Project statistics  
```

### Preview and Approval Mode
```bash
# Interactive preview with tree structure and approval
python run.py scrape https://example.com --preview

# Preview with pre-filtering patterns
python run.py scrape https://example.com --preview --exclude "/admin" --exclude "/api"

# Save approved URLs for future use
python run.py scrape https://example.com --preview --save-approved approved_urls.json
```

### URL Filtering  
```bash
# Exclude specific patterns
python run.py scrape https://example.com --exclude "/login" --exclude "/search"

# Exclude using regex patterns
python run.py scrape https://example.com --exclude ".*\.(pdf|zip|exe)$"

# Multiple exclude patterns
python run.py scrape https://example.com --exclude "/admin" --exclude "/api" --exclude "/private"
```

### Reusing Approved Lists
```bash
# Load previously approved URLs
python run.py scrape https://example.com --load-approved approved_urls.json

# Combine with additional filtering
python run.py scrape https://example.com --load-approved approved_urls.json --exclude "/temp"
```

### Advanced Options
```bash
# Full configuration with all options
python run.py scrape https://example.com \
  --preview \
  --max-depth 3 \
  --max-pages 100 \
  --delay 2.0 \
  --include-menus \
  --exclude "/admin" \
  --exclude "/search" \
  --save-approved my-site-approved.json \
  --output my-site.pdf \
  --verbose

# Configuration file usage
python run.py scrape https://example.com --config custom-config.yaml --preview
```

### Interactive Preview Workflow
1. **Discovery**: URLs are discovered and organized in a tree structure
2. **Preview**: Navigate through the hierarchical display of URLs
3. **Exclusion**: Use interactive commands to exclude unwanted paths:
   - `e <number>` - Exclude a path and all subpaths
   - `i <number>` - Include previously excluded path
   - `r` - Refresh the display
   - `s` - Show currently excluded URLs
   - `c` - Continue to final approval
   - `q` - Quit without scraping
4. **Approval**: Review final summary and confirm scraping
5. **Scraping**: Only approved URLs are scraped and processed