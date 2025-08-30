#!/usr/bin/env python3
"""
JavaScript Dependencies Installer

Installs optional JavaScript authentication dependencies (Selenium, ChromeDriver).
Run this script to enable JavaScript-based authentication for sites that require it.
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, description=""):
    """Run a command and handle errors"""
    try:
        logger.info(f"🔧 {description}")
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            logger.info(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed:")
        logger.error(f"   {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8+ required for Selenium support")
        return False
    logger.info(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def install_selenium():
    """Install Selenium WebDriver"""
    logger.info("📦 Installing Selenium WebDriver...")
    
    packages = [
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.0"
    ]
    
    success = True
    for package in packages:
        if not run_command(f"pip install {package}", f"Installing {package}"):
            success = False
    
    return success

def verify_installation():
    """Verify that Selenium and WebDriver are working"""
    logger.info("🔍 Verifying installation...")
    
    try:
        # Test Selenium import
        import selenium
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager
        logger.info(f"✅ Selenium {selenium.__version__} installed successfully")
        
        # Test ChromeDriver download (but don't launch browser)
        chrome_driver_path = ChromeDriverManager().install()
        logger.info(f"✅ ChromeDriver installed at: {chrome_driver_path}")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ ChromeDriver setup failed: {e}")
        logger.info("   This might be normal on headless systems")
        return True  # Don't fail on ChromeDriver issues

def main():
    """Main installation process"""
    logger.info("🚀 Installing JavaScript Authentication Dependencies")
    logger.info("=" * 50)
    
    # Check requirements
    if not check_python_version():
        sys.exit(1)
    
    # Install packages
    if not install_selenium():
        logger.error("❌ Installation failed")
        sys.exit(1)
    
    # Verify installation
    if not verify_installation():
        logger.error("❌ Verification failed")
        sys.exit(1)
    
    logger.info("")
    logger.info("🎉 JavaScript authentication dependencies installed successfully!")
    logger.info("")
    logger.info("You can now use JavaScript-enabled authentication with commands like:")
    logger.info("  python run.py scrape --auth email_otp --username your@email.com URL")
    logger.info("")
    logger.info("The system will automatically detect when JavaScript is needed")
    logger.info("and fall back to browser automation.")

if __name__ == "__main__":
    main()