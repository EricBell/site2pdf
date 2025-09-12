"""
Unit tests for URL Preview functionality
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Set

from src.preview import URLPreview
from src.preview_cache import PreviewCache
from src.content_classifier import ContentType
from src.cache_manager import CacheManager


class TestURLPreview:
    """Test URLPreview functionality"""
    
    @pytest.fixture
    def mock_cache_manager(self, temp_dir):
        """Create mock CacheManager instance"""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.previews_dir = temp_dir / 'previews'
        cache_manager.previews_dir.mkdir(exist_ok=True)
        cache_manager.config = {'test': True}
        cache_manager._generate_session_id.return_value = 'test_session_123'
        cache_manager._save_json = Mock()
        cache_manager._load_json = Mock()
        return cache_manager
    
    @pytest.fixture
    def mock_path_scope(self):
        """Create mock PathScopeManager"""
        path_scope = Mock()
        path_scope.get_scope_summary.return_value = {
            'enabled': True,
            'starting_path': '/docs',
            'allowed_paths': ['/docs', '/help'],
            'navigation_policy': 'strict',
            'allow_siblings': True
        }
        return path_scope
    
    @pytest.fixture
    def sample_urls(self):
        """Sample URLs for testing"""
        return [
            'https://example.com/',
            'https://example.com/docs/',
            'https://example.com/docs/getting-started',
            'https://example.com/docs/api/reference',
            'https://example.com/docs/api/auth',
            'https://example.com/blog/',
            'https://example.com/blog/post-1',
            'https://example.com/about/',
            'https://example.com/help/faq',
            'https://example.com/admin/login'
        ]
    
    @pytest.fixture
    def sample_classifications(self):
        """Sample URL classifications"""
        return {
            'https://example.com/': ContentType.NAVIGATION,
            'https://example.com/docs/': ContentType.DOCUMENTATION,
            'https://example.com/docs/getting-started': ContentType.DOCUMENTATION,
            'https://example.com/docs/api/reference': ContentType.DOCUMENTATION,
            'https://example.com/docs/api/auth': ContentType.DOCUMENTATION,
            'https://example.com/blog/': ContentType.CONTENT,
            'https://example.com/blog/post-1': ContentType.CONTENT,
            'https://example.com/about/': ContentType.CONTENT,
            'https://example.com/help/faq': ContentType.DOCUMENTATION,
            'https://example.com/admin/login': ContentType.EXCLUDED
        }
    
    @pytest.fixture
    def url_preview(self, mock_cache_manager, mock_path_scope):
        """Create URLPreview instance"""
        preview = URLPreview(
            exclude_patterns=['admin/', 'login'],
            path_scope=mock_path_scope,
            cache_manager=mock_cache_manager,
            preview_session_id='test_session_123'
        )
        # Replace preview_cache with a mock for testing
        preview.preview_cache = Mock()
        return preview

    def test_initialization(self, url_preview):
        """Test URLPreview initialization"""
        assert url_preview.exclude_patterns == ['admin/', 'login']
        assert url_preview.excluded_urls == set()
        assert url_preview.approved_urls == set()
        assert url_preview.cache_enabled is True
        assert url_preview.preview_session_id == 'test_session_123'

    def test_build_url_tree(self, url_preview, sample_urls, sample_classifications):
        """Test URL tree building"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        
        # Check tree structure
        assert 'example.com' in tree
        domain_data = tree['example.com']
        
        # Check URLs are stored
        assert len(domain_data['urls']) > 0
        assert 'https://example.com/' in domain_data['urls']
        
        # Check classifications are stored
        assert domain_data['classifications']['https://example.com/'] == ContentType.NAVIGATION
        
        # Check children structure
        assert 'docs' in domain_data['children']
        docs_node = domain_data['children']['docs']
        assert 'getting-started' in docs_node['children']

    def test_exclude_patterns(self, url_preview, sample_urls):
        """Test URL exclusion by patterns"""
        tree = url_preview.build_url_tree(sample_urls)
        
        # Admin URLs should be excluded by pattern
        admin_urls = [url for url in sample_urls if 'admin' in url]
        for url in admin_urls:
            assert url_preview._is_excluded(url)

    def test_parse_selection_single_numbers(self, url_preview):
        """Test parsing single number selections"""
        result = url_preview._parse_selection("1,3,5", 10)
        assert result == [1, 3, 5]
        
        result = url_preview._parse_selection("1 3 5", 10)
        assert result == [1, 3, 5]

    def test_parse_selection_ranges(self, url_preview):
        """Test parsing range selections"""
        result = url_preview._parse_selection("5-8", 10)
        assert result == [5, 6, 7, 8]
        
        result = url_preview._parse_selection("1,3,5-7,10", 10)
        assert result == [1, 3, 5, 6, 7, 10]

    def test_parse_selection_invalid_range(self, url_preview):
        """Test parsing invalid selections"""
        with pytest.raises(ValueError, match="out of bounds"):
            url_preview._parse_selection("1-15", 10)
        
        with pytest.raises(ValueError, match="Invalid number"):
            url_preview._parse_selection("abc", 10)

    def test_exclude_path(self, url_preview, sample_urls, sample_classifications):
        """Test path exclusion functionality"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        
        initial_excluded_count = len(url_preview.excluded_urls)
        url_preview._exclude_path(tree, 'example.com/blog')
        
        # Check that blog URLs are excluded
        blog_urls = [url for url in sample_urls if '/blog' in url]
        for url in blog_urls:
            assert url in url_preview.excluded_urls
        
        assert len(url_preview.excluded_urls) > initial_excluded_count

    def test_include_path(self, url_preview, sample_urls, sample_classifications):
        """Test path inclusion functionality"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        
        # First exclude, then include
        url_preview._exclude_path(tree, 'example.com/docs')
        docs_urls = [url for url in sample_urls if '/docs' in url]
        
        # Verify exclusion
        for url in docs_urls:
            assert url in url_preview.excluded_urls
        
        # Now include back
        url_preview._include_path(tree, 'example.com/docs')
        
        # Verify inclusion
        for url in docs_urls:
            assert url not in url_preview.excluded_urls

    def test_get_approved_urls(self, url_preview, sample_urls, sample_classifications):
        """Test getting final approved URLs"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        
        # Exclude some URLs
        url_preview._exclude_path(tree, 'example.com/admin')
        
        approved_urls = url_preview._get_approved_urls(tree)
        
        # Should not contain excluded URLs
        admin_urls = [url for url in sample_urls if '/admin' in url]
        for url in admin_urls:
            assert url not in approved_urls

    def test_type_counts(self, url_preview, sample_urls, sample_classifications):
        """Test content type counting"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        domain_data = tree['example.com']
        
        type_counts = url_preview._get_type_counts(domain_data)
        
        # Should have counts for different types
        assert type_counts[ContentType.DOCUMENTATION] > 0
        assert type_counts[ContentType.CONTENT] > 0
        assert type_counts[ContentType.NAVIGATION] > 0

    def test_primary_type_detection(self, url_preview):
        """Test primary content type detection"""
        type_counts = {
            ContentType.DOCUMENTATION: 5,
            ContentType.CONTENT: 2,
            ContentType.NAVIGATION: 1,
            ContentType.TECHNICAL: 0,
            ContentType.EXCLUDED: 0
        }
        
        primary_type = url_preview._get_primary_type(type_counts)
        assert primary_type == ContentType.DOCUMENTATION

    def test_type_icon_selection(self, url_preview):
        """Test icon selection for content types"""
        assert url_preview._get_type_icon(ContentType.DOCUMENTATION, True) == "📚"
        assert url_preview._get_type_icon(ContentType.DOCUMENTATION, False) == "📖"
        assert url_preview._get_type_icon(ContentType.CONTENT, True) == "📁"
        assert url_preview._get_type_icon(ContentType.NAVIGATION, False) == "🧭"

    def test_cache_session_management(self, url_preview, sample_urls, sample_classifications):
        """Test preview session caching"""
        base_url = "https://example.com"
        
        # Mock the preview_cache methods
        url_preview.preview_cache.create_preview_session = Mock()
        url_preview.preview_cache.save_discovery_results = Mock()
        
        # Clear preview_session_id to test creation path
        url_preview.preview_session_id = None
        
        # Test saving session
        session_id = url_preview.save_preview_session(
            base_url, sample_urls, sample_classifications
        )
        
        assert session_id is not None
        assert url_preview.preview_cache.create_preview_session.called
        assert url_preview.preview_cache.save_discovery_results.called

    def test_load_preview_session(self, url_preview):
        """Test loading preview session"""
        # Mock session data
        session_data = {
            'session_id': 'test_session_123',
            'approval_state': {
                'excluded': [{'url': 'https://example.com/admin'}],
                'approved': [{'url': 'https://example.com/docs'}]
            }
        }
        
        # Mock the load_preview_session method
        url_preview.preview_cache.load_preview_session = Mock(return_value=session_data)
        
        result = url_preview.load_preview_session('test_session_123')
        
        assert result is True
        assert 'https://example.com/admin' in url_preview.excluded_urls
        assert 'https://example.com/docs' in url_preview.approved_urls

    @patch('click.echo')
    def test_display_tree_output(self, mock_echo, url_preview, sample_urls, sample_classifications):
        """Test tree display functionality"""
        tree = url_preview.build_url_tree(sample_urls, sample_classifications)
        items = url_preview.display_tree(tree)
        
        # Should return selectable items
        assert len(items) > 0
        
        # Should have called click.echo for display
        assert mock_echo.called
        
        # Items should have correct structure (name, path, indent)
        for item in items:
            assert len(item) >= 3
            assert isinstance(item[0], str)  # name
            assert isinstance(item[1], str)  # path
            assert isinstance(item[2], int)  # indent

    def test_save_and_load_approved_urls(self, url_preview, temp_dir):
        """Test saving and loading approved URLs to file"""
        approved_urls = {'https://example.com/page1', 'https://example.com/page2'}
        url_preview.excluded_urls = {'https://example.com/excluded'}
        
        filepath = str(temp_dir / 'approved_urls.json')
        
        # Test saving
        with patch('click.echo'):
            url_preview.save_approved_urls(approved_urls, filepath)
        
        # Verify file was created
        assert Path(filepath).exists()
        
        # Test loading
        with patch('click.echo'):
            loaded_urls = url_preview.load_approved_urls(filepath)
        
        assert loaded_urls == approved_urls
        assert url_preview.excluded_urls == {'https://example.com/excluded'}


class TestPreviewCache:
    """Test PreviewCache functionality"""
    
    @pytest.fixture
    def preview_cache(self, temp_dir):
        """Create PreviewCache instance with temp directory"""
        cache_manager = Mock(spec=CacheManager)
        cache_manager.previews_dir = temp_dir / 'previews'
        cache_manager.previews_dir.mkdir(exist_ok=True)
        cache_manager._save_json = self._mock_save_json
        cache_manager._load_json = self._mock_load_json
        
        # Store data for mocking
        self.json_storage = {}
        
        return PreviewCache(cache_manager)
    
    def _mock_save_json(self, filepath, data):
        """Mock save JSON to memory storage"""
        self.json_storage[str(filepath)] = data
    
    def _mock_load_json(self, filepath):
        """Mock load JSON from memory storage"""
        data = self.json_storage.get(str(filepath))
        if data is None:
            raise FileNotFoundError(f"No data for {filepath}")
        return data

    def test_create_preview_session(self, preview_cache):
        """Test creating preview session"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        config = {"test": True}
        
        result = preview_cache.create_preview_session(session_id, base_url, config)
        
        assert result == session_id
        
        # Verify session data was saved
        preview_file = str(preview_cache.cache_manager.previews_dir / session_id / "preview.json")
        assert preview_file in self.json_storage
        
        preview_data = self.json_storage[preview_file]
        assert preview_data["session_id"] == session_id
        assert preview_data["base_url"] == base_url
        assert preview_data["status"] == "in_progress"

    def test_save_discovery_results(self, preview_cache):
        """Test saving URL discovery results"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        
        # Create session first
        preview_cache.create_preview_session(session_id, base_url)
        
        urls = ["https://example.com/page1", "https://example.com/page2"]
        classifications = {
            "https://example.com/page1": ContentType.CONTENT,
            "https://example.com/page2": ContentType.DOCUMENTATION
        }
        
        result = preview_cache.save_discovery_results(session_id, urls, classifications)
        
        assert result is True
        
        # Verify discovery data was saved
        discovery_file = str(preview_cache.cache_manager.previews_dir / session_id / "discovery.json")
        assert discovery_file in self.json_storage
        
        discovery_data = self.json_storage[discovery_file]
        assert discovery_data["urls"] == urls
        assert len(discovery_data["classifications"]) == 2

    def test_save_user_decision(self, preview_cache):
        """Test saving user approval/exclusion decisions"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        url = "https://example.com/page1"
        
        # Setup session with pending URL
        preview_cache.create_preview_session(session_id, base_url)
        preview_cache.save_discovery_results(session_id, [url])
        
        # Save approval decision
        result = preview_cache.save_user_decision(session_id, url, "approve", "good content")
        
        assert result is True
        
        # Verify decision was saved
        approval_file = str(preview_cache.cache_manager.previews_dir / session_id / "approved_urls.json")
        approval_data = self.json_storage[approval_file]
        
        assert len(approval_data["approved"]) == 1
        assert approval_data["approved"][0]["url"] == url
        assert approval_data["approved"][0]["reason"] == "good content"

    def test_save_bulk_decisions(self, preview_cache):
        """Test saving multiple decisions at once"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        urls = ["https://example.com/page1", "https://example.com/page2"]
        
        # Setup session
        preview_cache.create_preview_session(session_id, base_url)
        preview_cache.save_discovery_results(session_id, urls)
        
        decisions = [
            {"url": urls[0], "action": "approve", "reason": "good"},
            {"url": urls[1], "action": "exclude", "reason": "bad"}
        ]
        
        saved_count = preview_cache.save_bulk_decisions(session_id, decisions)
        
        assert saved_count == 2
        
        # Verify both decisions were saved
        approval_file = str(preview_cache.cache_manager.previews_dir / session_id / "approved_urls.json")
        approval_data = self.json_storage[approval_file]
        
        assert len(approval_data["approved"]) == 1
        assert len(approval_data["excluded"]) == 1

    def test_load_discovery_results(self, preview_cache):
        """Test loading discovery results"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        urls = ["https://example.com/page1"]
        classifications = {"https://example.com/page1": ContentType.CONTENT}
        
        # Setup and save discovery results
        preview_cache.create_preview_session(session_id, base_url)
        preview_cache.save_discovery_results(session_id, urls, classifications)
        
        # Load discovery results
        result = preview_cache.load_discovery_results(session_id)
        
        assert result is not None
        assert result["urls"] == urls
        assert len(result["classifications"]) == 1

    def test_get_approved_excluded_urls(self, preview_cache):
        """Test getting approved and excluded URLs"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        urls = ["https://example.com/page1", "https://example.com/page2"]
        
        # Setup session and make decisions
        preview_cache.create_preview_session(session_id, base_url)
        preview_cache.save_discovery_results(session_id, urls)
        preview_cache.save_user_decision(session_id, urls[0], "approve")
        preview_cache.save_user_decision(session_id, urls[1], "exclude")
        
        approved_urls = preview_cache.get_approved_urls(session_id)
        excluded_urls = preview_cache.get_excluded_urls(session_id)
        
        assert urls[0] in approved_urls
        assert urls[1] in excluded_urls

    def test_mark_preview_complete(self, preview_cache):
        """Test marking preview session as complete"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        
        # Setup session
        preview_cache.create_preview_session(session_id, base_url)
        
        result = preview_cache.mark_preview_complete(session_id)
        
        assert result is True
        
        # Verify status was updated
        preview_file = str(preview_cache.cache_manager.previews_dir / session_id / "preview.json")
        preview_data = self.json_storage[preview_file]
        assert preview_data["status"] == "completed"
        assert "completed_at" in preview_data

    def test_list_preview_sessions(self, preview_cache):
        """Test listing preview sessions"""
        # Create multiple sessions
        sessions = ["session1", "session2", "session3"]
        for session_id in sessions:
            preview_cache.create_preview_session(session_id, f"https://example{session_id}.com")
        
        # Mark one as completed
        preview_cache.mark_preview_complete("session2")
        
        # List all sessions
        all_sessions = preview_cache.list_preview_sessions()
        assert len(all_sessions) == 3
        
        # List only completed sessions
        completed_sessions = preview_cache.list_preview_sessions(status="completed")
        assert len(completed_sessions) == 1
        assert completed_sessions[0]["session_id"] == "session2"

    def test_export_approved_urls(self, preview_cache, temp_dir):
        """Test exporting approved URLs to file"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        url = "https://example.com/page1"
        
        # Setup session with approved URL
        preview_cache.create_preview_session(session_id, base_url)
        preview_cache.save_discovery_results(session_id, [url])
        preview_cache.save_user_decision(session_id, url, "approve")
        
        output_file = str(temp_dir / "approved_urls.json")
        result = preview_cache.export_approved_urls(session_id, output_file)
        
        assert result is True
        
        # Verify file was created with correct content
        with open(output_file, 'r') as f:
            export_data = json.load(f)
        
        assert export_data["session_id"] == session_id
        assert url in export_data["approved_urls"]
        assert export_data["total_urls"] == 1

    def test_classification_serialization(self, preview_cache):
        """Test ContentType enum serialization/deserialization"""
        classifications = {
            "url1": ContentType.CONTENT,
            "url2": ContentType.DOCUMENTATION
        }
        
        # Test serialization
        serialized = preview_cache._serialize_classifications(classifications)
        assert isinstance(serialized["url1"], str)
        assert isinstance(serialized["url2"], str)
        
        # Test deserialization
        deserialized = preview_cache._deserialize_classifications(serialized)
        assert deserialized["url1"] == ContentType.CONTENT
        assert deserialized["url2"] == ContentType.DOCUMENTATION

    def test_save_tree_state_and_filters(self, preview_cache):
        """Test saving UI state"""
        session_id = "test_session_123"
        base_url = "https://example.com"
        
        preview_cache.create_preview_session(session_id, base_url)
        
        # Test saving tree state
        tree_state = {
            "expanded_nodes": ["docs", "api"],
            "selected_nodes": ["getting-started"],
            "current_view": "detailed"
        }
        
        result = preview_cache.save_tree_state(session_id, tree_state)
        assert result is True
        
        # Test saving filters
        filters = {
            "exclude_patterns": ["admin", "test"],
            "content_types": ["documentation"],
            "search_term": "getting started"
        }
        
        result = preview_cache.save_filters(session_id, filters)
        assert result is True

    def test_find_compatible_preview(self, preview_cache):
        """Test finding compatible preview sessions"""
        base_url = "https://example.com"
        config_hash = "abc123"
        
        # Create session with specific config
        session_id = "test_session_123"
        config = {"config_hash": config_hash}
        preview_cache.create_preview_session(session_id, base_url, config)
        
        # Mock the methods that would be called
        preview_cache.list_preview_sessions = Mock(return_value=[
            {"session_id": session_id}
        ])
        preview_cache.load_preview_session = Mock(return_value={
            "base_url": base_url,
            "config": config
        })
        
        # Should find compatible session
        compatible_session = preview_cache.find_compatible_preview(base_url, config_hash)
        assert compatible_session == session_id
        
        # Should not find incompatible session
        incompatible_session = preview_cache.find_compatible_preview("https://other.com", config_hash)
        assert incompatible_session is None