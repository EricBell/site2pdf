# Content Generators Package

A collection of extensible output format generators for scraped web content. Each generator converts scraped data into different output formats while maintaining consistent APIs and robust error handling.

## Available Generators

### 📄 PDF Generator (`generators.pdf`)
**Status: ✅ Complete**

High-quality PDF generation using WeasyPrint:
- HTML/CSS to PDF conversion
- Image embedding and optimization  
- Table of contents generation
- Robust error handling and validation
- Custom styling support

```python
from generators.pdf import PDFGenerator

generator = PDFGenerator(config)
success = generator.generate(scraped_data, "output.pdf", base_url="https://example.com")
```

**Dependencies:**
- `weasyprint` - HTML/CSS to PDF conversion
- `beautifulsoup4` - HTML parsing and sanitization

### 🌐 HTML Generator (`generators.html`)
**Status: 🚧 Planned**

Static HTML site generation:
- Multi-page HTML output with navigation
- Custom CSS themes and styling
- Search functionality
- Responsive design templates

### 📖 EPUB Generator (`generators.epub`) 
**Status: 🚧 Planned**

EPUB book generation:
- EPUB3 format support
- Chapter organization
- Table of contents generation
- Metadata embedding
- Custom cover generation

### 📝 Markdown Generator (`generators.markdown`)
**Status: ✅ Complete**

Clean, structured markdown generation from scraped content:
- HTML-to-Markdown conversion with proper formatting
- Single-file or multi-file output modes
- Table of contents with anchor links
- GitHub-compatible markdown syntax
- Configurable content processing

```python
from generators.markdown import MarkdownGenerator

generator = MarkdownGenerator(config)
output_path = generator.generate(scraped_data, base_url="https://example.com", output="docs.md")
```

**Dependencies:**
- None (uses built-in HTML parsing and text conversion)

## Architecture

### Base Generator Interface

All generators inherit from `BaseGenerator` providing consistent APIs:

```python
from generators import BaseGenerator

class CustomGenerator(BaseGenerator):
    def generate(self, scraped_data: List[Dict], output_path: str, **kwargs) -> bool:
        # Implementation
        return True
    
    def validate_config(self) -> bool:
        # Validate configuration
        return True
```

### Content Validation

Built-in content validation ensures data integrity:

```python
from generators import ContentValidator

is_valid, errors = ContentValidator.validate_scraped_data(scraped_data)
if not is_valid:
    print(f"Validation errors: {errors}")
```

## Usage Examples

### Basic Usage

#### PDF Generation
```python
from generators.pdf import PDFGenerator

# Initialize generator with configuration
generator = PDFGenerator(config)

# Validate configuration
if not generator.validate_config():
    print("Invalid configuration")
    exit(1)

# Generate PDF
success = generator.generate(
    scraped_data=scraped_pages,
    output_path="documentation.pdf", 
    base_url="https://example.com"
)

if success:
    print("PDF generated successfully!")
```

#### Markdown Generation
```python
from generators.markdown import MarkdownGenerator

# Initialize generator
generator = MarkdownGenerator(config)

# Generate single markdown file
output_path = generator.generate(
    scraped_data=scraped_pages,
    base_url="https://example.com",
    output="documentation.md"
)

print(f"Markdown generated: {output_path}")
```

### Advanced Configuration

#### PDF Configuration
```python
# Custom PDF styling
pdf_config = {
    'pdf': {
        'format': 'A4',
        'orientation': 'portrait',
        'include_toc': True,
        'include_cover': True
    },
    'content': {
        'min_content_length': 100,
        'include_images': True
    },
    'directories': {
        'output_dir': './output'
    }
}

generator = PDFGenerator(pdf_config)
```

#### Markdown Configuration
```python
# Custom markdown settings
markdown_config = {
    'markdown': {
        'output_filename': 'docs.md',
        'multi_file': False,    # Single file vs directory with multiple files
        'include_toc': True     # Include table of contents
    },
    'content': {
        'min_content_length': 50,
        'include_images': True,
        'include_menus': False
    },
    'directories': {
        'output_dir': './output'
    }
}

generator = MarkdownGenerator(markdown_config)

# Multi-file output creates directory with README.md and individual page files
markdown_config['markdown']['multi_file'] = True
output_dir = generator.generate(scraped_data, base_url)
```

### Error Handling
```python
from generators import ContentValidator

# Validate data before generation
is_valid, errors = ContentValidator.validate_scraped_data(scraped_data)
if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")
    exit(1)

# Generate with error handling
try:
    success = generator.generate(scraped_data, output_path)
    if not success:
        print("Generation failed - check logs for details")
except Exception as e:
    print(f"Generation error: {e}")
```

## Extending Generators

### Creating New Generators

1. **Inherit from BaseGenerator**:
```python
from generators import BaseGenerator

class CustomGenerator(BaseGenerator):
    def __init__(self, config):
        super().__init__(config)
        # Custom initialization
    
    def generate(self, scraped_data, output_path, **kwargs):
        # Implementation
        return True
    
    def validate_config(self):
        # Configuration validation
        return True
```

2. **Create subpackage structure**:
```
generators/
└── custom/
    ├── __init__.py
    ├── custom_generator.py
    └── README.md
```

3. **Update main package exports**:
```python
# In generators/__init__.py
from .custom import CustomGenerator
__all__.append('CustomGenerator')
```

### Generator Guidelines

- **Inherit from BaseGenerator** for consistent interface
- **Validate input data** using ContentValidator
- **Handle errors gracefully** with informative logging
- **Support configuration** through config dictionary
- **Document dependencies** clearly
- **Provide usage examples** in README

## Configuration Schema

Generators expect configuration dictionaries with these sections:

```python
config = {
    'pdf': {           # PDF-specific settings
        'format': 'A4',
        'orientation': 'portrait',
        'include_toc': True
    },
    'markdown': {      # Markdown-specific settings  
        'output_filename': 'scraped_website.md',
        'multi_file': False,
        'include_toc': True
    },
    'content': {       # Content processing settings
        'min_content_length': 100,
        'include_images': True,
        'include_menus': False
    },
    'directories': {   # Output settings
        'output_dir': './output',
        'temp_dir': './temp'
    }
}
```

## Dependencies

### PDF Generator
- `weasyprint >= 52.0` - HTML/CSS to PDF conversion
- `beautifulsoup4 >= 4.9.0` - HTML parsing and sanitization

### Markdown Generator  
- None (uses built-in Python libraries for HTML parsing and text conversion)

### Future Generators
Dependencies will be documented in each subpackage's README.

## Installation

### Current Project
```python
from generators.pdf import PDFGenerator
from generators.markdown import MarkdownGenerator
```

### Copy to Other Projects
1. Copy entire `generators/` directory
2. Install required dependencies
3. Update import paths if needed
4. Customize configuration as needed

## Testing

Each generator should include comprehensive tests:

```python
# Test basic functionality
def test_pdf_generation():
    generator = PDFGenerator(test_config)
    success = generator.generate(test_data, "test.pdf")
    assert success == True

# Test error handling  
def test_invalid_data():
    generator = PDFGenerator(test_config)
    success = generator.generate([], "test.pdf")
    assert success == False
```

## Contributing

When adding new generators:

1. Follow the BaseGenerator interface
2. Add comprehensive documentation
3. Include usage examples
4. Document all dependencies
5. Add appropriate tests
6. Update main package exports

## License

Each generator maintains its own license. Check individual README files for details.