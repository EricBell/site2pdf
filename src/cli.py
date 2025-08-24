import click
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from .scraper import WebScraper
    from .utils import load_config, setup_logging
    from .preview import URLPreview
except ImportError:
    from scraper import WebScraper
    from utils import load_config, setup_logging
    from preview import URLPreview

# Import from new package structure
try:
    # Try importing from project root (when run via run.py)
    from generators.pdf import PDFGenerator
    from generators.markdown import MarkdownGenerator
except ImportError:
    try:
        # Try importing from parent directory (when run from src/)
        import sys
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from generators.pdf import PDFGenerator
        from generators.markdown import MarkdownGenerator
    except ImportError:
        # Fallback to old location during transition
        try:
            from .pdf_generator import PDFGenerator
            from generators.markdown import MarkdownGenerator
        except ImportError:
            from pdf_generator import PDFGenerator
            from generators.markdown import MarkdownGenerator


@click.command()
@click.argument('base_url', type=str)
@click.option('--output', '-o', 
              type=click.Path(), 
              help='Output PDF filename')
@click.option('--max-depth', '-d', 
              type=int, 
              help='Maximum crawl depth')
@click.option('--max-pages', '-p', 
              type=int, 
              help='Maximum number of pages to scrape')
@click.option('--delay', 
              type=float, 
              help='Delay between requests (seconds)')
@click.option('--config', '-c', 
              type=click.Path(exists=True), 
              help='Configuration file path')
@click.option('--verbose', '-v', 
              is_flag=True, 
              help='Enable verbose logging')
@click.option('--dry-run', 
              is_flag=True, 
              help='Show what would be scraped without actually doing it')
@click.option('--preview', 
              is_flag=True, 
              help='Preview URLs in tree structure with interactive approval')
@click.option('--exclude', 
              multiple=True, 
              help='URL patterns to exclude (can be used multiple times)')
@click.option('--save-approved', 
              type=click.Path(), 
              help='Save approved URLs to file for reuse')
@click.option('--load-approved', 
              type=click.Path(exists=True), 
              help='Load previously approved URLs from file')
@click.option('--include-menus', 
              is_flag=True, 
              help='Include navigation menus in output (default: exclude)')
@click.option('--format', '-f',
              type=click.Choice(['pdf', 'markdown', 'md'], case_sensitive=False),
              default='pdf',
              help='Output format (pdf, markdown)')
@click.option('--resume', 
              help='Resume from cached session ID')
@click.option('--resume-preview',
              help='Resume from cached preview session ID')
@click.option('--from-cache',
              help='Generate output from cached session (no scraping)')
def scrape(base_url: str, 
           output: Optional[str],
           max_depth: Optional[int],
           max_pages: Optional[int], 
           delay: Optional[float],
           config: Optional[str],
           verbose: bool,
           dry_run: bool,
           preview: bool,
           exclude: tuple,
           save_approved: Optional[str],
           load_approved: Optional[str],
           include_menus: bool,
           format: str,
           resume: Optional[str],
           resume_preview: Optional[str],
           from_cache: Optional[str]):
    """
    Scrape a website and generate output document.
    
    BASE_URL: The starting URL to scrape from
    """
    try:
        # Load configuration
        config_path = config or 'config.yaml'
        app_config = load_config(config_path)
        
        # Override config with CLI options
        if max_depth:
            app_config['crawling']['max_depth'] = max_depth
        if max_pages:
            app_config['crawling']['max_pages'] = max_pages
        if delay:
            app_config['crawling']['request_delay'] = delay
        if output:
            app_config['pdf']['output_filename'] = output
        if verbose:
            app_config['logging']['level'] = 'DEBUG'
        if include_menus:
            app_config['content']['include_menus'] = True
            
        # Setup logging
        logger = setup_logging(app_config['logging'])
        
        # Handle cache operations first
        if from_cache:
            return _handle_from_cache(from_cache, format, output, verbose, app_config)
        
        # Validate base URL
        if not base_url.startswith(('http://', 'https://')):
            click.echo(f"Error: Invalid URL '{base_url}'. Must start with http:// or https://")
            sys.exit(1)
            
        # Create output directories
        os.makedirs(app_config['directories']['output_dir'], exist_ok=True)
        os.makedirs(app_config['directories']['temp_dir'], exist_ok=True)
        os.makedirs(app_config['directories']['logs_dir'], exist_ok=True)
        
        # Handle exclude patterns
        exclude_patterns = list(exclude) if exclude else []
        
        if dry_run:
            click.echo(f"🔍 Dry run mode - analyzing what would be scraped from: {base_url}")
            scraper = WebScraper(app_config, dry_run=True, exclude_patterns=exclude_patterns, verbose=verbose)
            try:
                urls, classifications = scraper.discover_urls(base_url)
                if urls:
                    click.echo(f"\n📄 Would scrape {len(urls)} pages:")
                    for i, url in enumerate(urls[:10], 1):  # Show first 10
                        content_type = classifications.get(url, "📄 Content")
                        click.echo(f"  {i}. {content_type.value if hasattr(content_type, 'value') else content_type} {url}")
                    if len(urls) > 10:
                        click.echo(f"  ... and {len(urls) - 10} more pages")
                else:
                    click.echo("❌ No suitable URLs found for scraping")
            finally:
                scraper.cleanup()
            return
        
        # Handle preview mode with interactive approval
        if preview or load_approved:
            approved_urls = set()
            
            if load_approved:
                # Create temporary preview to load URLs
                temp_preview = URLPreview(exclude_patterns)
                approved_urls = temp_preview.load_approved_urls(load_approved)
                if not approved_urls:
                    click.echo("No approved URLs loaded. Switching to discovery mode.")
                    preview = True
            
            if preview or not approved_urls:
                click.echo(f"🔍 Discovering URLs from: {base_url}")
                scraper = WebScraper(app_config, dry_run=True, exclude_patterns=exclude_patterns, verbose=verbose)
                try:
                    discovered_urls, classifications = scraper.discover_urls(base_url)
                    
                    # Create preview with path scope information
                    url_preview = URLPreview(exclude_patterns, scraper.path_scope)
                    
                    if not discovered_urls:
                        click.echo("❌ No URLs discovered. Check the URL and try again.")
                        sys.exit(1)
                    
                    # Build tree with classifications and interactive approval
                    tree = url_preview.build_url_tree(discovered_urls, classifications)
                    approved_urls = url_preview.interactive_exclude(tree)
                finally:
                    scraper.cleanup()
                
                if approved_urls is None:  # User quit
                    sys.exit(0)
                
                # Final approval
                if not url_preview.final_approval(approved_urls):
                    click.echo("Scraping cancelled.")
                    sys.exit(0)
                
                # Save approved URLs if requested
                if save_approved:
                    url_preview.save_approved_urls(approved_urls, save_approved)
            
            # Scrape approved URLs
            if approved_urls:
                click.echo(f"🚀 Starting to scrape {len(approved_urls)} approved URLs")
                scraper = WebScraper(app_config, exclude_patterns=exclude_patterns, verbose=verbose, 
                                   cache_session_id=resume)
                try:
                    scraped_data = scraper.scrape_approved_urls(approved_urls)
                finally:
                    scraper.cleanup()
            else:
                click.echo("❌ No URLs approved for scraping.")
                sys.exit(1)
        else:
            # Standard scraping mode
            click.echo(f"🚀 Starting to scrape: {base_url}")
            scraper = WebScraper(app_config, exclude_patterns=exclude_patterns, verbose=verbose, 
                               cache_session_id=resume)
            try:
                scraped_data = scraper.scrape_website(base_url)
            finally:
                scraper.cleanup()
        
        if not scraped_data:
            click.echo("❌ No content was scraped. Check the URL and try again.")
            sys.exit(1)
            
        click.echo(f"✅ Scraped {len(scraped_data)} pages")
        
        # Generate output based on format
        try:
            from .progress_tracker import ProgressTracker, Phase
        except ImportError:
            from progress_tracker import ProgressTracker, Phase
        progress = ProgressTracker(verbose=verbose)
        
        # Normalize format
        format_lower = format.lower()
        if format_lower == 'md':
            format_lower = 'markdown'
        
        if format_lower == 'pdf':
            progress.start_phase(Phase.PDF_GENERATION, 1, "Creating PDF document")
            generator = PDFGenerator(app_config)
            output_path = generator.generate_pdf(scraped_data, base_url)
            progress.finish_phase("PDF generated successfully")
            click.echo(f"🎉 PDF generated successfully: {output_path}")
        
        elif format_lower == 'markdown':
            progress.start_phase(Phase.PDF_GENERATION, 1, "Creating Markdown document")  # Reusing PDF phase for now
            generator = MarkdownGenerator(app_config)
            output_path = generator.generate(scraped_data, base_url, output=output)
            progress.finish_phase("Markdown generated successfully")
            click.echo(f"🎉 Markdown generated successfully: {output_path}")
        
        progress.cleanup()
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def _handle_from_cache(session_id: str, format: str, output: Optional[str], verbose: bool, app_config: dict):
    """Generate output from cached session data without scraping."""
    try:
        from .cache_manager import CacheManager
    except ImportError:
        from cache_manager import CacheManager
    
    cache_manager = CacheManager(config=app_config)
    
    # Load session data
    session_data = cache_manager.load_session(session_id)
    if not session_data:
        click.echo(f"❌ Session not found: {session_id}")
        sys.exit(1)
    
    # Load cached pages
    cached_pages = cache_manager.load_cached_pages(session_id)
    if not cached_pages:
        click.echo(f"❌ No cached pages found for session: {session_id}")
        sys.exit(1)
    
    base_url = session_data.get('base_url', '')
    click.echo(f"📦 Loading {len(cached_pages)} pages from cache session: {session_id[:8]}...")
    
    # Generate output based on format
    try:
        from .progress_tracker import ProgressTracker, Phase
    except ImportError:
        from progress_tracker import ProgressTracker, Phase
    
    progress = ProgressTracker(verbose=verbose)
    
    # Normalize format
    format_lower = format.lower()
    if format_lower == 'md':
        format_lower = 'markdown'
    
    if format_lower == 'pdf':
        progress.start_phase(Phase.PDF_GENERATION, 1, "Creating PDF from cached data")
        generator = PDFGenerator(app_config)
        output_path = generator.generate_pdf(cached_pages, base_url)
        progress.finish_phase("PDF generated successfully from cache")
        click.echo(f"🎉 PDF generated from cache: {output_path}")
    
    elif format_lower == 'markdown':
        progress.start_phase(Phase.PDF_GENERATION, 1, "Creating Markdown from cached data")  # Reusing PDF phase for now
        generator = MarkdownGenerator(app_config)
        output_path = generator.generate(cached_pages, base_url, output=output)
        progress.finish_phase("Markdown generated successfully from cache")
        click.echo(f"🎉 Markdown generated from cache: {output_path}")
    
    progress.cleanup()


# Import todo commands
try:
    from .todo_cli import todo
    from .cache_cli import cache
except ImportError:
    from todo_cli import todo
    from cache_cli import cache


@click.group()
def main():
    """site2pdf - Convert websites to PDF documents with caching, todo management, and multi-format output."""
    pass


# Add command groups to the main group
main.add_command(scrape)
main.add_command(todo)
main.add_command(cache)


if __name__ == '__main__':
    main()