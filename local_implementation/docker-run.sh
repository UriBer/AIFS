#!/bin/bash
# Docker run script for AIFS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE="aifs:latest"
CONTAINER_NAME="aifs-server"
PORT="50051"
DATA_DIR="./aifs-data"
MODE="production"
DEV=false
INTERACTIVE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--image)
            IMAGE="$2"
            shift 2
            ;;
        -n|--name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --dev)
            DEV=true
            MODE="development"
            shift
            ;;
        --interactive|-it)
            INTERACTIVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -i, --image IMAGE     Docker image to run (default: aifs:latest)"
            echo "  -n, --name NAME       Container name (default: aifs-server)"
            echo "  -p, --port PORT       Host port to map (default: 50051)"
            echo "  -d, --data-dir DIR    Local data directory (default: ./aifs-data)"
            echo "  --dev                 Run in development mode with gRPC reflection"
            echo "  --interactive, -it    Run interactively"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🐳 Running AIFS Docker Container${NC}"
echo -e "Image: ${GREEN}${IMAGE}${NC}"
echo -e "Container: ${GREEN}${CONTAINER_NAME}${NC}"
echo -e "Port: ${GREEN}${PORT}${NC}"
echo -e "Mode: ${GREEN}${MODE}${NC}"
echo -e "Data Directory: ${GREEN}${DATA_DIR}${NC}"
echo ""

# Create data directory if it doesn't exist
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${YELLOW}📁 Creating data directory: ${DATA_DIR}${NC}"
    mkdir -p "$DATA_DIR"
fi

# Stop and remove existing container if it exists
if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${YELLOW}🛑 Stopping existing container...${NC}"
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1 || true
fi

# Build run command
RUN_CMD="docker run"
RUN_CMD="$RUN_CMD --name $CONTAINER_NAME"
RUN_CMD="$RUN_CMD -p $PORT:50051"
RUN_CMD="$RUN_CMD -v $(realpath "$DATA_DIR"):/data/aifs"

if [ "$INTERACTIVE" = true ]; then
    RUN_CMD="$RUN_CMD -it"
fi

RUN_CMD="$RUN_CMD --restart unless-stopped"

# Add environment variables
RUN_CMD="$RUN_CMD -e PYTHONUNBUFFERED=1"
RUN_CMD="$RUN_CMD -e AIFS_DATA_DIR=/data/aifs"
RUN_CMD="$RUN_CMD -e AIFS_PORT=50051"
RUN_CMD="$RUN_CMD -e AIFS_HOST=0.0.0.0"

if [ "$DEV" = true ]; then
    RUN_CMD="$RUN_CMD -e AIFS_LOG_LEVEL=DEBUG"
    RUN_CMD="$RUN_CMD $IMAGE python start_server.py --dev --storage-dir /data/aifs --port 50051"
else
    RUN_CMD="$RUN_CMD -e AIFS_LOG_LEVEL=INFO"
    RUN_CMD="$RUN_CMD $IMAGE"
fi

# Run the container
echo -e "${YELLOW}🚀 Starting container...${NC}"
echo -e "Command: ${BLUE}$RUN_CMD${NC}"
echo ""

if eval "$RUN_CMD"; then
    echo -e "\n${GREEN}✅ Container started successfully!${NC}"
    echo -e "\n${BLUE}📋 Container Information:${NC}"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo -e "\n${BLUE}🔗 Connection Information:${NC}"
    echo -e "gRPC Server: ${GREEN}localhost:${PORT}${NC}"
    if [ "$DEV" = true ]; then
        echo -e "gRPC Reflection: ${GREEN}Enabled${NC}"
        echo -e "API Discovery: ${GREEN}grpcurl -plaintext localhost:${PORT} list${NC}"
    else
        echo -e "gRPC Reflection: ${GREEN}Disabled (production mode)${NC}"
    fi
    
    echo -e "\n${BLUE}📁 Data Directory:${NC}"
    echo -e "Host: ${GREEN}$(realpath "$DATA_DIR")${NC}"
    echo -e "Container: ${GREEN}/data/aifs${NC}"
    
    echo -e "\n${BLUE}🛠️  Management Commands:${NC}"
    echo -e "View logs: ${BLUE}docker logs $CONTAINER_NAME${NC}"
    echo -e "Stop: ${BLUE}docker stop $CONTAINER_NAME${NC}"
    echo -e "Restart: ${BLUE}docker restart $CONTAINER_NAME${NC}"
    echo -e "Remove: ${BLUE}docker rm -f $CONTAINER_NAME${NC}"
    
else
    echo -e "${RED}❌ Failed to start container!${NC}"
    exit 1
fi
