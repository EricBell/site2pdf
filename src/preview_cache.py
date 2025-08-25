"""
Preview Cache Manager

Handles persistence of preview sessions, allowing users to save and resume
their URL approval/exclusion decisions across sessions.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from urllib.parse import urlparse

try:
    from .cache_manager import CacheManager
except ImportError:
    from cache_manager import CacheManager


class PreviewCache:
    """
    Manages preview session caching and persistence.
    
    Features:
    - Save/resume preview sessions
    - Persistent URL approval/exclusion state
    - Tree view state preservation
    - Filter and search state recovery
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.previews_dir = cache_manager.previews_dir
        self.logger = logging.getLogger(__name__)
    
    def create_preview_session(self, session_id: str, base_url: str, config: Dict[str, Any] = None) -> str:
        """
        Create new preview session.
        
        Args:
            session_id: Associated scraping session ID
            base_url: Base URL being previewed
            config: Configuration used for discovery
            
        Returns:
            Preview session ID
        """
        try:
            # Create preview directory
            preview_dir = self.previews_dir / session_id
            preview_dir.mkdir(exist_ok=True)
            
            # Create preview session metadata
            preview_data = {
                "session_id": session_id,
                "base_url": base_url,
                "created_at": datetime.now().isoformat(),
                "last_modified": datetime.now().isoformat(),
                "status": "in_progress",  # in_progress, completed, abandoned
                "config": config or {},
                "discovery_complete": False,
                "urls_discovered": 0,
                "urls_approved": 0,
                "urls_excluded": 0,
                "tree_state": {
                    "expanded_nodes": [],
                    "selected_nodes": [],
                    "current_view": "tree",
                    "sort_by": "path",
                    "show_excluded": False
                },
                "filters_applied": {
                    "exclude_patterns": [],
                    "include_patterns": [],
                    "content_types": [],
                    "min_word_count": 0,
                    "search_term": ""
                },
                "user_actions": [],  # History of user decisions
                "cache_version": "1.0"
            }
            
            self.cache_manager._save_json(preview_dir / "preview.json", preview_data)
            
            # Initialize empty approval state
            approval_data = {
                "approved": [],
                "excluded": [],
                "pending": [],
                "last_updated": datetime.now().isoformat()
            }
            
            self.cache_manager._save_json(preview_dir / "approved_urls.json", approval_data)
            
            self.logger.info(f"Created preview session: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create preview session: {e}")
            raise
    
    def _serialize_classifications(self, classifications: Dict[str, Any]) -> Dict[str, str]:
        """Convert ContentType enums to strings for JSON serialization."""
        if not classifications:
            return {}
        
        serialized = {}
        for url, content_type in classifications.items():
            if hasattr(content_type, 'value'):
                # ContentType enum - use the value
                serialized[url] = content_type.value
            elif hasattr(content_type, 'name'):
                # ContentType enum - use the name
                serialized[url] = content_type.name
            else:
                # Already a string or other serializable type
                serialized[url] = str(content_type)
        return serialized
    
    def _deserialize_classifications(self, classifications: Dict[str, str]) -> Dict[str, Any]:
        """Convert classification strings back to ContentType enums."""
        if not classifications:
            return {}
        
        try:
            from .content_classifier import ContentType
        except ImportError:
            from content_classifier import ContentType
        
        deserialized = {}
        for url, classification_str in classifications.items():
            # Try to find matching ContentType by value or name
            content_type = None
            for ct in ContentType:
                if ct.value == classification_str or ct.name == classification_str:
                    content_type = ct
                    break
            
            if content_type:
                deserialized[url] = content_type
            else:
                # Fallback to string if no matching enum found
                deserialized[url] = classification_str
        
        return deserialized

    def save_discovery_results(self, session_id: str, urls: List[str], classifications: Dict[str, Any] = None, 
                             discovery_params: Dict[str, Any] = None) -> bool:
        """
        Save URL discovery results for preview.
        
        Args:
            session_id: Preview session ID
            urls: Discovered URLs
            classifications: URL classifications
            discovery_params: Discovery parameters (max_depth, max_pages, etc.)
            
        Returns:
            True if saved successfully
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return False
            
            # Save discovery data (serialize ContentType enums)
            discovery_data = {
                "discovered_at": datetime.now().isoformat(),
                "urls": urls,
                "classifications": self._serialize_classifications(classifications),
                "total_urls": len(urls),
                "discovery_params": discovery_params or {}
            }
            
            self.cache_manager._save_json(preview_dir / "discovery.json", discovery_data)
            
            # Update preview metadata
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            preview_data["discovery_complete"] = True
            preview_data["urls_discovered"] = len(urls)
            preview_data["last_modified"] = datetime.now().isoformat()
            
            self.cache_manager._save_json(preview_file, preview_data)
            
            # Initialize all URLs as pending
            approval_file = preview_dir / "approved_urls.json"
            approval_data = self.cache_manager._load_json(approval_file)
            
            for url in urls:
                url_info = {
                    "url": url,
                    "title": '',  # ContentType objects don't have title field
                    "content_type": str(classifications.get(url, 'unknown')) if classifications else 'unknown',
                    "discovered_at": datetime.now().isoformat()
                }
                approval_data["pending"].append(url_info)
            
            approval_data["last_updated"] = datetime.now().isoformat()
            self.cache_manager._save_json(approval_file, approval_data)
            
            self.logger.info(f"Saved discovery results for preview: {len(urls)} URLs")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save discovery results: {e}")
            return False
    
    def save_user_decision(self, session_id: str, url: str, action: str, reason: str = None) -> bool:
        """
        Save user approval/exclusion decision.
        
        Args:
            session_id: Preview session ID
            url: URL being decided on
            action: 'approve' or 'exclude'
            reason: Optional reason for decision
            
        Returns:
            True if saved successfully
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return False
            
            # Load current approval state
            approval_file = preview_dir / "approved_urls.json"
            approval_data = self.cache_manager._load_json(approval_file)
            
            # Find URL in pending list
            url_info = None
            for i, pending_url in enumerate(approval_data["pending"]):
                if pending_url["url"] == url:
                    url_info = approval_data["pending"].pop(i)
                    break
            
            # If not in pending, might be moving between approved/excluded
            if not url_info:
                # Check if it's in approved list
                for i, approved_url in enumerate(approval_data["approved"]):
                    if approved_url["url"] == url:
                        url_info = approval_data["approved"].pop(i)
                        break
                
                # Check if it's in excluded list
                if not url_info:
                    for i, excluded_url in enumerate(approval_data["excluded"]):
                        if excluded_url["url"] == url:
                            url_info = approval_data["excluded"].pop(i)
                            break
            
            if not url_info:
                self.logger.warning(f"URL not found in any list: {url}")
                return False
            
            # Update URL info with decision
            timestamp = datetime.now().isoformat()
            
            if action == "approve":
                url_info["approved_at"] = timestamp
                url_info["reason"] = reason
                approval_data["approved"].append(url_info)
            elif action == "exclude":
                url_info["excluded_at"] = timestamp
                url_info["reason"] = reason
                approval_data["excluded"].append(url_info)
            else:
                self.logger.error(f"Invalid action: {action}")
                return False
            
            approval_data["last_updated"] = timestamp
            self.cache_manager._save_json(approval_file, approval_data)
            
            # Record user action for history
            self._record_user_action(session_id, url, action, reason)
            
            # Update counts in preview metadata
            self._update_preview_counts(session_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save user decision: {e}")
            return False
    
    def save_bulk_decisions(self, session_id: str, decisions: List[Dict[str, Any]]) -> int:
        """
        Save multiple user decisions at once.
        
        Args:
            session_id: Preview session ID
            decisions: List of {url, action, reason} dictionaries
            
        Returns:
            Number of decisions saved successfully
        """
        saved_count = 0
        for decision in decisions:
            url = decision.get('url')
            action = decision.get('action')
            reason = decision.get('reason')
            
            if self.save_user_decision(session_id, url, action, reason):
                saved_count += 1
        
        return saved_count
    
    def save_tree_state(self, session_id: str, tree_state: Dict[str, Any]) -> bool:
        """
        Save UI tree view state.
        
        Args:
            session_id: Preview session ID
            tree_state: Tree UI state
            
        Returns:
            True if saved successfully
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return False
            
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            
            preview_data["tree_state"] = tree_state
            preview_data["last_modified"] = datetime.now().isoformat()
            
            self.cache_manager._save_json(preview_file, preview_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save tree state: {e}")
            return False
    
    def save_filters(self, session_id: str, filters: Dict[str, Any]) -> bool:
        """
        Save applied filters and search terms.
        
        Args:
            session_id: Preview session ID
            filters: Applied filters
            
        Returns:
            True if saved successfully
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return False
            
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            
            preview_data["filters_applied"] = filters
            preview_data["last_modified"] = datetime.now().isoformat()
            
            self.cache_manager._save_json(preview_file, preview_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save filters: {e}")
            return False
    
    def load_preview_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete preview session data.
        
        Args:
            session_id: Preview session ID
            
        Returns:
            Dictionary containing all preview session data
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return None
            
            # Load main preview data
            preview_data = self.cache_manager._load_json(preview_dir / "preview.json")
            
            # Load approval state
            approval_data = self.cache_manager._load_json(preview_dir / "approved_urls.json")
            
            # Load discovery results if available
            discovery_file = preview_dir / "discovery.json"
            discovery_data = None
            if discovery_file.exists():
                discovery_data = self.cache_manager._load_json(discovery_file)
            
            # Combine all data
            complete_data = {
                **preview_data,
                "approval_state": approval_data,
                "discovery_data": discovery_data
            }
            
            return complete_data
            
        except Exception as e:
            self.logger.error(f"Failed to load preview session: {e}")
            return None
    
    def load_discovery_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load discovery results from cached preview session.
        
        Args:
            session_id: Preview session ID
            
        Returns:
            Dictionary with 'urls' and 'classifications' or None if not found
        """
        try:
            preview_dir = self.previews_dir / session_id
            discovery_file = preview_dir / "discovery.json"
            
            # Use cache manager's _load_json which handles compression automatically
            try:
                discovery_data = self.cache_manager._load_json(discovery_file)
            except FileNotFoundError:
                self.logger.warning(f"No discovery data found for session: {session_id}")
                return None
            
            if not discovery_data:
                return None
            
            return {
                'urls': discovery_data.get('urls', []),
                'classifications': self._deserialize_classifications(discovery_data.get('classifications', {})),
                'total_urls': discovery_data.get('total_urls', 0),
                'discovered_at': discovery_data.get('discovered_at'),
                'discovery_params': discovery_data.get('discovery_params', {})
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load discovery results for session {session_id}: {e}")
            return None
    
    def get_approved_urls(self, session_id: str) -> Set[str]:
        """
        Get set of approved URLs from preview session.
        
        Args:
            session_id: Preview session ID
            
        Returns:
            Set of approved URLs
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return set()
            
            approval_data = self.cache_manager._load_json(preview_dir / "approved_urls.json")
            approved_urls = {url_info["url"] for url_info in approval_data.get("approved", [])}
            
            return approved_urls
            
        except Exception as e:
            self.logger.error(f"Failed to get approved URLs: {e}")
            return set()
    
    def get_excluded_urls(self, session_id: str) -> Set[str]:
        """
        Get set of excluded URLs from preview session.
        
        Args:
            session_id: Preview session ID
            
        Returns:
            Set of excluded URLs
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return set()
            
            approval_data = self.cache_manager._load_json(preview_dir / "approved_urls.json")
            excluded_urls = {url_info["url"] for url_info in approval_data.get("excluded", [])}
            
            return excluded_urls
            
        except Exception as e:
            self.logger.error(f"Failed to get excluded URLs: {e}")
            return set()
    
    def mark_preview_complete(self, session_id: str) -> bool:
        """
        Mark preview session as completed.
        
        Args:
            session_id: Preview session ID
            
        Returns:
            True if marked successfully
        """
        try:
            preview_dir = self.previews_dir / session_id
            if not preview_dir.exists():
                return False
            
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            
            preview_data["status"] = "completed"
            preview_data["completed_at"] = datetime.now().isoformat()
            preview_data["last_modified"] = datetime.now().isoformat()
            
            self.cache_manager._save_json(preview_file, preview_data)
            
            self.logger.info(f"Marked preview session complete: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark preview complete: {e}")
            return False
    
    def list_preview_sessions(self, status: str = None) -> List[Dict[str, Any]]:
        """
        List available preview sessions.
        
        Args:
            status: Filter by status
            
        Returns:
            List of preview session summaries
        """
        sessions = []
        try:
            for preview_dir in self.previews_dir.iterdir():
                if not preview_dir.is_dir():
                    continue
                
                try:
                    preview_data = self.cache_manager._load_json(preview_dir / "preview.json")
                    
                    if status and preview_data.get('status') != status:
                        continue
                    
                    summary = {
                        "session_id": preview_data.get('session_id'),
                        "base_url": preview_data.get('base_url'),
                        "status": preview_data.get('status'),
                        "created_at": preview_data.get('created_at'),
                        "last_modified": preview_data.get('last_modified'),
                        "urls_discovered": preview_data.get('urls_discovered', 0),
                        "urls_approved": preview_data.get('urls_approved', 0),
                        "urls_excluded": preview_data.get('urls_excluded', 0)
                    }
                    sessions.append(summary)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load preview session {preview_dir.name}: {e}")
            
            # Sort by last modified, newest first
            sessions.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to list preview sessions: {e}")
            return sessions
    
    def export_approved_urls(self, session_id: str, output_file: str) -> bool:
        """
        Export approved URLs to JSON file.
        
        Args:
            session_id: Preview session ID
            output_file: Output file path
            
        Returns:
            True if exported successfully
        """
        try:
            approved_urls = self.get_approved_urls(session_id)
            
            export_data = {
                "session_id": session_id,
                "exported_at": datetime.now().isoformat(),
                "approved_urls": list(approved_urls),
                "total_urls": len(approved_urls)
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported {len(approved_urls)} approved URLs to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export approved URLs: {e}")
            return False
    
    def _record_user_action(self, session_id: str, url: str, action: str, reason: str = None) -> None:
        """Record user action for history tracking"""
        try:
            preview_dir = self.previews_dir / session_id
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            
            action_record = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "action": action,
                "reason": reason
            }
            
            preview_data.setdefault("user_actions", []).append(action_record)
            
            # Keep only last 1000 actions to prevent unlimited growth
            if len(preview_data["user_actions"]) > 1000:
                preview_data["user_actions"] = preview_data["user_actions"][-1000:]
            
            self.cache_manager._save_json(preview_file, preview_data)
            
        except Exception as e:
            self.logger.error(f"Failed to record user action: {e}")
    
    def _update_preview_counts(self, session_id: str) -> None:
        """Update URL counts in preview metadata"""
        try:
            preview_dir = self.previews_dir / session_id
            
            # Load current counts from approval data
            approval_data = self.cache_manager._load_json(preview_dir / "approved_urls.json")
            
            # Update preview metadata
            preview_file = preview_dir / "preview.json"
            preview_data = self.cache_manager._load_json(preview_file)
            
            preview_data["urls_approved"] = len(approval_data.get("approved", []))
            preview_data["urls_excluded"] = len(approval_data.get("excluded", []))
            preview_data["last_modified"] = datetime.now().isoformat()
            
            self.cache_manager._save_json(preview_file, preview_data)
            
        except Exception as e:
            self.logger.error(f"Failed to update preview counts: {e}")
    
    def find_compatible_preview(self, base_url: str, config_hash: str) -> Optional[str]:
        """
        Find existing preview session compatible with current parameters.
        
        Args:
            base_url: Base URL being previewed
            config_hash: Configuration hash
            
        Returns:
            Preview session ID or None
        """
        sessions = self.list_preview_sessions()
        for session in sessions:
            session_data = self.load_preview_session(session['session_id'])
            if (session_data and 
                session_data.get('base_url') == base_url and
                session_data.get('config', {}).get('config_hash') == config_hash):
                return session['session_id']
        
        return None