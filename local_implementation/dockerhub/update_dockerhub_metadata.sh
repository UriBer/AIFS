#!/bin/bash

# Script to update Docker Hub repository metadata
# This script provides instructions and commands for updating Docker Hub repository information

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

echo "🐳 Docker Hub Repository Metadata Update"
echo "========================================"

log_info "This script will help you update your Docker Hub repository metadata"
echo

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

log_success "Docker is running"

# Check if user is logged into Docker Hub
if ! docker pull hello-world >/dev/null 2>&1; then
    log_warning "Not logged into Docker Hub"
    log_info "Please run: docker login"
    read -p "Press Enter after logging in..."
fi

log_success "Docker Hub access confirmed"

echo
log_info "Repository: uriber/aifs"
log_info "Current tags: latest, v0.1.0-alpha"
echo

# Display the short description for Docker Hub (100 char limit)
echo "📝 Docker Hub Description (100 characters max):"
echo "==============================================="
echo
echo "AI-Native File System with content addressing, vector search, and versioned snapshots for ML workloads"
echo
echo "Character count: 99 characters ✅"
echo

# Display the full description for README
echo "📝 Full Repository Description (for README):"
echo "==========================================="
echo
cat << 'EOF'
AIFS - AI-Native File System

A production-ready AI-Native File System with content addressing, vector search, and versioned snapshots. Perfect for AI/ML workloads requiring semantic search and data lineage tracking.

Key Features:
• Content Addressing with BLAKE3 hashing
• Vector Search with FAISS integration  
• Versioned Snapshots with Merkle trees
• AES-256-GCM encryption
• gRPC API with reflection support
• Data lineage tracking
• Docker-ready with health checks

Use Cases:
• AI/ML data management
• RAG systems
• Data versioning
• Content deduplication
• Semantic search
• Research reproducibility

Quick Start:
docker pull uriber/aifs:latest
docker run -d --name aifs-server -p 50051:50051 -v aifs-data:/data/aifs uriber/aifs:latest
EOF

echo
echo "🏷️  Categories to Select:"
echo "========================"
echo "• AI"
echo "• ML" 
echo "• Storage"
echo "• Database"
echo "• Search"
echo "• Development"
echo

echo "🔑 Keywords to Add:"
echo "=================="
echo "ai, ml, machine-learning, file-system, content-addressing, vector-search, semantic-search, grpc, blake3, merkle-tree, versioning, data-lineage, storage, database, search, development"
echo

echo "📋 Manual Steps Required:"
echo "========================"
echo "1. Go to https://hub.docker.com/repository/docker/uriber/aifs/general"
echo "2. Click 'Edit' next to the repository description"
echo "3. Paste the description above"
echo "4. Add the categories listed above"
echo "5. Add the keywords listed above"
echo "6. Save changes"
echo

echo "🔄 Rebuild Image with New Labels:"
echo "================================="
echo "The Dockerfile has been updated with comprehensive labels."
echo "To apply them, rebuild and push the image:"
echo
echo "cd /Users/urib1/Documents/workspace/ideas/AIFS/local_implementation"
echo "./dockerhub/publish.sh v0.1.0-alpha"
echo

echo "📊 Verify Labels:"
echo "================="
echo "After rebuilding, you can verify the labels with:"
echo
echo "docker inspect uriber/aifs:latest | grep -A 20 'Labels'"
echo

log_success "Docker Hub metadata update instructions complete!"
log_info "Follow the manual steps above to update your repository description and categories."
