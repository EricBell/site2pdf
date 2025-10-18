#!/usr/bin/env python3
"""
JavaScript Renderer Module

Provides browser automation for rendering JavaScript-heavy websites
before content extraction. Reuses existing Selenium infrastructure
from the authentication system.
"""

import logging
import time
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Import Selenium components
try:
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available - JavaScript rendering disabled")

# Import our existing WebDriver setup from authentication system
try:
    import sys
    import os

    # Add system_tools to path if not already there
    system_tools_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'system_tools')
    if system_tools_path not in sys.path:
        sys.path.insert(0, system_tools_path)

    from authentication.plugins.js_auth_mixin import JavaScriptAuthMixin
    JS_AUTH_MIXIN_AVAILABLE = True
except ImportError:
    JS_AUTH_MIXIN_AVAILABLE = False
    logger.warning("JavaScriptAuthMixin not available - using basic Selenium setup")


class JavaScriptRenderer:
    """
    Renders JavaScript-heavy pages using browser automation.

    Leverages the existing Selenium infrastructure from the authentication
    system to minimize code duplication and reuse battle-tested WebDriver
    setup with WSL optimizations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JavaScript renderer

        Args:
            config: Configuration dictionary containing javascript settings
        """
        self.config = config
        self.js_config = config.get('javascript', {})
        self.driver: Optional[webdriver.Remote] = None
        self.driver_manager = None

        # Check if JavaScript rendering is enabled
        if not self.js_config.get('enabled_for_content', False):
            logger.info("JavaScript rendering disabled in config")
            return

        # Check Selenium availability
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium not installed. Install with: pip install selenium webdriver-manager")
            logger.error("JavaScript rendering will not work until Selenium is installed")
            return

        # Create driver manager using existing infrastructure
        if JS_AUTH_MIXIN_AVAILABLE:
            logger.info("Using JavaScriptAuthMixin for WebDriver management")
            # Create a minimal config object for the mixin
            mixin_config = {
                'javascript': self.js_config,
                'config': config
            }

            # Create an instance that inherits from JavaScriptAuthMixin
            class RendererDriverManager(JavaScriptAuthMixin):
                def __init__(self, cfg):
                    self.config = cfg
                    super().__init__()

            self.driver_manager = RendererDriverManager(mixin_config)
        else:
            logger.warning("JavaScriptAuthMixin not available - basic Selenium setup")
            self.driver_manager = None

    def _wait_for_page_ready(self, timeout: int = 30) -> bool:
        """
        Wait for page to be fully loaded and JavaScript to finish executing

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if page is ready, False if timeout
        """
        if not self.driver:
            return False

        try:
            # Wait for document.readyState to be complete
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Give additional time for dynamic content to render
            # This helps with SPAs and infinite scroll sites
            additional_wait = self.js_config.get('additional_wait', 2)
            if additional_wait > 0:
                logger.debug(f"Waiting {additional_wait}s for dynamic content...")
                time.sleep(additional_wait)

            # Check if page has finished loading AJAX requests
            # This is a heuristic - works for jQuery and some frameworks
            try:
                ajax_complete = self.driver.execute_script(
                    "return typeof jQuery !== 'undefined' ? jQuery.active === 0 : true"
                )
                if not ajax_complete:
                    logger.debug("Waiting for AJAX requests to complete...")
                    time.sleep(2)
            except:
                pass  # jQuery might not be present

            return True

        except TimeoutException:
            logger.warning(f"Page load timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Error waiting for page ready: {e}")
            return False

    def _detect_infinite_scroll(self) -> bool:
        """
        Detect if page uses infinite scroll pattern

        Returns:
            True if infinite scroll detected
        """
        if not self.driver:
            return False

        try:
            # Check page height before and after scroll
            initial_height = self.driver.execute_script("return document.body.scrollHeight")

            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # Check if height increased (new content loaded)
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            return new_height > initial_height

        except Exception as e:
            logger.debug(f"Error detecting infinite scroll: {e}")
            return False

    def _handle_infinite_scroll(self, max_scrolls: int = 5):
        """
        Handle infinite scroll by scrolling and waiting for content

        Args:
            max_scrolls: Maximum number of scrolls to perform
        """
        if not self.driver:
            return

        logger.info(f"Handling infinite scroll (max {max_scrolls} scrolls)...")

        for i in range(max_scrolls):
            # Get current scroll height
            last_height = self.driver.execute_script("return document.body.scrollHeight")

            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new content to load
            time.sleep(2)

            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # Break if no new content loaded
            if new_height == last_height:
                logger.debug(f"No new content after scroll {i+1}")
                break

            logger.debug(f"Scroll {i+1}: {last_height} -> {new_height}")

        # Scroll back to top for consistent content extraction
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

    def render_page(self, url: str) -> Optional[str]:
        """
        Render a page with JavaScript and return final HTML

        Args:
            url: URL to render

        Returns:
            Rendered HTML as string, or None if rendering failed
        """
        if not self.driver:
            logger.error("WebDriver not initialized - cannot render page")
            return None

        try:
            logger.info(f"Rendering JavaScript page: {url}")

            # Load the page
            self.driver.get(url)

            # Wait for page to be ready
            if not self._wait_for_page_ready():
                logger.warning("Page may not be fully loaded")

            # Handle infinite scroll if enabled
            if self.js_config.get('handle_infinite_scroll', False):
                if self._detect_infinite_scroll():
                    max_scrolls = self.js_config.get('max_scroll_attempts', 5)
                    self._handle_infinite_scroll(max_scrolls)

            # Get the final rendered HTML
            rendered_html = self.driver.page_source

            logger.info(f"Successfully rendered page ({len(rendered_html)} chars)")
            return rendered_html

        except TimeoutException as e:
            logger.error(f"Timeout rendering page {url}: {e}")
            # Try to recover - check if driver is still alive
            try:
                self.driver.current_url  # Test if driver is responsive
            except:
                logger.error("WebDriver appears to have crashed - attempting recovery")
                self.stop()
                if self.start():
                    logger.info("WebDriver recovered successfully")
                else:
                    logger.error("Failed to recover WebDriver")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver error rendering {url}: {e}")
            # Check if it's a connection error (driver crashed)
            error_str = str(e).lower()
            if "connection refused" in error_str or "cannot connect" in error_str:
                logger.error("WebDriver connection lost - attempting recovery")
                self.stop()
                if self.start():
                    logger.info("WebDriver recovered successfully")
                else:
                    logger.error("Failed to recover WebDriver")
            return None
        except Exception as e:
            logger.error(f"Unexpected error rendering {url}: {e}")
            return None

    def start(self) -> bool:
        """
        Start the browser and initialize WebDriver

        Returns:
            True if successful, False otherwise
        """
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium not available - cannot start renderer")
            return False

        if self.driver:
            logger.debug("WebDriver already started")
            return True

        try:
            if self.driver_manager:
                # Use existing infrastructure
                logger.info("Starting WebDriver using JavaScriptAuthMixin...")
                self.driver = self.driver_manager._create_driver()

                if self.driver:
                    logger.info("✅ WebDriver started successfully")
                    return True
                else:
                    logger.error("Failed to create WebDriver")
                    return False
            else:
                logger.error("No driver manager available")
                return False

        except Exception as e:
            logger.error(f"Error starting WebDriver: {e}")
            return False

    def stop(self):
        """Stop the browser and cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🧹 WebDriver stopped")
            except Exception as e:
                logger.warning(f"Error stopping WebDriver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Context manager entry - start browser"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup browser"""
        self.stop()

    def is_enabled(self) -> bool:
        """Check if JavaScript rendering is enabled and available"""
        return (
            SELENIUM_AVAILABLE and
            self.js_config.get('enabled_for_content', False) and
            self.driver_manager is not None
        )
