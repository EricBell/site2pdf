# site2pdf 📄

A powerful Python CLI application that intelligently scrapes websites and generates comprehensive PDF documents with human-like behavior.

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

### 📄 **Advanced PDF Generation**
- 📖 **Documentation Focus**: Prioritizes user-facing content over technical files
- 🖼️ **Image Embedding**: Downloads and includes images with proper formatting
- 📚 **Table of Contents**: Automatic TOC generation with page links
- 🎨 **Professional Layout**: Clean, readable formatting with proper structure

### 🔧 **Powerful Configuration**
- 🎮 **Interactive Preview**: Tree-view URL selection with approval system
- 💾 **URL List Persistence**: Save and reuse approved URL lists
- ⚙️ **Extensive Options**: Fine-tune crawling, delays, content filtering, and output

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

```bash
# Scrape a website and generate PDF
python run.py https://example.com

# With custom options
python run.py https://example.com --output my-site.pdf --max-depth 3 --verbose

# Dry run to see what would be scraped
python run.py https://example.com --dry-run
```

### Command Line Options

- `base_url` (required): The starting URL to scrape
- `--output, -o`: Output PDF filename
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

## Configuration

### Configuration File (config.yaml)

The application uses `config.yaml` for public configuration:

```yaml
crawling:
  max_depth: 5
  request_delay: 2.0
  max_pages: 1000

pdf:
  output_filename: "scraped_website.pdf"
  page_size: "A4"
  include_toc: true

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
├── requirements.txt        # Python dependencies
├── run.py                  # Main entry point
├── src/
│   ├── cli.py             # Click CLI interface
│   ├── scraper.py         # Web scraping logic
│   ├── extractor.py       # Content extraction
│   ├── pdf_generator.py   # PDF creation
│   └── utils.py           # Utility functions
├── output/                # Generated PDFs
├── temp/                  # Temporary files (images)
└── logs/                  # Log files
```

## Examples

### Basic Website Scraping
```bash
python run.py https://docs.python.org
```

### Limited Depth Scraping
```bash
python run.py https://example.com --max-depth 2 --max-pages 50
```

### Custom Configuration
```bash
python run.py https://example.com --config custom-config.yaml --output custom-name.pdf
```

### Verbose Mode with Custom Delay
```bash
python run.py https://example.com --verbose --delay 3
```

## Advanced Features

### 🎮 Interactive Preview Mode
Preview and approve URLs before scraping with a tree-view interface:

```bash
# Interactive preview with approval
python run.py https://example.com/docs/ --preview

# Preview with URL filtering
python run.py https://example.com --preview --exclude "/admin" --exclude "/api"

# Save approved URLs for reuse
python run.py https://example.com --preview --save-approved approved_urls.json
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
python run.py https://example.com/docs/getting-started/

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
python run.py https://example.com --verbose
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

## Output

The application generates:

- **PDF Document**: Comprehensive PDF with all scraped content
- **Log Files**: Detailed crawling and processing logs in `logs/`
- **Temporary Files**: Downloaded images stored in `temp/` during processing

## PDF Features

- ✅ Table of contents with page links
- ✅ Preserved content structure and formatting
- ✅ Embedded images with captions
- ✅ Page numbers and metadata
- ✅ Professional styling and layout
- ✅ Link references for each page

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
- **beautifulsoup4**: HTML parsing
- **click**: Command-line interface
- **weasyprint**: PDF generation
- **python-dotenv**: Environment variables
- **PyYAML**: Configuration files
- **tqdm**: Progress bars
- **Pillow**: Image processing

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