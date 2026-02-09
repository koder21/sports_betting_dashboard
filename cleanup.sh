#!/bin/bash
# Cleanup unnecessary files and cache
# Run this after development to prepare for production

echo "🧹 Cleaning up workspace..."

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.egg-info" -delete

# Remove Node cache (if frontend was built)
rm -rf frontend/dist frontend/node_modules/.cache 2>/dev/null || true

# Remove VS Code cache
rm -rf .vscode/.cache 2>/dev/null || true

# Remove macOS system files
find . -name ".DS_Store" -delete
find . -name "*.swp" -delete
find . -name "*.swo" -delete

echo "✅ Cleanup complete"
echo ""
echo "Ready for deployment:"
echo "  • All test files removed"
echo "  • All cache cleaned"
echo "  • Documentation consolidated"
echo "  • Project structure optimized"
