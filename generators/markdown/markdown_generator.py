"""
Markdown Generator

Generates markdown files from scraped website content.
Provides clean, formatted markdown output with proper structure.
"""

import os
import re
import html
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

try:
    from generators import BaseGenerator, ContentValidator
except ImportError:
    try:
        from .. import BaseGenerator, ContentValidator
    except ImportError:
        from abc import ABC, abstractmethod
        
        class BaseGenerator(ABC):
            def __init__(self, config: Dict[str, Any]):
                self.config = config
                self.logger = logging.getLogger(__name__)
            
            @abstractmethod
            def generate(self, scraped_data: List[Dict[str, Any]], base_url: str, **kwargs) -> str:
                pass
                
            @abstractmethod
            def validate_config(self) -> bool:
                pass
        
        class ContentValidator:
            @staticmethod
            def validate_scraped_data(data):
                if not isinstance(data, list) or len(data) == 0:
                    return False, ["No scraped data provided"]
                
                errors = []
                for i, page_data in enumerate(data):
                    if not isinstance(page_data, dict):
                        errors.append(f"Invalid page data at index {i}: not a dictionary")
                        continue
                    
                    # Check for required fields based on actual scraper format
                    required_fields = ['url']
                    for field in required_fields:
                        if field not in page_data:
                            errors.append(f"Missing required field '{field}' in page data at index {i}")
                
                return len(errors) == 0, errors


class MarkdownGenerator(BaseGenerator):
    """
    Markdown generator for scraped website content.
    
    Converts HTML content to clean, structured markdown format.
    Supports single-file or multi-file output modes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.output_dir = config.get('directories', {}).get('output_dir', 'output')
        self.markdown_config = config.get('markdown', {})
        self.content_config = config.get('content', {})
        
    def validate_config(self) -> bool:
        """Validate markdown generator configuration"""
        required_sections = ['directories', 'markdown']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"Missing required config section: {section}")
                return False
        
        return True
    
    def generate(self, scraped_data: List[Dict[str, Any]], base_url: str, **kwargs) -> str:
        """
        Generate markdown from scraped data
        
        Args:
            scraped_data: List of scraped page data
            base_url: Base URL of the scraped site
            **kwargs: Additional generation options
            
        Returns:
            str: Path to generated markdown file
        """
        # Basic validation - check if we have data
        if not scraped_data or len(scraped_data) == 0:
            raise ValueError("No scraped data provided")
            
        # Validate first page has required fields
        first_page = scraped_data[0]
        if not isinstance(first_page, dict) or 'url' not in first_page:
            raise ValueError("Invalid scraped data format")
        
        if not self.validate_config():
            raise ValueError("Invalid configuration for markdown generation")
        
        self.logger.info(f"Starting markdown generation for {len(scraped_data)} pages")
        
        # Determine output mode
        multi_file = kwargs.get('multi_file', self.markdown_config.get('multi_file', False))
        output_filename = kwargs.get('output', self.markdown_config.get('output_filename'))
        
        if multi_file:
            return self._generate_multi_file(scraped_data, base_url)
        else:
            return self._generate_single_file(scraped_data, base_url, output_filename)
    
    def _generate_single_file(self, scraped_data: List[Dict[str, Any]], base_url: str, output_filename: Optional[str] = None) -> str:
        """Generate a single markdown file with all content"""
        
        if not output_filename:
            domain = urlparse(base_url).netloc.replace('www.', '').replace('.', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{domain}_{timestamp}.md"
        
        # Ensure .md extension
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Generate markdown content
        markdown_content = self._build_markdown_content(scraped_data, base_url)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        self.logger.info(f"Markdown file generated: {output_path}")
        return output_path
    
    def _generate_multi_file(self, scraped_data: List[Dict[str, Any]], base_url: str) -> str:
        """Generate multiple markdown files, one per page"""
        domain = urlparse(base_url).netloc.replace('www.', '').replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(self.output_dir, f"{domain}_{timestamp}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate index file
        index_content = self._build_index_content(scraped_data, base_url)
        index_path = os.path.join(output_dir, "README.md")
        
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        # Generate individual page files
        for i, page_data in enumerate(scraped_data, 1):
            page_content = self._build_page_markdown(page_data, i)
            title = page_data.get('metadata', {}).get('title', f"page_{i}")
            filename = self._sanitize_filename(title) + ".md"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(page_content)
        
        self.logger.info(f"Multi-file markdown generated in: {output_dir}")
        return output_dir
    
    def _build_markdown_content(self, scraped_data: List[Dict[str, Any]], base_url: str) -> str:
        """Build complete markdown content for single file output"""
        domain = urlparse(base_url).netloc
        
        content_parts = []
        
        # Add header
        content_parts.append(f"# Website Content: {domain}")
        content_parts.append(f"\n**Source:** {base_url}")
        content_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append(f"**Total Pages:** {len(scraped_data)}")
        content_parts.append("\n---\n")
        
        # Add table of contents
        if self.markdown_config.get('include_toc', True):
            content_parts.append("## Table of Contents\n")
            for i, page_data in enumerate(scraped_data, 1):
                title = page_data.get('metadata', {}).get('title', f'Page {i}')
                anchor = self._create_anchor(title)
                content_parts.append(f"{i}. [{title}](#{anchor})")
            content_parts.append("\n---\n")
        
        # Add page content
        for i, page_data in enumerate(scraped_data, 1):
            page_md = self._build_page_markdown(page_data, i, include_header=True)
            content_parts.append(page_md)
            content_parts.append("\n---\n")
        
        return "\n".join(content_parts)
    
    def _build_index_content(self, scraped_data: List[Dict[str, Any]], base_url: str) -> str:
        """Build index/README content for multi-file output"""
        domain = urlparse(base_url).netloc
        
        content_parts = []
        content_parts.append(f"# {domain} - Website Content")
        content_parts.append(f"\n**Source:** {base_url}")
        content_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append(f"**Total Pages:** {len(scraped_data)}")
        content_parts.append("\n## Pages\n")
        
        for i, page_data in enumerate(scraped_data, 1):
            title = page_data.get('metadata', {}).get('title', f'Page {i}')
            filename = self._sanitize_filename(title) + ".md"
            url = page_data.get('url', '')
            content_parts.append(f"{i}. [{title}]({filename}) - {url}")
        
        return "\n".join(content_parts)
    
    def _build_page_markdown(self, page_data: Dict[str, Any], page_num: int, include_header: bool = False) -> str:
        """Build markdown content for a single page"""
        # Extract title from metadata or fallback to Page N
        title = page_data.get('metadata', {}).get('title', f'Page {page_num}')
        url = page_data.get('url', '')
        
        # Use html_content first, then text as fallback
        content = page_data.get('html_content', page_data.get('text', ''))
        
        parts = []
        
        if include_header:
            parts.append(f"## {page_num}. {title}")
            parts.append(f"**URL:** {url}")
            if page_data.get('scraped_at'):
                parts.append(f"**Scraped:** {page_data['scraped_at']}")
            parts.append("")
        else:
            parts.append(f"# {title}")
            parts.append(f"**URL:** {url}")
            if page_data.get('scraped_at'):
                parts.append(f"**Scraped:** {page_data['scraped_at']}")
            parts.append("")
        
        # Convert HTML content to markdown
        markdown_content = self._html_to_markdown(content)
        parts.append(markdown_content)
        
        return "\n".join(parts)
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to markdown"""
        if not html_content:
            return ""
        
        # Basic HTML to Markdown conversion
        content = html_content
        
        # Headers
        content = re.sub(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', lambda m: f"{'#' * int(m.group(1))} {self._clean_text(m.group(2))}", content, flags=re.IGNORECASE | re.DOTALL)
        
        # Bold and italic
        content = re.sub(r'<(strong|b)[^>]*>(.*?)</(?:strong|b)>', r'**\2**', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<(em|i)[^>]*>(.*?)</(?:em|i)>', r'*\2*', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Links
        content = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Images
        content = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*/?>', r'![\2](\1)', content, flags=re.IGNORECASE)
        content = re.sub(r'<img[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*)["\'][^>]*/?>', r'![\1](\2)', content, flags=re.IGNORECASE)
        content = re.sub(r'<img[^>]*src=["\']([^"\']*)["\'][^>]*/?>', r'![](\1)', content, flags=re.IGNORECASE)
        
        # Lists
        content = re.sub(r'<ul[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</ul>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<ol[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</ol>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Code blocks and inline code
        content = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'```\n\1\n```', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Paragraphs and breaks
        content = re.sub(r'<p[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</p>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<br[^>]*/?>', '\n', content, flags=re.IGNORECASE)
        
        # Tables (basic support)
        content = re.sub(r'<table[^>]*>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'</table>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<tr[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</tr>', '\n', content, flags=re.IGNORECASE)
        content = re.sub(r'<t[hd][^>]*>(.*?)</t[hd]>', r'| \1 ', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove remaining HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Clean up text
        content = html.unescape(content)
        
        # Clean up whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Multiple newlines to double
        content = re.sub(r'[ \t]+', ' ', content)  # Multiple spaces to single
        content = content.strip()
        
        return content
    
    def _clean_text(self, text: str) -> str:
        """Clean text content for markdown"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = html.unescape(text)
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _create_anchor(self, title: str) -> str:
        """Create markdown anchor from title"""
        # Convert to lowercase, replace spaces and special chars with hyphens
        anchor = re.sub(r'[^\w\s-]', '', title.lower())
        anchor = re.sub(r'[\s_]+', '-', anchor)
        anchor = anchor.strip('-')
        return anchor
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove/replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename[:100]  # Limit length
        return filename.strip('_')