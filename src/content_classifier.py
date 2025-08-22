import re
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from enum import Enum
import logging


class ContentType(Enum):
    DOCUMENTATION = "📖 Documentation"
    CONTENT = "📄 Content"
    NAVIGATION = "🧭 Navigation" 
    TECHNICAL = "⚙️ Technical"
    EXCLUDED = "❌ Excluded"


class ContentClassifier:
    """Classifies URLs and content for documentation-focused scraping."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # URL patterns for different content types
        self.documentation_patterns = [
            r'/docs?/',
            r'/documentation/',
            r'/help/',
            r'/guide/',
            r'/tutorial/',
            r'/manual/',
            r'/reference/',
            r'/api-docs/',
            r'/getting-started/',
            r'/how-to/',
            r'/faq/',
            r'/support/',
            r'/knowledge-base/',
            r'/wiki/',
        ]
        
        self.content_patterns = [
            r'/about/',
            r'/features/',
            r'/blog/',
            r'/news/',
            r'/articles/',
            r'/posts/',
            r'/case-studies/',
            r'/examples/',
            r'/showcase/',
            r'/portfolio/',
            r'/services/',
            r'/products/',
            r'/solutions/',
        ]
        
        self.navigation_patterns = [
            r'^/$',  # Homepage
            r'/index\.(html?|php)$',
            r'/home/?$',
            r'/main/?$',
            r'/sitemap\.(xml|html)$',
        ]
        
        self.excluded_patterns = [
            r'/api/',
            r'/admin/',
            r'/login/',
            r'/logout/',
            r'/signin/',
            r'/signup/',
            r'/register/',
            r'/auth/',
            r'/search\?',
            r'/filter\?',
            r'/sort\?',
            r'/cart/',
            r'/checkout/',
            r'/order/',
            r'/payment/',
            r'/account/',
            r'/profile/',
            r'/settings/',
            r'/dashboard/',
            r'/upload/',
            r'/download/',
            r'/edit/',
            r'/delete/',
            r'/create/',
            r'/ajax/',
            r'/json/',
            r'/xml/',
            r'/rss/',
            r'/feed/',
            r'/subscribe/',
            r'/unsubscribe/',
            r'/contact-form/',
            r'/submit/',
            r'\.css$',
            r'\.js$',
            r'\.json$',
            r'\.xml$',
            r'\.pdf$',
            r'\.zip$',
            r'\.tar\.gz$',
            r'\.exe$',
            r'\.dmg$',
            r'\.pkg$',
            r'\.(jpg|jpeg|png|gif|svg|webp|ico)$',
            r'\.(mp4|avi|mov|wmv|flv|webm)$',
            r'\.(mp3|wav|ogg|flac|aac)$',
        ]
        
    def classify_url(self, url: str) -> ContentType:
        """Classify a URL based on its path and patterns."""
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Check for excluded patterns first
        for pattern in self.excluded_patterns:
            if re.search(pattern, path) or re.search(pattern, url.lower()):
                return ContentType.EXCLUDED
        
        # Check for documentation patterns
        for pattern in self.documentation_patterns:
            if re.search(pattern, path):
                return ContentType.DOCUMENTATION
        
        # Check for navigation patterns
        for pattern in self.navigation_patterns:
            if re.search(pattern, path):
                return ContentType.NAVIGATION
        
        # Check for content patterns
        for pattern in self.content_patterns:
            if re.search(pattern, path):
                return ContentType.CONTENT
        
        # Check for query parameters that indicate dynamic/technical content
        if parsed_url.query:
            query_params = parse_qs(parsed_url.query)
            technical_params = ['id', 'page', 'sort', 'filter', 'search', 'q', 'action']
            if any(param in query_params for param in technical_params):
                return ContentType.TECHNICAL
        
        # Default to content if no specific pattern matches
        return ContentType.CONTENT
    
    def analyze_content_quality(self, html: str, url: str) -> Dict[str, any]:
        """Analyze the quality and characteristics of page content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            text = '\n'.join(line for line in lines if line)
            
            # Count various elements
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            paragraphs = soup.find_all('p')
            lists = soup.find_all(['ul', 'ol'])
            images = soup.find_all('img')
            links = soup.find_all('a')
            
            # Calculate metrics
            word_count = len(text.split())
            sentence_count = len([s for s in text.split('.') if s.strip()])
            
            # Determine content quality score
            quality_score = 0
            
            # Word count scoring
            if word_count >= 500:
                quality_score += 30
            elif word_count >= 200:
                quality_score += 20
            elif word_count >= 100:
                quality_score += 10
            
            # Structure scoring
            if len(headings) >= 2:
                quality_score += 20
            elif len(headings) >= 1:
                quality_score += 10
                
            if len(paragraphs) >= 3:
                quality_score += 20
            elif len(paragraphs) >= 1:
                quality_score += 10
            
            # Content diversity scoring
            if len(lists) > 0:
                quality_score += 10
            if len(images) > 0:
                quality_score += 10
            
            # Penalize pages with too many links (might be navigation/index pages)
            if len(links) > 50:
                quality_score -= 20
            
            # Determine quality level
            if quality_score >= 70:
                quality_level = "High"
            elif quality_score >= 40:
                quality_level = "Medium"
            else:
                quality_level = "Low"
            
            return {
                'quality_score': quality_score,
                'quality_level': quality_level,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'heading_count': len(headings),
                'paragraph_count': len(paragraphs),
                'list_count': len(lists),
                'image_count': len(images),
                'link_count': len(links),
                'has_substantial_content': word_count >= 100 and len(paragraphs) >= 1,
                'title': soup.find('title').get_text().strip() if soup.find('title') else 'No Title',
                'description': self._extract_description(soup),
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing content quality for {url}: {e}")
            return {
                'quality_score': 0,
                'quality_level': "Unknown",
                'word_count': 0,
                'has_substantial_content': False,
                'title': 'Error',
                'description': 'Content analysis failed',
            }
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract a brief description of the page content."""
        # Try meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        
        # Try first paragraph
        first_p = soup.find('p')
        if first_p:
            text = first_p.get_text().strip()
            return text[:150] + "..." if len(text) > 150 else text
        
        # Try first text content
        text = soup.get_text().strip()
        if text:
            return text[:150] + "..." if len(text) > 150 else text
        
        return "No description available"
    
    def should_scrape_url(self, url: str, content_type: ContentType = None) -> bool:
        """Determine if a URL should be scraped based on its classification."""
        if content_type is None:
            content_type = self.classify_url(url)
        
        return content_type in [ContentType.DOCUMENTATION, ContentType.CONTENT, ContentType.NAVIGATION]
    
    def get_priority_score(self, url: str, content_type: ContentType = None) -> int:
        """Get priority score for URL (higher = more important)."""
        if content_type is None:
            content_type = self.classify_url(url)
        
        priority_map = {
            ContentType.DOCUMENTATION: 100,
            ContentType.CONTENT: 80,
            ContentType.NAVIGATION: 60,
            ContentType.TECHNICAL: 20,
            ContentType.EXCLUDED: 0,
        }
        
        return priority_map.get(content_type, 40)