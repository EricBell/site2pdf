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

scrap-bloodhound/
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

### Output
- **PDF File**: Single document containing all scraped content
- **Log Files**: Detailed crawling and processing logs
- **Asset Directory**: Downloaded images and resources

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