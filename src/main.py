#!/usr/bin/env python3
"""
ScrapBloodhound - Website to PDF Scraper
Main entry point for the application.
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import scrape

if __name__ == '__main__':
    scrape()