#!/bin/bash

# AIFS gRPC API Exploration Script
# This script demonstrates how to explore the AIFS gRPC API using grpcurl

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_HOST="localhost"
SERVER_PORT="50051"
SERVER_ADDRESS="$SERVER_HOST:$SERVER_PORT"

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

# Check if grpcurl is installed
check_grpcurl() {
    if ! command -v grpcurl >/dev/null 2>&1; then
        log_error "grpcurl is not installed"
        echo ""
        echo "Please install grpcurl:"
        echo "  macOS: brew install grpcurl"
        echo "  Ubuntu/Debian: sudo apt-get install grpcurl"
        echo "  Or download from: https://github.com/fullstorydev/grpcurl/releases"
        exit 1
    fi
    log_success "grpcurl is available"
}

# Check if server is running
check_server() {
    log_info "Checking if AIFS server is running at $SERVER_ADDRESS..."
    
    if grpcurl -plaintext $SERVER_ADDRESS list >/dev/null 2>&1; then
        log_success "AIFS server is running and accessible"
    else
        log_error "Cannot connect to AIFS server at $SERVER_ADDRESS"
        echo ""
        echo "Make sure the AIFS server is running:"
        echo "  docker run -d --name aifs-server -p 50051:50051 uriber/aifs:latest"
        echo ""
        echo "Or for development mode with gRPC reflection:"
        echo "  docker run -d --name aifs-dev -p 50051:50051 uriber/aifs:dev"
        exit 1
    fi
}

# List all services
list_services() {
    log_info "Discovering available services..."
    echo ""
    
    echo "🔍 Available gRPC services:"
    grpcurl -plaintext $SERVER_ADDRESS list
    echo ""
}

# List service methods
list_service_methods() {
    local service=$1
    log_info "Methods available in $service service:"
    echo ""
    
    grpcurl -plaintext $SERVER_ADDRESS list $service
    echo ""
}

# Test health service
test_health_service() {
    log_info "Testing Health service..."
    echo ""
    
    echo "🏥 Health Check:"
    grpcurl -plaintext $SERVER_ADDRESS grpc.health.v1.Health/Check
    echo ""
}

# Test AIFS service
test_aifs_service() {
    log_info "Testing AIFS service..."
    echo ""
    
    echo "📋 Listing assets:"
    grpcurl -plaintext $SERVER_ADDRESS aifs.AIFS/ListAssets
    echo ""
    
    echo "📊 Getting system info:"
    grpcurl -plaintext $SERVER_ADDRESS aifs.AIFS/GetSystemInfo
    echo ""
}

# Test introspection service
test_introspection_service() {
    log_info "Testing Introspection service..."
    echo ""
    
    echo "🔍 Getting service info:"
    grpcurl -plaintext $SERVER_ADDRESS aifs.Introspect/GetServiceInfo
    echo ""
    
    echo "📋 Listing methods:"
    grpcurl -plaintext $SERVER_ADDRESS aifs.Introspect/ListMethods
    echo ""
}

# Interactive mode
interactive_mode() {
    log_info "Entering interactive mode..."
    echo ""
    echo "You can now run grpcurl commands interactively."
    echo "Examples:"
    echo "  grpcurl -plaintext $SERVER_ADDRESS list"
    echo "  grpcurl -plaintext $SERVER_ADDRESS list aifs.AIFS"
    echo "  grpcurl -plaintext $SERVER_ADDRESS aifs.AIFS/ListAssets"
    echo ""
    echo "Type 'exit' to quit."
    echo ""
    
    while true; do
        read -p "grpcurl> " command
        if [ "$command" = "exit" ]; then
            break
        fi
        
        if [ -n "$command" ]; then
            echo "Running: grpcurl -plaintext $SERVER_ADDRESS $command"
            grpcurl -plaintext $SERVER_ADDRESS $command 2>/dev/null || echo "Command failed or returned no output"
            echo ""
        fi
    done
}

# Store a sample asset
store_sample_asset() {
    log_info "Storing a sample asset..."
    echo ""
    
    # Create a sample asset request
    local request='{
        "chunks": [
            {
                "data": "SGVsbG8sIEFJRlMhIFRoaXMgaXMgYSBzYW1wbGUgZG9jdW1lbnQu"
            }
        ],
        "kind": "BLOB",
        "metadata": {
            "title": "Sample Document",
            "description": "A sample document for gRPC exploration",
            "author": "grpcurl demo"
        }
    }'
    
    echo "📝 Storing sample asset:"
    echo "$request" | grpcurl -plaintext -d @ $SERVER_ADDRESS aifs.AIFS/PutAsset
    echo ""
}

# Main exploration function
explore_api() {
    log_info "🔍 Starting AIFS gRPC API exploration"
    echo ""
    
    # List all services
    list_services
    
    # Test each service
    test_health_service
    test_aifs_service
    test_introspection_service
    
    # Store a sample asset
    store_sample_asset
    
    # List assets again to show the new one
    log_info "Listing assets after storing sample:"
    grpcurl -plaintext $SERVER_ADDRESS aifs.AIFS/ListAssets
    echo ""
    
    log_success "API exploration completed!"
}

# Help function
show_help() {
    echo "AIFS gRPC API Exploration Script"
    echo ""
    echo "This script demonstrates how to explore the AIFS gRPC API using grpcurl."
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -i, --interactive       Enter interactive mode"
    echo "  -s, --server HOST:PORT  Specify server address (default: localhost:50051)"
    echo ""
    echo "Examples:"
    echo "  $0                      # Run full exploration"
    echo "  $0 -i                   # Enter interactive mode"
    echo "  $0 -s localhost:50052   # Connect to different port"
    echo ""
    echo "Prerequisites:"
    echo "  - grpcurl must be installed"
    echo "  - AIFS server must be running"
    echo ""
    echo "Install grpcurl:"
    echo "  macOS: brew install grpcurl"
    echo "  Ubuntu/Debian: sudo apt-get install grpcurl"
}

# Parse command line arguments
INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -s|--server)
            SERVER_ADDRESS="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    # Pre-flight checks
    check_grpcurl
    check_server
    
    if [ "$INTERACTIVE" = true ]; then
        interactive_mode
    else
        explore_api
    fi
}

# Run main function
main
