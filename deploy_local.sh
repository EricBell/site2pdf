#!/bin/bash

# deploy_local.sh - Deploy executable to /usr/local/bin
# Usage: ./deploy_local.sh <executable_file>

set -e  # Exit on any error

# Check if argument provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <executable_file>"
    echo "Example: $0 dist/site2pdf"
    exit 1
fi

EXECUTABLE_FILE="$1"

# Check if file exists
if [ ! -f "$EXECUTABLE_FILE" ]; then
    echo "❌ Error: File '$EXECUTABLE_FILE' does not exist"
    exit 1
fi

# Get just the filename without path
FILENAME=$(basename "$EXECUTABLE_FILE")

echo "🚀 Deploying '$FILENAME' to /usr/local/bin..."

# Move file to /usr/local/bin (requires sudo)
echo "📂 Moving file to /usr/local/bin (requires sudo)..."
sudo cp "$EXECUTABLE_FILE" "/usr/local/bin/$FILENAME"

# Make it executable
echo "🔧 Setting executable permissions..."
sudo chmod +x "/usr/local/bin/$FILENAME"

# Verify deployment
if [ -x "/usr/local/bin/$FILENAME" ]; then
    echo "✅ Successfully deployed '$FILENAME' to /usr/local/bin"
    echo "📍 Location: /usr/local/bin/$FILENAME"
    echo "🎉 You can now run '$FILENAME' from anywhere in your terminal!"
    echo ""
    echo "Test it:"
    echo "  $FILENAME --version"
    echo "  $FILENAME --help"
else
    echo "❌ Deployment failed - file not executable"
    exit 1
fi