#!/bin/bash
# Docker build script for AIFS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TAG="aifs"
VERSION="latest"
PLATFORM="linux/amd64"
PUSH=false
NO_CACHE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -t, --tag TAG        Docker image tag (default: aifs)"
            echo "  -v, --version VER    Docker image version (default: latest)"
            echo "  -p, --platform PLAT  Target platform (default: linux/amd64)"
            echo "  --push               Push image to registry after building"
            echo "  --no-cache           Build without using cache"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

FULL_TAG="${TAG}:${VERSION}"

echo -e "${BLUE}🐳 Building AIFS Docker Image${NC}"
echo -e "Tag: ${GREEN}${FULL_TAG}${NC}"
echo -e "Platform: ${GREEN}${PLATFORM}${NC}"
echo -e "Push: ${GREEN}${PUSH}${NC}"
echo ""

# Build arguments
BUILD_ARGS=""
if [ "$NO_CACHE" = true ]; then
    BUILD_ARGS="--no-cache"
fi

# Build the image
echo -e "${YELLOW}📦 Building Docker image...${NC}"
if docker buildx build \
    --platform "${PLATFORM}" \
    --tag "${FULL_TAG}" \
    ${BUILD_ARGS} \
    .; then
    echo -e "${GREEN}✅ Docker image built successfully!${NC}"
else
    echo -e "${RED}❌ Docker build failed!${NC}"
    exit 1
fi

# Show image info
echo -e "\n${BLUE}📋 Image Information:${NC}"
docker images "${FULL_TAG}"

# Push if requested
if [ "$PUSH" = true ]; then
    echo -e "\n${YELLOW}🚀 Pushing image to registry...${NC}"
    if docker push "${FULL_TAG}"; then
        echo -e "${GREEN}✅ Image pushed successfully!${NC}"
    else
        echo -e "${RED}❌ Push failed!${NC}"
        exit 1
    fi
fi

echo -e "\n${GREEN}🎉 Build completed successfully!${NC}"
echo -e "To run the container:"
echo -e "  ${BLUE}docker run -p 50051:50051 -v aifs-data:/data/aifs ${FULL_TAG}${NC}"
echo -e "\nTo run with docker-compose:"
echo -e "  ${BLUE}docker-compose up -d${NC}"
