#!/bin/bash
# AIFS gRPC API Explorer
# Provides comprehensive gRPC API testing and documentation tools

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_HOST=${SERVER_HOST:-localhost}
SERVER_PORT=${SERVER_PORT:-50051}
AUTH_TOKEN=${AUTH_TOKEN:-""}

# Check if grpcurl is installed
check_grpcurl() {
    if ! command -v grpcurl &> /dev/null; then
        echo -e "${RED}❌ grpcurl is not installed${NC}"
        echo "Install with: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest"
        exit 1
    fi
}

# Check if server is running
check_server() {
    echo -e "${BLUE}🔍 Checking server connectivity...${NC}"
    if grpcurl -plaintext ${SERVER_HOST}:${SERVER_PORT} list &> /dev/null; then
        echo -e "${GREEN}✅ Server is running on ${SERVER_HOST}:${SERVER_PORT}${NC}"
    else
        echo -e "${RED}❌ Server is not running or not accessible${NC}"
        echo "Start server with: aifs server --dev --port ${SERVER_PORT}"
        exit 1
    fi
}

# List all services
list_services() {
    echo -e "${BLUE}📋 Available Services:${NC}"
    echo "========================"
    grpcurl -plaintext ${SERVER_HOST}:${SERVER_PORT} list
    echo ""
}

# List methods for a service
list_methods() {
    local service=$1
    echo -e "${BLUE}🔧 Methods for ${service}:${NC}"
    echo "================================"
    grpcurl -plaintext ${SERVER_HOST}:${SERVER_PORT} list ${service}
    echo ""
}

# Test health check
test_health() {
    echo -e "${BLUE}🏥 Testing Health Check:${NC}"
    echo "========================"
    grpcurl -plaintext ${SERVER_HOST}:${SERVER_PORT} aifs.v1.Health/Check
    echo ""
}

# Test introspection
test_introspect() {
    echo -e "${BLUE}🔍 Testing Introspection:${NC}"
    echo "=========================="
    grpcurl -plaintext ${SERVER_HOST}:${SERVER_PORT} aifs.v1.Introspect/GetInfo
    echo ""
}

# Test asset operations
test_assets() {
    echo -e "${BLUE}📦 Testing Asset Operations:${NC}"
    echo "============================="
    
    # List assets
    echo "📋 Listing assets..."
    if [ -n "$AUTH_TOKEN" ]; then
        grpcurl -plaintext -H "authorization: Bearer $AUTH_TOKEN" \
            ${SERVER_HOST}:${SERVER_PORT} aifs.v1.AIFS/ListAssets \
            -d '{"limit": 10}'
    else
        echo "⚠️  No auth token provided, skipping authenticated operations"
    fi
    echo ""
}

# Test vector search
test_vector_search() {
    echo -e "${BLUE}🔍 Testing Vector Search:${NC}"
    echo "============================"
    
    if [ -n "$AUTH_TOKEN" ]; then
        # Create a dummy embedding (128 bytes of random data)
        local dummy_embedding=$(python3 -c "import base64; print(base64.b64encode(b'0' * 128).decode())")
        
        grpcurl -plaintext -H "authorization: Bearer $AUTH_TOKEN" \
            ${SERVER_HOST}:${SERVER_PORT} aifs.v1.AIFS/VectorSearch \
            -d "{\"query_embedding\": \"$dummy_embedding\", \"k\": 5}"
    else
        echo "⚠️  No auth token provided, skipping authenticated operations"
    fi
    echo ""
}

# Test snapshot operations
test_snapshots() {
    echo -e "${BLUE}📸 Testing Snapshot Operations:${NC}"
    echo "================================="
    
    if [ -n "$AUTH_TOKEN" ]; then
        # Create a test snapshot
        echo "📸 Creating test snapshot..."
        grpcurl -plaintext -H "authorization: Bearer $AUTH_TOKEN" \
            ${SERVER_HOST}:${SERVER_PORT} aifs.v1.AIFS/CreateSnapshot \
            -d '{"namespace": "test", "metadata": {"description": "Test snapshot"}}'
        
        echo ""
        echo "📋 Listing snapshots..."
        # Note: ListSnapshots method would need to be implemented
        echo "⚠️  ListSnapshots method not yet implemented"
    else
        echo "⚠️  No auth token provided, skipping authenticated operations"
    fi
    echo ""
}

# Generate authentication token
generate_auth_token() {
    echo -e "${BLUE}🔐 Generating Authentication Token:${NC}"
    echo "====================================="
    
    # Create a simple JSON token
    local token=$(python3 -c "
import json
import base64
import time

# Create token payload
payload = {
    'permissions': ['put', 'get', 'delete', 'list', 'search', 'snapshot'],
    'expires': int(time.time()) + 3600,  # 1 hour from now
    'user': 'test_user'
}

# Encode as base64
token = base64.b64encode(json.dumps(payload).encode()).decode()
print(token)
")
    
    echo "Generated token: $token"
    echo "Set AUTH_TOKEN environment variable:"
    echo "export AUTH_TOKEN=\"$token\""
    echo ""
}

# Interactive mode
interactive_mode() {
    echo -e "${BLUE}🎯 Interactive Mode${NC}"
    echo "=================="
    echo "Available commands:"
    echo "  services    - List all services"
    echo "  methods <service> - List methods for a service"
    echo "  health      - Test health check"
    echo "  introspect  - Test introspection"
    echo "  assets      - Test asset operations"
    echo "  vector      - Test vector search"
    echo "  snapshots   - Test snapshot operations"
    echo "  token       - Generate auth token"
    echo "  quit        - Exit"
    echo ""
    
    while true; do
        read -p "grpc> " command
        case $command in
            services)
                list_services
                ;;
            methods*)
                local service=$(echo $command | cut -d' ' -f2)
                if [ -z "$service" ]; then
                    echo "Usage: methods <service_name>"
                else
                    list_methods "$service"
                fi
                ;;
            health)
                test_health
                ;;
            introspect)
                test_introspect
                ;;
            assets)
                test_assets
                ;;
            vector)
                test_vector_search
                ;;
            snapshots)
                test_snapshots
                ;;
            token)
                generate_auth_token
                ;;
            quit|exit)
                echo "Goodbye!"
                break
                ;;
            help)
                echo "Available commands: services, methods <service>, health, introspect, assets, vector, snapshots, token, quit"
                ;;
            *)
                echo "Unknown command: $command. Type 'help' for available commands."
                ;;
        esac
    done
}

# Run comprehensive tests
run_tests() {
    echo -e "${GREEN}🚀 Running Comprehensive gRPC Tests${NC}"
    echo "====================================="
    echo ""
    
    check_grpcurl
    check_server
    
    list_services
    test_health
    test_introspect
    test_assets
    test_vector_search
    test_snapshots
    
    echo -e "${GREEN}✅ All tests completed!${NC}"
}

# Show usage
show_usage() {
    echo "AIFS gRPC API Explorer"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  test        - Run comprehensive tests"
    echo "  interactive - Start interactive mode"
    echo "  services    - List all services"
    echo "  health      - Test health check"
    echo "  token       - Generate auth token"
    echo "  help        - Show this help"
    echo ""
    echo "Environment Variables:"
    echo "  SERVER_HOST - gRPC server host (default: localhost)"
    echo "  SERVER_PORT - gRPC server port (default: 50051)"
    echo "  AUTH_TOKEN  - Authentication token for protected operations"
    echo ""
    echo "Examples:"
    echo "  $0 test                           # Run all tests"
    echo "  $0 interactive                    # Interactive mode"
    echo "  AUTH_TOKEN=xxx $0 test            # Run tests with auth"
    echo "  SERVER_PORT=50052 $0 test         # Test different port"
}

# Main script
main() {
    case "${1:-test}" in
        test)
            run_tests
            ;;
        interactive)
            check_grpcurl
            check_server
            interactive_mode
            ;;
        services)
            check_grpcurl
            check_server
            list_services
            ;;
        health)
            check_grpcurl
            check_server
            test_health
            ;;
        token)
            generate_auth_token
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            echo "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
