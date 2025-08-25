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
        # Remove script and style elements (always)
        for element in soup(['script', 'style']):
            element.decompose()
            
        # Remove menus and navigation elements (configurable)
        if not self.config['content'].get('include_menus', False):
            self._remove_menu_elements(soup)
            
        # Remove header and footer (always, as they're typically not main content)
        for element in soup(['header', 'footer']):
            element.decompose()
            
        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, type(soup.find_all(string=True)[0])) and text.parent.name == '[document]'):
            comment.extract()
            
        # Remove elements with common noise classes/ids
        noise_selectors = [
            '.advertisement', '.ads', '.banner',
            '.social-media', '.share', '.comments', '.related',
            '#ads', '#banner', '#social', '#comments'
        ]
        
        # Only add sidebar to noise selectors if menus are not being included
        if not self.config['content'].get('include_menus', False):
            noise_selectors.extend(['.sidebar', '#sidebar'])
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()

    def _remove_menu_elements(self, soup: BeautifulSoup) -> None:
        """Remove menu and navigation elements from the soup."""
        # Remove semantic navigation elements
        for element in soup(['nav']):
            element.decompose()
            
        # Remove elements with navigation/menu roles
        for element in soup.find_all(attrs={'role': ['navigation', 'menu', 'menubar']}):
            element.decompose()
            
        # Common menu/navigation selectors
        menu_selectors = [
            # Class-based selectors
            '.menu', '.nav', '.navigation', '.navbar', '.nav-menu',
            '.main-menu', '.primary-menu', '.secondary-menu', '.site-menu',
            '.menu-main', '.menu-primary', '.menu-secondary',
            '.nav-primary', '.nav-secondary', '.nav-main',
            '.sidebar-menu', '.left-menu', '.right-menu', '.top-menu',
            '.breadcrumb', '.breadcrumbs',
            # ID-based selectors  
            '#menu', '#nav', '#navigation', '#navbar', '#main-menu',
            '#primary-menu', '#secondary-menu', '#site-menu',
            '#left-menu', '#right-menu', '#top-menu', '#main-nav',
            # Structural selectors for common menu patterns
            '.sidebar nav', '.header nav', '.main-header nav',
            'aside nav'
        ]
        
        for selector in menu_selectors:
            for element in soup.select(selector):
                element.decompose()
                
        # Heuristic-based menu detection
        self._remove_heuristic_menus(soup)
    
    def _remove_heuristic_menus(self, soup: BeautifulSoup) -> None:
        """Remove elements that appear to be menus based on heuristics."""
        # Find list elements that might be menus
        for list_elem in soup.find_all(['ul', 'ol']):
            if self._is_likely_menu(list_elem):
                list_elem.decompose()
                
        # Find div/section elements that might be menus
        for container in soup.find_all(['div', 'section']):
            if self._is_likely_menu_container(container):
                container.decompose()
                
        # Handle aside elements specially (they often contain menus)
        for aside in soup.find_all('aside'):
            # Check if the aside primarily contains navigation links
            links = aside.find_all('a')
            text_length = len(aside.get_text().strip())
            
            # If it has many links and little content, it's likely a menu
            if len(links) >= 3 and text_length < 500:
                aside.decompose()
    
    def _is_likely_menu(self, element) -> bool:
        """Determine if a list element is likely a menu."""
        # Count list items
        list_items = element.find_all('li', recursive=False)
        if len(list_items) < 3:  # Too few items to be a typical menu
            return False
            
        # Count links in list items
        total_items = len(list_items)
        items_with_links = 0
        
        for li in list_items:
            if li.find('a'):
                items_with_links += 1
                
        # If most items have links, it's likely a menu
        link_ratio = items_with_links / total_items if total_items > 0 else 0
        if link_ratio > 0.7:  # 70% or more items have links
            return True
            
        # Check for menu-like text content
        text_content = element.get_text().lower()
        menu_keywords = [
            'home', 'about', 'contact', 'services', 'products', 'blog',
            'login', 'register', 'dashboard', 'profile', 'settings',
            'getting started', 'documentation', 'guide', 'tutorial',
            'overview', 'installation', 'configuration', 'api'
        ]
        
        keyword_matches = sum(1 for keyword in menu_keywords if keyword in text_content)
        if keyword_matches >= 3:  # Multiple menu-like keywords
            return True
            
        return False
    
    def _is_likely_menu_container(self, element) -> bool:
        """Determine if a container element is likely a menu."""
        # Check class and id for menu indicators
        classes = ' '.join(element.get('class', [])).lower()
        element_id = element.get('id', '').lower()
        
        menu_indicators = ['menu', 'nav', 'navigation', 'sidebar', 'toc', 'table-of-contents']
        
        for indicator in menu_indicators:
            if indicator in classes or indicator in element_id:
                # Additional check: does it contain mostly links?
                links = element.find_all('a')
                text_length = len(element.get_text().strip())
                
                if len(links) >= 5 and text_length < 1000:  # Many links, not much content
                    return True
                    
        return False

    def _get_image_description(self, img_tag: Tag) -> str:
        """Extract descriptive text for an image from various sources."""
        # Try different sources for image description
        alt_text = img_tag.get('alt', '').strip()
        title_text = img_tag.get('title', '').strip()
        src = img_tag.get('src', '')
        
        # Use alt text if available and meaningful
        if alt_text and len(alt_text) > 2:
            return alt_text
        
        # Use title text if available and meaningful
        if title_text and len(title_text) > 2:
            return title_text
        
        # Try to extract filename from src
        if src:
            try:
                filename = src.split('/')[-1].split('?')[0]  # Remove query params
                name_part = filename.split('.')[0]  # Remove extension
                # Clean up filename (replace common separators with spaces)
                name_part = re.sub(r'[-_]', ' ', name_part)
                if len(name_part) > 2 and not name_part.isdigit():
                    return name_part
            except:
                pass
        
        # Look for nearby captions or descriptive text
        parent = img_tag.parent
        if parent:
            # Check for figure captions
            figcaption = parent.find('figcaption')
            if figcaption:
                caption_text = self._clean_text(figcaption.get_text()).strip()
                if caption_text and len(caption_text) > 2:
                    return caption_text
        
        return "image"

    def _process_html_content_with_images(self, soup: BeautifulSoup, url: str) -> str:
        """Process HTML content while preserving image positions and downloading images."""
        # Check if image removal is enabled
        remove_images = self.config.get('content', {}).get('remove_images', False)
        
        # Find and process all images in the HTML
        for img_tag in soup.find_all('img'):
            if remove_images:
                # Replace image with text placeholder
                description = self._get_image_description(img_tag)
                placeholder_text = f"[image: {description} removed]"
                
                # Create a new text node to replace the image
                from bs4 import NavigableString
                img_tag.replace_with(NavigableString(placeholder_text))
            else:
                # Original image processing logic
                src = img_tag.get('src')
                if src:
                    # Download the image
                    local_path = self._download_image(src, url)
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
                        
                        # Update the img tag with the data URL and add styling
                        img_tag['src'] = data_url
                        img_tag['style'] = 'max-width: 100%; height: auto; display: inline-block; margin: 10px 0;'
                    else:
                        # Remove broken image tags
                        img_tag.decompose()
        
        return str(soup)

    def extract_content(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Extract all content from HTML page."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            self._remove_unwanted_elements(soup)
            
            # Extract metadata
            metadata = self._extract_metadata(soup, url) if self.config['content']['include_metadata'] else {}
            
            # Extract main text content
            # If including menus, use the whole body; otherwise find main content area
            if self.config['content'].get('include_menus', False):
                main_content = soup.find('body') or soup
            else:
                # Try to find main content area
                main_content = (
                    soup.find('main') or 
                    soup.find('article') or 
                    soup.find('div', class_=re.compile(r'content|main|body', re.I)) or
                    soup.find('body') or
                    soup
                )
            
            # Process HTML content with inline images (NEW)
            html_content_with_images = self._process_html_content_with_images(main_content, url)
            
            # Extract text (for backward compatibility)
            text_content = self._clean_text(main_content.get_text())
            
            # Extract headings
            headings = self._extract_headings(main_content)
            
            # Extract structured content
            structured = self._extract_structured_content(main_content)
            
            # Process images (keep for backward compatibility)
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
                'html_content': html_content_with_images,  # NEW: HTML with inline images
                'headings': headings,
                'structured': structured,
                'images': images,  # Keep for backward compatibility
                'links': links,
                'word_count': len(text_content.split()),
                'char_count': len(text_content)
            }
            
            return content_data
            
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None