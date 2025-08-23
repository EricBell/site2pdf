import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import tempfile
import shutil


class PDFGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.font_config = FontConfiguration()

    def _generate_html_content(self, scraped_data: List[Dict[str, Any]], base_url: str) -> str:
        """Generate HTML content for PDF conversion."""
        html_parts = []
        
        # Document header
        html_parts.append(self._generate_document_header(base_url))
        
        # Table of contents
        if self.config['pdf']['include_toc']:
            html_parts.append(self._generate_table_of_contents(scraped_data))
            
        # Main content
        for i, page_data in enumerate(scraped_data):
            html_parts.append(self._generate_page_content(page_data, i + 1))
            
        # Document footer
        html_parts.append(self._generate_document_footer())
        
        return '\n'.join(html_parts)

    def _generate_document_header(self, base_url: str) -> str:
        """Generate document header with title and metadata."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Website Scrape: {base_url}</title>
            {self._generate_css_styles()}
        </head>
        <body>
            <div class="cover-page">
                <h1 class="cover-title">Website Documentation</h1>
                <h2 class="cover-url">{base_url}</h2>
                <p class="cover-date">Generated on {timestamp}</p>
                <p class="cover-generator">Created with site2pdf</p>
            </div>
            <div class="page-break"></div>
        """

    def _generate_css_styles(self) -> str:
        """Generate CSS styles for the PDF."""
        margins = self.config['pdf']['margins']
        font_family = self.config['pdf']['font']['family']
        font_size = self.config['pdf']['font']['size']
        
        return f"""
        <style>
            @page {{
                size: {self.config['pdf']['page_size']};
                margin: {margins['top']}mm {margins['right']}mm {margins['bottom']}mm {margins['left']}mm;
                @bottom-right {{
                    content: {"'Page ' counter(page)" if self.config['pdf']['include_page_numbers'] else "''"};
                    font-size: 10px;
                    color: #666;
                }}
            }}
            
            body {{
                font-family: {font_family}, Arial, sans-serif;
                font-size: {font_size}px;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            
            .cover-page {{
                text-align: center;
                padding: 100px 0;
                page-break-after: always;
            }}
            
            .cover-title {{
                font-size: 36px;
                font-weight: bold;
                margin-bottom: 30px;
                color: #2c3e50;
            }}
            
            .cover-url {{
                font-size: 24px;
                color: #3498db;
                margin-bottom: 50px;
                word-break: break-all;
            }}
            
            .cover-date, .cover-generator {{
                font-size: 16px;
                color: #7f8c8d;
                margin: 10px 0;
            }}
            
            .page-break {{
                page-break-before: always;
            }}
            
            .toc {{
                margin-bottom: 30px;
            }}
            
            .toc h2 {{
                font-size: 24px;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            
            .toc-item {{
                margin: 8px 0;
                padding-left: 20px;
            }}
            
            .toc-url {{
                color: #3498db;
                text-decoration: none;
                display: block;
                margin-bottom: 4px;
            }}
            
            .toc-title {{
                color: #2c3e50;
                font-weight: bold;
            }}
            
            .page-section {{
                margin-bottom: 40px;
                page-break-inside: avoid;
            }}
            
            .page-header {{
                border-bottom: 2px solid #3498db;
                padding-bottom: 15px;
                margin-bottom: 25px;
            }}
            
            .page-title {{
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                margin: 0 0 10px 0;
            }}
            
            .page-url {{
                font-size: 14px;
                color: #3498db;
                word-break: break-all;
                margin: 5px 0;
            }}
            
            .page-meta {{
                font-size: 12px;
                color: #7f8c8d;
                margin: 5px 0;
            }}
            
            h1, h2, h3, h4, h5, h6 {{
                color: #2c3e50;
                margin: 25px 0 15px 0;
                page-break-after: avoid;
            }}
            
            h1 {{ font-size: 28px; }}
            h2 {{ font-size: 24px; }}
            h3 {{ font-size: 20px; }}
            h4 {{ font-size: 18px; }}
            h5 {{ font-size: 16px; }}
            h6 {{ font-size: 14px; }}
            
            p {{
                margin: 12px 0;
                text-align: justify;
            }}
            
            .content-text {{
                margin: 20px 0;
                text-align: justify;
                line-height: 1.7;
            }}
            
            .html-content {{
                margin: 20px 0;
                line-height: 1.7;
            }}
            
            .html-content img {{
                max-width: 100%;
                height: auto;
                display: inline-block;
                vertical-align: middle;
                margin: 10px 0;
            }}
            
            .html-content p {{
                margin: 12px 0;
                text-align: justify;
            }}
            
            .html-content h1, .html-content h2, .html-content h3, 
            .html-content h4, .html-content h5, .html-content h6 {{
                color: #2c3e50;
                margin: 25px 0 15px 0;
                page-break-after: avoid;
            }}
            
            .image-container {{
                text-align: center;
                margin: 20px 0;
                page-break-inside: avoid;
            }}
            
            .content-image {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            .image-caption {{
                font-style: italic;
                color: #666;
                font-size: 12px;
                margin-top: 8px;
            }}
            
            .content-list {{
                margin: 15px 0;
            }}
            
            .content-list li {{
                margin: 6px 0;
            }}
            
            .content-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 12px;
            }}
            
            .content-table th,
            .content-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            
            .content-table th {{
                background-color: #f8f9fa;
                font-weight: bold;
            }}
            
            .code-block {{
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 15px;
                margin: 15px 0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                overflow-x: auto;
                page-break-inside: avoid;
            }}
            
            .blockquote {{
                border-left: 4px solid #3498db;
                margin: 20px 0;
                padding: 10px 20px;
                background-color: #f8f9fa;
                font-style: italic;
            }}
            
            .links-section {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
            }}
            
            .links-title {{
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            
            .link-item {{
                margin: 5px 0;
                font-size: 12px;
            }}
            
            .link-url {{
                color: #3498db;
                word-break: break-all;
            }}
        </style>
        """

    def _generate_table_of_contents(self, scraped_data: List[Dict[str, Any]]) -> str:
        """Generate table of contents."""
        toc_parts = ['<div class="toc page-break">', '<h2>Table of Contents</h2>']
        
        for i, page_data in enumerate(scraped_data):
            url = page_data.get('url', 'Unknown URL')
            title = page_data.get('metadata', {}).get('title', 'Untitled Page')
            word_count = page_data.get('word_count', 0)
            
            toc_parts.append(f'''
                <div class="toc-item">
                    <div class="toc-title">{self._escape_html(title)}</div>
                    <div class="toc-url">{self._escape_html(url)}</div>
                    <div class="toc-meta">Words: {word_count}</div>
                </div>
            ''')
            
        toc_parts.append('</div>')
        return '\n'.join(toc_parts)

    def _generate_page_content(self, page_data: Dict[str, Any], page_number: int) -> str:
        """Generate content for a single page."""
        parts = [f'<div class="page-section" id="page-{page_number}">']
        
        # Page header
        parts.append(self._generate_page_header(page_data, page_number))
        
        # Use HTML content with inline images if available
        html_content = page_data.get('html_content', '')
        if html_content:
            # Clean and process the HTML content
            parts.append(f'<div class="html-content">{html_content}</div>')
        else:
            # Fallback to old method for backward compatibility
            # Main text content
            text = page_data.get('text', '')
            if text:
                parts.append(f'<div class="content-text">{self._format_text_content(text)}</div>')
                
            # Headings (if they exist as separate structure)
            headings = page_data.get('headings', [])
            if headings:
                parts.append(self._format_headings(headings))
                
            # Structured content
            structured = page_data.get('structured', {})
            if structured:
                parts.append(self._format_structured_content(structured))
                
            # Images
            images = page_data.get('images', [])
            if images:
                parts.append(self._format_images(images))
        
        # Links (always show regardless of content method)
        links = page_data.get('links', [])
        if links:
            parts.append(self._format_links(links))
            
        parts.append('</div>')
        return '\n'.join(parts)

    def _generate_page_header(self, page_data: Dict[str, Any], page_number: int) -> str:
        """Generate header for a page."""
        metadata = page_data.get('metadata', {})
        url = page_data.get('url', 'Unknown URL')
        title = metadata.get('title', f'Page {page_number}')
        description = metadata.get('description', '')
        word_count = page_data.get('word_count', 0)
        
        return f'''
        <div class="page-header">
            <h1 class="page-title">{self._escape_html(title)}</h1>
            <div class="page-url">{self._escape_html(url)}</div>
            {f'<div class="page-meta">Description: {self._escape_html(description)}</div>' if description else ''}
            <div class="page-meta">Word Count: {word_count} | Page {page_number}</div>
        </div>
        '''

    def _format_text_content(self, text: str) -> str:
        """Format main text content with paragraphs."""
        paragraphs = text.split('\n\n')
        formatted_paragraphs = []
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                formatted_paragraphs.append(f'<p>{self._escape_html(paragraph)}</p>')
                
        return '\n'.join(formatted_paragraphs)

    def _format_headings(self, headings: List[Dict[str, Any]]) -> str:
        """Format headings structure."""
        if not headings:
            return ""
            
        parts = ['<div class="headings-section">']
        for heading in headings:
            level = heading.get('level', 1)
            text = heading.get('text', '')
            if text:
                parts.append(f'<h{level}>{self._escape_html(text)}</h{level}>')
        parts.append('</div>')
        
        return '\n'.join(parts)

    def _format_structured_content(self, structured: Dict[str, Any]) -> str:
        """Format structured content (lists, tables, etc.)."""
        parts = []
        
        # Lists
        for list_data in structured.get('lists', []):
            list_type = list_data.get('type', 'ul')
            items = list_data.get('items', [])
            if items:
                parts.append(f'<{list_type} class="content-list">')
                for item in items:
                    parts.append(f'<li>{self._escape_html(item)}</li>')
                parts.append(f'</{list_type}>')
                
        # Tables
        for table_data in structured.get('tables', []):
            rows = table_data.get('rows', [])
            caption = table_data.get('caption', '')
            if rows:
                parts.append('<table class="content-table">')
                if caption:
                    parts.append(f'<caption>{self._escape_html(caption)}</caption>')
                    
                for i, row in enumerate(rows):
                    tag = 'th' if i == 0 else 'td'
                    parts.append('<tr>')
                    for cell in row:
                        parts.append(f'<{tag}>{self._escape_html(cell)}</{tag}>')
                    parts.append('</tr>')
                parts.append('</table>')
                
        # Code blocks
        for code_data in structured.get('code_blocks', []):
            text = code_data.get('text', '')
            if text:
                parts.append(f'<div class="code-block">{self._escape_html(text)}</div>')
                
        # Blockquotes
        for quote in structured.get('blockquotes', []):
            if quote:
                parts.append(f'<div class="blockquote">{self._escape_html(quote)}</div>')
                
        return '\n'.join(parts)

    def _format_images(self, images: List[Dict[str, str]]) -> str:
        """Format images for PDF."""
        if not images or not self.config['content']['include_images']:
            return ""
            
        parts = []
        for img_data in images:
            local_path = img_data.get('local_path', '')
            alt_text = img_data.get('alt', '')
            title = img_data.get('title', '')
            
            if local_path and os.path.exists(local_path):
                # Convert to data URL for embedding
                with open(local_path, 'rb') as f:
                    import base64
                    img_data_b64 = base64.b64encode(f.read()).decode()
                    
                ext = local_path.split('.')[-1].lower()
                mime_type = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg', 
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }.get(ext, 'image/jpeg')
                
                data_url = f"data:{mime_type};base64,{img_data_b64}"
                
                parts.append('<div class="image-container">')
                parts.append(f'<img src="{data_url}" class="content-image" alt="{self._escape_html(alt_text)}">')
                
                caption_parts = []
                if alt_text:
                    caption_parts.append(alt_text)
                if title and title != alt_text:
                    caption_parts.append(title)
                    
                if caption_parts:
                    caption = ' - '.join(caption_parts)
                    parts.append(f'<div class="image-caption">{self._escape_html(caption)}</div>')
                    
                parts.append('</div>')
                
        return '\n'.join(parts)

    def _format_links(self, links: List[Dict[str, str]]) -> str:
        """Format links section."""
        if not links:
            return ""
            
        parts = [
            '<div class="links-section">',
            '<div class="links-title">Links found on this page:</div>'
        ]
        
        for link_data in links[:20]:  # Limit to first 20 links
            text = link_data.get('text', '')
            href = link_data.get('href', '')
            if text and href:
                parts.append(f'''
                    <div class="link-item">
                        <strong>{self._escape_html(text)}</strong><br>
                        <span class="link-url">{self._escape_html(href)}</span>
                    </div>
                ''')
                
        if len(links) > 20:
            parts.append(f'<div class="link-item"><em>... and {len(links) - 20} more links</em></div>')
            
        parts.append('</div>')
        return '\n'.join(parts)

    def _generate_document_footer(self) -> str:
        """Generate document footer."""
        return """
            </body>
        </html>
        """

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))

    def generate_pdf(self, scraped_data: List[Dict[str, Any]], base_url: str) -> str:
        """Generate PDF from scraped data."""
        try:
            self.logger.info("Generating PDF content...")
            
            # Generate HTML content
            html_content = self._generate_html_content(scraped_data, base_url)
            
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(html_content)
                tmp_html_path = tmp_file.name
                
            try:
                # Generate PDF
                output_filename = self.config['pdf']['output_filename']
                output_dir = self.config['directories']['output_dir']
                output_path = os.path.join(output_dir, output_filename)
                
                self.logger.info(f"Converting to PDF: {output_path}")
                
                html_doc = HTML(filename=tmp_html_path)
                html_doc.write_pdf(output_path, font_config=self.font_config)
                
                self.logger.info(f"PDF generated successfully: {output_path}")
                return output_path
                
            finally:
                # Clean up temporary HTML file
                os.unlink(tmp_html_path)
                
        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            raise