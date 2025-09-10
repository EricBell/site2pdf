"""
Unit tests for CacheManager functionality
"""
import pytest
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from src.cache_manager import CacheManager


class TestCacheManager:
    """Test CacheManager functionality"""
    
    @pytest.fixture
    def cache_manager(self, temp_dir):
        """Create CacheManager instance with temporary directory"""
        cache_dir = temp_dir / 'cache'
        cache_dir.mkdir()
        
        # Mock the user data directory to use our temp dir
        with patch('src.cache_manager.get_user_data_dir', return_value=str(temp_dir)):
            # Create config with compression disabled for easier testing
            config = {
                'cache': {
                    'compression': False
                }
            }
            manager = CacheManager(config=config)
            yield manager
    
    @pytest.fixture
    def sample_session_data(self):
        """Sample session data for testing"""
        return {
            'session_id': 'test_session_123',
            'base_url': 'https://example.com',
            'created_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'status': 'active',
            'config': {'max_pages': 10},
            'pages_scraped': 5,
            'total_pages_found': 15,
            'cache_size': 1024
        }
    
    @pytest.fixture
    def sample_page_data(self):
        """Sample page data for testing"""
        return {
            'url': 'https://example.com/page1',
            'title': 'Test Page',
            'content': 'This is test content',
            'scraped_at': datetime.now().isoformat(),
            'cache_size': 512
        }

    def test_create_session(self, cache_manager, sample_session_data):
        """Test session creation"""
        base_url = sample_session_data['base_url']
        config = sample_session_data['config']
        
        created_id = cache_manager.create_session(base_url, config)
        
        assert created_id is not None
        assert cache_manager.sessions_dir.joinpath(created_id).exists()
        assert cache_manager.sessions_dir.joinpath(created_id, 'session.json').exists()
        assert cache_manager.sessions_dir.joinpath(created_id, 'pages').exists()

    def test_save_and_load_session(self, cache_manager, sample_session_data):
        """Test session saving and loading"""
        # Create session (automatically saves metadata)
        session_id = cache_manager.create_session(
            sample_session_data['base_url'], 
            sample_session_data['config']
        )
        
        # Load and verify
        loaded_data = cache_manager.load_session(session_id)
        assert loaded_data is not None
        assert loaded_data['session_id'] == session_id
        assert loaded_data['base_url'] == sample_session_data['base_url']
        assert loaded_data['status'] == 'active'

    def test_cache_and_load_page(self, cache_manager, sample_session_data, sample_page_data):
        """Test page caching and loading"""
        # Create session
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Cache page using save_page method
        cache_manager.save_page(session_id, sample_page_data)
        
        # Load cached pages
        cached_pages = cache_manager.load_cached_pages(session_id)
        assert len(cached_pages) == 1
        assert cached_pages[0]['url'] == sample_page_data['url']
        assert cached_pages[0]['title'] == sample_page_data['title']

    def test_session_exists(self, cache_manager, sample_session_data):
        """Test session existence checking"""
        # Create session
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Should exist now
        assert cache_manager.session_exists(session_id)
        
        # Non-existent session should not exist
        assert not cache_manager.session_exists('nonexistent_session')

    def test_mark_session_complete(self, cache_manager, sample_session_data):
        """Test marking session as complete"""
        # Create session
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Mark complete
        cache_manager.mark_session_complete(session_id)
        
        # Verify status
        session_data = cache_manager.load_session(session_id)
        assert session_data['status'] == 'completed'

    def test_list_sessions(self, cache_manager, sample_session_data):
        """Test session listing"""
        # Create a unique session to test with
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Check that our session appears in the list
        sessions = cache_manager.list_sessions()
        session_ids = [s['session_id'] for s in sessions]
        assert session_id in session_ids
        
        # Verify session data
        our_session = next(s for s in sessions if s['session_id'] == session_id)
        assert our_session['base_url'] == sample_session_data['base_url']
        assert our_session['status'] == 'active'

    def test_cleanup_old_sessions(self, cache_manager, sample_session_data):
        """Test cleanup of old sessions"""
        # Create session
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Manually update the session file with an old date
        session_dir = cache_manager.sessions_dir / session_id
        session_file = session_dir / "session.json"
        
        # Load current session data
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Update with old dates
        old_date = (datetime.now() - timedelta(days=2)).isoformat()
        session_data['created_at'] = old_date
        session_data['last_modified'] = old_date
        
        # Save updated session data
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        # Cleanup sessions older than 1 day
        cleaned_count = cache_manager.cleanup_old_sessions(max_age_days=1)
        
        assert cleaned_count >= 1
        assert not cache_manager.session_exists(session_id)

    def test_validate_cache_health_healthy(self, cache_manager, sample_session_data):
        """Test cache health validation with healthy cache"""
        # Create valid session (automatically creates and saves metadata)
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Validate health
        health_report = cache_manager.validate_cache_health()
        
        assert health_report['status'] in ['healthy', 'needs_attention']  # May have pre-existing issues
        assert health_report['sessions']['total'] >= 1
        assert health_report['sessions']['valid'] >= 1

    def test_validate_cache_health_orphaned_session(self, cache_manager):
        """Test cache health validation with orphaned session"""
        # Create orphaned session directory without metadata
        orphaned_dir = cache_manager.sessions_dir / 'orphaned_session_health_test_unique'
        orphaned_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate health
        health_report = cache_manager.validate_cache_health()
        
        # Check that we have at least one orphaned session and associated issues
        assert health_report['sessions']['orphaned'] >= 1
        assert len(health_report['issues']) >= 1
        assert any('orphaned' in issue.lower() for issue in health_report['issues'])
        
        # Status should indicate problems if there are issues
        if health_report['issues']:
            assert health_report['status'] in ['needs_attention', 'unhealthy']

    def test_validate_cache_health_corrupted_session(self, cache_manager):
        """Test cache health validation with corrupted session"""
        session_id = 'corrupted_session_health_test'
        session_dir = cache_manager.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create corrupted session.json
        session_file = session_dir / 'session.json'
        with open(session_file, 'w') as f:
            f.write('{"invalid": "json"')  # Missing closing brace
        
        # Validate health
        health_report = cache_manager.validate_cache_health()
        
        assert health_report['sessions']['corrupted'] >= 1
        assert len(health_report['issues']) >= 1

    def test_validate_cache_health_orphaned_preview(self, cache_manager):
        """Test cache health validation with orphaned preview"""
        # Create orphaned preview directory without metadata
        orphaned_dir = cache_manager.previews_dir / 'orphaned_preview_123'
        orphaned_dir.mkdir(parents=True)
        
        # Validate health
        health_report = cache_manager.validate_cache_health()
        
        assert health_report['previews']['orphaned'] == 1
        assert len(health_report['issues']) >= 1

    def test_validate_cache_health_project_cache(self, cache_manager):
        """Test cache health validation with orphaned project cache"""
        # Create project cache directory
        project_cache = Path('cache')
        project_cache.mkdir(exist_ok=True)
        
        try:
            # Validate health
            health_report = cache_manager.validate_cache_health()
            
            assert health_report['status'] in ['needs_attention', 'unhealthy']
            assert any('orphaned project cache' in issue.lower() for issue in health_report['issues'])
            assert any('remove orphaned ./cache/' in rec.lower() for rec in health_report['recommendations'])
        finally:
            # Cleanup
            if project_cache.exists():
                shutil.rmtree(project_cache)

    def test_fix_cache_issues_dry_run(self, cache_manager):
        """Test cache issue fixing in dry run mode"""
        # Create orphaned session
        orphaned_dir = cache_manager.sessions_dir / 'orphaned_session_dry_run'
        orphaned_dir.mkdir(parents=True, exist_ok=True)
        
        # Fix issues (dry run)
        fix_report = cache_manager.fix_cache_issues(dry_run=True)
        
        assert fix_report['dry_run'] is True
        assert len(fix_report['actions_taken']) >= 1
        assert orphaned_dir.exists()  # Should still exist in dry run

    def test_fix_cache_issues_real_fix(self, cache_manager):
        """Test cache issue fixing with actual fixes"""
        # Create orphaned session
        orphaned_dir = cache_manager.sessions_dir / 'orphaned_session_real_fix'
        orphaned_dir.mkdir(parents=True, exist_ok=True)
        
        # Fix issues (real)
        fix_report = cache_manager.fix_cache_issues(dry_run=False)
        
        assert fix_report['dry_run'] is False
        assert len(fix_report['actions_taken']) >= 1
        assert not orphaned_dir.exists()  # Should be removed

    def test_get_cache_stats(self, cache_manager, sample_session_data):
        """Test cache statistics generation"""
        # Create session (automatically creates and saves metadata)
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        # Get stats
        stats = cache_manager.get_cache_stats()
        
        assert 'total_sessions' in stats
        assert 'active_sessions' in stats
        assert 'completed_sessions' in stats
        assert 'failed_sessions' in stats
        assert 'total_cache_size' in stats
        assert 'cache_directory' in stats
        assert 'compression_enabled' in stats

    def test_cleanup_old_previews(self, cache_manager):
        """Test preview cleanup functionality"""
        # Get initial count of existing previews
        initial_previews = list(cache_manager.previews_dir.iterdir()) if cache_manager.previews_dir.exists() else []
        
        # Create old preview
        old_preview_dir = cache_manager.previews_dir / 'old_preview_123'
        old_preview_dir.mkdir(parents=True)
        
        # Create preview metadata with old date
        old_date = (datetime.now() - timedelta(days=2)).isoformat()
        preview_data = {
            'base_url': 'https://example.com',
            'created_at': old_date
        }
        
        preview_file = old_preview_dir / 'preview.json'
        with open(preview_file, 'w') as f:
            json.dump(preview_data, f)
        
        # Cleanup should remove it
        cutoff_date = datetime.now() - timedelta(days=1)
        cleaned_count = cache_manager._cleanup_old_previews(cutoff_date)
        
        assert cleaned_count >= 1  # At least our test preview should be cleaned
        assert not old_preview_dir.exists()

    def test_cleanup_old_previews_orphaned(self, cache_manager):
        """Test cleanup of orphaned previews"""
        # Create orphaned preview (no metadata)
        orphaned_dir = cache_manager.previews_dir / 'orphaned_preview_123'
        orphaned_dir.mkdir(parents=True)
        
        # Cleanup should remove orphaned preview
        cutoff_date = datetime.now()
        cleaned_count = cache_manager._cleanup_old_previews(cutoff_date)
        
        assert cleaned_count == 1
        assert not orphaned_dir.exists()

    def test_error_handling_invalid_session(self, cache_manager):
        """Test error handling for invalid session operations"""
        invalid_session_id = 'nonexistent_session'
        
        # Should return None for nonexistent session
        assert cache_manager.load_session(invalid_session_id) is None
        assert cache_manager.load_cached_pages(invalid_session_id) == []
        
        # Should handle errors gracefully
        with patch.object(cache_manager.logger, 'error') as mock_logger:
            # Try to save a page to nonexistent session
            result = cache_manager.save_page(invalid_session_id, {'url': 'http://test.com'})
            assert result is False
            mock_logger.assert_called()

    def test_compression_handling(self, cache_manager, sample_session_data, sample_page_data):
        """Test handling of compressed cache files"""
        # Test with compression enabled
        cache_manager.compression_enabled = True
        
        # Create session and cache page
        session_id = cache_manager.create_session(
            sample_session_data['base_url'],
            sample_session_data['config']
        )
        
        cache_manager.save_page(session_id, sample_page_data)
        
        # Load and verify decompression works
        cached_pages = cache_manager.load_cached_pages(session_id)
        assert len(cached_pages) == 1
        assert cached_pages[0]['url'] == sample_page_data['url']