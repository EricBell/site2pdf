#!/usr/bin/env python3
"""Quick diagnostic script to test content extraction from a URL."""

import requests
from src.extractor import ContentExtractor
from src.utils import load_config

# Load config
config = load_config('config.yaml')

# Test URL
test_url = 'https://minesweeper.online/'

print(f"Testing content extraction from: {test_url}\n")

# Fetch the page
response = requests.get(test_url, timeout=30)
print(f"HTTP Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Raw HTML length: {len(response.text)} characters\n")

# Extract content
extractor = ContentExtractor(config)
content_data = extractor.extract_content(response.text, test_url)

if content_data:
    print("=" * 60)
    print("EXTRACTED CONTENT DATA:")
    print("=" * 60)
    print(f"Title: {content_data['metadata'].get('title', 'N/A')}")
    print(f"Description: {content_data['metadata'].get('description', 'N/A')}")
    print(f"Text length: {len(content_data['text'])} characters")
    print(f"Word count: {content_data['word_count']}")
    print(f"Char count: {content_data['char_count']}")
    print(f"Headings: {len(content_data['headings'])}")
    print(f"Images: {len(content_data['images'])}")
    print(f"Links: {len(content_data['links'])}")
    print("\n" + "=" * 60)
    print("EXTRACTED TEXT (first 500 chars):")
    print("=" * 60)
    print(content_data['text'][:500])
    print("\n" + "=" * 60)
    print(f"Min content length requirement: {config['content']['min_content_length']}")
    print(f"Actual text length: {len(content_data['text'])}")
    print(f"Passes threshold: {len(content_data['text']) >= config['content']['min_content_length']}")
else:
    print("ERROR: Failed to extract content")
