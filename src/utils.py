import os
import logging
import logging.handlers
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """Load configuration from YAML file with environment variable overrides."""
    # Load environment variables
    load_dotenv()
    
    # Load default config
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        else:
            # Return default config if file doesn't exist
            config = get_default_config()
    except Exception as e:
        logging.warning(f"Could not load config from {config_path}: {e}")
        config = get_default_config()
    
    # Override with environment variables
    config = apply_env_overrides(config)
    
    return config


def get_default_config() -> Dict[str, Any]:
    """Get default configuration values."""
    return {
        'crawling': {
            'max_depth': 5,
            'request_delay': 2.0,
            'max_pages': 1000,
            'timeout': 30,
            'follow_external': False,
            'respect_robots': True
        },
        'http': {
            'user_agent': 'site2pdf/1.0 (+https://github.com/yourusername/site2pdf)',
            'max_retries': 3,
            'retry_delay': 5,
            'use_cookies': True
        },
        'content': {
            'include_images': True,
            'max_image_size': 10,
            'allowed_image_formats': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'include_metadata': True,
            'min_content_length': 100
        },
        'pdf': {
            'output_filename': 'scraped_website.pdf',
            'page_size': 'A4',
            'margins': {
                'top': 20,
                'bottom': 20,
                'left': 15,
                'right': 15
            },
            'font': {
                'family': 'Arial',
                'size': 11
            },
            'include_toc': True,
            'include_page_numbers': True
        },
        'logging': {
            'level': 'INFO',
            'log_to_file': True,
            'log_filename': 'scraper.log',
            'rotate_logs': True
        },
        'directories': {
            'output_dir': 'output',
            'temp_dir': 'temp',
            'logs_dir': 'logs'
        },
        'filters': {
            'exclude_patterns': [
                r'.*\.pdf$',
                r'.*\.zip$',
                r'.*\.exe$',
                r'/admin/.*',
                r'/login.*',
                r'/logout.*'
            ],
            'skip_extensions': ['pdf', 'zip', 'exe', 'dmg', 'pkg'],
            'max_url_length': 2000
        }
    }


def apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration."""
    env_mappings = {
        'CRAWL_DELAY_OVERRIDE': ('crawling', 'request_delay', float),
        'MAX_DEPTH': ('crawling', 'max_depth', int),
        'MAX_PAGES': ('crawling', 'max_pages', int),
        'TIMEOUT': ('crawling', 'timeout', int),
        'USER_AGENT': ('http', 'user_agent', str),
        'MAX_RETRIES': ('http', 'max_retries', int),
        'INCLUDE_IMAGES': ('content', 'include_images', lambda x: x.lower() == 'true'),
        'MAX_IMAGE_SIZE': ('content', 'max_image_size', int),
        'OUTPUT_FILENAME': ('pdf', 'output_filename', str),
        'LOG_LEVEL': ('logging', 'level', str),
        'DEBUG_MODE': ('logging', 'level', lambda x: 'DEBUG' if x.lower() == 'true' else config['logging']['level'])
    }
    
    for env_var, (section, key, converter) in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            try:
                converted_value = converter(value)
                config[section][key] = converted_value
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid value for {env_var}: {value} - {e}")
    
    return config


def setup_logging(logging_config: Dict[str, Any]) -> logging.Logger:
    """Setup logging configuration."""
    # Create logs directory
    logs_dir = logging_config.get('logs_dir', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, logging_config.get('level', 'INFO').upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, logging_config.get('level', 'INFO').upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if logging_config.get('log_to_file', True):
        log_filename = os.path.join(logs_dir, logging_config.get('log_filename', 'scraper.log'))
        
        if logging_config.get('rotate_logs', True):
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_filename,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
        else:
            # Regular file handler
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            
        file_handler.setLevel(logging.DEBUG)  # File gets all logs
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted."""
    import re
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def clean_filename(filename: str) -> str:
    """Clean filename to be filesystem safe."""
    import re
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename.strip()


def ensure_directories(config: Dict[str, Any]) -> None:
    """Ensure all required directories exist."""
    directories = [
        config['directories']['output_dir'],
        config['directories']['temp_dir'],
        config['directories']['logs_dir']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def cleanup_temp_files(config: Dict[str, Any]) -> None:
    """Clean up temporary files."""
    import shutil
    
    temp_dir = config['directories']['temp_dir']
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
            logging.info("Cleaned up temporary files")
        except Exception as e:
            logging.warning(f"Could not clean up temp directory: {e}")


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    return urlparse(url).netloc.lower()


def is_valid_image_url(url: str) -> bool:
    """Check if URL points to a valid image."""
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg']
    
    from urllib.parse import urlparse
    path = urlparse(url).path.lower()
    
    return any(path.endswith(f'.{ext}') for ext in image_extensions)


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def create_progress_callback(description: str = "Processing"):
    """Create a progress callback function for long operations."""
    from tqdm import tqdm
    
    def callback(current: int, total: int, message: str = ""):
        if not hasattr(callback, 'pbar'):
            callback.pbar = tqdm(total=total, desc=description, unit="items")
        
        callback.pbar.set_description(f"{description}: {message}")
        callback.pbar.update(current - callback.pbar.n)
        
        if current >= total:
            callback.pbar.close()
            delattr(callback, 'pbar')
    
    return callback