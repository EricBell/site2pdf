#!/usr/bin/env python3
"""
site2pdf - Website to PDF Scraper
Convenient entry point script in project root.
"""

import sys
import os

# Add src directory and project root to Python path  
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)  # For generators and system_tools packages
sys.path.insert(0, src_path)      # For src modules

# Import and run the CLI
from cli import main

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Application interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)