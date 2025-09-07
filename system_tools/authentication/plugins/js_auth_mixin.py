#!/usr/bin/env python3
"""
JavaScript Authentication Mixin

Provides browser automation capabilities for authentication plugins
that need to handle JavaScript-dependent forms.
"""

import time
import logging
import os
from datetime import datetime
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
        self.screenshot_counter = 1
        self.screenshot_session_dir = None
        self.debug_screenshots_enabled = self.js_config.get('debug_screenshots', True)
    
    def _get_js_config(self) -> Dict[str, Any]:
        """Get JavaScript execution configuration"""
        default_config = {
            'enabled': True,
            'headless': True,
            'timeout': 30,
            'implicit_wait': 10,
            'browser': 'auto',  # auto-detect available browser
            'window_size': (1920, 1080),
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'debug_screenshots': True
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
        
        # Check if we're in WSL environment
        is_wsl = False
        try:
            with open('/proc/version', 'r') as f:
                proc_version = f.read().lower()
                is_wsl = 'microsoft' in proc_version or 'wsl' in proc_version
        except:
            pass
        
        if is_wsl:
            # In WSL, prefer Chrome over Firefox due to faster startup times
            print("🐧 WSL environment detected - prioritizing Chrome for faster startup")
            browsers_to_try = [
                ('chrome', ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']),
                ('firefox', ['firefox', 'firefox-esr']),
            ]
        else:
            # On regular Linux, Firefox is often more stable
            browsers_to_try = [
                ('firefox', ['firefox', 'firefox-esr']),
                ('chrome', ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']),
            ]
        
        for browser_type, commands in browsers_to_try:
            for cmd in commands:
                try:
                    result = subprocess.run([cmd, '--version'], capture_output=True, check=True, text=True)
                    version = result.stdout.strip()
                    logger.info(f"Found {browser_type} browser: {cmd} - {version}")
                    # Clear any portable Chrome binary path when using system browser
                    if 'chrome_binary_path' in self.js_config:
                        del self.js_config['chrome_binary_path']
                    return browser_type
                except (subprocess.CalledProcessError, FileNotFoundError):
                    logger.debug(f"Browser check failed for: {cmd}")
                    continue
        
        # Check for portable/extracted Chrome as fallback
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
        
        logger.error("No browser found. Install one of:")
        logger.error("  Firefox: sudo apt install firefox")
        logger.error("  Chrome: sudo apt install google-chrome-stable")
        return None
    
    def _create_driver(self) -> Optional[webdriver.Remote]:
        """Create and configure WebDriver (Chrome or Firefox)"""
        if not self._check_selenium_availability():
            return None
        
        # Setup WSL display if needed
        if not self._setup_wsl_display():
            logger.error("Failed to setup display for browser automation")
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
        
        # Try browsers in order of preference with fallback
        browsers_to_try = [browser_type]
        if browser_type == 'chrome':
            browsers_to_try.append('firefox')
        elif browser_type == 'firefox':
            browsers_to_try.append('chrome')
        
        for attempt_browser in browsers_to_try:
            try:
                logger.info(f"Attempting to create {attempt_browser} WebDriver...")
                if attempt_browser == 'chrome':
                    return self._create_chrome_driver()
                elif attempt_browser == 'firefox':
                    return self._create_firefox_driver()
            except Exception as e:
                # Classify the error type for better handling
                error_msg = str(e).lower()
                if "timeout" in error_msg or "read timed out" in error_msg:
                    logger.warning(f"{attempt_browser} WebDriver timed out: {e}")
                    logger.warning("This is common in WSL environments due to display server issues")
                elif "connection" in error_msg:
                    logger.warning(f"{attempt_browser} WebDriver connection failed: {e}")
                else:
                    logger.warning(f"Failed to create {attempt_browser} WebDriver: {e}")
                
                if attempt_browser != browsers_to_try[-1]:  # Not the last attempt
                    logger.info(f"Trying fallback browser...")
                    continue
        
        # All browsers failed - suggest manual intervention
        logger.error("🚫 All browser automation failed. Switching to manual intervention mode.")
        logger.error("💡 Common causes: WSL display issues, browser startup timeouts, missing dependencies")
        return None
    
    def _setup_wsl_display(self) -> bool:
        """Setup display for WSL environment if needed"""
        import os
        import subprocess
        
        # Check if we're in WSL
        try:
            with open('/proc/version', 'r') as f:
                proc_version = f.read().lower()
                is_wsl = 'microsoft' in proc_version or 'wsl' in proc_version
        except:
            is_wsl = False
        
        if not is_wsl:
            logger.debug("Not in WSL environment, skipping display setup")
            return True
        
        logger.info("🐧 WSL environment detected")
        
        # Force headless mode in WSL for better reliability
        if not self.js_config['headless']:
            logger.info("🖥️ Forcing headless mode for WSL compatibility")
            self.js_config['headless'] = True
        
        # For headless mode, we don't need a display server
        if self.js_config['headless']:
            logger.debug("Headless mode configured, no display server needed")
            return True
        
        # Check if DISPLAY is already set
        if os.environ.get('DISPLAY'):
            logger.debug(f"DISPLAY already configured: {os.environ['DISPLAY']}")
            return True
        
        # Try to setup Xvfb virtual display (fallback option)
        try:
            logger.info("🖼️ Attempting virtual display setup...")
            
            # Check if Xvfb is available
            try:
                subprocess.run(['which', 'Xvfb'], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("Xvfb not available. Install with: sudo apt install xvfb")
                raise FileNotFoundError("Xvfb not found")
            
            # Kill any existing Xvfb on :99
            try:
                subprocess.run(['pkill', '-f', 'Xvfb.*:99'], capture_output=True)
            except:
                pass  # Ignore if no existing process
            
            # Start Xvfb on display :99 with better options for stability
            xvfb_cmd = [
                'Xvfb', ':99', 
                '-screen', '0', '1920x1080x24',
                '-ac',  # Disable access control
                '+extension', 'GLX',
                '-nolisten', 'tcp',
                '-dpi', '96'
            ]
            
            xvfb_process = subprocess.Popen(
                xvfb_cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid  # Start in new process group
            )
            
            # Set DISPLAY environment variable
            os.environ['DISPLAY'] = ':99'
            
            # Give Xvfb time to initialize
            import time
            time.sleep(3)
            
            # Verify Xvfb is running
            if xvfb_process.poll() is None:
                logger.info("✅ Virtual display setup complete: DISPLAY=:99")
                return True
            else:
                logger.warning("⚠️ Xvfb process terminated unexpectedly")
                raise Exception("Xvfb failed to start")
            
        except Exception as e:
            logger.warning(f"Virtual display setup failed: {e}")
            logger.info("🔄 Ensuring headless mode is enabled")
            self.js_config['headless'] = True
            return True
    
    def _create_chrome_driver(self) -> Optional[webdriver.Chrome]:
        """Create Chrome WebDriver"""
        options = ChromeOptions()
        
        # Set custom binary path if available
        if self.js_config.get('chrome_binary_path'):
            options.binary_location = self.js_config['chrome_binary_path']
            logger.info(f"Using Chrome binary: {self.js_config['chrome_binary_path']}")
        
        # Configure options for WSL/Linux environment
        if self.js_config['headless']:
            options.add_argument('--headless=new')  # Use new headless mode
        
        # Essential WSL compatibility options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')  # Important for WSL
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI,VizDisplayCompositor')
        
        # Additional stability options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-web-security')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors-spki-list')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-dev-tools')
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--password-store=basic')
        options.add_argument('--single-process')  # Can help with WSL stability
        options.add_argument('--disable-zygote')  # Reduces process complexity
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("detach", True)
        
        # Network logging capabilities (comment out if causing crashes)
        # options.set_capability('goog:loggingPrefs', {
        #     'performance': 'INFO',
        #     'browser': 'INFO'
        # })
        
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
            import subprocess
            
            # Try to get version from system Chrome or custom binary
            chrome_command = self.js_config.get('chrome_binary_path', 'google-chrome')
            try:
                result = subprocess.run([chrome_command, '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    version_output = result.stdout.strip()
                    # Extract major version (e.g., "140" from "Google Chrome 140.0.7339.80")
                    import re
                    version_match = re.search(r'(\d+)\.', version_output)
                    if version_match:
                        chrome_version = version_match.group(1)
                        logger.info(f"Detected Chrome major version: {chrome_version}")
            except FileNotFoundError:
                logger.warning(f"Could not get Chrome version from: {chrome_command}")
            
            # Install matching ChromeDriver
            import os
            chromedriver_path = None
            
            # For Chrome versions that are too new, skip version-specific downloads
            # and let webdriver-manager handle it
            if chrome_version and chrome_version == "131":
                # Use pre-downloaded matching ChromeDriver for Chrome 131
                manual_chromedriver_path = "/tmp/chromedriver-linux64/chromedriver"
                if os.path.exists(manual_chromedriver_path):
                    chromedriver_path = manual_chromedriver_path
                    logger.info(f"Using manually downloaded ChromeDriver {chrome_version}")
            elif chrome_version and chrome_version == "139":
                # Use pre-downloaded matching ChromeDriver for Chrome 139
                manual_chromedriver_path = "/tmp/chromedriver-linux64/chromedriver"
                if os.path.exists(manual_chromedriver_path):
                    chromedriver_path = manual_chromedriver_path
                    logger.info(f"Using manually downloaded ChromeDriver {chrome_version}")
                    
            if not chromedriver_path:
                # Use webdriver-manager to get the latest compatible ChromeDriver
                try:
                    logger.info("Using webdriver-manager to get compatible ChromeDriver")
                    chromedriver_path = ChromeDriverManager().install()
                    logger.info(f"Downloaded ChromeDriver via webdriver-manager")
                except Exception as wdm_error:
                    logger.error(f"ChromeDriver installation failed: {wdm_error}")
                    raise wdm_error
                
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
        """Create Firefox WebDriver with improved WSL compatibility and timeout handling"""
        options = FirefoxOptions()
        
        # Force headless mode in WSL environments for better compatibility
        import os
        is_wsl = False
        try:
            with open('/proc/version', 'r') as f:
                proc_version = f.read().lower()
                is_wsl = 'microsoft' in proc_version or 'wsl' in proc_version
        except:
            pass
            
        if is_wsl or self.js_config['headless']:
            options.add_argument('--headless')
            logger.info("🖥️ Using headless mode (WSL detected or configured)")
        
        # Set window size
        width, height = self.js_config['window_size']
        options.add_argument(f'--width={width}')
        options.add_argument(f'--height={height}')
        
        # Set user agent
        if self.js_config.get('user_agent'):
            options.set_preference("general.useragent.override", self.js_config["user_agent"])
        
        # Disable automation indicators and improve stability
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("marionette.logging", 0)  # Reduce logging
        options.set_preference("browser.startup.page", 0)  # Blank startup page
        options.set_preference("browser.sessionstore.resume_from_crash", False)
        
        # WSL-specific preferences for faster startup
        options.set_preference("media.navigator.permission.disabled", True)
        options.set_preference("dom.file.createInChild", True)
        options.set_preference("extensions.blocklist.enabled", False)  # Disable extension blocklist
        options.set_preference("browser.safebrowsing.enabled", False)  # Disable safe browsing
        options.set_preference("browser.safebrowsing.malware.enabled", False)
        options.set_preference("browser.ping-centre.telemetry", False)  # Disable telemetry
        options.set_preference("datareporting.healthreport.service.enabled", False)
        options.set_preference("datareporting.healthreport.uploadEnabled", False)
        options.set_preference("datareporting.policy.dataSubmissionEnabled", False)
        options.set_preference("app.update.enabled", False)  # Disable auto-updates
        options.set_preference("browser.startup.homepage", "about:blank")  # Fast startup
        options.set_preference("startup.homepage_welcome_url", "")
        options.set_preference("startup.homepage_welcome_url.additional", "")
        
        # Additional performance optimizations
        options.set_preference("browser.cache.disk.enable", False)
        options.set_preference("browser.cache.memory.enable", True)
        options.set_preference("browser.cache.offline.enable", False)
        options.set_preference("network.http.use-cache", False)
        
        try:
            logger.info("📥 Getting GeckoDriver...")
            geckodriver_path = GeckoDriverManager().install()
            logger.info(f"✅ GeckoDriver ready: {geckodriver_path}")
            
            # Create service with reduced timeout
            service = FirefoxService(geckodriver_path)
            
            logger.info("🚀 Starting Firefox WebDriver (this may take 30-60 seconds)...")
            
            # Create driver with aggressive timeout handling
            import socket
            import threading
            import time
            from selenium.common.exceptions import TimeoutException, WebDriverException
            
            # Set aggressive timeout for WSL environments
            timeout_seconds = 20  # Reduced from 30 to 20 seconds
            
            def create_driver_with_timeout():
                """Create WebDriver in a separate thread with timeout"""
                result = {'driver': None, 'error': None}
                
                def driver_creation():
                    try:
                        original_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(timeout_seconds)
                        
                        logger.info(f"⏱️ Starting Firefox with {timeout_seconds}s timeout...")
                        driver = webdriver.Firefox(service=service, options=options)
                        
                        # Configure driver timeouts
                        driver.implicitly_wait(self.js_config['implicit_wait'])
                        driver.set_page_load_timeout(self.js_config['timeout'])
                        
                        result['driver'] = driver
                        socket.setdefaulttimeout(original_timeout)
                        
                    except Exception as e:
                        result['error'] = e
                        if 'original_timeout' in locals():
                            socket.setdefaulttimeout(original_timeout)
                
                # Start driver creation in thread
                thread = threading.Thread(target=driver_creation, daemon=True)
                thread.start()
                
                # Wait for completion with timeout
                thread.join(timeout_seconds + 5)  # Extra 5 seconds buffer
                
                if thread.is_alive():
                    logger.error(f"🚫 Firefox startup exceeded {timeout_seconds}s timeout")
                    result['error'] = TimeoutError(f"Firefox startup timeout after {timeout_seconds} seconds")
                
                return result
            
            try:
                result = create_driver_with_timeout()
                
                if result['driver']:
                    logger.info(f"🦊 Firefox WebDriver created successfully (headless={options.headless})")
                    return result['driver']
                elif result['error']:
                    raise result['error']
                else:
                    raise TimeoutError("Firefox WebDriver creation failed - unknown error")
                
            except (TimeoutException, TimeoutError, socket.timeout) as timeout_error:
                logger.error(f"🕐 Firefox WebDriver startup timeout: {timeout_error}")
                logger.error("💡 This timeout is common in WSL environments")
                logger.error("💡 Falling back to manual intervention mode")
                raise timeout_error
            except WebDriverException as wd_error:
                error_msg = str(wd_error).lower()
                if "timeout" in error_msg or "read timed out" in error_msg:
                    logger.error(f"🕐 Firefox WebDriver connection timeout: {wd_error}")
                    logger.error("💡 Firefox startup is too slow for WSL environment")
                else:
                    logger.error(f"🚫 Firefox WebDriver error: {wd_error}")
                raise wd_error
            
        except Exception as e:
            logger.error(f"Firefox WebDriver creation failed: {e}")
            if "timeout" in str(e).lower():
                logger.error("💡 Suggestion: This timeout is often caused by WSL display issues")
                logger.error("💡 Manual intervention mode will be available as fallback")
            raise e
    
    def _setup_screenshot_session(self):
        """Setup screenshot session directory"""
        if not self.debug_screenshots_enabled or not self.driver:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_session_dir = f"debug_screenshots/auth_{timestamp}"
        os.makedirs(self.screenshot_session_dir, exist_ok=True)
        logger.info(f"📸 Debug screenshots enabled: {self.screenshot_session_dir}")
        
        # Setup network logging
        self._setup_network_logging()
    
    def _setup_network_logging(self):
        """Enable Chrome DevTools Protocol network logging"""
        if not self.driver:
            return
            
        try:
            # Enable network domain
            self.driver.execute_cdp_cmd('Network.enable', {})
            self.network_requests = []
            
            # Add event listener for network requests
            self.driver.execute_cdp_cmd('Runtime.enable', {})
            
            logger.info("🌐 Network request logging enabled")
            
        except Exception as e:
            logger.warning(f"Failed to enable network logging: {e}")
    
    def _log_network_requests(self, step_name: str):
        """Log captured network requests for debugging"""
        if not self.driver:
            return
            
        try:
            # Get network activity
            logs = self.driver.get_log('performance')
            
            network_events = []
            for log_entry in logs:
                message = log_entry.get('message', {})
                if isinstance(message, str):
                    import json
                    try:
                        message = json.loads(message)
                    except:
                        continue
                        
                method = message.get('message', {}).get('method', '')
                params = message.get('message', {}).get('params', {})
                
                if method in ['Network.requestWillBeSent', 'Network.responseReceived']:
                    network_events.append({
                        'method': method,
                        'url': params.get('request', {}).get('url', '') or params.get('response', {}).get('url', ''),
                        'httpMethod': params.get('request', {}).get('method', ''),
                        'status': params.get('response', {}).get('status', ''),
                        'timestamp': message.get('message', {}).get('timestamp', 0)
                    })
            
            if network_events:
                print(f"🌐 Network Activity during {step_name}:")
                for event in network_events[-10:]:  # Show last 10 events
                    if event['url'] and not event['url'].startswith('data:'):
                        print(f"  {event['method']}: {event['httpMethod']} {event['url']} - {event['status']}")
                        
                # Save detailed network log
                if self.screenshot_session_dir:
                    log_file = os.path.join(self.screenshot_session_dir, f"{step_name}_network.txt")
                    with open(log_file, 'w') as f:
                        for event in network_events:
                            f.write(f"{event}\n")
                        
        except Exception as e:
            logger.warning(f"Failed to log network requests: {e}")
    
    def _take_debug_screenshot(self, step_name: str, description: str = ""):
        """Take screenshot for debugging authentication steps"""
        if not self.debug_screenshots_enabled or not self.driver or not self.screenshot_session_dir:
            return
        
        try:
            filename = f"step_{self.screenshot_counter:03d}_{step_name}.png"
            filepath = os.path.join(self.screenshot_session_dir, filename)
            
            self.driver.save_screenshot(filepath)
            print(f"📸 Screenshot: {filename} - {description}")
            self.screenshot_counter += 1
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
    
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
            if self.driver:
                self._setup_screenshot_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup driver"""
        self._cleanup_driver()