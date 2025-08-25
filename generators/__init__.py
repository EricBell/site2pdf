#!/usr/bin/env python3
"""
Content Generators Package
==========================

A collection of output format generators for scraped content.

Available generators:
- pdf: PDF document generation with WeasyPrint
- html: Static HTML generation (future)
- epub: EPUB book generation (future)  
- markdown: Markdown documentation (future)

Base Classes:
- BaseGenerator: Abstract interface for all generators
- ContentValidator: Validates scraped content before generation
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging


class BaseGenerator(ABC):
    """Abstract base class for all content generators."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def generate(self, scraped_data: List[Dict[str, Any]], output_path: str, **kwargs) -> bool:
        """Generate output from scraped data.
        
        Args:
            scraped_data: List of scraped page data
            output_path: Path for output file
            **kwargs: Generator-specific options
            
        Returns:
            bool: True if generation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate generator configuration.
        
        Returns:
            bool: True if config is valid, False otherwise
        """
        pass
    
    def get_supported_formats(self) -> List[str]:
        """Return list of supported output formats."""
        return []
    
    def supports_chunking(self) -> bool:
        """Return whether this generator supports chunking.
        
        Returns:
            bool: True if chunking is supported, False otherwise
        """
        return False
    
    def generate_chunked(self, scraped_data: List[Dict[str, Any]], base_url: str, 
                        chunk_size: Optional[str] = None, chunk_pages: Optional[int] = None,
                        chunk_prefix: Optional[str] = None, **kwargs) -> List[str]:
        """Generate output with chunking support.
        
        Args:
            scraped_data: List of scraped page data
            base_url: Base URL of the scraped site
            chunk_size: Maximum size per chunk (e.g., '5MB')
            chunk_pages: Maximum pages per chunk
            chunk_prefix: Custom prefix for chunk filenames
            **kwargs: Generator-specific options
            
        Returns:
            List[str]: Paths to generated files
        """
        # Default implementation - call regular generate method
        output_path = kwargs.get('output', 'output')
        success = self.generate(scraped_data, output_path, **kwargs)
        return [output_path] if success else []


class ContentValidator:
    """Validates scraped content before generation."""
    
    @staticmethod
    def validate_page_data(page_data: Dict[str, Any]) -> bool:
        """Validate individual page data structure."""
        required_fields = ['url', 'text', 'title']
        return all(field in page_data for field in required_fields)
    
    @staticmethod
    def validate_scraped_data(scraped_data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate entire scraped dataset.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if not scraped_data:
            return False, ["No scraped data provided"]
        
        errors = []
        for i, page_data in enumerate(scraped_data):
            if not ContentValidator.validate_page_data(page_data):
                errors.append(f"Invalid page data at index {i}")
        
        return len(errors) == 0, errors


# Import main generators for convenience
try:
    from .pdf import PDFGenerator
    __all__ = ['BaseGenerator', 'ContentValidator', 'PDFGenerator']
except ImportError:
    __all__ = ['BaseGenerator', 'ContentValidator']

__version__ = "1.0.0"