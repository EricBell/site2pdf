import requests
import time
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from typing import Set, List, Dict, Optional, Any
from bs4 import BeautifulSoup
from tqdm import tqdm
import re

from .extractor import ContentExtractor


class WebScraper:
    def __init__(self, config: Dict[str, Any], dry_run: bool = False, exclude_patterns: List[str] = None):
        self.config = config
        self.dry_run = dry_run
        self.session = requests.Session()
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.base_domain = ""
        self.logger = logging.getLogger(__name__)
        self.extractor = ContentExtractor(config)
        self.exclude_patterns = exclude_patterns or []
        
        # Configure session
        self.session.headers.update({
            'User-Agent': config['http']['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=config['http']['max_retries'],
            backoff_factor=config['http']['retry_delay'],
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and query parameters."""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip('/') or '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled based on filters."""
        # Check URL length
        if len(url) > self.config['filters']['max_url_length']:
            return False
            
        # Check excluded patterns from config
        for pattern in self.config['filters']['exclude_patterns']:
            if re.search(pattern, url):
                self.logger.debug(f"URL excluded by config pattern {pattern}: {url}")
                return False
        
        # Check CLI exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, url):
                self.logger.debug(f"URL excluded by CLI pattern {pattern}: {url}")
                return False
                
        # Check file extensions
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext in self.config['filters']['skip_extensions']:
            if path.endswith(f'.{ext}'):
                self.logger.debug(f"URL excluded by extension .{ext}: {url}")
                return False
                
        return True

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base URL."""
        return urlparse(url).netloc.lower() == self.base_domain.lower()

    def _check_robots_txt(self, base_url: str) -> bool:
        """Check robots.txt compliance."""
        if not self.config['crawling']['respect_robots']:
            return True
            
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            user_agent = self.config['http']['user_agent']
            can_fetch = rp.can_fetch(user_agent, base_url)
            
            if not can_fetch:
                self.logger.warning(f"Robots.txt disallows crawling: {base_url}")
                
            return can_fetch
            
        except Exception as e:
            self.logger.debug(f"Could not check robots.txt: {e}")
            return True  # Allow if robots.txt is inaccessible

    def _extract_links(self, html: str, base_url: str) -> Set[str]:
        """Extract all valid links from HTML content."""
        links = set()
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract links from various elements
            for element in soup.find_all(['a', 'link']):
                href = element.get('href')
                if href:
                    # Resolve relative URLs
                    absolute_url = urljoin(base_url, href)
                    normalized_url = self._normalize_url(absolute_url)
                    
                    # Check if it's a valid URL to crawl
                    if (self._is_same_domain(normalized_url) and 
                        self._is_valid_url(normalized_url)):
                        links.add(normalized_url)
                        
        except Exception as e:
            self.logger.error(f"Error extracting links from {base_url}: {e}")
            
        return links

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single page and return its HTML content."""
        try:
            self.logger.debug(f"Fetching: {url}")
            
            response = self.session.get(
                url, 
                timeout=self.config['crawling']['timeout'],
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.logger.debug(f"Skipping non-HTML content: {url}")
                return None
                
            return response.text
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def discover_urls(self, base_url: str) -> List[str]:
        """Discover all URLs to be scraped (for dry-run mode)."""
        self.base_domain = urlparse(base_url).netloc
        
        if not self._check_robots_txt(base_url):
            return []
            
        to_visit = [self._normalize_url(base_url)]
        discovered = set(to_visit)
        depth = 0
        
        while (to_visit and 
               depth < self.config['crawling']['max_depth'] and
               len(discovered) < self.config['crawling']['max_pages']):
               
            current_level = to_visit.copy()
            to_visit.clear()
            
            for url in current_level:
                if len(discovered) >= self.config['crawling']['max_pages']:
                    break
                    
                html = self._fetch_page(url)
                if html:
                    links = self._extract_links(html, url)
                    new_links = links - discovered
                    
                    for link in new_links:
                        if len(discovered) < self.config['crawling']['max_pages']:
                            discovered.add(link)
                            to_visit.append(link)
                        else:
                            break
                            
                # Respect rate limiting
                time.sleep(self.config['crawling']['request_delay'])
                
            depth += 1
            
        return sorted(list(discovered))

    def scrape_approved_urls(self, approved_urls: Set[str]) -> List[Dict[str, Any]]:
        """Scrape only the pre-approved URLs."""
        if self.dry_run:
            return []
        
        scraped_data = []
        total_urls = len(approved_urls)
        
        self.logger.info(f"Starting to scrape {total_urls} approved URLs")
        
        # Progress bar setup
        pbar = tqdm(total=total_urls, desc="Scraping approved URLs", unit="pages")
        
        try:
            for url in approved_urls:
                pbar.set_description(f"Scraping: {url[:50]}...")
                
                html = self._fetch_page(url)
                if html:
                    # Extract content
                    content_data = self.extractor.extract_content(html, url)
                    
                    if content_data and len(content_data.get('text', '')) >= self.config['content']['min_content_length']:
                        content_data['url'] = url
                        scraped_data.append(content_data)
                        self.logger.info(f"Scraped: {url}")
                    else:
                        self.logger.debug(f"Skipped (insufficient content): {url}")
                
                # Respect rate limiting
                time.sleep(self.config['crawling']['request_delay'])
                pbar.update(1)
                
        finally:
            pbar.close()
        
        self.logger.info(f"Scraping completed. Total pages: {len(scraped_data)}")
        return scraped_data

    def scrape_website(self, base_url: str) -> List[Dict[str, Any]]:
        """Scrape the entire website starting from base_url."""
        if self.dry_run:
            return []
            
        self.base_domain = urlparse(base_url).netloc
        
        if not self._check_robots_txt(base_url):
            self.logger.error("Robots.txt disallows crawling this site")
            return []
            
        scraped_data = []
        to_visit = [self._normalize_url(base_url)]
        self.visited_urls.clear()
        depth = 0
        
        self.logger.info(f"Starting crawl of {base_url}")
        
        # Progress bar setup
        pbar = tqdm(desc="Scraping pages", unit="pages")
        
        try:
            while (to_visit and 
                   depth < self.config['crawling']['max_depth'] and
                   len(self.visited_urls) < self.config['crawling']['max_pages']):
                   
                current_level = to_visit.copy()
                to_visit.clear()
                
                for url in current_level:
                    if len(self.visited_urls) >= self.config['crawling']['max_pages']:
                        break
                        
                    if url in self.visited_urls:
                        continue
                        
                    self.visited_urls.add(url)
                    pbar.set_description(f"Scraping: {url[:50]}...")
                    
                    html = self._fetch_page(url)
                    if html:
                        # Extract content
                        content_data = self.extractor.extract_content(html, url)
                        
                        if content_data and len(content_data.get('text', '')) >= self.config['content']['min_content_length']:
                            content_data['url'] = url
                            content_data['depth'] = depth
                            scraped_data.append(content_data)
                            
                            self.logger.info(f"Scraped: {url}")
                            
                            # Extract new links for next level
                            links = self._extract_links(html, url)
                            new_links = links - self.visited_urls
                            to_visit.extend(new_links)
                        else:
                            self.logger.debug(f"Skipped (insufficient content): {url}")
                    
                    # Respect rate limiting
                    time.sleep(self.config['crawling']['request_delay'])
                    pbar.update(1)
                    
                depth += 1
                self.logger.info(f"Completed depth {depth}, found {len(scraped_data)} pages")
                
        finally:
            pbar.close()
            
        self.logger.info(f"Scraping completed. Total pages: {len(scraped_data)}")
        return scraped_data