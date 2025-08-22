# site2pdf 📄

A powerful Python CLI application that intelligently scrapes websites and generates comprehensive PDF documents with human-like behavior.

## Features

- 🌐 **Complete Website Scraping**: Crawls all internal links starting from a base URL
- 📄 **PDF Generation**: Creates a single, well-formatted PDF with all content
- 🖼️ **Image Handling**: Downloads and embeds images into the PDF
- ⚙️ **Configurable**: Extensive configuration options via YAML and environment variables
- 🤖 **Respectful Crawling**: Respects robots.txt, implements rate limiting
- 📊 **Progress Tracking**: Real-time progress reporting and comprehensive logging
- 🎯 **Content Filtering**: Smart filtering to avoid unwanted content

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