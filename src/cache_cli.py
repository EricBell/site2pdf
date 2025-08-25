"""
Cache CLI Commands

Command-line interface for managing cache sessions and preview states.
Provides commands for listing, cleaning, resuming, and managing cached data.
"""

import click
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from .cache_manager import CacheManager
    from .preview_cache import PreviewCache
except ImportError:
    from cache_manager import CacheManager
    from preview_cache import PreviewCache


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_time_ago(timestamp_str: str) -> str:
    """Format timestamp as time ago"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now()
        if timestamp.tzinfo:
            # Convert to naive datetime for comparison
            timestamp = timestamp.replace(tzinfo=None)
        
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    except Exception:
        return "Unknown"


@click.group()
def cache():
    """Cache management commands for scraping sessions and preview states."""
    pass


@cache.command()
@click.option('--status', type=click.Choice(['active', 'completed', 'failed']),
              help='Filter sessions by status')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def list(status, verbose):
    """List cached scraping sessions."""
    try:
        cache_manager = CacheManager()
        sessions = cache_manager.list_sessions(status=status)
        
        if not sessions:
            click.echo(f"No {'cached sessions' if not status else f'{status} sessions'} found.")
            return
        
        if verbose:
            click.echo(f"{'='*80}")
            click.echo(f"{'SESSION ID':<20} {'URL':<35} {'STATUS':<12} {'PAGES':<12} {'SIZE':<8} {'LAST MODIFIED'}")
            click.echo(f"{'='*80}")
            
            for session in sessions:
                session_id = session['session_id'][:18] + '...' if len(session['session_id']) > 20 else session['session_id']
                url = session['base_url'][:33] + '...' if len(session['base_url']) > 35 else session['base_url']
                status_display = session.get('status', 'unknown')
                pages = f"{session.get('pages_scraped', 0)}/{session.get('pages_total', 0)}"
                size = format_size(session.get('cache_size', 0))
                modified = format_time_ago(session.get('last_modified', ''))
                
                click.echo(f"{session_id:<20} {url:<35} {status_display:<12} {pages:<12} {size:<8} {modified}")
        else:
            click.echo("┌─────────────────────────────────────────────────────────────────┐")
            click.echo("│                        Cached Sessions                          │")
            click.echo("├─────────────────────────────────────────────────────────────────┤")
            
            for session in sessions[:10]:  # Show first 10 sessions
                session_id = session['session_id'][:8]
                url_parts = session['base_url'].replace('https://', '').replace('http://', '')
                url_display = url_parts[:25] + '...' if len(url_parts) > 28 else url_parts
                
                status_display = session.get('status', 'unknown')
                status_icon = {'active': '🔄', 'completed': '✅', 'failed': '❌'}.get(status_display, '❓')
                
                pages = f"{session.get('pages_scraped', 0)}/{session.get('pages_total', 0)} pages"
                size = format_size(session.get('cache_size', 0))
                modified = format_time_ago(session.get('last_modified', ''))
                
                click.echo(f"│ {session_id:<8} {url_display:<28} {pages:<12} {size:<8} {modified:<8} {status_icon} │")
            
            if len(sessions) > 10:
                click.echo(f"│ ... and {len(sessions) - 10} more sessions                                      │")
            
            click.echo("└─────────────────────────────────────────────────────────────────┘")
        
    except Exception as e:
        click.echo(f"❌ Error listing sessions: {e}")


@cache.command()
@click.option('--older-than', default='30d', help='Remove sessions older than this (e.g., 7d, 24h)')
@click.option('--keep-completed', default=10, help='Always keep this many most recent completed sessions')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without doing it')
def clean(older_than, keep_completed, dry_run):
    """Clean up old cache sessions."""
    try:
        # Parse time duration
        if older_than.endswith('d'):
            max_age_days = int(older_than[:-1])
        elif older_than.endswith('h'):
            max_age_days = int(older_than[:-1]) / 24
        else:
            max_age_days = int(older_than)
        
        cache_manager = CacheManager()
        
        if dry_run:
            # Show what would be cleaned
            sessions = cache_manager.list_sessions()
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            to_clean = []
            for session in sessions:
                last_modified = datetime.fromisoformat(session.get('last_modified', ''))
                if last_modified < cutoff_date:
                    to_clean.append(session)
            
            if to_clean:
                click.echo(f"🔍 Would clean {len(to_clean)} sessions:")
                for session in to_clean:
                    session_id = session['session_id'][:12]
                    url = session['base_url']
                    modified = format_time_ago(session.get('last_modified', ''))
                    size = format_size(session.get('cache_size', 0))
                    click.echo(f"  - {session_id}... ({url}) - {size}, {modified}")
            else:
                click.echo("🧹 No sessions would be cleaned.")
        else:
            cleaned_count = cache_manager.cleanup_old_sessions(
                max_age_days=max_age_days,
                keep_completed=keep_completed
            )
            
            if cleaned_count > 0:
                click.echo(f"🧹 Cleaned up {cleaned_count} old sessions.")
            else:
                click.echo(f"🧹 No old sessions to clean up.")
        
    except Exception as e:
        click.echo(f"❌ Error cleaning sessions: {e}")


@cache.command()
def stats():
    """Show cache statistics."""
    try:
        cache_manager = CacheManager()
        stats = cache_manager.get_cache_stats()
        
        click.echo("📊 Cache Statistics")
        click.echo("═" * 50)
        click.echo(f"Total sessions:     {stats.get('total_sessions', 0)}")
        click.echo(f"Active sessions:    {stats.get('active_sessions', 0)}")
        click.echo(f"Completed sessions: {stats.get('completed_sessions', 0)}")
        click.echo(f"Failed sessions:    {stats.get('failed_sessions', 0)}")
        click.echo(f"")
        click.echo(f"Total cache size:   {format_size(stats.get('total_cache_size', 0))}")
        click.echo(f"Cache directory:    {stats.get('cache_directory', 'N/A')}")
        click.echo(f"Compression:        {'Enabled' if stats.get('compression_enabled') else 'Disabled'}")
        
    except Exception as e:
        click.echo(f"❌ Error getting cache stats: {e}")


@cache.command()
@click.argument('session_id', required=True)
@click.option('--format', '-f', type=click.Choice(['pdf', 'markdown', 'md']), 
              help='Output format for cached data')
@click.option('--output', '-o', help='Output filename')
def export(session_id, format, output):
    """Export cached session data to different formats."""
    try:
        cache_manager = CacheManager()
        session_data = cache_manager.load_session(session_id)
        
        if not session_data:
            click.echo(f"❌ Session not found: {session_id}")
            return
        
        cached_pages = cache_manager.load_cached_pages(session_id)
        if not cached_pages:
            click.echo(f"❌ No cached pages found for session: {session_id}")
            return
        
        base_url = session_data.get('base_url', '')
        
        if format in ['markdown', 'md']:
            # Use markdown generator
            try:
                # Import here to avoid circular imports
                import sys
                import os
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                
                from generators.markdown import MarkdownGenerator
                
                config = session_data.get('config', {})
                generator = MarkdownGenerator(config)
                
                output_path = generator.generate(cached_pages, base_url, output=output)
                click.echo(f"✅ Exported {len(cached_pages)} pages to: {output_path}")
                
            except ImportError as e:
                click.echo(f"❌ Markdown generator not available: {e}")
        
        elif format == 'pdf':
            # Use PDF generator
            try:
                # Import here to avoid circular imports
                import sys
                import os
                parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                
                from generators.pdf import PDFGenerator
                
                config = session_data.get('config', {})
                generator = PDFGenerator(config)
                
                success = generator.generate_pdf(cached_pages, base_url)
                if success:
                    click.echo(f"✅ Exported {len(cached_pages)} pages to PDF")
                else:
                    click.echo(f"❌ PDF generation failed")
                
            except ImportError as e:
                click.echo(f"❌ PDF generator not available: {e}")
        
        else:
            click.echo("ℹ️  Available formats: pdf, markdown, md")
            click.echo(f"Session {session_id} contains {len(cached_pages)} cached pages")
            click.echo(f"Base URL: {base_url}")
        
    except Exception as e:
        click.echo(f"❌ Error exporting session: {e}")


@cache.command()
@click.argument('session_id', required=True)
def show(session_id):
    """Show detailed information about a cached session."""
    try:
        cache_manager = CacheManager()
        session_data = cache_manager.load_session(session_id)
        
        if not session_data:
            click.echo(f"❌ Session not found: {session_id}")
            return
        
        cached_pages = cache_manager.load_cached_pages(session_id)
        
        click.echo(f"📋 Session Details: {session_id}")
        click.echo("═" * 60)
        click.echo(f"Base URL:         {session_data.get('base_url', 'N/A')}")
        click.echo(f"Status:           {session_data.get('status', 'N/A')}")
        click.echo(f"Created:          {session_data.get('created_at', 'N/A')}")
        click.echo(f"Last Modified:    {session_data.get('last_modified', 'N/A')}")
        click.echo(f"Pages Scraped:    {len(cached_pages)}")
        click.echo(f"Pages Total:      {session_data.get('pages_total', 0)}")
        click.echo(f"")
        
        if session_data.get('status') == 'completed':
            click.echo("✅ Session completed successfully")
        elif session_data.get('status') == 'active':
            remaining = session_data.get('pages_total', 0) - len(cached_pages)
            click.echo(f"🔄 Session can be resumed ({remaining} pages remaining)")
        
        # Show sample URLs
        if cached_pages:
            click.echo(f"")
            click.echo("📄 Sample cached pages:")
            for i, page in enumerate(cached_pages[:5]):
                url = page.get('url', 'Unknown URL')
                word_count = page.get('word_count', 0)
                click.echo(f"  {i+1}. {url} ({word_count} words)")
            
            if len(cached_pages) > 5:
                click.echo(f"  ... and {len(cached_pages) - 5} more pages")
        
    except Exception as e:
        click.echo(f"❌ Error showing session: {e}")


@cache.command()
@click.argument('session_id', required=True)
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
def delete(session_id, force):
    """Delete a cached session."""
    try:
        cache_manager = CacheManager()
        session_data = cache_manager.load_session(session_id)
        
        if not session_data:
            click.echo(f"❌ Session not found: {session_id}")
            return
        
        if not force:
            base_url = session_data.get('base_url', 'Unknown')
            pages_count = session_data.get('pages_scraped', 0)
            
            click.echo(f"⚠️  About to delete session:")
            click.echo(f"   Session ID: {session_id}")
            click.echo(f"   Base URL: {base_url}")
            click.echo(f"   Pages cached: {pages_count}")
            
            if not click.confirm("Are you sure you want to delete this session?"):
                click.echo("❌ Deletion cancelled.")
                return
        
        # Delete session directory
        import shutil
        session_dir = cache_manager.sessions_dir / session_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
            click.echo(f"✅ Deleted session: {session_id}")
        else:
            click.echo(f"❌ Session directory not found: {session_id}")
        
    except Exception as e:
        click.echo(f"❌ Error deleting session: {e}")


@cache.command()
@click.option('--status', type=click.Choice(['in_progress', 'completed', 'abandoned']),
              help='Filter preview sessions by status')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information including full session IDs')
def previews(status, verbose):
    """List cached preview sessions."""
    try:
        cache_manager = CacheManager()
        preview_cache = PreviewCache(cache_manager)
        sessions = preview_cache.list_preview_sessions(status=status)
        
        if not sessions:
            status_text = f" {status}" if status else ""
            click.echo(f"No{status_text} preview sessions found.")
            return
        
        if verbose:
            click.echo("┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐")
            click.echo("│                                                  Preview Sessions                                                           │")
            click.echo("├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤")
        else:
            click.echo("┌─────────────────────────────────────────────────────────────────┐")
            click.echo("│                      Preview Sessions                           │")
            click.echo("├─────────────────────────────────────────────────────────────────┤")
        
        for session in sessions:
            session_id = session['session_id'] if verbose else session['session_id'][:8]
            url_parts = session['base_url'].replace('https://', '').replace('http://', '')
            url_display = url_parts[:25] + '...' if len(url_parts) > 28 else url_parts
            
            status_display = session.get('status', 'unknown')
            status_icon = {'in_progress': '🔄', 'completed': '✅', 'abandoned': '❌'}.get(status_display, '❓')
            
            discovered = session.get('urls_discovered', 0)
            approved = session.get('urls_approved', 0)
            excluded = session.get('urls_excluded', 0)
            
            urls_info = f"{approved}A/{excluded}E/{discovered}T"
            modified = format_time_ago(session.get('last_modified', ''))
            
            if verbose:
                click.echo(f"│ {session_id:<50} {url_display:<28} {urls_info:<12} {modified:<8} {status_icon} │")
            else:
                click.echo(f"│ {session_id:<8} {url_display:<28} {urls_info:<12} {modified:<8} {status_icon} │")
        
        if verbose:
            click.echo("└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘")
        else:
            click.echo("└─────────────────────────────────────────────────────────────────┘")
        click.echo("A=Approved, E=Excluded, T=Total")
        
    except Exception as e:
        click.echo(f"❌ Error listing preview sessions: {e}")


if __name__ == '__main__':
    cache()