import time
from typing import Dict, List, Optional, Any
from enum import Enum
import click
from tqdm import tqdm
from dataclasses import dataclass
try:
    from .content_classifier import ContentType
except ImportError:
    from content_classifier import ContentType


class Phase(Enum):
    DISCOVERY = "🔍 Discovering URLs"
    CLASSIFICATION = "🏷️ Classifying content"
    SCRAPING = "📄 Scraping pages"
    PDF_GENERATION = "📖 Generating PDF"


@dataclass
class ScrapingStats:
    """Statistics for the scraping process."""
    total_discovered: int = 0
    by_type: Dict[ContentType, int] = None
    scraped_count: int = 0
    excluded_count: int = 0
    failed_count: int = 0
    total_words: int = 0
    total_images: int = 0
    start_time: float = None
    
    def __post_init__(self):
        if self.by_type is None:
            self.by_type = {content_type: 0 for content_type in ContentType}
        if self.start_time is None:
            self.start_time = time.time()


class ProgressTracker:
    """Enhanced progress tracking with multi-level notifications."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = ScrapingStats()
        self.current_phase: Optional[Phase] = None
        self.phase_progress: Optional[tqdm] = None
        self.overall_progress: Optional[tqdm] = None
        self.current_url: str = ""
        self.phase_start_time: float = 0
        
    def start_phase(self, phase: Phase, total: int = 0, description: str = ""):
        """Start a new phase of the scraping process."""
        if self.phase_progress:
            self.phase_progress.close()
            
        self.current_phase = phase
        self.phase_start_time = time.time()
        
        phase_desc = f"{phase.value}"
        if description:
            phase_desc += f" - {description}"
            
        self.phase_progress = tqdm(
            total=total,
            desc=phase_desc,
            unit="items",
            colour="blue",
            leave=True
        )
        
        click.echo(f"\n{phase.value} {'(Phase ' + str(list(Phase).index(phase) + 1) + '/4)' if phase != Phase.PDF_GENERATION else '(Phase 4/4)'}")
        
    def update_phase(self, amount: int = 1, description: str = ""):
        """Update the current phase progress."""
        if self.phase_progress:
            if description:
                self.phase_progress.set_description(f"{self.current_phase.value} - {description}")
            self.phase_progress.update(amount)
    
    def set_current_activity(self, activity: str, url: str = "", content_type: ContentType = None):
        """Set the current activity being performed."""
        self.current_url = url
        
        if self.phase_progress:
            activity_text = activity
            if url:
                # Truncate long URLs for display
                display_url = url if len(url) <= 60 else f"{url[:57]}..."
                activity_text += f": {display_url}"
            
            if content_type and content_type != ContentType.EXCLUDED:
                activity_text = f"{content_type.value} | {activity_text}"
            
            self.phase_progress.set_description(activity_text)
    
    def log_discovery(self, urls: List[str], classifications: Dict[str, ContentType]):
        """Log URL discovery results."""
        self.stats.total_discovered = len(urls)
        
        # Count by type
        for url in urls:
            content_type = classifications.get(url, ContentType.TECHNICAL)
            self.stats.by_type[content_type] += 1
        
        # Display summary
        doc_count = self.stats.by_type[ContentType.DOCUMENTATION]
        content_count = self.stats.by_type[ContentType.CONTENT]
        nav_count = self.stats.by_type[ContentType.NAVIGATION]
        excluded_count = self.stats.by_type[ContentType.EXCLUDED] + self.stats.by_type[ContentType.TECHNICAL]
        
        click.echo(f"\n📊 Discovery Summary:")
        click.echo(f"   Total URLs found: {self.stats.total_discovered}")
        click.echo(f"   📖 Documentation: {doc_count}")
        click.echo(f"   📄 Content pages: {content_count}")
        click.echo(f"   🧭 Navigation: {nav_count}")
        click.echo(f"   ❌ Excluded: {excluded_count}")
        
        approved_count = doc_count + content_count + nav_count
        if approved_count > 0:
            click.echo(f"   ✅ Ready to scrape: {approved_count} pages")
        
    def log_page_scraped(self, url: str, content_data: Dict[str, Any], content_type: ContentType):
        """Log a successfully scraped page."""
        self.stats.scraped_count += 1
        
        if content_data:
            word_count = content_data.get('word_count', 0)
            image_count = content_data.get('image_count', 0)
            self.stats.total_words += word_count
            self.stats.total_images += image_count
            
            quality_level = content_data.get('quality_level', 'Unknown')
            
            # Show detailed info if verbose
            if self.verbose:
                click.echo(f"   ✅ {content_type.value} | {quality_level} quality | {word_count} words | {image_count} images")
        
        self.update_phase(1, f"Scraped {self.stats.scraped_count} pages")
    
    def log_page_skipped(self, url: str, reason: str, content_type: ContentType = None):
        """Log a skipped page."""
        self.stats.excluded_count += 1
        
        if self.verbose:
            type_str = f"{content_type.value} | " if content_type else ""
            click.echo(f"   ⚠️ {type_str}Skipped: {reason}")
    
    def log_page_failed(self, url: str, error: str):
        """Log a failed page."""
        self.stats.failed_count += 1
        
        if self.verbose:
            click.echo(f"   ❌ Failed: {error}")
        
        self.update_phase(1, f"Failed to scrape page")
    
    def log_retry(self, url: str, attempt: int, max_attempts: int):
        """Log a retry attempt."""
        if self.verbose:
            click.echo(f"   🔄 Retrying {url} (attempt {attempt}/{max_attempts})")
    
    def show_scraping_summary(self):
        """Show final scraping statistics."""
        elapsed_time = time.time() - self.stats.start_time
        
        click.echo(f"\n📈 Scraping Summary:")
        click.echo(f"   ✅ Successfully scraped: {self.stats.scraped_count} pages")
        click.echo(f"   📝 Total content: {self.stats.total_words:,} words")
        click.echo(f"   🖼️ Total images: {self.stats.total_images}")
        click.echo(f"   ⚠️ Skipped/excluded: {self.stats.excluded_count}")
        click.echo(f"   ❌ Failed: {self.stats.failed_count}")
        click.echo(f"   ⏱️ Total time: {self._format_duration(elapsed_time)}")
        
        if self.stats.scraped_count > 0:
            avg_words = self.stats.total_words // self.stats.scraped_count
            click.echo(f"   📊 Average: {avg_words} words per page")
    
    def finish_phase(self, success_message: str = ""):
        """Finish the current phase."""
        if self.phase_progress:
            self.phase_progress.close()
            self.phase_progress = None
        
        if success_message:
            click.echo(f"   ✅ {success_message}")
        
        if self.current_phase:
            elapsed = time.time() - self.phase_start_time
            click.echo(f"   ⏱️ Phase completed in {self._format_duration(elapsed)}")
    
    def cleanup(self):
        """Clean up progress bars."""
        if self.phase_progress:
            self.phase_progress.close()
        if self.overall_progress:
            self.overall_progress.close()
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def estimate_time_remaining(self, completed: int, total: int) -> str:
        """Estimate remaining time based on current progress."""
        if completed == 0:
            return "Unknown"
        
        elapsed = time.time() - self.phase_start_time
        rate = completed / elapsed
        remaining = (total - completed) / rate if rate > 0 else 0
        
        return self._format_duration(remaining)
    
    def show_quality_alert(self, url: str, quality_level: str, reason: str):
        """Show quality-based alerts."""
        if quality_level == "Low":
            click.echo(f"   ⚠️ Low quality content detected: {reason}")
        elif quality_level == "High":
            if self.verbose:
                click.echo(f"   ⭐ High quality content found!")
    
    def show_discovery_alert(self, message: str, url: str = ""):
        """Show discovery-related alerts."""
        display_url = f": {url}" if url else ""
        click.echo(f"   ✨ {message}{display_url}")