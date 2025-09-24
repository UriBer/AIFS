#!/bin/bash
# AIFS Docker Entrypoint Script
# Supports environment variables for easy configuration

set -e

# Default values
AIFS_MODE=${AIFS_MODE:-"production"}
AIFS_HOST=${AIFS_HOST:-"0.0.0.0"}
AIFS_PORT=${AIFS_PORT:-"50051"}
AIFS_STORAGE_DIR=${AIFS_STORAGE_DIR:-"/data/aifs"}
AIFS_MAX_WORKERS=${AIFS_MAX_WORKERS:-"10"}
AIFS_COMPRESSION_LEVEL=${AIFS_COMPRESSION_LEVEL:-"1"}

# Print configuration
echo "🚀 Starting AIFS Server"
echo "================================"
echo "Mode: $AIFS_MODE"
echo "Host: $AIFS_HOST"
echo "Port: $AIFS_PORT"
echo "Storage: $AIFS_STORAGE_DIR"
echo "Max Workers: $AIFS_MAX_WORKERS"
echo "Compression Level: $AIFS_COMPRESSION_LEVEL"
echo "================================"

# Create storage directory if it doesn't exist
mkdir -p "$AIFS_STORAGE_DIR"

# Set Python path
export PYTHONPATH=/app

# Build command arguments
ARGS=(
    "start_server.py"
    "--host" "$AIFS_HOST"
    "--port" "$AIFS_PORT"
    "--storage-dir" "$AIFS_STORAGE_DIR"
)

# Add dev mode flag if in development mode
if [ "$AIFS_MODE" = "development" ] || [ "$AIFS_MODE" = "dev" ]; then
    echo "🔧 Development mode: gRPC reflection enabled"
    ARGS+=("--dev")
else
    echo "🔒 Production mode: gRPC reflection disabled"
fi

# Start the server
echo "Starting AIFS server..."
exec python "${ARGS[@]}"
