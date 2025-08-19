#!/usr/bin/env bash
set -euo pipefail

# Persistent base
export WORKDATA="/workdata"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$WORKDATA/cache}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$WORKDATA/config}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$WORKDATA/state}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$WORKDATA/data}"
export VIRTUAL_ENV="${VIRTUAL_ENV:-$WORKDATA/venv}"

# Prepare directories
mkdir -p "$WORKDATA/results" "$WORKDATA/test_results" \
  "$XDG_CACHE_HOME/pytest" "$XDG_CACHE_HOME/ruff" "$XDG_CACHE_HOME/mypy" "$XDG_CACHE_HOME/pip" "$XDG_CACHE_HOME/uv" \
  "$XDG_STATE_HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CONFIG_HOME/bash"

# Seed .env if present in workspace (RO)
if [[ -f /workspace/.env ]] && [[ ! -f "$WORKDATA/.env" ]]; then
  cp /workspace/.env "$WORKDATA/.env" || true
fi

# Install project dependencies into persistent venv
if command -v uv >/dev/null 2>&1; then
  uv sync --frozen || uv sync
else
  pip install -e /workspace[dev] || pip install -e /workspace
fi

# Create Jupyter kernel linked to this venv for notebooks
"$VIRTUAL_ENV/bin/python" -m ipykernel install --user --name net-worker --display-name "Python (net-worker)" || true

# Setup Atuin using persistent XDG paths
if command -v atuin >/dev/null 2>&1; then
  # Write persistent bash init snippet
  ATUIN_SNIPPET_FILE="$XDG_CONFIG_HOME/bash/atuin.sh"
  if ! grep -q "atuin init bash" "$ATUIN_SNIPPET_FILE" 2>/dev/null; then
    echo 'eval "$(atuin init bash)"' > "$ATUIN_SNIPPET_FILE"
  fi
  # Ensure user's bash sources the persistent snippet
  if ! grep -q "$ATUIN_SNIPPET_FILE" /home/vscode/.bashrc 2>/dev/null; then
    {
      echo ""
      echo "# Source persistent devcontainer profile"
      echo "[ -f '$ATUIN_SNIPPET_FILE' ] && . '$ATUIN_SNIPPET_FILE'"
    } >> /home/vscode/.bashrc
  fi
fi

# Summary
printf "Setup complete.\nVIRTUAL_ENV=%s\nResults: %s\nTest Results: %s\n" "$VIRTUAL_ENV" \
  "$WORKDATA/results" "$WORKDATA/test_results"
