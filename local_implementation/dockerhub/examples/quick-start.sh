#!/bin/bash

# AIFS Quick Start Example
# This script demonstrates how to quickly get started with AIFS using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="uriber/aifs:latest"
CONTAINER_NAME="aifs-demo"
PORT="50051"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up demo container..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    docker volume rm aifs-demo-data 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

# Main demo function
run_demo() {
    log_info "🚀 Starting AIFS Quick Start Demo"
    echo ""
    
    # Step 1: Pull the image
    log_info "Step 1: Pulling AIFS Docker image..."
    if docker pull $IMAGE_NAME; then
        log_success "Image pulled successfully"
    else
        log_error "Failed to pull image. Make sure you're connected to the internet."
        exit 1
    fi
    echo ""
    
    # Step 2: Start the container
    log_info "Step 2: Starting AIFS server..."
    if docker run -d --name $CONTAINER_NAME \
        -p $PORT:50051 \
        -v aifs-demo-data:/data/aifs \
        $IMAGE_NAME; then
        log_success "Server started successfully"
    else
        log_error "Failed to start server"
        exit 1
    fi
    echo ""
    
    # Step 3: Wait for server to be ready
    log_info "Step 3: Waiting for server to be ready..."
    sleep 10
    
    # Step 4: Test health check
    log_info "Step 4: Testing health check..."
    if docker exec $CONTAINER_NAME /app/healthcheck.sh; then
        log_success "Server is healthy and ready"
    else
        log_error "Server health check failed"
        exit 1
    fi
    echo ""
    
    # Step 5: Demonstrate basic operations
    log_info "Step 5: Demonstrating basic AIFS operations..."
    echo ""
    
    # Store an asset
    log_info "Storing a sample asset..."
    if docker exec $CONTAINER_NAME python -c "
from aifs.client import AIFSClient
import json

client = AIFSClient('localhost:50051')

# Store a text asset
asset_id = client.put_asset(
    data=b'Hello, AIFS! This is a sample document for demonstration.',
    kind='blob',
    metadata={
        'title': 'Welcome to AIFS',
        'description': 'A sample document for the quick start demo',
        'author': 'AIFS Demo',
        'type': 'text/plain'
    }
)
print(f'✅ Stored asset with ID: {asset_id}')

# Store another asset
asset_id2 = client.put_asset(
    data=b'This is another document about machine learning and AI.',
    kind='blob',
    metadata={
        'title': 'AI and ML Introduction',
        'description': 'A document about artificial intelligence',
        'author': 'AIFS Demo',
        'type': 'text/plain',
        'topics': 'ai, machine learning, artificial intelligence'
    }
)
print(f'✅ Stored second asset with ID: {asset_id2}')

print('\\n📊 Asset storage completed!')
"; then
        log_success "Assets stored successfully"
    else
        log_error "Failed to store assets"
        exit 1
    fi
    echo ""
    
    # List assets
    log_info "Listing all assets..."
    if docker exec $CONTAINER_NAME python -c "
from aifs.client import AIFSClient
import json

client = AIFSClient('localhost:50051')
assets = client.list_assets()

print(f'📋 Found {len(assets)} assets:')
for i, asset in enumerate(assets, 1):
    print(f'  {i}. ID: {asset[\"asset_id\"]}')
    print(f'     Kind: {asset[\"kind\"]}')
    print(f'     Size: {asset[\"size\"]} bytes')
    print(f'     Metadata: {json.dumps(asset[\"metadata\"], indent=6)}')
    print()
"; then
        log_success "Asset listing completed"
    else
        log_error "Failed to list assets"
        exit 1
    fi
    echo ""
    
    # Retrieve an asset
    log_info "Retrieving the first asset..."
    if docker exec $CONTAINER_NAME python -c "
from aifs.client import AIFSClient

client = AIFSClient('localhost:50051')
assets = client.list_assets()

if assets:
    asset_id = assets[0]['asset_id']
    asset = client.get_asset(asset_id)
    print(f'📖 Retrieved asset: {asset[\"data\"].decode(\"utf-8\")}')
    print(f'   Metadata: {asset[\"metadata\"]}')
else:
    print('No assets found')
"; then
        log_success "Asset retrieval completed"
    else
        log_error "Failed to retrieve asset"
        exit 1
    fi
    echo ""
    
    # Step 6: Show API information
    log_info "Step 6: AIFS API Information"
    echo ""
    echo "🌐 AIFS Server is running on:"
    echo "   - Host: localhost"
    echo "   - Port: $PORT"
    echo "   - gRPC endpoint: localhost:$PORT"
    echo ""
    echo "🔧 Available operations:"
    echo "   - Store assets: client.put_asset()"
    echo "   - Retrieve assets: client.get_asset()"
    echo "   - List assets: client.list_assets()"
    echo "   - Search assets: client.vector_search()"
    echo "   - Create snapshots: client.create_snapshot()"
    echo ""
    echo "📚 Next steps:"
    echo "   1. Explore the Python client API"
    echo "   2. Try vector search with embeddings"
    echo "   3. Create versioned snapshots"
    echo "   4. Check out the full documentation"
    echo ""
    
    # Step 7: Interactive mode
    log_info "Step 7: Interactive Demo Mode"
    echo ""
    echo "You can now interact with the AIFS server:"
    echo ""
    echo "🐍 Python client example:"
    echo "   python -c \""
    echo "   from aifs.client import AIFSClient"
    echo "   client = AIFSClient('localhost:$PORT')"
    echo "   assets = client.list_assets()"
    echo "   print(f'Found {len(assets)} assets')"
    echo "   \""
    echo ""
    echo "🔍 gRPC exploration (if grpcurl is installed):"
    echo "   grpcurl -plaintext localhost:$PORT list"
    echo ""
    echo "📊 Container logs:"
    echo "   docker logs $CONTAINER_NAME"
    echo ""
    echo "🛑 Stop the demo:"
    echo "   docker stop $CONTAINER_NAME"
    echo ""
    
    # Keep container running for interactive use
    log_info "Demo container is running. Press Ctrl+C to stop and clean up."
    log_info "Or run 'docker stop $CONTAINER_NAME' in another terminal to stop it."
    echo ""
    
    # Wait for user interrupt
    while true; do
        sleep 30
        if ! docker ps | grep -q $CONTAINER_NAME; then
            log_warning "Container stopped unexpectedly"
            break
        fi
    done
}

# Help function
show_help() {
    echo "AIFS Quick Start Demo"
    echo ""
    echo "This script demonstrates how to quickly get started with AIFS using Docker."
    echo "It will:"
    echo "  1. Pull the AIFS Docker image"
    echo "  2. Start the AIFS server"
    echo "  3. Demonstrate basic operations"
    echo "  4. Keep the server running for interactive use"
    echo ""
    echo "Usage: $0"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker must be installed and running"
    echo "  - Internet connection to pull the image"
    echo ""
    echo "The demo will clean up automatically when you stop it (Ctrl+C)."
}

# Parse arguments
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run the demo
run_demo
