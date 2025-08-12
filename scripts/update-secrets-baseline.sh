#!/bin/bash
# Script to update the secrets baseline for detect-secrets

echo "Updating secrets baseline..."
uv run detect-secrets scan . > .secrets.baseline
echo "✅ Secrets baseline updated successfully!"
echo ""
echo "To verify the baseline, run:"
echo "  pre-commit run detect-secrets --all-files"
