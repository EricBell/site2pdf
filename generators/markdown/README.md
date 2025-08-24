# Markdown Generator

Clean, structured markdown generation from scraped website content. Converts HTML to properly formatted GitHub-compatible markdown with support for both single-file and multi-file output modes.

## Features

- ✅ **HTML-to-Markdown Conversion**: Intelligent conversion of HTML elements to markdown syntax
- ✅ **Single & Multi-File Modes**: Generate one markdown file or a directory with multiple files
- ✅ **Table of Contents**: Automatic TOC generation with anchor links
- ✅ **Content Preservation**: Maintains structure, links, and formatting
- ✅ **GitHub Compatible**: Produces standard markdown that works everywhere
- ✅ **Zero Dependencies**: Uses only built-in Python libraries

## Installation

No additional dependencies required - uses built-in Python libraries.

```python
from generators.markdown import MarkdownGenerator
```

## Basic Usage

### Single File Output

```python
from generators.markdown import MarkdownGenerator

# Configure generator
config = {
    'markdown': {
        'output_filename': 'documentation.md',
        'multi_file': False,
        'include_toc': True
    },
    'directories': {
        'output_dir': './output'
    }
}

# Initialize and generate
generator = MarkdownGenerator(config)
output_path = generator.generate(
    scraped_data=scraped_pages,
    base_url="https://example.com",
    output="my-docs.md"
)

print(f"Markdown file generated: {output_path}")
```

**Output Structure (Single File):**
```markdown
# Website Content: example.com

**Source:** https://example.com
**Generated:** 2025-08-24 15:23:13
**Total Pages:** 3

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [API Reference](#api-reference)  
3. [Examples](#examples)

---

## 1. Getting Started
**URL:** https://example.com/docs/getting-started

# Getting Started

Welcome to our documentation...

---

## 2. API Reference
**URL:** https://example.com/docs/api

# API Reference

Our API provides the following endpoints...
```

### Multi-File Output

```python
# Configure for multi-file output
config = {
    'markdown': {
        'multi_file': True,
        'include_toc': True
    },
    'directories': {
        'output_dir': './output'
    }
}

generator = MarkdownGenerator(config)
output_dir = generator.generate(scraped_data, base_url="https://example.com")

print(f"Multi-file markdown generated in: {output_dir}")
```

**Output Structure (Multi-File):**
```
output/
└── example_com_20250824_152458/
    ├── README.md           # Index with links to all pages
    ├── Getting_Started.md  # Individual page files
    ├── API_Reference.md    
    └── Examples.md
```

**README.md (Index File):**
```markdown
# example.com - Website Content

**Source:** https://example.com
**Generated:** 2025-08-24 15:24:58
**Total Pages:** 3

## Pages

1. [Getting Started](Getting_Started.md) - https://example.com/docs/getting-started
2. [API Reference](API_Reference.md) - https://example.com/docs/api  
3. [Examples](Examples.md) - https://example.com/docs/examples
```

## Configuration Options

### Markdown-Specific Settings

```yaml
markdown:
  output_filename: "scraped_website.md"  # Default filename for single-file mode
  multi_file: false                      # true = directory with multiple files
  include_toc: true                      # Include table of contents
```

### Content Processing

```yaml
content:
  include_images: true      # Convert <img> tags to markdown images
  include_menus: false     # Exclude navigation menus (recommended)
  min_content_length: 50   # Skip pages with very little content
```

### Output Directory

```yaml
directories:
  output_dir: "./output"   # Where to save generated files
```

## HTML-to-Markdown Conversion

The generator intelligently converts HTML elements to markdown:

| HTML Element | Markdown Output | Example |
|-------------|-----------------|---------|
| `<h1>` - `<h6>` | `#` - `######` | `# Title` |
| `<strong>`, `<b>` | `**text**` | `**bold text**` |
| `<em>`, `<i>` | `*text*` | `*italic text*` |
| `<a href="url">` | `[text](url)` | `[Link](https://example.com)` |
| `<img src="url" alt="alt">` | `![alt](url)` | `![Image](image.jpg)` |
| `<ul><li>` | `- item` | `- List item` |
| `<code>` | `` `code` `` | `` `inline code` `` |
| `<pre><code>` | ` ```code``` ` | Code blocks |
| `<p>` | Paragraphs | Proper spacing |

## Advanced Usage

### Custom Output Filename

```python
# Override default filename
output_path = generator.generate(
    scraped_data,
    base_url="https://example.com", 
    output="custom-name.md"
)
```

### Error Handling

```python
try:
    output_path = generator.generate(scraped_data, base_url)
    print(f"Success: {output_path}")
except ValueError as e:
    print(f"Invalid data: {e}")
except Exception as e:
    print(f"Generation failed: {e}")
```

### Validation

```python
# Validate configuration before use
if not generator.validate_config():
    print("Invalid configuration - check markdown and directories sections")
    exit(1)

# The generator automatically validates scraped data format
```

## Output Examples

### Headers and Text
```markdown
# Main Title
## Subtitle
### Section

This is a paragraph with **bold text** and *italic text*.

Here's a [link to example](https://example.com) and some `inline code`.
```

### Lists and Code
```markdown
- Item 1
- Item 2  
- Item 3

```python
def example_function():
    return "Hello, World!"
```
```

### Images and Links
```markdown
![Screenshot](screenshot.png)

[Read more about this topic](https://example.com/docs)
```

## CLI Integration

The markdown generator is fully integrated with the site2pdf CLI:

```bash
# Generate markdown instead of PDF
python run.py scrape https://example.com --format markdown

# Custom filename
python run.py scrape https://example.com --format md --output docs.md

# Works with all scraping options
python run.py scrape https://example.com --format markdown --max-depth 3 --preview
```

## Comparison with PDF Generator

| Feature | Markdown Generator | PDF Generator |
|---------|-------------------|---------------|
| **File Size** | Very small | Larger |
| **Editability** | Fully editable | Read-only |
| **Portability** | Universal | Needs PDF viewer |
| **Version Control** | Git-friendly | Binary format |
| **Searchability** | Full text search | Limited |
| **Customization** | Easy to modify | Requires regeneration |
| **Dependencies** | None | WeasyPrint |

## Best Practices

### When to Use Single File Mode
- Documentation sites with sequential content
- Creating a single reference document  
- When you want everything searchable in one file
- For printing or PDF conversion later

### When to Use Multi-File Mode
- Large websites with many distinct sections
- When you want to maintain original site structure
- For importing into documentation systems (GitBook, etc.)
- When individual pages need separate processing

### Content Quality
- Use `--include-menus` sparingly - usually creates cluttered markdown
- Set appropriate `min_content_length` to filter out sparse pages
- Preview mode helps select only relevant content

## Troubleshooting

### Common Issues

1. **Empty Output Files**
   - Check if scraped data contains valid content
   - Verify `min_content_length` isn't too restrictive
   - Enable verbose mode to see processing details

2. **Malformed Markdown**
   - Usually caused by complex HTML structures
   - The generator handles most cases gracefully
   - Check source HTML for unusual formatting

3. **Missing Images**
   - Image links are preserved but images aren't downloaded
   - Use `include_images: true` to ensure image tags are converted
   - Consider the PDF generator if you need embedded images

### Debug Mode

```bash
# Enable verbose logging to troubleshoot issues
python run.py scrape https://example.com --format markdown --verbose
```

## License

MIT License - Part of the site2pdf project.