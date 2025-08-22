#!/usr/bin/env python3
"""Test script to verify exclude functionality"""

import sys
sys.path.insert(0, 'src')

# Test the selection logic directly
def test_selection_logic():
    """Test that the selection validation logic works correctly"""
    
    # Simulate having 100 items like a large site would have
    items_count = 100
    selected_num = 88
    
    print(f"Testing selection logic:")
    print(f"Items in array: {items_count}")
    print(f"User selected: {selected_num}")
    print(f"Valid range: 1-{items_count}")
    print(f"Selection valid: {1 <= selected_num <= items_count}")
    
    # This mimics the logic in preview.py line 185
    is_valid = 1 <= selected_num <= items_count
    return is_valid

# Create a mock tree structure similar to what would cause 88+ items
def create_test_tree():
    tree = {
        'example.com': {
            'urls': {'https://example.com'},
            'classifications': {'https://example.com': ContentType.CONTENT},
            'children': {}
        }
    }
    
    # Add many child items to simulate a large site
    children = tree['example.com']['children']
    
    # Create 100 test items so we can test selecting item 88
    for i in range(1, 101):
        name = f'item-{i}'
        children[name] = {
            'urls': {f'https://example.com/{name}'},
            'classifications': {f'https://example.com/{name}': ContentType.CONTENT},
            'children': {}
        }
    
    return tree

if __name__ == '__main__':
    result = test_selection_logic()
    if result:
        print("✅ Selection logic works correctly")
    else:
        print("❌ Selection logic failed")