#!/bin/bash
set -euo pipefail

# Seed environment variables into the env volume
# This script is idempotent - safe to run multiple times

ENV_FILE="${WORKSPACE_FOLDER}/.env"
ENV_TEMPLATE="${WORKSPACE_FOLDER}/.env.example"

echo "=== Seeding .env file into volume ==="

# Check if .env already exists in volume
if [[ -f "$ENV_FILE" ]]; then
    echo "PASS: .env already exists in volume"
    echo "  Current size: $(wc -l < "$ENV_FILE") lines"
    echo "  To recreate, run: rm $ENV_FILE && bash .devcontainer/scripts/seed-env.sh"
    exit 0
fi

# Create .env from template if it exists
if [[ -f "$ENV_TEMPLATE" ]]; then
    echo "PASS: Found .env.example, copying to volume..."
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    echo "PASS: Created .env from template with $(wc -l < "$ENV_FILE") lines"
else
    echo "PASS: Creating default .env file..."
    cat > "$ENV_FILE" << 'EOF'
# Network Toolkit Environment Variables
# Copy this file and customize for your environment

# Default credentials (used when device-specific credentials not found)
# NW_USER_DEFAULT=admin
# NW_PASSWORD_DEFAULT=your_password_here

# Device-specific credentials (optional)
# Format: NW_{DEVICE_NAME}_USER and NW_{DEVICE_NAME}_PASSWORD
# Example:
# NW_ROUTER1_USER=admin
# NW_ROUTER1_PASSWORD=router1_password
# NW_SWITCH1_USER=admin
# NW_SWITCH1_PASSWORD=switch1_password

# Logging configuration
# LOG_LEVEL=INFO
# LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Connection timeouts (seconds)
# CONNECTION_TIMEOUT=30
# COMMAND_TIMEOUT=60

# Output directories
# RESULTS_DIR=results
# TEST_RESULTS_DIR=test_results
# OUTPUTS_DIR=outputs
EOF
    echo "PASS: Created default .env with $(wc -l < "$ENV_FILE") lines"
fi

# Set appropriate permissions
chmod 600 "$ENV_FILE"
echo "PASS: Set secure permissions (600) on .env file"

echo ""
echo "Next steps:"
echo "1. Edit $ENV_FILE to add your credentials"
echo "2. Run: uv sync"
echo "3. Start developing!"

echo ""
echo "Security note: .env is in a read-only volume mounted into the container."
echo "The container cannot modify your host repository."
