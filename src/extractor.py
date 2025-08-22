import logging
import re
import os
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Any, Optional, Set
from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from PIL import Image
import hashlib


class ContentExtractor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.downloaded_images: Set[str] = set()
        
        # Configure session for image downloads
        self.session.headers.update({
            'User-Agent': config['http']['user_agent']
        })

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove common unwanted characters
        text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)  # Zero-width chars
        
        return text

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, str]:
        """Extract page metadata."""
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = self._clean_text(title_tag.get_text())
            
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '')
            
        # Meta keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            metadata['keywords'] = keywords_tag.get('content', '')
            
        # Author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '')
            
        # Open Graph data
        for og_tag in soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
            prop = og_tag.get('property', '').replace('og:', '')
            content = og_tag.get('content', '')
            if prop and content:
                metadata[f'og_{prop}'] = content
                
        return metadata

    def _download_image(self, img_url: str, base_url: str) -> Optional[str]:
        """Download an image and return local file path."""
        if not self.config['content']['include_images']:
            return None
            
        try:
            # Resolve relative URLs
            absolute_url = urljoin(base_url, img_url)
            
            # Skip if already downloaded
            if absolute_url in self.downloaded_images:
                return self._get_local_image_path(absolute_url)
                
            # Download image
            response = self.session.get(
                absolute_url, 
                timeout=self.config['crawling']['timeout'],
                stream=True
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if not any(fmt in content_type for fmt in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']):
                self.logger.debug(f"Skipping non-image content: {absolute_url}")
                return None
                
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.config['content']['max_image_size'] * 1024 * 1024:
                self.logger.debug(f"Skipping large image: {absolute_url}")
                return None
                
            # Generate unique filename
            url_hash = hashlib.md5(absolute_url.encode()).hexdigest()[:12]
            file_ext = self._get_image_extension(content_type, absolute_url)
            filename = f"img_{url_hash}.{file_ext}"
            
            # Save to temp directory
            temp_dir = self.config['directories']['temp_dir']
            local_path = os.path.join(temp_dir, filename)
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Validate image
            try:
                with Image.open(local_path) as img:
                    img.verify()  # Verify it's a valid image
                    
                self.downloaded_images.add(absolute_url)
                self.logger.debug(f"Downloaded image: {absolute_url} -> {local_path}")
                return local_path
                
            except Exception as e:
                self.logger.debug(f"Invalid image file: {absolute_url} - {e}")
                os.remove(local_path)
                return None
                
        except Exception as e:
            self.logger.debug(f"Failed to download image {img_url}: {e}")
            return None

    def _get_local_image_path(self, url: str) -> str:
        """Get local path for a downloaded image."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        temp_dir = self.config['directories']['temp_dir']
        
        # Try different extensions
        for ext in ['jpg', 'png', 'gif', 'webp']:
            path = os.path.join(temp_dir, f"img_{url_hash}.{ext}")
            if os.path.exists(path):
                return path
                
        return ""

    def _get_image_extension(self, content_type: str, url: str) -> str:
        """Determine image file extension."""
        if 'jpeg' in content_type or 'jpg' in content_type:
            return 'jpg'
        elif 'png' in content_type:
            return 'png'
        elif 'gif' in content_type:
            return 'gif'
        elif 'webp' in content_type:
            return 'webp'
        else:
            # Try to get from URL
            parsed = urlparse(url)
            path = parsed.path.lower()
            for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                if path.endswith(f'.{ext}'):
                    return ext.replace('jpeg', 'jpg')
            return 'jpg'  # Default

    def _process_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Process all images in the content."""
        images = []
        
        for img_tag in soup.find_all('img'):
            src = img_tag.get('src')
            if not src:
                continue
                
            # Download image
            local_path = self._download_image(src, base_url)
            
            image_data = {
                'src': src,
                'alt': img_tag.get('alt', ''),
                'title': img_tag.get('title', ''),
                'local_path': local_path or ''
            }
            images.append(image_data)
            
        return images

    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all headings with hierarchy."""
        headings = []
        
        for i in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{i}'):
                text = self._clean_text(heading.get_text())
                if text:
                    headings.append({
                        'level': i,
                        'text': text,
                        'id': heading.get('id', ''),
                        'class': ' '.join(heading.get('class', []))
                    })
                    
        return headings

    def _extract_structured_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured content (lists, tables, etc.)."""
        structured = {
            'lists': [],
            'tables': [],
            'code_blocks': [],
            'blockquotes': []
        }
        
        # Extract lists
        for ul in soup.find_all(['ul', 'ol']):
            list_items = []
            for li in ul.find_all('li', recursive=False):
                text = self._clean_text(li.get_text())
                if text:
                    list_items.append(text)
                    
            if list_items:
                structured['lists'].append({
                    'type': ul.name,
                    'items': list_items
                })
                
        # Extract tables
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = []
                for td in tr.find_all(['td', 'th']):
                    text = self._clean_text(td.get_text())
                    cells.append(text)
                if cells:
                    rows.append(cells)
                    
            if rows:
                structured['tables'].append({
                    'rows': rows,
                    'caption': self._clean_text(table.find('caption').get_text()) if table.find('caption') else ''
                })
                
        # Extract code blocks
        for code in soup.find_all(['code', 'pre']):
            text = code.get_text()
            if text.strip():
                structured['code_blocks'].append({
                    'text': text,
                    'language': code.get('class', [''])[0] if code.get('class') else ''
                })
                
        # Extract blockquotes
        for quote in soup.find_all('blockquote'):
            text = self._clean_text(quote.get_text())
            if text:
                structured['blockquotes'].append(text)
                
        return structured

    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """Remove unwanted elements from the soup."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.find_all(string=True)[0])) and text.parent.name == '[document]'):
            comment.extract()
            
        # Remove elements with common noise classes/ids
        noise_selectors = [
            '.sidebar', '.advertisement', '.ads', '.banner',
            '.social-media', '.share', '.comments', '.related',
            '#sidebar', '#ads', '#banner', '#social', '#comments'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()

    def extract_content(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract all content from HTML page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url) if self.config['content']['include_metadata'] else {}
            
            # Extract main text content
            # Try to find main content area
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', class_=re.compile(r'content|main|body', re.I)) or
                soup.find('body') or
                soup
            )
            
            # Extract text
            text_content = self._clean_text(main_content.get_text())
            
            # Extract headings
            headings = self._extract_headings(main_content)
            
            # Extract structured content
            structured = self._extract_structured_content(main_content)
            
            # Process images
            images = self._process_images(main_content, url)
            
            # Extract links
            links = []
            for link in main_content.find_all('a', href=True):
                link_text = self._clean_text(link.get_text())
                if link_text:
                    links.append({
                        'text': link_text,
                        'href': link['href'],
                        'title': link.get('title', '')
                    })
            
            content_data = {
                'metadata': metadata,
                'text': text_content,
                'headings': headings,
                'structured': structured,
                'images': images,
                'links': links,
                'word_count': len(text_content.split()),
                'char_count': len(text_content)
            }
            
            return content_data
            
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None