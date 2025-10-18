#!/usr/bin/env python3
"""Test JS rendering with a simpler JS-rendered site."""

from src.js_renderer import JavaScriptRenderer
from src.extractor import ContentExtractor
from src.utils import load_config

# Load config
config = load_config('config.yaml')

# Enable JavaScript rendering with longer timeout
config['javascript']['enabled_for_content'] = True
config['javascript']['timeout'] = 60  # Increase timeout to 60 seconds

# Test with a simpler JS site (React documentation)
test_url = 'https://react.dev/'

print(f"Testing JavaScript rendering for: {test_url}\n")

# Create renderer
renderer = JavaScriptRenderer(config)

if renderer.is_enabled():
    print("JavaScript renderer is enabled")

    # Start the browser
    if renderer.start():
        print("✅ Browser started successfully\n")

        try:
            # Render the page
            print("Rendering page with JavaScript (60s timeout)...")
            rendered_html = renderer.render_page(test_url)

            if rendered_html:
                print(f"✅ Page rendered: {len(rendered_html)} characters\n")

                # Now extract content from rendered HTML
                extractor = ContentExtractor(config, js_renderer=None)  # Don't double-render
                # Use extract_content but skip the JS rendering since we already have rendered HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(rendered_html, 'html.parser')
                extractor._remove_unwanted_elements(soup)

                # Extract text
                text_content = extractor._clean_text(soup.get_text())

                print("=" * 60)
                print("EXTRACTED CONTENT FROM RENDERED HTML:")
                print("=" * 60)
                print(f"Text length: {len(text_content)} characters")
                print(f"Word count: {len(text_content.split())}")
                print("\n" + "=" * 60)
                print("EXTRACTED TEXT (first 500 chars):")
                print("=" * 60)
                print(text_content[:500])
                print("\n" + "=" * 60)
                print(f"Passes threshold: {len(text_content) >= config['content']['min_content_length']}")
            else:
                print("❌ Failed to render page")
        finally:
            # Stop the browser
            renderer.stop()
            print("\n🧹 Browser stopped")
    else:
        print("❌ Failed to start browser")
else:
    print("❌ JavaScript renderer not enabled")
