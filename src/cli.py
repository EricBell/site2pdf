import click
import os
import sys
from pathlib import Path
from typing import Optional

from .scraper import WebScraper
from .pdf_generator import PDFGenerator
from .utils import load_config, setup_logging
from .preview import URLPreview


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
           load_approved: Optional[str]):
    """
    Scrape a website and generate a PDF document.
    
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
            
        # Setup logging
        logger = setup_logging(app_config['logging'])
        
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
            scraper = WebScraper(app_config, dry_run=True, exclude_patterns=exclude_patterns)
            urls = scraper.discover_urls(base_url)
            click.echo(f"📄 Would scrape {len(urls)} pages:")
            for i, url in enumerate(urls[:10], 1):  # Show first 10
                click.echo(f"  {i}. {url}")
            if len(urls) > 10:
                click.echo(f"  ... and {len(urls) - 10} more pages")
            return
        
        # Handle preview mode with interactive approval
        if preview or load_approved:
            url_preview = URLPreview(exclude_patterns)
            approved_urls = set()
            
            if load_approved:
                approved_urls = url_preview.load_approved_urls(load_approved)
                if not approved_urls:
                    click.echo("No approved URLs loaded. Switching to discovery mode.")
                    preview = True
            
            if preview or not approved_urls:
                click.echo(f"🔍 Discovering URLs from: {base_url}")
                scraper = WebScraper(app_config, dry_run=True, exclude_patterns=exclude_patterns)
                discovered_urls = scraper.discover_urls(base_url)
                
                if not discovered_urls:
                    click.echo("❌ No URLs discovered. Check the URL and try again.")
                    sys.exit(1)
                
                # Build tree and interactive approval
                tree = url_preview.build_url_tree(discovered_urls)
                approved_urls = url_preview.interactive_exclude(tree)
                
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
                scraper = WebScraper(app_config, exclude_patterns=exclude_patterns)
                scraped_data = scraper.scrape_approved_urls(approved_urls)
            else:
                click.echo("❌ No URLs approved for scraping.")
                sys.exit(1)
        else:
            # Standard scraping mode
            click.echo(f"🚀 Starting to scrape: {base_url}")
            scraper = WebScraper(app_config, exclude_patterns=exclude_patterns)
            scraped_data = scraper.scrape_website(base_url)
        
        if not scraped_data:
            click.echo("❌ No content was scraped. Check the URL and try again.")
            sys.exit(1)
            
        click.echo(f"✅ Scraped {len(scraped_data)} pages")
        
        # Generate PDF
        click.echo("📄 Generating PDF...")
        pdf_generator = PDFGenerator(app_config)
        output_path = pdf_generator.generate_pdf(scraped_data, base_url)
        
        click.echo(f"🎉 PDF generated successfully: {output_path}")
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    scrape()