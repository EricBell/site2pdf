#!/bin/bash

# site2pdf Executable Builder
# This script builds a standalone executable for the site2pdf application

set -e  # Exit on any error

echo "🔨 Building site2pdf executable..."

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in a virtual environment. Consider activating one first."
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Clean previous builds
if [ -d "build" ]; then
    echo "🧹 Cleaning previous build artifacts..."
    rm -rf build
fi

if [ -d "dist" ]; then
    echo "🧹 Cleaning previous distribution..."
    rm -rf dist
fi

# Build the executable using PyInstaller
echo "🚀 Building executable with PyInstaller..."
pyinstaller site2pdf.spec

# Check if build was successful
if [ -f "dist/site2pdf" ]; then
    echo "✅ Build successful!"
    echo "📍 Executable location: $(pwd)/dist/site2pdf"
    
    # Show file size
    SIZE=$(du -h dist/site2pdf | cut -f1)
    echo "📏 Executable size: $SIZE"
    
    # Test the executable
    echo "🧪 Testing executable..."
    if ./dist/site2pdf --help > /dev/null 2>&1; then
        echo "✅ Executable test passed!"
    else
        echo "❌ Executable test failed!"
        exit 1
    fi
    
    echo ""
    echo "🎉 Build complete! You can now run the executable with:"
    echo "   ./dist/site2pdf [options]"
    echo ""
    echo "📋 To distribute this executable:"
    echo "   1. Copy the 'dist/site2pdf' file to the target system"
    echo "   2. Make it executable: chmod +x site2pdf"
    echo "   3. Run it: ./site2pdf [options]"
    
else
    echo "❌ Build failed! Check the output above for errors."
    exit 1
fi