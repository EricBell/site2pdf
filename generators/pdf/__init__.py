#!/usr/bin/env python3
"""
PDF Generator
=============

High-quality PDF generation from scraped web content using WeasyPrint.

Features:
- HTML to PDF conversion with CSS styling
- Image embedding and optimization
- Table of contents generation
- Robust error handling and content validation
- Custom styling and formatting options

Dependencies:
- weasyprint: HTML/CSS to PDF conversion
- beautifulsoup4: HTML parsing and sanitization

Usage:
    from generators.pdf import PDFGenerator
    
    generator = PDFGenerator(config)
    success = generator.generate(scraped_data, "output.pdf")
"""

from .pdf_generator import PDFGenerator

__all__ = ['PDFGenerator']
__version__ = "1.0.0"