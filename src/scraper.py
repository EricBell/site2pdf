import requests
import time
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from typing import Set, List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup
from tqdm import tqdm
import re

try:
    from .extractor import ContentExtractor
    from .content_classifier import ContentClassifier, ContentType
    from .progress_tracker import ProgressTracker, Phase
    from .human_behavior import HumanBehaviorSimulator
    from .path_scoping import PathScopeManager
    from .cache_manager import CacheManager
except ImportError:
    from extractor import ContentExtractor
    from content_classifier import ContentClassifier, ContentType
    from progress_tracker import ProgressTracker, Phase
    from human_behavior import HumanBehaviorSimulator
    from path_scoping import PathScopeManager
    from cache_manager import CacheManager


class WebScraper:
    def __init__(self, config: Dict[str, Any], dry_run: bool = False, exclude_patterns: List[str] = None, verbose: bool = False, cache_session_id: str = None):
        self.config = config
        self.dry_run = dry_run
        self.verbose = verbose
        self.session = requests.Session()
        self.visited_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.url_classifications: Dict[str, ContentType] = {}
        self.base_domain = ""
        self.logger = logging.getLogger(__name__)
        self.extractor = ContentExtractor(config)
        self.classifier = ContentClassifier()
        self.progress = ProgressTracker(verbose=verbose)
        self.human_behavior = HumanBehaviorSimulator(config) if not dry_run else None
        self.exclude_patterns = exclude_patterns or []
        self.path_scope: Optional[PathScopeManager] = None  # Initialized when we know the starting URL
        
        # Caching support
        self.cache_enabled = config.get('cache', {}).get('enabled', True) and not dry_run
        self.cache_manager = CacheManager(config=config) if self.cache_enabled else None
        self.cache_session_id = cache_session_id
        self.resume_mode = cache_session_id is not None
        
        # Configure session with human-like headers
        if self.human_behavior and config.get('human_behavior', {}).get('detection_avoidance', {}).get('realistic_headers', True):
            # Use realistic Microsoft Edge headers
            self.session.headers.update(self.human_behavior.get_realistic_headers())
        else:
            # Fallback to original headers
            self.session.headers.update({
                'User-Agent': config['http']['user_agent'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
        
        # Enable cookies if human behavior is enabled
        if self.human_behavior and config.get('human_behavior', {}).get('detection_avoidance', {}).get('handle_cookies', True):
            # Session already handles cookies by default, but ensure it's enabled
            pass
        
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

    def _is_valid_url(self, url: str, is_navigation: bool = False, current_depth: int = 0) -> bool:
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
        
        # Check path scoping
        if self.path_scope:
            allowed, reason = self.path_scope.is_url_in_scope(url, is_navigation, current_depth)
            if not allowed:
                self.logger.debug(f"URL excluded by path scoping: {url} - {reason}")
                return False
                
        return True

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as base URL."""
        return urlparse(url).netloc.lower() == self.base_domain.lower()

    def _check_robots_txt(self, base_url: str) -> bool:
        """Check robots.txt compliance."""
        # Human behavior: sometimes ignore robots.txt
        if self.human_behavior and not self.human_behavior.should_respect_robots_txt():
            self.logger.debug("Ignoring robots.txt (simulating human behavior)")
            return True
            
        if not self.config['crawling']['respect_robots']:
            return True
            
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            user_agent = self.config['http']['user_agent']
            if self.human_behavior:
                # Use the realistic user agent for robots.txt check
                headers = self.human_behavior.get_realistic_headers()
                user_agent = headers.get('User-Agent', user_agent)
                
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
                        self._is_valid_url(normalized_url, is_navigation=False, current_depth=0)):
                        links.add(normalized_url)
                        
        except Exception as e:
            self.logger.error(f"Error extracting links from {base_url}: {e}")
            
        return links

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a single page and return its HTML content."""
        try:
            self.logger.debug(f"Fetching: {url}")
            
            # Update headers with referrer if human behavior is enabled
            headers = {}
            if self.human_behavior and self.config.get('human_behavior', {}).get('detection_avoidance', {}).get('track_referrers', True):
                headers = self.human_behavior.get_realistic_headers()
            
            response = self.session.get(
                url, 
                timeout=self.config['crawling']['timeout'],
                allow_redirects=True,
                headers=headers if headers else None
            )
            response.raise_for_status()
            
            # Update human behavior session state
            if self.human_behavior:
                self.human_behavior.update_session_state(url, response)
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.logger.debug(f"Skipping non-HTML content: {url}")
                return None
                
            return response.text
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None

    def discover_urls(self, base_url: str) -> Tuple[List[str], Dict[str, 'ContentType']]:
        """Discover all URLs to be scraped (for dry-run mode)."""
        self.base_domain = urlparse(base_url).netloc
        
        # Initialize path scoping
        if not self.path_scope:
            self.path_scope = PathScopeManager(self.config, base_url)
            if self.verbose:
                scope_summary = self.path_scope.get_scope_summary()
                self.logger.info(f"Path scoping enabled: {scope_summary}")
        
        if not self._check_robots_txt(base_url):
            return [], {}
            
        to_visit = [self._normalize_url(base_url)]
        discovered = set(to_visit)
        classifications = {}
        depth = 0
        last_progress_time = time.time()
        
        if self.verbose:
            self.logger.info("Starting URL discovery...")
        
        while (to_visit and 
               depth < self.config['crawling']['max_depth'] and
               len(discovered) < self.config['crawling']['max_pages']):
               
            current_level = to_visit.copy()
            to_visit.clear()
            
            for url in current_level:
                if len(discovered) >= self.config['crawling']['max_pages']:
                    break
                
                # Progress notification every 10 seconds
                current_time = time.time()
                if current_time - last_progress_time > 10:
                    if self.verbose:
                        self.logger.info(f"Discovery progress: {len(discovered)} URLs found, depth {depth}")
                    else:
                        print(f"🔍 Discovering... {len(discovered)} URLs found (depth {depth})")
                    last_progress_time = current_time
                    
                html = self._fetch_page(url)
                if html:
                    # Classify the current URL
                    if url not in classifications:
                        classifications[url] = self.classifier.classify_url(url)
                    
                    links = self._extract_links(html, url)
                    new_links = links - discovered
                    
                    for link in new_links:
                        if len(discovered) < self.config['crawling']['max_pages']:
                            discovered.add(link)
                            to_visit.append(link)
                            # Pre-classify new URLs (without HTML for now)
                            classifications[link] = self.classifier.classify_url(link)
                        else:
                            break
                            
                # Human-like delay between requests
                if self.human_behavior:
                    content_type = classifications.get(url, ContentType.CONTENT)
                    content_data = None  # Could enhance to pass actual content data
                    self.human_behavior.simulate_human_delay(url, content_type, content_data)
                else:
                    time.sleep(self.config['crawling']['request_delay'])
                
            depth += 1
        
        if self.verbose:
            self.logger.info(f"URL discovery completed: {len(discovered)} URLs found")
        else:
            print(f"✅ Discovery complete: {len(discovered)} URLs found")
            
        discovered_list = sorted(list(discovered))
        
        # Save discovery results to cache if available
        if self.cache_enabled and self.cache_manager and self.cache_session_id:
            self.cache_manager.save_discovery_results(self.cache_session_id, discovered_list, classifications)
            
        return discovered_list, classifications

    def scrape_approved_urls(self, approved_urls: Set[str]) -> List[Dict[str, Any]]:
        """Scrape only the pre-approved URLs."""
        if self.dry_run:
            return []
        
        # Handle caching and resume
        if self.cache_enabled and self.cache_manager:
            if self.resume_mode and self.cache_session_id:
                # Resume from existing session - check what we already have
                cached_pages = self.cache_manager.load_cached_pages(self.cache_session_id)
                if cached_pages:
                    cached_urls = {page.get('url') for page in cached_pages}
                    remaining_urls = approved_urls - cached_urls
                    if remaining_urls:
                        self.logger.info(f"Resuming session {self.cache_session_id[:8]}... - {len(remaining_urls)} URLs remaining")
                        approved_urls = remaining_urls
                    else:
                        self.logger.info(f"All URLs already cached in session {self.cache_session_id[:8]}...")
                        return cached_pages
            else:
                # Create new cache session - use first URL as base URL for session naming
                base_url = next(iter(approved_urls)) if approved_urls else "approved_urls"
                self.cache_session_id = self.cache_manager.create_session(base_url, self.config)
                self.logger.info(f"Created cache session: {self.cache_session_id}")
        
        scraped_data = []
        total_urls = len(approved_urls)
        
        self.logger.info(f"Starting to scrape {total_urls} approved URLs")
        
        # Progress bar setup
        session_info = f" [Session: {self.cache_session_id[:8]}...]" if self.cache_session_id else ""
        pbar = tqdm(total=total_urls, desc=f"Scraping approved URLs{session_info}", unit="pages")
        
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
                        
                        # Cache the page immediately after scraping
                        if self.cache_enabled and self.cache_manager and self.cache_session_id:
                            self.cache_manager.save_page(self.cache_session_id, content_data)
                        
                        self.logger.info(f"Scraped: {url}")
                    else:
                        self.logger.debug(f"Skipped (insufficient content): {url}")
                
                # Human-like delay between requests
                if self.human_behavior:
                    content_type = self.url_classifications.get(url, ContentType.CONTENT)
                    content_data = None  # Could enhance to pass actual content data
                    self.human_behavior.simulate_human_delay(url, content_type, content_data)
                else:
                    time.sleep(self.config['crawling']['request_delay'])
                pbar.update(1)
                
        finally:
            pbar.close()
        
        # Mark session as completed
        if self.cache_enabled and self.cache_manager and self.cache_session_id:
            self.cache_manager.mark_session_completed(self.cache_session_id, len(scraped_data))
            
        self.logger.info(f"Scraping completed. Total pages: {len(scraped_data)}")
        return scraped_data

    def scrape_website(self, base_url: str) -> List[Dict[str, Any]]:
        """Scrape the entire website starting from base_url with caching support."""
        if self.dry_run:
            return []
            
        self.base_domain = urlparse(base_url).netloc
        
        # Initialize path scoping
        if not self.path_scope:
            self.path_scope = PathScopeManager(self.config, base_url)
            if self.verbose:
                scope_summary = self.path_scope.get_scope_summary()
                self.logger.info(f"Path scoping enabled: {scope_summary}")
        
        if not self._check_robots_txt(base_url):
            self.logger.error("Robots.txt disallows crawling this site")
            return []
        
        # Handle caching and resume
        if self.cache_enabled and self.cache_manager:
            if self.resume_mode and self.cache_session_id:
                # Resume from existing session
                return self._resume_scraping(base_url)
            else:
                # Create new cache session
                self.cache_session_id = self.cache_manager.create_session(base_url, self.config)
                self.logger.info(f"Created cache session: {self.cache_session_id}")
        
        scraped_data = []
        to_visit = [self._normalize_url(base_url)]
        self.visited_urls.clear()
        depth = 0
        
        self.logger.info(f"Starting crawl of {base_url}")
        
        # Progress bar setup
        session_info = f" [Session: {self.cache_session_id[:8]}...]" if self.cache_session_id else ""
        pbar = tqdm(desc=f"Scraping: {self.base_domain}{session_info}", unit="pages")
        
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
                            
                            # Cache the page immediately after scraping
                            if self.cache_enabled and self.cache_manager and self.cache_session_id:
                                self.cache_manager.save_page(self.cache_session_id, content_data)
                            
                            self.logger.info(f"Scraped: {url}")
                            
                            # Extract new links for next level
                            links = self._extract_links(html, url)
                            new_links = links - self.visited_urls
                            to_visit.extend(new_links)
                        else:
                            self.logger.debug(f"Skipped (insufficient content): {url}")
                    
                    # Human-like delay
                    if self.human_behavior:
                        delay = self.human_behavior.calculate_delay()
                        time.sleep(delay)
                    else:
                        time.sleep(self.config['crawling']['request_delay'])
                    
                    pbar.update(1)
                    
                depth += 1
                self.logger.info(f"Completed depth {depth}, found {len(scraped_data)} pages")
                
        except KeyboardInterrupt:
            self.logger.info("Scraping interrupted by user")
            # Mark session as incomplete but recoverable
            if self.cache_enabled and self.cache_manager and self.cache_session_id:
                self.logger.info(f"Session {self.cache_session_id} can be resumed later")
            raise
        finally:
            pbar.close()
            
        # Mark session as complete
        if self.cache_enabled and self.cache_manager and self.cache_session_id:
            self.cache_manager.mark_session_complete(self.cache_session_id)
            
        self.logger.info(f"Scraping completed. Total pages: {len(scraped_data)}")
        return scraped_data
    
    def _resume_scraping(self, base_url: str) -> List[Dict[str, Any]]:
        """Resume scraping from cached session."""
        if not self.cache_manager or not self.cache_session_id:
            self.logger.error("Cannot resume: no cache manager or session ID")
            return []
        
        self.logger.info(f"Resuming scraping session: {self.cache_session_id}")
        
        # Load cached session data
        session_data = self.cache_manager.load_session(self.cache_session_id)
        if not session_data:
            self.logger.error(f"Session not found: {self.cache_session_id}")
            return []
        
        # Load already scraped pages
        cached_pages = self.cache_manager.load_cached_pages(self.cache_session_id)
        self.logger.info(f"Found {len(cached_pages)} cached pages")
        
        # Check if we need to continue scraping or if session was complete
        if session_data.get('status') == 'completed':
            self.logger.info("Session already complete, returning cached pages")
            return cached_pages
        
        # Get URLs that still need to be scraped
        all_urls = session_data.get('urls_discovered', [])
        if not all_urls:
            # If no discovery data, try to discover URLs first
            urls, classifications = self.discover_urls(base_url)
            all_urls = urls
            # Save discovery results to cache
            self.cache_manager.save_discovery_results(self.cache_session_id, urls, classifications)
        
        remaining_urls = self.cache_manager.get_resume_urls(self.cache_session_id, all_urls)
        
        if not remaining_urls:
            self.logger.info("No remaining URLs to scrape")
            self.cache_manager.mark_session_complete(self.cache_session_id)
            return cached_pages
        
        self.logger.info(f"Resuming scraping for {len(remaining_urls)} remaining URLs")
        
        # Continue scraping remaining URLs
        scraped_data = cached_pages.copy()
        self.visited_urls = set(page.get('url') for page in cached_pages)
        
        # Progress bar for resume
        pbar = tqdm(desc=f"Resuming: {self.base_domain} [{self.cache_session_id[:8]}...]", 
                   total=len(all_urls), initial=len(cached_pages), unit="pages")
        
        try:
            for url in remaining_urls:
                if len(scraped_data) >= self.config['crawling']['max_pages']:
                    break
                
                pbar.set_description(f"Scraping: {url[:50]}...")
                
                html = self._fetch_page(url)
                if html:
                    # Extract content
                    content_data = self.extractor.extract_content(html, url)
                    
                    if content_data and len(content_data.get('text', '')) >= self.config['content']['min_content_length']:
                        content_data['url'] = url
                        # Approximate depth based on URL structure
                        content_data['depth'] = len(urlparse(url).path.strip('/').split('/'))
                        scraped_data.append(content_data)
                        
                        # Cache the page immediately
                        self.cache_manager.save_page(self.cache_session_id, content_data)
                        
                        self.logger.info(f"Scraped: {url}")
                    else:
                        self.logger.debug(f"Skipped (insufficient content): {url}")
                
                # Human-like delay
                if self.human_behavior:
                    delay = self.human_behavior.calculate_delay()
                    time.sleep(delay)
                else:
                    time.sleep(self.config['crawling']['request_delay'])
                
                pbar.update(1)
                
        except KeyboardInterrupt:
            self.logger.info("Resume scraping interrupted by user")
            self.logger.info(f"Session {self.cache_session_id} can be resumed again later")
            raise
        finally:
            pbar.close()
        
        # Mark session as complete
        self.cache_manager.mark_session_complete(self.cache_session_id)
        
        self.logger.info(f"Resume scraping completed. Total pages: {len(scraped_data)}")
        return scraped_data
    
    def cleanup(self):
        """Clean up resources."""
        self.progress.cleanup()
        if hasattr(self.session, 'close'):
            self.session.close()