import random
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import requests
try:
    from .content_classifier import ContentType
except ImportError:
    from content_classifier import ContentType


class HumanBehaviorSimulator:
    """Simulates human browsing behavior to avoid detection."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('human_behavior', {})
        self.logger = logging.getLogger(__name__)
        
        # Session tracking
        self.pages_visited = 0
        self.session_start_time = time.time()
        self.last_request_time = 0
        self.current_referrer = None
        
        # Behavior parameters
        self.delays = self.config.get('delays', {})
        self.browsing = self.config.get('browsing', {})
        
        # Anti-detection state
        self.consecutive_fast_requests = 0
        self.rate_limit_detected = False
        self.last_rate_limit_time = 0
        
    def calculate_delay(self, url: str, content_type: ContentType, 
                       content_data: Optional[Dict] = None) -> float:
        """Calculate human-like delay before next request."""
        
        # Base reading time
        base_range = self.delays.get('base_reading_time', [2, 8])
        base_delay = random.uniform(base_range[0], base_range[1])
        
        # Navigation decision time
        decision_range = self.delays.get('navigation_decision', [1, 3])
        decision_delay = random.uniform(decision_range[0], decision_range[1])
        
        total_delay = base_delay + decision_delay
        
        # Content complexity adjustment
        if content_data:
            word_count = content_data.get('word_count', 0)
            image_count = content_data.get('image_count', 0)
            
            # More content = more reading time
            if word_count > 1000:
                complexity_multiplier = self.delays.get('complexity_multiplier', 1.5)
                total_delay *= complexity_multiplier
            elif word_count > 500:
                total_delay *= 1.2
            
            # Images also add reading time
            if image_count > 0:
                total_delay += min(image_count * 0.5, 2.0)  # Max 2 seconds for images
        
        # Content type adjustments
        if content_type == ContentType.DOCUMENTATION:
            total_delay *= 1.3  # Documentation takes more time to read
        elif content_type == ContentType.NAVIGATION:
            total_delay *= 0.7  # Navigation is quicker
        
        # Fatigue factor (get slower over time)
        fatigue_factor = self.delays.get('fatigue_factor', 0.1)
        fatigue_multiplier = 1 + (self.pages_visited * fatigue_factor * 0.01)
        total_delay *= fatigue_multiplier
        
        # Time-of-day adjustments
        if self.browsing.get('respect_business_hours', False):
            total_delay *= self._get_time_of_day_factor()
        
        # Weekend factor
        if self._is_weekend() and self.browsing.get('weekend_factor'):
            total_delay *= self.browsing['weekend_factor']
        
        # Add random variance
        variance_percent = self.delays.get('variance_percent', 30)
        variance = 1 + random.uniform(-variance_percent/100, variance_percent/100)
        total_delay *= variance
        
        # Rate limiting adjustments
        if self.rate_limit_detected:
            total_delay *= 3  # Much slower if rate limited
        elif self.consecutive_fast_requests > 5:
            total_delay *= 1.5  # Slow down if too fast
        
        # Minimum delay to avoid suspicion
        min_delay = self.delays.get('minimum_delay', 0.5)
        total_delay = max(total_delay, min_delay)
        
        # Maximum delay for practicality
        max_delay = self.delays.get('maximum_delay', 30)
        total_delay = min(total_delay, max_delay)
        
        return total_delay
    
    def should_take_session_break(self) -> bool:
        """Determine if we should take a longer break (simulate human breaks)."""
        break_after = self.browsing.get('session_break_after', 50)
        return self.pages_visited > 0 and self.pages_visited % break_after == 0
    
    def get_session_break_duration(self) -> float:
        """Get duration for session break."""
        break_range = self.browsing.get('session_break_duration', [30, 120])
        return random.uniform(break_range[0], break_range[1])
    
    def update_session_state(self, url: str, response: requests.Response = None):
        """Update session state after a request."""
        self.pages_visited += 1
        current_time = time.time()
        
        # Track request timing
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < 1.0:  # Very fast request
                self.consecutive_fast_requests += 1
            else:
                self.consecutive_fast_requests = 0
        
        self.last_request_time = current_time
        
        # Update referrer for next request
        self.current_referrer = url
        
        # Check for rate limiting
        if response:
            self._check_rate_limiting(response)
    
    def _check_rate_limiting(self, response: requests.Response):
        """Check if we're being rate limited."""
        if response.status_code == 429:
            self.rate_limit_detected = True
            self.last_rate_limit_time = time.time()
            self.logger.warning("Rate limiting detected (HTTP 429)")
        elif response.status_code in [503, 502]:
            # Server errors might indicate overload
            self.consecutive_fast_requests += 2
            self.logger.warning(f"Server error {response.status_code}, slowing down")
        else:
            # Check if rate limiting has expired
            if self.rate_limit_detected and time.time() - self.last_rate_limit_time > 300:
                self.rate_limit_detected = False
                self.logger.info("Rate limiting cooldown expired")
    
    def _get_time_of_day_factor(self) -> float:
        """Get delay multiplier based on time of day."""
        current_hour = datetime.now().hour
        
        # Business hours (9-17) are normal speed
        if 9 <= current_hour <= 17:
            return 1.0
        # Evening (18-22) is slightly slower
        elif 18 <= current_hour <= 22:
            return 1.2
        # Late night/early morning is much slower
        else:
            return 1.8
    
    def _is_weekend(self) -> bool:
        """Check if it's weekend."""
        return datetime.now().weekday() >= 5  # Saturday = 5, Sunday = 6
    
    def get_realistic_headers(self, referrer: str = None) -> Dict[str, str]:
        """Generate realistic browser headers for Microsoft Edge."""
        
        # Latest Microsoft Edge user agent (Windows 11)
        edge_versions = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
        ]
        
        headers = {
            'User-Agent': random.choice(edge_versions),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Charset': 'utf-8, iso-8859-1;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',  # Do Not Track
        }
        
        # Add referrer if we have one (simulate following links)
        if referrer or self.current_referrer:
            ref_url = referrer or self.current_referrer
            headers['Referer'] = ref_url
            headers['Sec-Fetch-Site'] = 'same-origin'
        
        return headers
    
    def should_respect_robots_txt(self) -> bool:
        """Determine if we should respect robots.txt (humans sometimes ignore it)."""
        respect_chance = self.browsing.get('robots_respect_probability', 0.8)
        return random.random() < respect_chance
    
    def simulate_human_delay(self, url: str, content_type: ContentType, 
                           content_data: Optional[Dict] = None):
        """Execute the calculated delay with human-like progress updates."""
        
        # Calculate delay
        delay = self.calculate_delay(url, content_type, content_data)
        
        # Check for session break
        if self.should_take_session_break():
            break_duration = self.get_session_break_duration()
            self.logger.info(f"Taking session break: {break_duration:.1f}s (after {self.pages_visited} pages)")
            time.sleep(break_duration)
        
        # Log the delay reasoning
        if self.logger.isEnabledFor(logging.DEBUG):
            delay_reasons = []
            if content_data and content_data.get('word_count', 0) > 500:
                delay_reasons.append(f"reading {content_data['word_count']} words")
            if content_type == ContentType.DOCUMENTATION:
                delay_reasons.append("documentation page")
            if self.pages_visited > 20:
                delay_reasons.append(f"fatigue after {self.pages_visited} pages")
            
            reason_str = f" ({', '.join(delay_reasons)})" if delay_reasons else ""
            self.logger.debug(f"Human delay: {delay:.1f}s{reason_str}")
        
        # Execute delay with occasional "micro-breaks" to simulate real behavior
        remaining = delay
        while remaining > 0:
            chunk = min(remaining, random.uniform(0.5, 2.0))
            time.sleep(chunk)
            remaining -= chunk
            
            # Occasional micro-break (simulate user distraction)
            if remaining > 5 and random.random() < 0.1:
                micro_break = random.uniform(1, 3)
                time.sleep(micro_break)
                remaining -= micro_break
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        session_duration = time.time() - self.session_start_time
        return {
            'pages_visited': self.pages_visited,
            'session_duration': session_duration,
            'avg_time_per_page': session_duration / max(self.pages_visited, 1),
            'rate_limited': self.rate_limit_detected,
            'consecutive_fast_requests': self.consecutive_fast_requests
        }