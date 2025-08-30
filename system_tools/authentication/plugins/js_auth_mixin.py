#!/usr/bin/env python3
"""
JavaScript Authentication Mixin

Provides browser automation capabilities for authentication plugins
that need to handle JavaScript-dependent forms.
"""

import time
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

from .base_plugin import AuthResult

logger = logging.getLogger(__name__)

class JavaScriptAuthMixin:
    """
    Mixin class that adds JavaScript execution capabilities to authentication plugins.
    
    This mixin provides browser automation functionality using Selenium WebDriver
    for handling JavaScript-dependent authentication forms.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver: Optional[webdriver.Remote] = None
        self.js_config = self._get_js_config()
    
    def _get_js_config(self) -> Dict[str, Any]:
        """Get JavaScript execution configuration"""
        default_config = {
            'enabled': True,
            'headless': True,
            'timeout': 30,
            'implicit_wait': 10,
            'browser': 'auto',  # auto-detect available browser
            'window_size': (1920, 1080),
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Merge with plugin config
        js_config = self.config.get('javascript', {})
        default_config.update(js_config)
        return default_config
    
    def _check_selenium_availability(self) -> bool:
        """Check if Selenium is available and properly configured"""
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium is not installed. Install with: pip install selenium")
            return False
        return True
    
    def _detect_available_browser(self) -> Optional[str]:
        """Detect which browser is available on the system"""
        import subprocess
        import os
        
        # Check for portable/extracted Chrome first
        portable_chrome_paths = [
            '/tmp/chrome_extracted/opt/google/chrome/chrome',
            '/tmp/chrome/chrome',
            './chrome/chrome'
        ]
        
        for chrome_path in portable_chrome_paths:
            if os.path.exists(chrome_path) and os.access(chrome_path, os.X_OK):
                logger.info(f"Found portable Chrome browser: {chrome_path}")
                self.js_config['chrome_binary_path'] = chrome_path
                return 'chrome'
        
        # Check for system-installed browsers
        browsers_to_try = [
            ('chrome', ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']),
            ('firefox', ['firefox', 'firefox-esr']),
        ]
        
        for browser_type, commands in browsers_to_try:
            for cmd in commands:
                try:
                    subprocess.run([cmd, '--version'], capture_output=True, check=True)
                    logger.info(f"Found {browser_type} browser: {cmd}")
                    return browser_type
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
        
        return None
    
    def _create_driver(self) -> Optional[webdriver.Remote]:
        """Create and configure WebDriver (Chrome or Firefox)"""
        if not self._check_selenium_availability():
            return None
        
        # Determine which browser to use
        browser_type = self.js_config['browser']
        if browser_type == 'auto':
            browser_type = self._detect_available_browser()
            
        if not browser_type:
            logger.error("No supported browser found. Please install one of:")
            logger.error("  - Chrome: sudo apt install google-chrome-stable")
            logger.error("  - Firefox: sudo apt install firefox")
            return None
        
        try:
            if browser_type == 'chrome':
                return self._create_chrome_driver()
            elif browser_type == 'firefox':
                return self._create_firefox_driver()
            else:
                logger.error(f"Unsupported browser type: {browser_type}")
                return None
                
        except WebDriverException as e:
            logger.error(f"Failed to create {browser_type} WebDriver: {e}")
            
            # Try the other browser as fallback
            fallback = 'firefox' if browser_type == 'chrome' else 'chrome'
            if self._detect_available_browser() == fallback:
                logger.info(f"Trying {fallback} as fallback...")
                try:
                    if fallback == 'chrome':
                        return self._create_chrome_driver()
                    else:
                        return self._create_firefox_driver()
                except WebDriverException:
                    pass
            
            logger.error("Failed to create WebDriver with any available browser")
            return None
    
    def _create_chrome_driver(self) -> Optional[webdriver.Chrome]:
        """Create Chrome WebDriver"""
        options = ChromeOptions()
        
        # Set custom binary path if available
        if self.js_config.get('chrome_binary_path'):
            options.binary_location = self.js_config['chrome_binary_path']
            logger.info(f"Using Chrome binary: {self.js_config['chrome_binary_path']}")
        
        # Configure options
        if self.js_config['headless']:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set window size
        width, height = self.js_config['window_size']
        options.add_argument(f'--window-size={width},{height}')
        
        # Set user agent
        if self.js_config.get('user_agent'):
            options.add_argument(f'--user-agent={self.js_config["user_agent"]}')
        
        # Create driver with version matching
        try:
            # Get Chrome version to match ChromeDriver
            chrome_version = None
            if self.js_config.get('chrome_binary_path'):
                import subprocess
                result = subprocess.run([self.js_config['chrome_binary_path'], '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    version_output = result.stdout.strip()
                    # Extract major version (e.g., "139" from "Google Chrome 139.0.7258.154")
                    import re
                    version_match = re.search(r'(\d+)\.', version_output)
                    if version_match:
                        chrome_version = version_match.group(1)
                        logger.info(f"Detected Chrome major version: {chrome_version}")
            
            # Install matching ChromeDriver
            import os
            chromedriver_path = None
            if chrome_version and chrome_version == "139":
                # Use pre-downloaded matching ChromeDriver for Chrome 139
                manual_chromedriver_path = "/tmp/chromedriver-linux64/chromedriver"
                if os.path.exists(manual_chromedriver_path):
                    chromedriver_path = manual_chromedriver_path
                    logger.info(f"Using manually downloaded ChromeDriver {chrome_version}")
                    
            if not chromedriver_path:
                # Fallback to webdriver-manager
                try:
                    chromedriver_path = ChromeDriverManager(chrome_type="chrome-for-testing").install()
                    logger.info(f"Using Chrome for Testing ChromeDriver")
                except Exception as cft_error:
                    logger.warning(f"Chrome for Testing failed: {cft_error}")
                    chromedriver_path = ChromeDriverManager().install()
                
            service = ChromeService(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error(f"ChromeDriver creation failed: {e}")
            logger.error(f"Chrome binary path: {self.js_config.get('chrome_binary_path', 'default')}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise e
        
        # Configure timeouts
        driver.implicitly_wait(self.js_config['implicit_wait'])
        driver.set_page_load_timeout(self.js_config['timeout'])
        
        # Execute stealth script
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info(f"🚀 Created Chrome WebDriver (headless={self.js_config['headless']})")
        return driver
    
    def _create_firefox_driver(self) -> Optional[webdriver.Firefox]:
        """Create Firefox WebDriver"""
        options = FirefoxOptions()
        
        # Configure options
        if self.js_config['headless']:
            options.add_argument('--headless')
        
        # Set window size
        width, height = self.js_config['window_size']
        options.add_argument(f'--width={width}')
        options.add_argument(f'--height={height}')
        
        # Set user agent
        if self.js_config.get('user_agent'):
            options.set_preference("general.useragent.override", self.js_config["user_agent"])
        
        # Disable automation indicators
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        # Create driver
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)
        
        # Configure timeouts
        driver.implicitly_wait(self.js_config['implicit_wait'])
        driver.set_page_load_timeout(self.js_config['timeout'])
        
        logger.info(f"🚀 Created Firefox WebDriver (headless={self.js_config['headless']})")
        return driver
    
    def _cleanup_driver(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🧹 WebDriver cleaned up")
            except Exception as e:
                logger.warning(f"Error during WebDriver cleanup: {e}")
            finally:
                self.driver = None
    
    def _find_element_by_selectors(self, selectors: List[str], timeout: int = 5) -> Optional[Any]:
        """
        Find element using multiple CSS selectors
        
        Args:
            selectors: List of CSS selectors to try
            timeout: Maximum time to wait for element
            
        Returns:
            WebElement if found, None otherwise
        """
        if not self.driver:
            return None
        
        wait = WebDriverWait(self.driver, timeout)
        
        for selector in selectors:
            try:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.debug(f"Found element with selector: {selector}")
                return element
            except TimeoutException:
                continue
        
        logger.debug(f"No element found with selectors: {selectors}")
        return None
    
    def _wait_for_url_change(self, current_url: str, timeout: int = 10) -> bool:
        """
        Wait for URL to change from current URL
        
        Args:
            current_url: Current URL to wait for change from
            timeout: Maximum time to wait
            
        Returns:
            True if URL changed, False if timeout
        """
        if not self.driver:
            return False
        
        wait = WebDriverWait(self.driver, timeout)
        try:
            wait.until(lambda driver: driver.current_url != current_url)
            return True
        except TimeoutException:
            return False
    
    def _wait_for_element_with_text(self, selectors: List[str], text_patterns: List[str], 
                                   timeout: int = 10) -> bool:
        """
        Wait for element containing specific text to appear
        
        Args:
            selectors: CSS selectors to search
            text_patterns: Text patterns to look for (case insensitive)
            timeout: Maximum time to wait
            
        Returns:
            True if element with text found, False otherwise
        """
        if not self.driver:
            return False
        
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        element_text = element.text.lower()
                        for pattern in text_patterns:
                            if pattern.lower() in element_text:
                                logger.debug(f"Found element with text '{pattern}' using selector '{selector}'")
                                return True
                except Exception:
                    continue
            
            time.sleep(0.5)
        
        return False
    
    def perform_login_js(self, session, form, username: str, password: str) -> AuthResult:
        """
        Perform login using JavaScript/browser automation
        
        This method should be overridden by implementing plugins.
        
        Args:
            session: requests.Session (for compatibility, may not be used)
            form: LoginForm object from detect_login_form
            username: Username/email
            password: Password
            
        Returns:
            AuthResult indicating success/failure
        """
        return AuthResult(
            success=False,
            error_message="JavaScript login not implemented in this plugin"
        )
    
    def __enter__(self):
        """Context manager entry - create driver"""
        if self.js_config['enabled']:
            self.driver = self._create_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup driver"""
        self._cleanup_driver()