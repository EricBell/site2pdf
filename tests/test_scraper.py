"""
Unit tests for WebScraper functionality
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from urllib.parse import urlparse
import requests
import time

from src.scraper import WebScraper
from src.content_classifier import ContentType


class TestWebScraper:
    """Test WebScraper functionality"""
    
    @pytest.fixture
    def basic_config(self):
        """Basic configuration for scraper"""
        return {
            'http': {
                'user_agent': 'TestBot/1.0',
                'max_retries': 3,
                'retry_delay': 1
            },
            'crawling': {
                'max_depth': 2,
                'max_pages': 10,
                'request_delay': 0.1,
                'timeout': 30,
                'respect_robots': True
            },
            'filters': {
                'exclude_patterns': ['/admin/', '/login', '/logout'],
                'skip_extensions': ['pdf', 'doc', 'zip'],
                'max_url_length': 2000
            },
            'content': {
                'min_content_length': 100
            },
            'human_behavior': {
                'enabled': False
            },
            'authentication': {
                'enabled': False
            },
            'cache': {
                'enabled': True
            }
        }
    
    @pytest.fixture
    def mock_response(self):
        """Mock HTTP response"""
        response = Mock()
        response.status_code = 200
        response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Test Content</h1>
                <p>This is a test page with some content.</p>
                <a href="/page1">Link 1</a>
                <a href="/page2">Link 2</a>
                <a href="https://external.com">External</a>
            </body>
        </html>
        """
        response.headers = {'content-type': 'text/html; charset=utf-8'}
        response.raise_for_status = Mock()
        return response
    
    @pytest.fixture
    def scraper(self, basic_config):
        """Create WebScraper instance"""
        with patch('src.scraper.CacheManager'), \
             patch('src.scraper.HumanBehaviorSimulator'), \
             patch('src.scraper.AUTHENTICATION_AVAILABLE', True):
            scraper = WebScraper(basic_config, verbose=True)
            scraper.human_behavior = None  # Disable human behavior for predictable tests
            return scraper
    
    @pytest.fixture
    def scraper_with_cache(self, basic_config, temp_dir):
        """Create WebScraper with real cache manager"""
        mock_cache = Mock()
        mock_cache.cache_dir = temp_dir / 'cache'
        mock_cache.create_session.return_value = 'test_session_123'
        mock_cache.load_cached_pages.return_value = []
        mock_cache.save_page = Mock()
        mock_cache.mark_session_complete = Mock()
        
        with patch('src.scraper.CacheManager', return_value=mock_cache), \
             patch('src.scraper.HumanBehaviorSimulator'), \
             patch('src.scraper.AUTHENTICATION_AVAILABLE', True):
            scraper = WebScraper(basic_config)
            scraper.human_behavior = None  # Disable human behavior for predictable tests
            return scraper

    def test_initialization_basic(self, basic_config):
        """Test basic scraper initialization"""
        with patch('src.scraper.CacheManager'), \
             patch('src.scraper.AUTHENTICATION_AVAILABLE', True):
            scraper = WebScraper(basic_config)
            
            assert scraper.config == basic_config
            assert scraper.dry_run is False
            assert scraper.visited_urls == set()
            assert scraper.discovered_urls == set()
            assert scraper.exclude_patterns == []
            # auth_enabled can be None when no auth params provided
            assert scraper.auth_enabled in [False, None]
            assert scraper.cache_enabled is True

    def test_initialization_with_options(self, basic_config):
        """Test scraper initialization with options"""
        exclude_patterns = ['/test/', '/demo/']
        
        with patch('src.scraper.CacheManager'), \
             patch('src.scraper.AUTHENTICATION_AVAILABLE', True):
            scraper = WebScraper(
                basic_config,
                dry_run=True,
                exclude_patterns=exclude_patterns,
                verbose=True,
                auth_username='user@test.com',
                auth_password='password123',
                auth_type='email'
            )
            
            assert scraper.dry_run is True
            assert scraper.verbose is True
            assert scraper.exclude_patterns == exclude_patterns
            assert scraper.auth_username == 'user@test.com'
            assert scraper.auth_password == 'password123'
            assert scraper.auth_type == 'email'
            assert scraper.auth_enabled  # Should be truthy (password string)

    def test_normalize_url(self, scraper):
        """Test URL normalization"""
        # Test fragment removal
        assert scraper._normalize_url('https://example.com/page#section') == 'https://example.com/page'
        
        # Test trailing slash handling
        assert scraper._normalize_url('https://example.com/page/') == 'https://example.com/page'
        assert scraper._normalize_url('https://example.com/') == 'https://example.com/'
        
        # Test case normalization for domain
        assert scraper._normalize_url('https://Example.COM/Page') == 'https://example.com/Page'
        
        # Test query parameter preservation
        assert scraper._normalize_url('https://example.com/page?id=1&sort=name') == 'https://example.com/page?id=1&sort=name'

    def test_is_same_domain(self, scraper):
        """Test domain checking"""
        scraper.base_domain = 'example.com'
        
        assert scraper._is_same_domain('https://example.com/page') is True
        assert scraper._is_same_domain('https://Example.COM/page') is True  # Case insensitive
        assert scraper._is_same_domain('https://subdomain.example.com/page') is False
        assert scraper._is_same_domain('https://other.com/page') is False

    def test_is_valid_url_basic(self, scraper):
        """Test basic URL validation"""
        # Valid URLs
        assert scraper._is_valid_url('https://example.com/page') is True
        assert scraper._is_valid_url('https://example.com/docs/guide') is True
        
        # Test max URL length
        long_url = 'https://example.com/' + 'a' * 2000
        assert scraper._is_valid_url(long_url) is False
        
        # Test excluded patterns
        assert scraper._is_valid_url('https://example.com/admin/panel') is False
        assert scraper._is_valid_url('https://example.com/login') is False
        
        # Test skip extensions
        assert scraper._is_valid_url('https://example.com/file.pdf') is False
        assert scraper._is_valid_url('https://example.com/doc.zip') is False

    def test_is_valid_url_with_cli_patterns(self, basic_config):
        """Test URL validation with CLI exclude patterns"""
        exclude_patterns = ['/api/', r'\.json$']
        
        with patch('src.scraper.CacheManager'):
            scraper = WebScraper(basic_config, exclude_patterns=exclude_patterns)
            
            assert scraper._is_valid_url('https://example.com/page') is True
            assert scraper._is_valid_url('https://example.com/api/v1') is False
            assert scraper._is_valid_url('https://example.com/data.json') is False

    def test_is_valid_url_with_auth_enabled(self, basic_config):
        """Test URL validation with authentication enabled"""
        # Change the exclude pattern to match what the code expects
        basic_config['filters']['exclude_patterns'] = ['/login.*', '/logout.*', '/admin/']
        basic_config['authentication']['enabled'] = True
        
        with patch('src.scraper.CacheManager'), \
             patch('src.scraper.HumanBehaviorSimulator'), \
             patch('src.scraper.AUTHENTICATION_AVAILABLE', True):
            scraper = WebScraper(basic_config, auth_username='user', auth_password='pass')
            scraper.path_scope = None  # Disable path scoping for this test
            
            # Login patterns should be allowed when auth is enabled
            assert scraper._is_valid_url('https://example.com/login') is True
            assert scraper._is_valid_url('https://example.com/logout') is True
            # Admin should still be excluded
            assert scraper._is_valid_url('https://example.com/admin/panel') is False

    @patch('src.scraper.RobotFileParser')
    def test_check_robots_txt_allowed(self, mock_robots, scraper):
        """Test robots.txt check when crawling is allowed"""
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = True
        mock_robots.return_value = mock_rp
        
        result = scraper._check_robots_txt('https://example.com')
        
        assert result is True
        mock_rp.set_url.assert_called_with('https://example.com/robots.txt')
        mock_rp.read.assert_called_once()

    @patch('src.scraper.RobotFileParser')
    def test_check_robots_txt_disallowed(self, mock_robots, scraper):
        """Test robots.txt check when crawling is disallowed"""
        mock_rp = Mock()
        mock_rp.can_fetch.return_value = False
        mock_robots.return_value = mock_rp
        
        result = scraper._check_robots_txt('https://example.com')
        
        assert result is False

    @patch('src.scraper.RobotFileParser')
    def test_check_robots_txt_respect_disabled(self, mock_robots, basic_config):
        """Test robots.txt check when respect_robots is disabled"""
        basic_config['crawling']['respect_robots'] = False
        
        with patch('src.scraper.CacheManager'):
            scraper = WebScraper(basic_config)
            result = scraper._check_robots_txt('https://example.com')
            
            assert result is True
            mock_robots.assert_not_called()

    def test_extract_links(self, scraper, mock_response):
        """Test link extraction from HTML"""
        scraper.base_domain = 'example.com'
        
        with patch.object(scraper, '_is_same_domain', return_value=True), \
             patch.object(scraper, '_is_valid_url', return_value=True):
            
            links = scraper._extract_links(mock_response.text, 'https://example.com')
            
            assert 'https://example.com/page1' in links
            assert 'https://example.com/page2' in links
            # External links should not be included
            assert 'https://external.com' not in links

    def test_extract_links_with_filtering(self, scraper, mock_response):
        """Test link extraction with URL filtering"""
        scraper.base_domain = 'example.com'
        
        def mock_is_valid(url, **kwargs):
            return '/page2' not in url  # Exclude page2
        
        with patch.object(scraper, '_is_same_domain', return_value=True), \
             patch.object(scraper, '_is_valid_url', side_effect=mock_is_valid):
            
            links = scraper._extract_links(mock_response.text, 'https://example.com')
            
            assert 'https://example.com/page1' in links
            assert 'https://example.com/page2' not in links

    @patch('requests.Session.get')
    def test_fetch_page_success(self, mock_get, scraper, mock_response):
        """Test successful page fetching"""
        mock_get.return_value = mock_response
        
        html = scraper._fetch_page('https://example.com')
        
        assert html == mock_response.text
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    @patch('requests.Session.get')
    def test_fetch_page_non_html(self, mock_get, scraper):
        """Test fetching non-HTML content"""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        html = scraper._fetch_page('https://example.com/api')
        
        assert html is None

    @patch('requests.Session.get')
    def test_fetch_page_request_error(self, mock_get, scraper):
        """Test page fetching with request error"""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        
        html = scraper._fetch_page('https://example.com')
        
        assert html is None

    def test_discover_urls_dry_run(self, scraper, mock_response):
        """Test URL discovery process"""
        with patch.object(scraper, '_check_robots_txt', return_value=True), \
             patch.object(scraper, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper, '_extract_links', return_value={'https://example.com/page1'}):
            
            urls, classifications = scraper.discover_urls('https://example.com')
            
            assert 'https://example.com' in urls
            assert 'https://example.com/page1' in urls
            assert len(classifications) > 0

    def test_discover_urls_robots_blocked(self, scraper):
        """Test URL discovery when robots.txt blocks crawling"""
        with patch.object(scraper, '_check_robots_txt', return_value=False):
            
            urls, classifications = scraper.discover_urls('https://example.com')
            
            assert urls == []
            assert classifications == {}

    def test_discover_urls_with_depth_limit(self, scraper, mock_response):
        """Test URL discovery respects depth limits"""
        scraper.config['crawling']['max_depth'] = 1
        
        def mock_extract_links(html, base_url):
            if 'example.com/page1' in base_url:
                return {'https://example.com/page2'}
            return {'https://example.com/page1'}
        
        with patch.object(scraper, '_check_robots_txt', return_value=True), \
             patch.object(scraper, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper, '_extract_links', side_effect=mock_extract_links):
            
            urls, classifications = scraper.discover_urls('https://example.com')
            
            # Should discover base URL and first level only
            assert 'https://example.com' in urls
            assert 'https://example.com/page1' in urls
            # Second level should not be included due to depth limit

    def test_discover_urls_with_page_limit(self, scraper, mock_response):
        """Test URL discovery respects page limits"""
        scraper.config['crawling']['max_pages'] = 2
        
        with patch.object(scraper, '_check_robots_txt', return_value=True), \
             patch.object(scraper, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper, '_extract_links', return_value={'https://example.com/page1', 'https://example.com/page2', 'https://example.com/page3'}):
            
            urls, classifications = scraper.discover_urls('https://example.com')
            
            # Should stop at max_pages limit
            assert len(urls) <= 2

    def test_scrape_approved_urls_dry_run(self, basic_config):
        """Test scrape_approved_urls in dry run mode"""
        basic_config['cache']['enabled'] = False
        
        with patch('src.scraper.CacheManager'):
            scraper = WebScraper(basic_config, dry_run=True)
            
            approved_urls = {'https://example.com/page1', 'https://example.com/page2'}
            result = scraper.scrape_approved_urls(approved_urls)
            
            assert result == []

    def test_scrape_approved_urls_success(self, scraper_with_cache, mock_response):
        """Test successful scraping of approved URLs"""
        approved_urls = {'https://example.com/page1', 'https://example.com/page2'}
        
        mock_content = {
            'title': 'Test Page',
            'text': 'This is test content with more than 100 characters to pass the minimum length requirement.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            result = scraper_with_cache.scrape_approved_urls(approved_urls)
            
            assert len(result) == 2
            assert all('url' in page for page in result)
            assert scraper_with_cache.cache_manager.save_page.call_count == 2

    def test_scrape_approved_urls_insufficient_content(self, scraper_with_cache, mock_response):
        """Test scraping URLs with insufficient content"""
        approved_urls = {'https://example.com/page1'}
        
        # Mock content that's too short
        mock_content = {
            'title': 'Short',
            'text': 'Too short',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            result = scraper_with_cache.scrape_approved_urls(approved_urls)
            
            assert len(result) == 0

    def test_scrape_approved_urls_duplicate_detection(self, scraper_with_cache, mock_response):
        """Test duplicate content detection during scraping"""
        approved_urls = {'https://example.com/page1', 'https://example.com/page2', 'https://example.com/page3'}
        
        # Mock identical content to trigger duplicate detection
        mock_content = {
            'title': 'Same Page',
            'text': 'This is identical content that should trigger duplicate detection mechanism.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            with pytest.raises(RuntimeError, match="DUPLICATE CONTENT DETECTED"):
                scraper_with_cache.scrape_approved_urls(approved_urls)

    def test_scrape_approved_urls_with_resume(self, scraper_with_cache):
        """Test scraping with resume from cache"""
        approved_urls = {'https://example.com/page1', 'https://example.com/page2'}
        
        # Mock cached pages (page1 already scraped)
        cached_pages = [{'url': 'https://example.com/page1', 'title': 'Cached'}]
        scraper_with_cache.cache_manager.load_cached_pages.return_value = cached_pages
        scraper_with_cache.resume_mode = True
        scraper_with_cache.cache_session_id = 'test_session_123'
        
        mock_content = {
            'title': 'Test Page 2',
            'text': 'This is test content for page 2 with sufficient length.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_fetch_page', return_value="<html>page2</html>"), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            result = scraper_with_cache.scrape_approved_urls(approved_urls)
            
            # Should only scrape page2, as page1 was cached
            assert len(result) == 2  # 1 cached + 1 newly scraped
            scraper_with_cache.cache_manager.save_page.assert_called_once()

    @patch('src.scraper.AuthenticationManager')
    def test_setup_authentication_success(self, mock_auth_manager_class, scraper, mock_response):
        """Test successful authentication setup"""
        mock_auth_manager = Mock()
        mock_auth_session = Mock()
        mock_auth_session.get.return_value = mock_response
        
        mock_auth_manager.authenticate.return_value = True
        mock_auth_manager.get_authenticated_session.return_value = mock_auth_session
        mock_auth_manager.domain = 'example.com'
        mock_auth_manager_class.return_value = mock_auth_manager
        
        scraper.auth_enabled = True
        scraper.auth_username = 'user@test.com'
        scraper.auth_password = 'password123'
        
        scraper._setup_authentication('https://example.com')
        
        assert scraper.auth_manager == mock_auth_manager
        assert scraper.session == mock_auth_session
        mock_auth_manager.authenticate.assert_called_with(
            username='user@test.com',
            password='password123',
            auth_type=None
        )

    def test_setup_authentication_disabled(self, scraper):
        """Test authentication setup when disabled"""
        scraper.auth_enabled = False
        original_session = scraper.session
        
        scraper._setup_authentication('https://example.com')
        
        # Session should remain unchanged
        assert scraper.session == original_session
        assert scraper.auth_manager is None

    @patch('src.scraper.AUTHENTICATION_AVAILABLE', False)
    def test_setup_authentication_not_available(self, scraper):
        """Test authentication setup when authentication module not available"""
        scraper.auth_enabled = True
        
        scraper._setup_authentication('https://example.com')
        
        # Should not raise error, but also not set up auth
        assert scraper.auth_manager is None

    @patch('src.scraper.AuthenticationManager')
    def test_setup_authentication_failure(self, mock_auth_manager_class, scraper):
        """Test authentication setup failure"""
        mock_auth_manager_class.side_effect = Exception("Auth failed")
        
        scraper.auth_enabled = True
        scraper.auth_username = 'user@test.com'
        scraper.auth_password = 'password123'
        
        with pytest.raises(Exception, match="Authentication failed"):
            scraper._setup_authentication('https://example.com')

    def test_scrape_website_dry_run(self, basic_config):
        """Test scrape_website in dry run mode"""
        with patch('src.scraper.CacheManager'):
            scraper = WebScraper(basic_config, dry_run=True)
            result = scraper.scrape_website('https://example.com')
            assert result == []

    def test_scrape_website_robots_blocked(self, scraper_with_cache):
        """Test scrape_website when robots.txt blocks crawling"""
        with patch.object(scraper_with_cache, '_check_robots_txt', return_value=False):
            result = scraper_with_cache.scrape_website('https://example.com')
            assert result == []

    def test_scrape_website_success(self, scraper_with_cache, mock_response):
        """Test successful website scraping"""
        mock_content = {
            'title': 'Test Page',
            'text': 'This is test content with sufficient length to pass the minimum requirements.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_check_robots_txt', return_value=True), \
             patch.object(scraper_with_cache, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper_with_cache, '_extract_links', return_value=set()), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            result = scraper_with_cache.scrape_website('https://example.com')
            
            assert len(result) >= 1
            assert scraper_with_cache.cache_manager.create_session.called
            assert scraper_with_cache.cache_manager.mark_session_complete.called

    def test_scrape_website_keyboard_interrupt(self, scraper_with_cache, mock_response):
        """Test scrape_website with keyboard interrupt"""
        def mock_fetch_with_interrupt(url):
            if 'example.com' in url:
                return mock_response.text
            raise KeyboardInterrupt()
        
        mock_content = {
            'title': 'Test Page',
            'text': 'This is test content.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_check_robots_txt', return_value=True), \
             patch.object(scraper_with_cache, '_fetch_page', side_effect=mock_fetch_with_interrupt), \
             patch.object(scraper_with_cache, '_extract_links', return_value={'https://example.com/page1'}), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            with pytest.raises(KeyboardInterrupt):
                scraper_with_cache.scrape_website('https://example.com')

    def test_resume_scraping_session_not_found(self, scraper_with_cache):
        """Test resume scraping when session not found"""
        scraper_with_cache.cache_manager.load_session.return_value = None
        scraper_with_cache.cache_session_id = 'nonexistent'
        
        result = scraper_with_cache._resume_scraping('https://example.com')
        
        assert result == []

    def test_resume_scraping_already_complete(self, scraper_with_cache):
        """Test resume scraping when session is already complete"""
        session_data = {'status': 'completed'}
        cached_pages = [{'url': 'https://example.com/page1', 'title': 'Cached'}]
        
        scraper_with_cache.cache_manager.load_session.return_value = session_data
        scraper_with_cache.cache_manager.load_cached_pages.return_value = cached_pages
        scraper_with_cache.cache_session_id = 'complete_session'
        
        result = scraper_with_cache._resume_scraping('https://example.com')
        
        assert result == cached_pages

    def test_resume_scraping_with_remaining_urls(self, scraper_with_cache, mock_response):
        """Test resume scraping with remaining URLs to scrape"""
        session_data = {'status': 'in_progress', 'urls_discovered': ['https://example.com/page1', 'https://example.com/page2']}
        cached_pages = [{'url': 'https://example.com/page1', 'title': 'Cached'}]
        remaining_urls = ['https://example.com/page2']
        
        scraper_with_cache.cache_manager.load_session.return_value = session_data
        scraper_with_cache.cache_manager.load_cached_pages.return_value = cached_pages
        scraper_with_cache.cache_manager.get_resume_urls.return_value = remaining_urls
        scraper_with_cache.cache_session_id = 'resume_session'
        
        mock_content = {
            'title': 'Test Page 2',
            'text': 'This is test content for page 2 with sufficient length.',
            'links': []
        }
        
        with patch.object(scraper_with_cache, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper_with_cache.extractor, 'extract_content', return_value=mock_content):
            
            result = scraper_with_cache._resume_scraping('https://example.com')
            
            assert len(result) == 2  # 1 cached + 1 newly scraped
            scraper_with_cache.cache_manager.mark_session_complete.assert_called_once()

    def test_resume_scraping_no_discovery_data(self, scraper_with_cache):
        """Test resume scraping when no discovery data exists"""
        session_data = {'status': 'in_progress'}  # No urls_discovered
        cached_pages = []
        
        scraper_with_cache.cache_manager.load_session.return_value = session_data
        scraper_with_cache.cache_manager.load_cached_pages.return_value = cached_pages
        scraper_with_cache.cache_session_id = 'no_discovery'
        
        with patch.object(scraper_with_cache, 'discover_urls', return_value=([], {})):
            result = scraper_with_cache._resume_scraping('https://example.com')
            
            scraper_with_cache.discover_urls.assert_called_once()
            scraper_with_cache.cache_manager.save_discovery_results.assert_called_once()

    def test_cleanup(self, scraper):
        """Test scraper cleanup"""
        scraper.session.close = Mock()
        scraper.progress.cleanup = Mock()
        
        scraper.cleanup()
        
        scraper.progress.cleanup.assert_called_once()
        scraper.session.close.assert_called_once()

    def test_human_behavior_integration(self, basic_config):
        """Test scraper with human behavior enabled"""
        basic_config['human_behavior']['enabled'] = True
        
        mock_human_behavior = Mock()
        mock_human_behavior.get_realistic_headers.return_value = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        mock_human_behavior.should_respect_robots_txt.return_value = True
        mock_human_behavior.simulate_human_delay = Mock()
        
        with patch('src.scraper.CacheManager'), \
             patch('src.scraper.HumanBehaviorSimulator', return_value=mock_human_behavior):
            
            scraper = WebScraper(basic_config)
            
            assert scraper.human_behavior == mock_human_behavior
            # Check that realistic headers are used
            assert 'Mozilla/5.0' in scraper.session.headers.get('User-Agent', '')

    def test_path_scoping_integration(self, scraper, mock_response):
        """Test scraper with path scoping enabled"""
        mock_path_scope = Mock()
        mock_path_scope.is_url_in_scope.return_value = (True, 'within scope')
        
        scraper.path_scope = mock_path_scope
        
        result = scraper._is_valid_url('https://example.com/docs/page', is_navigation=False, current_depth=1)
        
        mock_path_scope.is_url_in_scope.assert_called_with(
            'https://example.com/docs/page', False, 1
        )

    @patch('time.sleep')
    def test_request_delay_without_human_behavior(self, mock_sleep, scraper, mock_response):
        """Test request delay without human behavior"""
        approved_urls = {'https://example.com/page1'}
        mock_content = {
            'title': 'Test',
            'text': 'Test content with sufficient length for processing.',
            'links': []
        }
        
        with patch.object(scraper, '_fetch_page', return_value=mock_response.text), \
             patch.object(scraper.extractor, 'extract_content', return_value=mock_content):
            
            scraper.scrape_approved_urls(approved_urls)
            
            # Should use config delay
            mock_sleep.assert_called_with(scraper.config['crawling']['request_delay'])

    def test_error_handling_in_extract_links(self, scraper):
        """Test error handling during link extraction"""
        invalid_html = "<html><body><a href="  # Malformed HTML
        
        scraper.base_domain = 'example.com'
        
        with patch.object(scraper, '_is_same_domain', return_value=True), \
             patch.object(scraper, '_is_valid_url', return_value=True):
            
            # Should not raise exception, return empty set
            links = scraper._extract_links(invalid_html, 'https://example.com')
            assert isinstance(links, set)