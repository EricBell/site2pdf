"""
Chunk Manager

Handles chunking of scraped content for output generators.
Supports chunking by file size or page count with size estimation.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class ChunkManager:
    """
    Manages chunking of scraped data for different output formats.
    
    Supports chunking by:
    - Maximum file size (with format-specific size estimation)
    - Maximum page count
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get chunking configuration
        chunking_config = config.get('chunking', {})
        self.default_max_size = chunking_config.get('default_max_size', '10MB')
        
        # Size estimation multipliers for different formats
        size_estimation = chunking_config.get('size_estimation', {})
        self.markdown_overhead = size_estimation.get('markdown_overhead', 1.2)
        self.pdf_overhead = size_estimation.get('pdf_overhead', 2.5)
    
    def should_chunk(self, chunk_size: Optional[str], chunk_pages: Optional[int]) -> bool:
        """Check if chunking should be performed"""
        return chunk_size is not None or chunk_pages is not None
    
    def parse_size(self, size_str: str) -> int:
        """
        Parse size string like '5MB', '100KB' to bytes.
        
        Args:
            size_str: Size string (e.g., '5MB', '100KB', '2GB')
            
        Returns:
            Size in bytes
        """
        if not size_str:
            return 0
        
        size_str = size_str.upper().strip()
        
        # Extract number and unit
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', size_str)
        if not match:
            raise ValueError(f"Invalid size format: {size_str}. Use formats like '5MB', '100KB', '2GB'")
        
        number, unit = match.groups()
        number = float(number)
        
        # Convert to bytes
        unit = unit or 'B'
        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }
        
        if unit not in multipliers:
            raise ValueError(f"Unknown size unit: {unit}")
        
        return int(number * multipliers[unit])
    
    def estimate_content_size(self, content_data: Dict[str, Any], output_format: str) -> int:
        """
        Estimate the output size of content data for a given format.
        
        Args:
            content_data: Single page content data
            output_format: Output format ('pdf', 'markdown', etc.)
            
        Returns:
            Estimated size in bytes
        """
        # Base size calculation from text content
        text_content = content_data.get('text', '')
        html_content = content_data.get('html_content', '')
        
        # Use the longer content as base
        base_content = html_content if len(html_content) > len(text_content) else text_content
        base_size = len(base_content.encode('utf-8'))
        
        # Add metadata overhead
        metadata = content_data.get('metadata', {})
        for value in metadata.values():
            if isinstance(value, str):
                base_size += len(value.encode('utf-8'))
        
        # Apply format-specific overhead multiplier
        if output_format.lower() in ['pdf']:
            estimated_size = int(base_size * self.pdf_overhead)
        elif output_format.lower() in ['markdown', 'md']:
            estimated_size = int(base_size * self.markdown_overhead)
        else:
            # Default overhead
            estimated_size = int(base_size * 1.5)
        
        # Add image size estimates if images are included
        if content_data.get('images'):
            # Rough estimate: 50KB per image on average
            estimated_size += len(content_data['images']) * 50 * 1024
        
        return estimated_size
    
    def chunk_by_size(self, scraped_data: List[Dict[str, Any]], max_size_str: str, 
                      output_format: str) -> List[List[Dict[str, Any]]]:
        """
        Chunk scraped data by maximum file size.
        
        Args:
            scraped_data: List of page data
            max_size_str: Maximum size per chunk (e.g., '5MB')
            output_format: Output format for size estimation
            
        Returns:
            List of chunks, each chunk is a list of page data
        """
        max_size_bytes = self.parse_size(max_size_str)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for page_data in scraped_data:
            page_size = self.estimate_content_size(page_data, output_format)
            
            # If adding this page would exceed max size and we have pages in current chunk
            if current_size + page_size > max_size_bytes and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [page_data]
                current_size = page_size
            else:
                current_chunk.append(page_data)
                current_size += page_size
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
        
        self.logger.info(f"Chunked {len(scraped_data)} pages into {len(chunks)} chunks by size ({max_size_str})")
        return chunks
    
    def chunk_by_pages(self, scraped_data: List[Dict[str, Any]], max_pages: int) -> List[List[Dict[str, Any]]]:
        """
        Chunk scraped data by maximum number of pages.
        
        Args:
            scraped_data: List of page data
            max_pages: Maximum pages per chunk
            
        Returns:
            List of chunks, each chunk is a list of page data
        """
        chunks = []
        for i in range(0, len(scraped_data), max_pages):
            chunk = scraped_data[i:i + max_pages]
            chunks.append(chunk)
        
        self.logger.info(f"Chunked {len(scraped_data)} pages into {len(chunks)} chunks by page count ({max_pages} per chunk)")
        return chunks
    
    def chunk_data(self, scraped_data: List[Dict[str, Any]], chunk_size: Optional[str], 
                   chunk_pages: Optional[int], output_format: str) -> List[List[Dict[str, Any]]]:
        """
        Chunk scraped data based on provided parameters.
        
        Args:
            scraped_data: List of page data
            chunk_size: Maximum size per chunk (takes precedence if both provided)
            chunk_pages: Maximum pages per chunk
            output_format: Output format for size estimation
            
        Returns:
            List of chunks, each chunk is a list of page data
        """
        if not scraped_data:
            return []
        
        # Size-based chunking takes precedence
        if chunk_size:
            return self.chunk_by_size(scraped_data, chunk_size, output_format)
        elif chunk_pages:
            return self.chunk_by_pages(scraped_data, chunk_pages)
        else:
            # No chunking requested
            return [scraped_data]
    
    def generate_chunk_filename(self, base_filename: str, chunk_num: int, total_chunks: int, 
                              extension: str, custom_prefix: Optional[str] = None) -> str:
        """
        Generate filename for a chunk.
        
        Args:
            base_filename: Base filename (without extension)
            chunk_num: Current chunk number (1-based)
            total_chunks: Total number of chunks
            extension: File extension (with or without dot)
            custom_prefix: Custom prefix to use instead of base_filename
            
        Returns:
            Generated chunk filename
        """
        # Clean extension
        if not extension.startswith('.'):
            extension = '.' + extension
        
        # Use custom prefix if provided
        prefix = custom_prefix if custom_prefix else base_filename
        
        # Remove extension from prefix if it exists
        if prefix.endswith(extension):
            prefix = prefix[:-len(extension)]
        
        # Generate filename with zero-padded numbers
        digits = len(str(total_chunks))
        chunk_filename = f"{prefix}_chunk_{chunk_num:0{digits}d}_of_{total_chunks:0{digits}d}{extension}"
        
        return chunk_filename
    
    def generate_summary_info(self, chunks: List[List[Dict[str, Any]]], output_format: str) -> Dict[str, Any]:
        """
        Generate summary information about chunks.
        
        Args:
            chunks: List of chunks
            output_format: Output format
            
        Returns:
            Summary information dictionary
        """
        total_pages = sum(len(chunk) for chunk in chunks)
        
        chunk_info = []
        for i, chunk in enumerate(chunks, 1):
            estimated_size = sum(self.estimate_content_size(page, output_format) for page in chunk)
            chunk_info.append({
                'chunk_number': i,
                'pages': len(chunk),
                'estimated_size_bytes': estimated_size,
                'estimated_size_human': self._format_bytes(estimated_size)
            })
        
        return {
            'total_chunks': len(chunks),
            'total_pages': total_pages,
            'chunks': chunk_info
        }
    
    def _format_bytes(self, size_bytes: int) -> str:
        """Format bytes as human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"