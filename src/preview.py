import json
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from urllib.parse import urlparse, unquote
import click
try:
    from .content_classifier import ContentClassifier, ContentType
    from .path_scoping import PathScopeManager
    from .preview_cache import PreviewCache
    from .cache_manager import CacheManager
except ImportError:
    from content_classifier import ContentClassifier, ContentType
    from path_scoping import PathScopeManager
    from preview_cache import PreviewCache
    from cache_manager import CacheManager


class URLPreview:
    """Handle URL discovery, preview, and interactive approval with content classification and caching."""
    
    def __init__(self, exclude_patterns: List[str] = None, path_scope: Optional[PathScopeManager] = None, 
                 cache_manager: CacheManager = None, preview_session_id: str = None):
        self.exclude_patterns = exclude_patterns or []
        self.excluded_urls: Set[str] = set()
        self.approved_urls: Set[str] = set()
        self.classifier = ContentClassifier()
        self.url_classifications: Dict[str, ContentType] = {}
        self.path_scope = path_scope
        
        # Caching support
        self.cache_manager = cache_manager
        self.preview_cache = PreviewCache(cache_manager) if cache_manager else None
        self.preview_session_id = preview_session_id
        self.cache_enabled = cache_manager is not None
        
    def build_url_tree(self, urls: List[str], classifications: Dict[str, ContentType] = None) -> Dict[str, any]:
        """Build a hierarchical tree structure from URLs with classification."""
        tree = defaultdict(lambda: {'urls': set(), 'children': defaultdict(dict), 'classifications': {}})
        
        # Store classifications for later use
        if classifications:
            self.url_classifications.update(classifications)
        else:
            # Classify URLs if not provided
            for url in urls:
                self.url_classifications[url] = self.classifier.classify_url(url)
        
        for url in urls:
            if self._is_excluded(url):
                continue
                
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.strip('/').split('/') if part]
            
            current = tree[parsed.netloc]
            current['urls'].add(url)
            current['classifications'][url] = self.url_classifications.get(url, ContentType.CONTENT)
            
            # Build tree structure
            for i, part in enumerate(path_parts):
                part = unquote(part)  # URL decode
                if 'children' not in current:
                    current['children'] = defaultdict(lambda: {'urls': set(), 'children': defaultdict(dict), 'classifications': {}})
                
                if part not in current['children']:
                    current['children'][part] = {'urls': set(), 'children': defaultdict(dict), 'classifications': {}}
                
                current['children'][part]['urls'].add(url)
                current['children'][part]['classifications'][url] = self.url_classifications.get(url, ContentType.CONTENT)
                current = current['children'][part]
        
        return dict(tree)
    
    def _is_excluded(self, url: str) -> bool:
        """Check if URL matches any exclude patterns."""
        for pattern in self.exclude_patterns:
            if re.search(pattern, url):
                return True
        return url in self.excluded_urls
    
    def display_tree(self, tree: Dict, indent: int = 0, parent_path: str = "") -> List[Tuple[str, str, int]]:
        """Display URL tree with content classification and numbering for interactive selection."""
        items = []
        
        for domain, domain_data in tree.items():
            if indent == 0:  # Root domain
                domain_urls = [url for url in domain_data['urls'] if not self._is_excluded(url)]
                if domain_urls or domain_data['children']:
                    # Count by type for domain summary
                    type_counts = self._get_type_counts(domain_data)
                    type_summary = self._format_type_summary(type_counts)
                    
                    click.echo(f"{'  ' * indent}🌐 {domain} ({len(domain_urls)} pages{type_summary})")
                    items.append((domain, parent_path + domain, indent))
            
            # Process children (they now store display info but don't display yet)
            children_items = self._display_children(domain_data['children'], indent + 1, parent_path + domain + "/", domain_data.get('classifications', {}))
            items.extend(children_items)
        
        # All items that will be numbered and selectable
        # (Exclude only the domain header, not domain items themselves)
        selectable_items = []
        numbered_display_items = []
        
        for item in items:
            if len(item) == 3:  # Simple domain or path item (not display-enhanced)
                # Only number items that aren't the main domain header
                if item[2] > 0:  # indent > 0 means it's not the root domain header
                    selectable_items.append(item)
                    numbered_display_items.append(item)
            elif len(item) > 3:  # Display-enhanced item from _display_children
                selectable_items.append((item[0], item[1], item[2]))  # Convert to simple format
                numbered_display_items.append(item)
        
        # Display all selectable items with correct sequential numbering
        self._display_numbered_items(numbered_display_items)
        
        # Return items that correspond exactly to the displayed numbers
        return selectable_items
    
    def _display_numbered_items(self, items_with_display_info):
        """Display items with proper sequential numbering."""
        number = 1
        for item in items_with_display_info:
            if len(item) >= 7:  # Display-enhanced item
                name, current_path, indent, icon, url_count, type_summary, status = item[:7]
                click.echo(f"{'  ' * indent}{number:2d}. {icon} {name} ({url_count} pages{type_summary}{status})")
            elif len(item) == 3:  # Simple item (shouldn't normally happen here now, but handle it)
                name, current_path, indent = item
                click.echo(f"{'  ' * indent}{number:2d}. 📁 {name}")
            number += 1
    
    def _display_children(self, children: Dict, indent: int, parent_path: str, parent_classifications: Dict = None) -> List[Tuple[str, str, int]]:
        """Recursively display child nodes with content classification."""
        items = []
        
        for i, (name, node_data) in enumerate(sorted(children.items())):
            current_path = parent_path + name
            node_urls = [url for url in node_data['urls'] if not self._is_excluded(url)]
            
            if node_urls or node_data['children']:
                # Get type information
                node_classifications = node_data.get('classifications', parent_classifications or {})
                type_counts = self._get_type_counts_from_classifications(node_classifications, node_urls)
                
                # Choose appropriate icon based on primary content type
                primary_type = self._get_primary_type(type_counts)
                icon = self._get_type_icon(primary_type, bool(node_data['children']))
                
                # Format type summary
                type_summary = self._format_type_summary(type_counts, compact=True)
                
                excluded_count = len([url for url in node_data['urls'] if self._is_excluded(url)])
                status = f" [{excluded_count} excluded]" if excluded_count else ""
                
                # Don't display here - will be displayed with correct numbering later
                items.append((name, current_path, indent, icon, len(node_urls), type_summary, status))
                
                # Recursively display children
                if node_data['children']:
                    child_items = self._display_children(
                        node_data['children'], 
                        indent + 1, 
                        current_path + "/",
                        node_classifications
                    )
                    items.extend(child_items)
        
        return items
    
    def interactive_exclude(self, tree: Dict) -> Set[str]:
        """Interactive exclusion of URL paths."""
        click.echo("\n🔍 URL Structure Preview:")
        click.echo("=" * 50)
        
        # Show path scoping information if available
        if self.path_scope:
            self._display_scope_info()
        
        # Display initial tree
        items = self.display_tree(tree)
        
        if not items:
            click.echo("No URLs found to display.")
            return set()
        
        while True:
            click.echo(f"\nOptions:")
            click.echo("  e <number>  - Exclude path and all subpaths")
            click.echo("  i <number>  - Include previously excluded path")
            click.echo("  r           - Refresh display")
            click.echo("  s           - Show excluded URLs")
            click.echo("  c           - Continue to approval")
            click.echo("  q           - Quit without scraping")
            
            try:
                choice = click.prompt("Enter your choice", type=str).strip().lower()
                
                if choice == 'q':
                    click.echo("Exiting...")
                    return None
                elif choice == 'c':
                    break
                elif choice == 'r':
                    click.echo("\n🔍 Updated URL Structure:")
                    click.echo("=" * 50)
                    items = self.display_tree(tree)
                elif choice == 's':
                    self._show_excluded_urls()
                elif choice.startswith('e '):
                    try:
                        num = int(choice.split()[1])
                        if 1 <= num <= len(items):
                            path = items[num-1][1]
                            self._exclude_path(tree, path)
                            click.echo(f"✅ Excluded path: {path}")
                            # Refresh display
                            click.echo("\n🔍 Updated URL Structure:")
                            click.echo("=" * 50)
                            items = self.display_tree(tree)
                        else:
                            click.echo(f"❌ Invalid number. Please enter 1-{len(items)} (you entered {num})")
                    except (ValueError, IndexError):
                        click.echo("❌ Invalid format. Use: e <number>")
                elif choice.startswith('i '):
                    try:
                        num = int(choice.split()[1])
                        if 1 <= num <= len(items):
                            path = items[num-1][1]
                            self._include_path(tree, path)
                            click.echo(f"✅ Included path: {path}")
                            # Refresh display
                            click.echo("\n🔍 Updated URL Structure:")
                            click.echo("=" * 50)
                            items = self.display_tree(tree)
                        else:
                            click.echo(f"❌ Invalid number. Please enter 1-{len(items)}")
                    except (ValueError, IndexError):
                        click.echo("❌ Invalid format. Use: i <number>")
                else:
                    click.echo("❌ Invalid choice. Please try again.")
                    
            except KeyboardInterrupt:
                click.echo("\nExiting...")
                return None
        
        # Calculate final URL list
        approved_urls = self._get_approved_urls(tree)
        return approved_urls
    
    def _exclude_path(self, tree: Dict, path: str):
        """Exclude all URLs under a given path."""
        excluded_urls = []
        for domain, domain_data in tree.items():
            urls_excluded = self._exclude_urls_in_node(domain_data, path)
            excluded_urls.extend(urls_excluded)
        
        # Save exclusions to cache if enabled
        if self.cache_enabled and self.preview_cache and self.preview_session_id:
            decisions = [{"url": url, "action": "exclude", "reason": f"excluded_path:{path}"} 
                        for url in excluded_urls]
            self.preview_cache.save_bulk_decisions(self.preview_session_id, decisions)
    
    def _include_path(self, tree: Dict, path: str):
        """Include all URLs under a given path."""
        urls_to_include = []
        for domain, domain_data in tree.items():
            self._collect_urls_in_path(domain_data, path, urls_to_include)
        
        for url in urls_to_include:
            self.excluded_urls.discard(url)
        
        # Save inclusions to cache if enabled
        if self.cache_enabled and self.preview_cache and self.preview_session_id:
            decisions = [{"url": url, "action": "approve", "reason": f"included_path:{path}"} 
                        for url in urls_to_include]
            self.preview_cache.save_bulk_decisions(self.preview_session_id, decisions)
    
    def _exclude_urls_in_node(self, node: Dict, target_path: str) -> List[str]:
        """Recursively exclude URLs matching the target path."""
        excluded_urls = []
        
        for url in node['urls']:
            parsed = urlparse(url)
            url_path = parsed.netloc + parsed.path
            if target_path in url_path:
                self.excluded_urls.add(url)
                excluded_urls.append(url)
        
        for child_node in node.get('children', {}).values():
            excluded_urls.extend(self._exclude_urls_in_node(child_node, target_path))
        
        return excluded_urls
    
    def _collect_urls_in_path(self, node: Dict, target_path: str, url_list: List[str]):
        """Recursively collect URLs matching the target path."""
        for url in node['urls']:
            parsed = urlparse(url)
            url_path = parsed.netloc + parsed.path
            if target_path in url_path:
                url_list.append(url)
        
        for child_node in node.get('children', {}).values():
            self._collect_urls_in_path(child_node, target_path, url_list)
    
    def _show_excluded_urls(self):
        """Display currently excluded URLs."""
        if not self.excluded_urls:
            click.echo("No URLs currently excluded.")
            return
        
        click.echo(f"\n❌ Excluded URLs ({len(self.excluded_urls)}):")
        click.echo("-" * 40)
        for i, url in enumerate(sorted(self.excluded_urls), 1):
            classification = self.url_classifications.get(url, ContentType.CONTENT)
            click.echo(f"  {i:2d}. {classification.value} {url}")
    
    def _get_approved_urls(self, tree: Dict) -> Set[str]:
        """Get final list of approved URLs (non-excluded)."""
        all_urls = set()
        
        def collect_urls(node):
            all_urls.update(node['urls'])
            for child in node.get('children', {}).values():
                collect_urls(child)
        
        for domain_data in tree.values():
            collect_urls(domain_data)
        
        approved = all_urls - self.excluded_urls
        return approved
    
    def final_approval(self, approved_urls: Set[str]) -> bool:
        """Final approval step with summary."""
        click.echo(f"\n📋 Final Summary:")
        click.echo("=" * 30)
        click.echo(f"URLs to scrape: {len(approved_urls)}")
        click.echo(f"URLs excluded: {len(self.excluded_urls)}")
        
        if approved_urls:
            click.echo(f"\nFirst 10 URLs to scrape:")
            for i, url in enumerate(sorted(list(approved_urls))[:10], 1):
                click.echo(f"  {i:2d}. {url}")
            
            if len(approved_urls) > 10:
                click.echo(f"  ... and {len(approved_urls) - 10} more")
        
        return click.confirm(f"\n✅ Proceed with scraping {len(approved_urls)} URLs?")
    
    def save_approved_urls(self, urls: Set[str], filepath: str):
        """Save approved URLs to file."""
        data = {
            'approved_urls': sorted(list(urls)),
            'excluded_patterns': self.exclude_patterns,
            'excluded_urls': sorted(list(self.excluded_urls))
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        click.echo(f"💾 Approved URLs saved to: {filepath}")
    
    def load_approved_urls(self, filepath: str) -> Set[str]:
        """Load previously approved URLs from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.excluded_urls = set(data.get('excluded_urls', []))
            approved = set(data.get('approved_urls', []))
            
            click.echo(f"📂 Loaded {len(approved)} approved URLs from: {filepath}")
            return approved
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            click.echo(f"❌ Error loading approved URLs: {e}")
            return set()
    
    def _get_type_counts(self, node_data: Dict) -> Dict[ContentType, int]:
        """Count URLs by content type in a node."""
        type_counts = {content_type: 0 for content_type in ContentType}
        
        classifications = node_data.get('classifications', {})
        for url in node_data['urls']:
            if not self._is_excluded(url):
                content_type = classifications.get(url, self.url_classifications.get(url, ContentType.CONTENT))
                type_counts[content_type] += 1
        
        # Recursively count children
        for child_node in node_data.get('children', {}).values():
            child_counts = self._get_type_counts(child_node)
            for content_type, count in child_counts.items():
                type_counts[content_type] += count
        
        return type_counts
    
    def _get_type_counts_from_classifications(self, classifications: Dict, urls: List[str]) -> Dict[ContentType, int]:
        """Count URLs by content type from classifications dict."""
        type_counts = {content_type: 0 for content_type in ContentType}
        
        for url in urls:
            if not self._is_excluded(url):
                content_type = classifications.get(url, self.url_classifications.get(url, ContentType.CONTENT))
                type_counts[content_type] += 1
        
        return type_counts
    
    def _get_primary_type(self, type_counts: Dict[ContentType, int]) -> ContentType:
        """Get the primary content type based on counts."""
        # Remove zero counts
        non_zero_counts = {k: v for k, v in type_counts.items() if v > 0}
        
        if not non_zero_counts:
            return ContentType.CONTENT
        
        # Priority order for determining primary type
        priority_order = [ContentType.DOCUMENTATION, ContentType.CONTENT, ContentType.NAVIGATION, ContentType.TECHNICAL, ContentType.EXCLUDED]
        
        for content_type in priority_order:
            if non_zero_counts.get(content_type, 0) > 0:
                return content_type
        
        return ContentType.CONTENT
    
    def _get_type_icon(self, content_type: ContentType, has_children: bool) -> str:
        """Get appropriate icon for content type."""
        if content_type == ContentType.DOCUMENTATION:
            return "📚" if has_children else "📖"
        elif content_type == ContentType.CONTENT:
            return "📁" if has_children else "📄"
        elif content_type == ContentType.NAVIGATION:
            return "🧭"
        elif content_type == ContentType.TECHNICAL:
            return "⚙️"
        elif content_type == ContentType.EXCLUDED:
            return "❌"
        else:
            return "📂" if has_children else "📄"
    
    def _format_type_summary(self, type_counts: Dict[ContentType, int], compact: bool = False) -> str:
        """Format content type summary for display."""
        non_zero_counts = {k: v for k, v in type_counts.items() if v > 0}
        
        if not non_zero_counts:
            return ""
        
        if compact:
            # Show only the most significant types
            summary_parts = []
            if non_zero_counts.get(ContentType.DOCUMENTATION, 0) > 0:
                summary_parts.append(f"📖{non_zero_counts[ContentType.DOCUMENTATION]}")
            if non_zero_counts.get(ContentType.CONTENT, 0) > 0:
                summary_parts.append(f"📄{non_zero_counts[ContentType.CONTENT]}")
            if non_zero_counts.get(ContentType.NAVIGATION, 0) > 0:
                summary_parts.append(f"🧭{non_zero_counts[ContentType.NAVIGATION]}")
            if non_zero_counts.get(ContentType.EXCLUDED, 0) > 0:
                summary_parts.append(f"❌{non_zero_counts[ContentType.EXCLUDED]}")
            
            return f" [{', '.join(summary_parts)}]" if summary_parts else ""
        else:
            # Full summary
            parts = []
            for content_type in ContentType:
                count = non_zero_counts.get(content_type, 0)
                if count > 0:
                    parts.append(f"{content_type.value}: {count}")
            
            return f" | {', '.join(parts)}" if parts else ""
    
    def _display_scope_info(self):
        """Display path scoping information."""
        scope_summary = self.path_scope.get_scope_summary()
        
        if scope_summary['enabled']:
            click.echo(f"🎯 Path Scoping: Enabled")
            click.echo(f"   📂 Starting path: {scope_summary['starting_path']}")
            click.echo(f"   ✅ Allowed paths: {', '.join(scope_summary['allowed_paths'])}")
            click.echo(f"   🧭 Navigation policy: {scope_summary['navigation_policy']}")
            if scope_summary['allow_siblings']:
                click.echo(f"   👥 Sibling paths: Allowed")
            click.echo(f"   📊 URLs outside scope will be filtered automatically")
        else:
            click.echo(f"🎯 Path Scoping: Disabled (all paths allowed)")
        
        click.echo()
    
    def save_preview_session(self, base_url: str, urls: List[str], classifications: Dict[str, ContentType] = None) -> str:
        """Save preview session to cache."""
        if not self.cache_enabled or not self.preview_cache:
            return None
        
        if not self.preview_session_id:
            # Create new preview session
            self.preview_session_id = self.cache_manager._generate_session_id(base_url)
            self.preview_cache.create_preview_session(
                self.preview_session_id, base_url, self.cache_manager.config
            )
        
        # Save discovery results
        self.preview_cache.save_discovery_results(self.preview_session_id, urls, classifications)
        
        return self.preview_session_id
    
    def load_preview_session(self, session_id: str) -> bool:
        """Load preview session from cache."""
        if not self.cache_enabled or not self.preview_cache:
            return False
        
        session_data = self.preview_cache.load_preview_session(session_id)
        if not session_data:
            return False
        
        # Restore preview state
        self.preview_session_id = session_id
        
        # Load excluded/approved URLs
        approval_state = session_data.get('approval_state', {})
        excluded_urls = {url_info['url'] for url_info in approval_state.get('excluded', [])}
        approved_urls = {url_info['url'] for url_info in approval_state.get('approved', [])}
        
        self.excluded_urls.update(excluded_urls)
        self.approved_urls.update(approved_urls)
        
        return True
    
    def get_approved_urls_from_cache(self, session_id: str) -> Set[str]:
        """Get approved URLs from cached preview session."""
        if not self.cache_enabled or not self.preview_cache:
            return set()
        
        return self.preview_cache.get_approved_urls(session_id)
    
    def mark_preview_complete(self):
        """Mark preview session as complete."""
        if self.cache_enabled and self.preview_cache and self.preview_session_id:
            self.preview_cache.mark_preview_complete(self.preview_session_id)