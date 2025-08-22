#!/usr/bin/env python3
"""
site2pdf - Website to PDF Scraper
Convenient entry point script in project root.
"""

import sys
import os

# Add src directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Import and run the CLI
from cli import scrape

if __name__ == '__main__':
    try:
        scrape()
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)