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
    from ...src.chunk_manager import ChunkManager
except ImportError:
    try:
        from src.chunk_manager import ChunkManager
    except ImportError:
        from chunk_manager import ChunkManager

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
        self.chunk_manager = ChunkManager(config)
        
    def validate_config(self) -> bool:
        """Validate markdown generator configuration"""
        required_sections = ['directories', 'markdown']
        
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"Missing required config section: {section}")
                return False
        
        return True
    
    def supports_chunking(self) -> bool:
        """Return whether this generator supports chunking."""
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
    
    def generate_chunked(self, scraped_data: List[Dict[str, Any]], base_url: str, 
                        chunk_size: Optional[str] = None, chunk_pages: Optional[int] = None,
                        chunk_prefix: Optional[str] = None, **kwargs) -> List[str]:
        """
        Generate chunked markdown files from scraped data.
        
        Args:
            scraped_data: List of scraped page data
            base_url: Base URL of the scraped site
            chunk_size: Maximum size per chunk (e.g., '5MB')
            chunk_pages: Maximum pages per chunk
            chunk_prefix: Custom prefix for chunk filenames
            **kwargs: Additional generation options
            
        Returns:
            List[str]: Paths to generated markdown files
        """
        if not self.chunk_manager.should_chunk(chunk_size, chunk_pages):
            # No chunking requested, use regular generation
            output_path = self.generate(scraped_data, base_url, **kwargs)
            return [output_path]
        
        # Basic validation
        if not scraped_data or len(scraped_data) == 0:
            raise ValueError("No scraped data provided")
            
        if not self.validate_config():
            raise ValueError("Invalid configuration for markdown generation")
        
        self.logger.info(f"Starting chunked markdown generation for {len(scraped_data)} pages")
        
        # Chunk the data
        chunks = self.chunk_manager.chunk_data(scraped_data, chunk_size, chunk_pages, 'markdown')
        
        if len(chunks) == 1:
            self.logger.info("Data fits in single chunk, generating single file")
            output_path = self.generate(scraped_data, base_url, **kwargs)
            return [output_path]
        
        # Generate chunk summary
        summary = self.chunk_manager.generate_summary_info(chunks, 'markdown')
        self.logger.info(f"Generating {summary['total_chunks']} markdown chunks")
        
        # Determine base filename
        domain = urlparse(base_url).netloc.replace('www.', '').replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = chunk_prefix if chunk_prefix else f"{domain}_{timestamp}"
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        generated_files = []
        
        # Generate individual chunk files
        for i, chunk in enumerate(chunks, 1):
            chunk_filename = self.chunk_manager.generate_chunk_filename(
                base_filename, i, len(chunks), 'md', chunk_prefix
            )
            chunk_path = os.path.join(self.output_dir, chunk_filename)
            
            # Generate chunk content
            chunk_content = self._build_chunk_content(chunk, base_url, i, len(chunks), summary)
            
            # Write chunk file
            with open(chunk_path, 'w', encoding='utf-8') as f:
                f.write(chunk_content)
            
            generated_files.append(chunk_path)
            self.logger.info(f"Generated chunk {i}/{len(chunks)}: {chunk_path}")
        
        # Generate index file
        index_path = self._generate_chunk_index(chunks, base_url, base_filename, summary)
        generated_files.insert(0, index_path)  # Put index first
        
        self.logger.info(f"Chunked markdown generation complete: {len(generated_files)} files generated")
        return generated_files
    
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
    
    def _build_chunk_content(self, chunk_data: List[Dict[str, Any]], base_url: str, 
                           chunk_num: int, total_chunks: int, summary: Dict[str, Any]) -> str:
        """Build markdown content for a single chunk"""
        domain = urlparse(base_url).netloc
        
        content_parts = []
        
        # Add chunk header
        content_parts.append(f"# {domain} - Part {chunk_num} of {total_chunks}")
        content_parts.append(f"\n**Source:** {base_url}")
        content_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append(f"**Chunk:** {chunk_num} of {total_chunks}")
        content_parts.append(f"**Pages in this chunk:** {len(chunk_data)}")
        
        # Add navigation info
        if chunk_num > 1:
            prev_filename = self.chunk_manager.generate_chunk_filename(
                f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                chunk_num - 1, total_chunks, 'md'
            )
            content_parts.append(f"**Previous:** [{prev_filename}](./{prev_filename})")
        
        if chunk_num < total_chunks:
            next_filename = self.chunk_manager.generate_chunk_filename(
                f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}", 
                chunk_num + 1, total_chunks, 'md'
            )
            content_parts.append(f"**Next:** [{next_filename}](./{next_filename})")
        
        content_parts.append("\n---\n")
        
        # Add page content
        page_start_num = sum(len(summary['chunks'][i]['pages']) for i in range(chunk_num - 1)) + 1
        for i, page_data in enumerate(chunk_data):
            page_num = page_start_num + i
            page_md = self._build_page_markdown(page_data, page_num, include_header=True)
            content_parts.append(page_md)
            content_parts.append("\n---\n")
        
        return "\n".join(content_parts)
    
    def _generate_chunk_index(self, chunks: List[List[Dict[str, Any]]], base_url: str, 
                            base_filename: str, summary: Dict[str, Any]) -> str:
        """Generate index file for chunks"""
        domain = urlparse(base_url).netloc
        index_filename = f"{base_filename}_INDEX.md"
        index_path = os.path.join(self.output_dir, index_filename)
        
        content_parts = []
        content_parts.append(f"# {domain} - Complete Documentation Index")
        content_parts.append(f"\n**Source:** {base_url}")
        content_parts.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content_parts.append(f"**Total Pages:** {summary['total_pages']}")
        content_parts.append(f"**Total Chunks:** {summary['total_chunks']}")
        content_parts.append("\n## Document Structure\n")
        content_parts.append("This documentation has been split into multiple files for easier handling:\n")
        
        # List all chunks
        for i, chunk_info in enumerate(summary['chunks'], 1):
            chunk_filename = self.chunk_manager.generate_chunk_filename(
                base_filename, i, summary['total_chunks'], 'md'
            )
            content_parts.append(f"{i}. [{chunk_filename}](./{chunk_filename})")
            content_parts.append(f"   - Pages: {chunk_info['pages']}")
            content_parts.append(f"   - Estimated size: {chunk_info['estimated_size_human']}")
        
        content_parts.append("\n## All Pages\n")
        
        # List all pages with their chunk locations
        page_num = 1
        for chunk_i, chunk in enumerate(chunks, 1):
            chunk_filename = self.chunk_manager.generate_chunk_filename(
                base_filename, chunk_i, len(chunks), 'md'
            )
            for page_data in chunk:
                title = page_data.get('metadata', {}).get('title', f'Page {page_num}')
                url = page_data.get('url', '')
                content_parts.append(f"{page_num}. [{title}](./{chunk_filename}) - {url}")
                page_num += 1
        
        index_content = "\n".join(content_parts)
        
        # Write index file
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        self.logger.info(f"Generated index file: {index_path}")
        return index_path