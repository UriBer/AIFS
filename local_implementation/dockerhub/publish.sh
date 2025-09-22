#!/bin/bash

# AIFS Docker Hub Publishing Script
# This script builds and pushes AIFS images to Docker Hub

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKERHUB_USERNAME="uriber"
IMAGE_NAME="aifs"
VERSION=${1:-"latest"}
PLATFORMS="linux/amd64,linux/arm64"

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

# Check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Check if logged into Docker Hub
check_dockerhub_login() {
    if ! docker info | grep -q "Username: $DOCKERHUB_USERNAME"; then
        log_warning "Not logged into Docker Hub as $DOCKERHUB_USERNAME"
        log_info "Please run: docker login"
        read -p "Press Enter after logging in..."
    else
        log_success "Logged into Docker Hub as $DOCKERHUB_USERNAME"
    fi
}

# Build and push image
build_and_push() {
    local tag=$1
    local dockerfile=$2
    local build_args=$3
    
    log_info "Building $IMAGE_NAME:$tag..."
    
    if [ -n "$dockerfile" ]; then
        dockerfile_arg="--file $dockerfile"
    else
        dockerfile_arg=""
    fi
    
    # Build for multiple platforms
    if docker buildx build \
        --platform "$PLATFORMS" \
        --tag "$DOCKERHUB_USERNAME/$IMAGE_NAME:$tag" \
        --push \
        $dockerfile_arg \
        $build_args \
        .; then
        log_success "Successfully built and pushed $DOCKERHUB_USERNAME/$IMAGE_NAME:$tag"
    else
        log_error "Failed to build and push $DOCKERHUB_USERNAME/$IMAGE_NAME:$tag"
        exit 1
    fi
}

# Create development image with gRPC reflection
create_dev_image() {
    log_info "Creating development image with gRPC reflection..."
    
    # Create a temporary Dockerfile for dev image
    cat > Dockerfile.dev << EOF
FROM $DOCKERHUB_USERNAME/$IMAGE_NAME:latest

# Enable gRPC reflection by default
ENV AIFS_DEV_MODE=true

# Override the default command to enable dev mode
CMD ["python", "start_server.py", "--dev", "--storage-dir", "/data/aifs", "--port", "50051"]
EOF

    build_and_push "dev" "Dockerfile.dev"
    rm -f Dockerfile.dev
}

# Main execution
main() {
    log_info "Starting AIFS Docker Hub publishing process..."
    log_info "Version: $VERSION"
    log_info "Platforms: $PLATFORMS"
    
    # Pre-flight checks
    check_docker
    check_dockerhub_login
    
    # Build and push main image
    log_info "Building production image..."
    build_and_push "$VERSION"
    
    # Create and push development image
    create_dev_image
    
    # If this is a version tag (not latest), also tag as latest
    if [[ "$VERSION" != "latest" ]]; then
        log_info "Tagging $VERSION as latest..."
        docker pull "$DOCKERHUB_USERNAME/$IMAGE_NAME:$VERSION"
        docker tag "$DOCKERHUB_USERNAME/$IMAGE_NAME:$VERSION" "$DOCKERHUB_USERNAME/$IMAGE_NAME:latest"
        docker push "$DOCKERHUB_USERNAME/$IMAGE_NAME:latest"
        log_success "Tagged and pushed as latest"
    fi
    
    log_success "Publishing complete!"
    log_info "Images available:"
    log_info "  - $DOCKERHUB_USERNAME/$IMAGE_NAME:$VERSION"
    log_info "  - $DOCKERHUB_USERNAME/$IMAGE_NAME:dev"
    if [[ "$VERSION" != "latest" ]]; then
        log_info "  - $DOCKERHUB_USERNAME/$IMAGE_NAME:latest"
    fi
    
    log_info "Test the images:"
    log_info "  docker run --rm -p 50051:50051 $DOCKERHUB_USERNAME/$IMAGE_NAME:$VERSION"
    log_info "  docker run --rm -p 50051:50051 $DOCKERHUB_USERNAME/$IMAGE_NAME:dev"
}

# Help function
show_help() {
    echo "AIFS Docker Hub Publishing Script"
    echo ""
    echo "Usage: $0 [VERSION]"
    echo ""
    echo "Arguments:"
    echo "  VERSION    Version tag to publish (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Publish as 'latest'"
    echo "  $0 v0.1.0-alpha      # Publish as 'v0.1.0-alpha'"
    echo "  $0 1.0.0             # Publish as '1.0.0'"
    echo ""
    echo "Prerequisites:"
    echo "  - Docker must be running"
    echo "  - Must be logged into Docker Hub (docker login)"
    echo "  - Must have push permissions to $DOCKERHUB_USERNAME/$IMAGE_NAME"
}

# Parse arguments
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main
