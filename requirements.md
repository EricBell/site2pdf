# Website Scraping to PDF Application - Requirements

## Project Overview
Create a Python CLI application that scrapes a website and all its subpages, then generates a single PDF document containing all the content with embedded images.

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
├── .gitignore             # Version control exclusions
├── package.json           # Project metadata
├── requirements.txt       # Python dependencies
├── src/
│   ├── __init__.py
│   ├── cli.py            # Click CLI interface
│   ├── scraper.py        # Web scraping logic
│   ├── extractor.py      # Content extraction
│   ├── pdf_generator.py  # PDF creation
│   ├── preview.py        # URL preview and approval system
│   └── utils.py          # Utility functions
└── output/               # Generated PDFs and assets
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

## Future Enhancements
- Support for JavaScript-rendered content
- Multiple output formats (HTML, EPUB, etc.)
- Advanced filtering and content selection
- Parallel crawling capabilities
- Custom CSS styling for PDF output

## Usage Examples

### Basic Usage
```bash
# Simple scraping
python -m src.cli https://example.com

# With custom output filename
python -m src.cli https://example.com --output my-site.pdf

# Dry run to see what would be scraped
python -m src.cli https://example.com --dry-run
```

### Preview and Approval Mode
```bash
# Interactive preview with tree structure and approval
python -m src.cli https://example.com --preview

# Preview with pre-filtering patterns
python -m src.cli https://example.com --preview --exclude "/admin" --exclude "/api"

# Save approved URLs for future use
python -m src.cli https://example.com --preview --save-approved approved_urls.json
```

### URL Filtering
```bash
# Exclude specific patterns
python -m src.cli https://example.com --exclude "/login" --exclude "/search"

# Exclude using regex patterns
python -m src.cli https://example.com --exclude ".*\.(pdf|zip|exe)$"

# Multiple exclude patterns
python -m src.cli https://example.com --exclude "/admin" --exclude "/api" --exclude "/private"
```

### Reusing Approved Lists
```bash
# Load previously approved URLs
python -m src.cli https://example.com --load-approved approved_urls.json

# Combine with additional filtering
python -m src.cli https://example.com --load-approved approved_urls.json --exclude "/temp"
```

### Advanced Options
```bash
# Full configuration with all options
python -m src.cli https://example.com \
  --preview \
  --max-depth 3 \
  --max-pages 100 \
  --delay 2.0 \
  --exclude "/admin" \
  --exclude "/search" \
  --save-approved my-site-approved.json \
  --output my-site.pdf \
  --verbose

# Configuration file usage
python -m src.cli https://example.com --config custom-config.yaml --preview
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