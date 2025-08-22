import json
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from urllib.parse import urlparse, unquote
import click


class URLPreview:
    """Handle URL discovery, preview, and interactive approval."""
    
    def __init__(self, exclude_patterns: List[str] = None):
        self.exclude_patterns = exclude_patterns or []
        self.excluded_urls: Set[str] = set()
        self.approved_urls: Set[str] = set()
        
    def build_url_tree(self, urls: List[str]) -> Dict[str, any]:
        """Build a hierarchical tree structure from URLs."""
        tree = defaultdict(lambda: {'urls': set(), 'children': defaultdict(dict)})
        
        for url in urls:
            if self._is_excluded(url):
                continue
                
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.strip('/').split('/') if part]
            
            current = tree[parsed.netloc]
            current['urls'].add(url)
            
            # Build tree structure
            for i, part in enumerate(path_parts):
                part = unquote(part)  # URL decode
                if 'children' not in current:
                    current['children'] = defaultdict(lambda: {'urls': set(), 'children': defaultdict(dict)})
                
                if part not in current['children']:
                    current['children'][part] = {'urls': set(), 'children': defaultdict(dict)}
                
                current['children'][part]['urls'].add(url)
                current = current['children'][part]
        
        return dict(tree)
    
    def _is_excluded(self, url: str) -> bool:
        """Check if URL matches any exclude patterns."""
        for pattern in self.exclude_patterns:
            if re.search(pattern, url):
                return True
        return url in self.excluded_urls
    
    def display_tree(self, tree: Dict, indent: int = 0, parent_path: str = "") -> List[Tuple[str, str, int]]:
        """Display URL tree with numbering for interactive selection."""
        items = []
        
        for domain, domain_data in tree.items():
            if indent == 0:  # Root domain
                domain_urls = [url for url in domain_data['urls'] if not self._is_excluded(url)]
                if domain_urls or domain_data['children']:
                    click.echo(f"{'  ' * indent}🌐 {domain} ({len(domain_urls)} pages)")
                    items.append((domain, parent_path + domain, indent))
            
            # Process children
            children_items = self._display_children(domain_data['children'], indent + 1, parent_path + domain + "/")
            items.extend(children_items)
        
        return items
    
    def _display_children(self, children: Dict, indent: int, parent_path: str) -> List[Tuple[str, str, int]]:
        """Recursively display child nodes."""
        items = []
        
        for i, (name, node_data) in enumerate(sorted(children.items())):
            current_path = parent_path + name
            node_urls = [url for url in node_data['urls'] if not self._is_excluded(url)]
            
            if node_urls or node_data['children']:
                # Choose appropriate icon
                if node_data['children']:
                    icon = "📁" if node_urls else "📂"
                else:
                    icon = "📄"
                
                excluded_count = len([url for url in node_data['urls'] if self._is_excluded(url)])
                status = f" [{excluded_count} excluded]" if excluded_count else ""
                
                click.echo(f"{'  ' * indent}{len(items)+1:2d}. {icon} {name} ({len(node_urls)} pages{status})")
                items.append((name, current_path, indent))
                
                # Recursively display children
                if node_data['children']:
                    child_items = self._display_children(node_data['children'], indent + 1, current_path + "/")
                    items.extend(child_items)
        
        return items
    
    def interactive_exclude(self, tree: Dict) -> Set[str]:
        """Interactive exclusion of URL paths."""
        click.echo("\n🔍 URL Structure Preview:")
        click.echo("=" * 50)
        
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
                            click.echo(f"❌ Invalid number. Please enter 1-{len(items)}")
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
        for domain, domain_data in tree.items():
            self._exclude_urls_in_node(domain_data, path)
    
    def _include_path(self, tree: Dict, path: str):
        """Include all URLs under a given path."""
        urls_to_include = []
        for domain, domain_data in tree.items():
            self._collect_urls_in_path(domain_data, path, urls_to_include)
        
        for url in urls_to_include:
            self.excluded_urls.discard(url)
    
    def _exclude_urls_in_node(self, node: Dict, target_path: str):
        """Recursively exclude URLs matching the target path."""
        for url in node['urls']:
            parsed = urlparse(url)
            url_path = parsed.netloc + parsed.path
            if target_path in url_path:
                self.excluded_urls.add(url)
        
        for child_node in node.get('children', {}).values():
            self._exclude_urls_in_node(child_node, target_path)
    
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
            click.echo(f"  {i:2d}. {url}")
    
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