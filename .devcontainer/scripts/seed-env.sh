#!/usr/bin/env bash
set -euo pipefail
: "${DOTENV_PATH:=/workdata/.env}"

# Generate minimal .env safely in persistent volume
if [[ -f "$DOTENV_PATH" ]] && [[ "${1:-}" != "--force" ]]; then
  echo ".env already exists at $DOTENV_PATH (use --force to overwrite)"
  exit 0
fi

mkdir -p "$(dirname "$DOTENV_PATH")"
cat > "$DOTENV_PATH" <<'EOF'
# Net-Worker environment (container)
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
NW_RESULTS_DIR=/workdata/results
NW_TEST_RESULTS_DIR=/workdata/test_results
# Add other secrets locally, this file stays in the volume only
EOF

echo "Wrote $DOTENV_PATH"
