"""
Cache Manager for Site2PDF

Provides comprehensive caching for scraped content and preview sessions.
Enables robust resume functionality and prevents data loss during crashes.
"""

import os
import json
import gzip
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, quote_plus


class CacheManager:
    """
    Manages caching of scraped content and preview sessions.
    
    Features:
    - Incremental page caching during scraping
    - Preview session persistence
    - Session resume capability
    - Automatic cleanup and compression
    - Cache validation and recovery
    """
    
    def __init__(self, cache_dir: str = "cache", config: Dict[str, Any] = None):
        self.cache_dir = Path(cache_dir)
        self.sessions_dir = self.cache_dir / "sessions"
        self.previews_dir = self.cache_dir / "previews"
        self.config = config or {}
        self.cache_config = self.config.get('cache', {})
        
        # Ensure cache directories exist
        self.cache_dir.mkdir(exist_ok=True)
        self.sessions_dir.mkdir(exist_ok=True)
        self.previews_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        # Handle compression config - can be boolean or dict
        compression_config = self.cache_config.get('compression', True)
        if isinstance(compression_config, bool):
            self.compression_enabled = compression_config
            self.compression_level = self.cache_config.get('compression_level', 6)
        else:
            self.compression_enabled = compression_config.get('enabled', True)
            self.compression_level = compression_config.get('level', 6)
    
    def _generate_session_id(self, base_url: str, config_hash: str = None) -> str:
        """Generate unique session ID based on URL and timestamp"""
        domain = urlparse(base_url).netloc.replace('www.', '').replace('.', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Include config hash for uniqueness
        if config_hash is None:
            config_hash = self._hash_config(self.config)[:8]
        
        return f"{domain}_{timestamp}_{config_hash}"
    
    def _hash_config(self, config: Dict[str, Any]) -> str:
        """Generate hash of relevant configuration for cache invalidation"""
        # Only include settings that affect scraping results
        relevant_config = {
            'crawling': config.get('crawling', {}),
            'content': config.get('content', {}),
            'filters': config.get('filters', {}),
            'path_scoping': config.get('path_scoping', {})
        }
        config_str = json.dumps(relevant_config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _hash_url(self, url: str) -> str:
        """Generate hash for URL to use as filename"""
        return hashlib.sha256(url.encode()).hexdigest()
    
    def _save_json(self, filepath: Path, data: Any, compress: bool = None) -> None:
        """Save data as JSON with optional compression"""
        if compress is None:
            compress = self.compression_enabled
        
        json_data = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        if compress:
            with gzip.open(f"{filepath}.gz", 'wt', encoding='utf-8') as f:
                f.write(json_data)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_data)
    
    def _load_json(self, filepath: Path) -> Any:
        """Load JSON data with automatic compression detection"""
        # Try compressed version first
        compressed_path = Path(f"{filepath}.gz")
        if compressed_path.exists():
            with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        
        # Fall back to uncompressed
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        raise FileNotFoundError(f"Cache file not found: {filepath}")
    
    def create_session(self, base_url: str, config: Dict[str, Any] = None) -> str:
        """
        Create new cache session for scraping.
        
        Returns:
            str: Session ID for the created session
        """
        if config is None:
            config = self.config
        
        config_hash = self._hash_config(config)
        session_id = self._generate_session_id(base_url, config_hash)
        
        # Create session directory structure
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(exist_ok=True)
        (session_dir / "pages").mkdir(exist_ok=True)
        (session_dir / "pages" / "images").mkdir(exist_ok=True)
        
        # Create session metadata
        session_data = {
            "session_id": session_id,
            "base_url": base_url,
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "status": "active",
            "config_hash": config_hash,
            "config": config,
            "pages_scraped": 0,
            "pages_total": 0,
            "urls_discovered": [],
            "urls_scraped": [],
            "urls_failed": [],
            "cache_version": "1.0"
        }
        
        self._save_json(session_dir / "session.json", session_data)
        
        self.logger.info(f"Created cache session: {session_id}")
        return session_id
    
    def save_page(self, session_id: str, page_data: Dict[str, Any]) -> bool:
        """
        Save scraped page data to cache.
        
        Args:
            session_id: Session identifier
            page_data: Scraped page data
            
        Returns:
            bool: True if saved successfully
        """
        try:
            session_dir = self.sessions_dir / session_id
            if not session_dir.exists():
                self.logger.error(f"Session directory not found: {session_id}")
                return False
            
            url = page_data.get('url')
            if not url:
                self.logger.error("Page data missing URL")
                return False
            
            # Add cache metadata
            page_data_with_cache = page_data.copy()
            page_data_with_cache.update({
                "cached_at": datetime.now().isoformat(),
                "session_id": session_id,
                "cache_version": "1.0"
            })
            
            # Save page data
            url_hash = self._hash_url(url)
            page_file = session_dir / "pages" / f"{url_hash}.json"
            self._save_json(page_file, page_data_with_cache)
            
            # Update session metadata
            self._update_session_progress(session_id, url, "scraped")
            
            self.logger.debug(f"Cached page: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache page {page_data.get('url', 'unknown')}: {e}")
            return False
    
    def save_discovery_results(self, session_id: str, urls: List[str], classifications: Dict[str, Any] = None) -> bool:
        """
        Save URL discovery results to cache.
        
        Args:
            session_id: Session identifier
            urls: List of discovered URLs
            classifications: URL classifications if available
            
        Returns:
            bool: True if saved successfully
        """
        try:
            session_dir = self.sessions_dir / session_id
            if not session_dir.exists():
                return False
            
            discovery_data = {
                "discovered_at": datetime.now().isoformat(),
                "urls": urls,
                "classifications": classifications or {},
                "total_urls": len(urls)
            }
            
            self._save_json(session_dir / "discovery.json", discovery_data)
            
            # Update session metadata
            session_file = session_dir / "session.json"
            session_data = self._load_json(session_file)
            session_data["urls_discovered"] = urls
            session_data["pages_total"] = len(urls)
            session_data["last_modified"] = datetime.now().isoformat()
            self._save_json(session_file, session_data)
            
            self.logger.info(f"Cached discovery results: {len(urls)} URLs")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache discovery results: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load cached session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict containing session data or None if not found
        """
        try:
            session_dir = self.sessions_dir / session_id
            if not session_dir.exists():
                return None
            
            session_data = self._load_json(session_dir / "session.json")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def load_cached_pages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Load all cached pages for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of cached page data
        """
        cached_pages = []
        try:
            session_dir = self.sessions_dir / session_id
            pages_dir = session_dir / "pages"
            
            if not pages_dir.exists():
                return cached_pages
            
            for page_file in pages_dir.glob("*.json*"):
                if page_file.stem.endswith('.json'):
                    # Skip .json.gz files, they'll be handled by the .gz check
                    continue
                    
                try:
                    page_data = self._load_json(page_file)
                    cached_pages.append(page_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load cached page {page_file}: {e}")
            
            # Sort by URL for consistent ordering
            cached_pages.sort(key=lambda x: x.get('url', ''))
            return cached_pages
            
        except Exception as e:
            self.logger.error(f"Failed to load cached pages for session {session_id}: {e}")
            return cached_pages
    
    def get_resume_urls(self, session_id: str, all_urls: List[str]) -> List[str]:
        """
        Get list of URLs that still need to be scraped.
        
        Args:
            session_id: Session identifier
            all_urls: Complete list of URLs from discovery
            
        Returns:
            List of URLs that haven't been scraped yet
        """
        try:
            session_data = self.load_session(session_id)
            if not session_data:
                return all_urls
            
            scraped_urls = set(session_data.get('urls_scraped', []))
            remaining_urls = [url for url in all_urls if url not in scraped_urls]
            
            self.logger.info(f"Resume session {session_id}: {len(scraped_urls)} completed, {len(remaining_urls)} remaining")
            return remaining_urls
            
        except Exception as e:
            self.logger.error(f"Failed to get resume URLs: {e}")
            return all_urls
    
    def _update_session_progress(self, session_id: str, url: str, status: str) -> None:
        """Update session progress tracking"""
        try:
            session_dir = self.sessions_dir / session_id
            session_file = session_dir / "session.json"
            
            session_data = self._load_json(session_file)
            
            if status == "scraped":
                if url not in session_data.get('urls_scraped', []):
                    session_data.setdefault('urls_scraped', []).append(url)
                    session_data['pages_scraped'] = len(session_data['urls_scraped'])
            elif status == "failed":
                if url not in session_data.get('urls_failed', []):
                    session_data.setdefault('urls_failed', []).append(url)
            
            session_data['last_modified'] = datetime.now().isoformat()
            self._save_json(session_file, session_data)
            
        except Exception as e:
            self.logger.error(f"Failed to update session progress: {e}")
    
    def mark_session_complete(self, session_id: str) -> None:
        """Mark session as completed"""
        try:
            session_dir = self.sessions_dir / session_id
            session_file = session_dir / "session.json"
            
            session_data = self._load_json(session_file)
            session_data['status'] = 'completed'
            session_data['completed_at'] = datetime.now().isoformat()
            session_data['last_modified'] = datetime.now().isoformat()
            
            self._save_json(session_file, session_data)
            self.logger.info(f"Marked session complete: {session_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to mark session complete: {e}")
    
    def list_sessions(self, status: str = None) -> List[Dict[str, Any]]:
        """
        List available cache sessions.
        
        Args:
            status: Filter by status (active, completed, failed)
            
        Returns:
            List of session summaries
        """
        sessions = []
        try:
            for session_dir in self.sessions_dir.iterdir():
                if not session_dir.is_dir():
                    continue
                
                try:
                    session_data = self._load_json(session_dir / "session.json")
                    
                    if status and session_data.get('status') != status:
                        continue
                    
                    # Calculate cache size
                    cache_size = sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file())
                    
                    summary = {
                        "session_id": session_data.get('session_id'),
                        "base_url": session_data.get('base_url'),
                        "status": session_data.get('status'),
                        "created_at": session_data.get('created_at'),
                        "last_modified": session_data.get('last_modified'),
                        "pages_scraped": session_data.get('pages_scraped', 0),
                        "pages_total": session_data.get('pages_total', 0),
                        "cache_size": cache_size,
                        "cache_size_mb": round(cache_size / (1024 * 1024), 2)
                    }
                    sessions.append(summary)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load session {session_dir.name}: {e}")
            
            # Sort by last modified, newest first
            sessions.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return sessions
    
    def cleanup_old_sessions(self, max_age_days: int = 30, keep_completed: int = 10) -> int:
        """
        Clean up old cache sessions.
        
        Args:
            max_age_days: Remove sessions older than this many days
            keep_completed: Always keep this many most recent completed sessions
            
        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            sessions = self.list_sessions()
            
            # Separate completed and other sessions
            completed_sessions = [s for s in sessions if s.get('status') == 'completed']
            other_sessions = [s for s in sessions if s.get('status') != 'completed']
            
            # Keep most recent completed sessions
            completed_sessions.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
            sessions_to_keep = set(s['session_id'] for s in completed_sessions[:keep_completed])
            
            for session in sessions:
                session_id = session['session_id']
                last_modified = datetime.fromisoformat(session.get('last_modified', ''))
                
                # Skip if we want to keep this session
                if session_id in sessions_to_keep:
                    continue
                
                # Remove if too old
                if last_modified < cutoff_date:
                    session_dir = self.sessions_dir / session_id
                    if session_dir.exists():
                        shutil.rmtree(session_dir)
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up old session: {session_id}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup sessions: {e}")
            return cleaned_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            sessions = self.list_sessions()
            total_size = sum(s.get('cache_size', 0) for s in sessions)
            
            stats = {
                "total_sessions": len(sessions),
                "active_sessions": len([s for s in sessions if s.get('status') == 'active']),
                "completed_sessions": len([s for s in sessions if s.get('status') == 'completed']),
                "failed_sessions": len([s for s in sessions if s.get('status') == 'failed']),
                "total_cache_size": total_size,
                "total_cache_size_mb": round(total_size / (1024 * 1024), 2),
                "cache_directory": str(self.cache_dir),
                "compression_enabled": self.compression_enabled
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    def find_compatible_session(self, base_url: str, config: Dict[str, Any] = None) -> Optional[str]:
        """
        Find existing session compatible with current scraping parameters.
        
        Args:
            base_url: Base URL being scraped
            config: Current configuration
            
        Returns:
            Session ID of compatible session or None
        """
        if config is None:
            config = self.config
        
        config_hash = self._hash_config(config)
        
        sessions = self.list_sessions(status='active')
        for session in sessions:
            if (session.get('base_url') == base_url and 
                session.get('config_hash') == config_hash):
                return session['session_id']
        
        return None