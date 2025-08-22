import logging
from typing import Set, List, Dict, Any
from urllib.parse import urlparse
import re


class PathScopeManager:
    """Manages path-based URL scoping to keep scraping focused on relevant sections."""
    
    def __init__(self, config: Dict[str, Any], starting_url: str):
        self.config = config.get('path_scoping', {})
        self.logger = logging.getLogger(__name__)
        self.starting_url = starting_url
        
        # Parse starting URL to determine scope
        self.starting_parsed = urlparse(starting_url)
        self.base_domain = self.starting_parsed.netloc
        self.starting_path = self._normalize_path(self.starting_parsed.path)
        
        # Calculate allowed scope boundaries
        self.allowed_paths = self._calculate_allowed_paths()
        
        # Track external crawl depth
        self.external_depth_tracker: Dict[str, int] = {}
        
        self.logger.info(f"Path scoping initialized for: {self.starting_path}")
        self.logger.info(f"Allowed paths: {self.allowed_paths}")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a URL path for consistent comparison."""
        # Remove trailing slash unless it's root
        path = path.rstrip('/') if path != '/' else '/'
        # Ensure it starts with /
        if not path.startswith('/'):
            path = '/' + path
        return path
    
    def _calculate_allowed_paths(self) -> Set[str]:
        """Calculate all allowed path prefixes based on starting URL and config."""
        allowed = set()
        
        if not self.config.get('enabled', True):
            # If scoping is disabled, allow everything
            return {'/'}
        
        # Always include the exact starting path and its parents
        current_path = self.starting_path
        
        # Add the starting path itself
        allowed.add(current_path)
        
        # Add parent paths based on configuration
        parent_levels = self.config.get('allow_parent_levels', 1)
        
        for level in range(parent_levels + 1):  # +1 to include current level
            if current_path == '/':
                break
                
            # Move up one level
            if current_path.endswith('/'):
                current_path = current_path[:-1]
            
            parent_path = '/'.join(current_path.split('/')[:-1])
            if not parent_path:
                parent_path = '/'
            
            allowed.add(parent_path)
            current_path = parent_path
        
        # Always allow homepage if configured
        if self.config.get('allow_homepage', True):
            allowed.add('/')
        
        # Add sibling paths if enabled
        if self.config.get('allow_siblings', True):
            self._add_sibling_paths(allowed)
        
        return allowed
    
    def _add_sibling_paths(self, allowed_paths: Set[str]):
        """Add sibling paths at the same level as starting path."""
        # Find the immediate parent of starting path
        if self.starting_path == '/':
            return  # No siblings for root
        
        path_parts = self.starting_path.strip('/').split('/')
        if len(path_parts) <= 1:
            return  # No siblings for top-level paths
        
        # Get parent path
        parent_parts = path_parts[:-1]
        parent_path = '/' + '/'.join(parent_parts) if parent_parts else '/'
        
        # The sibling path prefix is the parent - we'll validate siblings during crawling
        # This is a placeholder - actual siblings will be discovered and validated
        self.sibling_parent = parent_path
    
    def is_url_in_scope(self, url: str, is_navigation: bool = False, current_depth: int = 0) -> tuple[bool, str]:
        """
        Check if a URL is within the allowed scope.
        
        Returns:
            (is_allowed, reason)
        """
        if not self.config.get('enabled', True):
            return True, "Path scoping disabled"
        
        parsed = urlparse(url)
        
        # Different domain = not in scope
        if parsed.netloc != self.base_domain:
            return False, "Different domain"
        
        url_path = self._normalize_path(parsed.path)
        
        # Check if URL path starts with any allowed path (excluding root if not exact match)
        for allowed_path in sorted(self.allowed_paths, key=len, reverse=True):
            if allowed_path == '/' and url_path != '/':
                # Special handling for homepage - only allow exact match or navigation
                if self.config.get('allow_homepage', True) and (is_navigation or url_path == '/'):
                    continue  # Will be handled by navigation logic below
                else:
                    continue  # Skip root path for non-navigation content
            elif url_path.startswith(allowed_path):
                return True, f"Within allowed scope: {allowed_path}"
        
        # Handle homepage specifically
        if url_path == '/' and self.config.get('allow_homepage', True):
            return True, "Homepage allowed"
        
        # Special handling for navigation links
        if is_navigation:
            return self._handle_navigation_url(url_path, current_depth)
        
        # Check for sibling paths
        if self.config.get('allow_siblings', True) and hasattr(self, 'sibling_parent'):
            if url_path.startswith(self.sibling_parent) and url_path != self.sibling_parent:
                # Check if it's a sibling (same level as starting path)
                relative_path = url_path[len(self.sibling_parent):].strip('/')
                if '/' not in relative_path or relative_path.count('/') <= 1:
                    return True, f"Sibling path under: {self.sibling_parent}"
        
        return False, f"Outside scope (path: {url_path})"
    
    def _handle_navigation_url(self, url_path: str, current_depth: int) -> tuple[bool, str]:
        """Handle navigation URLs based on configuration."""
        nav_policy = self.config.get('allow_navigation', 'limited')
        
        if nav_policy == 'none':
            return False, "Navigation crawling disabled"
        elif nav_policy == 'strict':
            return False, "Strict navigation mode - only in-scope URLs"
        elif nav_policy == 'limited':
            max_external_depth = self.config.get('max_external_depth', 1)
            
            # Track external depth for this URL
            external_depth = self.external_depth_tracker.get(url_path, current_depth)
            if external_depth <= max_external_depth:
                self.external_depth_tracker[url_path] = external_depth
                return True, f"Navigation link within depth limit ({external_depth}/{max_external_depth})"
            else:
                return False, f"Navigation link exceeds depth limit ({external_depth}/{max_external_depth})"
        
        return False, "Unknown navigation policy"
    
    def is_likely_navigation(self, url: str, link_context: str = "") -> bool:
        """Determine if a URL is likely a navigation link based on context and patterns."""
        url_path = self._normalize_path(urlparse(url).path)
        
        # Common navigation patterns
        nav_patterns = [
            r'^/$',                          # Homepage
            r'^/(home|main|index)/?$',       # Home variations
            r'^/(about|contact|support)/?$', # Common nav pages
            r'^/sitemap',                    # Sitemap
        ]
        
        for pattern in nav_patterns:
            if re.match(pattern, url_path, re.IGNORECASE):
                return True
        
        # Check link context (if available)
        if link_context:
            nav_contexts = ['nav', 'navigation', 'menu', 'header', 'footer']
            if any(ctx in link_context.lower() for ctx in nav_contexts):
                return True
        
        return False
    
    def get_scope_summary(self) -> Dict[str, Any]:
        """Get a summary of the current scope configuration."""
        return {
            'enabled': self.config.get('enabled', True),
            'starting_path': self.starting_path,
            'allowed_paths': sorted(list(self.allowed_paths)),
            'allow_siblings': self.config.get('allow_siblings', True),
            'navigation_policy': self.config.get('allow_navigation', 'limited'),
            'max_external_depth': self.config.get('max_external_depth', 1),
        }
    
    def log_url_decision(self, url: str, allowed: bool, reason: str, url_type: str = "content"):
        """Log URL inclusion/exclusion decisions for debugging."""
        status = "✅ ALLOW" if allowed else "❌ BLOCK"
        self.logger.debug(f"{status} [{url_type}] {url} - {reason}")
    
    def get_path_hierarchy(self, url: str) -> List[str]:
        """Get the path hierarchy for a URL (useful for tree display)."""
        parsed = urlparse(url)
        path = self._normalize_path(parsed.path)
        
        if path == '/':
            return ['/']
        
        parts = path.strip('/').split('/')
        hierarchy = []
        current = ''
        
        for part in parts:
            current += '/' + part
            hierarchy.append(current)
        
        return ['/', ] + hierarchy if hierarchy else ['/']