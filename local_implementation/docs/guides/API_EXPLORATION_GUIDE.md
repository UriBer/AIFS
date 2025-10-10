# 🔍 AIFS API Exploration Guide

This guide provides comprehensive tools for exploring, testing, and understanding the AIFS gRPC API.

## 🛠️ **Available Tools**

### 1. **Lineage Explorer** (`lineage_explorer.py`)
Interactive tool for exploring file lineage relationships.

```bash
# Install dependencies
pip install networkx matplotlib

# Explore lineage for a specific asset
python lineage_explorer.py --asset <asset_id> --ancestors --descendants

# Visualize lineage graph
python lineage_explorer.py --asset <asset_id> --visualize

# Export lineage data
python lineage_explorer.py --asset <asset_id> --export lineage_data.json

# Find path between assets
python lineage_explorer.py --path <from_asset_id>,<to_asset_id>
```

### 2. **gRPC Web UI** (`grpc_web_ui.py`)
Swagger-like web interface for API testing.

```bash
# Install dependencies
pip install flask grpcio-reflection

# Start web UI (requires server running)
python grpc_web_ui.py --server-host localhost --server-port 50051

# Access at http://localhost:8080
```

### 3. **gRPC Explorer** (`grpc_explorer.sh`)
Command-line tool for comprehensive API testing.

```bash
# Make executable
chmod +x grpc_explorer.sh

# Run comprehensive tests
./grpc_explorer.sh test

# Interactive mode
./grpc_explorer.sh interactive

# Test specific operations
./grpc_explorer.sh health
./grpc_explorer.sh services
```

## 🚀 **Quick Start**

### **Step 1: Start the Server**
```bash
# Start in development mode (enables reflection)
aifs server --dev --port 50051
```

### **Step 2: Explore the API**

#### **Option A: Web Interface (Recommended)**
```bash
# Start web UI
python grpc_web_ui.py

# Open browser to http://localhost:8080
# - Browse services and methods
# - Test API calls interactively
# - View request/response examples
```

#### **Option B: Command Line**
```bash
# Run comprehensive tests
./grpc_explorer.sh test

# Interactive exploration
./grpc_explorer.sh interactive
```

#### **Option C: Direct gRPC Calls**
```bash
# List all services
grpcurl -plaintext localhost:50051 list

# Test health check
grpcurl -plaintext localhost:50051 aifs.v1.Health/Check

# List AIFS methods
grpcurl -plaintext localhost:50051 list aifs.v1.AIFS
```

## 📋 **API Services Overview**

### **Core Services**

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| **AIFS** | Main file system operations | `PutAsset`, `GetAsset`, `ListAssets`, `VectorSearch` |
| **Health** | Health monitoring | `Check` |
| **Introspect** | System information | `GetInfo` |
| **Admin** | Administrative operations | `CreateNamespace`, `PruneSnapshot` |
| **Metrics** | Performance metrics | `GetMetrics` |
| **Format** | Storage formatting | `FormatStorage` |

### **AIFS Service Methods**

| Method | Type | Purpose | Streaming |
|--------|------|---------|-----------|
| `PutAsset` | Store | Store assets with streaming | Client |
| `GetAsset` | Retrieve | Get asset metadata and data | Unary |
| `DeleteAsset` | Delete | Remove assets | Unary |
| `ListAssets` | List | List all assets | Unary |
| `VectorSearch` | Search | Find similar assets | Unary |
| `CreateSnapshot` | Snapshot | Create versioned snapshots | Unary |
| `GetSnapshot` | Snapshot | Get snapshot information | Unary |
| `SubscribeEvents` | Events | Real-time event streaming | Server |
| `ListNamespaces` | Namespace | List available namespaces | Unary |
| `GetNamespace` | Namespace | Get namespace details | Unary |
| `VerifyAsset` | Verify | Verify asset integrity | Unary |
| `VerifySnapshot` | Verify | Verify snapshot integrity | Unary |

## 🔐 **Authentication**

### **Generate Auth Token**
```bash
# Generate token using explorer
./grpc_explorer.sh token

# Or manually
python3 -c "
import json, base64, time
payload = {
    'permissions': ['put', 'get', 'delete', 'list', 'search', 'snapshot'],
    'expires': int(time.time()) + 3600
}
print(base64.b64encode(json.dumps(payload).encode()).decode())
"
```

### **Use Token in Requests**
```bash
# With grpcurl
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/ListAssets

# With web UI
# Paste token in the "Auth Token" field
```

## 📊 **Lineage Exploration**

### **View Asset Lineage**
```bash
# Get ancestors (parents)
python lineage_explorer.py --asset <asset_id> --ancestors

# Get descendants (children)
python lineage_explorer.py --asset <asset_id> --descendants

# Visualize lineage graph
python lineage_explorer.py --asset <asset_id> --visualize --max-depth 3
```

### **Find Lineage Paths**
```bash
# Find path between two assets
python lineage_explorer.py --path <from_asset_id>,<to_asset_id>

# Export complete lineage data
python lineage_explorer.py --export complete_lineage.json
```

## 🧪 **Testing Examples**

### **Basic Asset Operations**
```bash
# 1. Put an asset
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/PutAsset \
    -d '{
        "kind": "BLOB",
        "metadata": {"description": "Test asset"},
        "chunks": [{"data": "SGVsbG8gQUlGUw=="}]
    }'

# 2. List assets
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/ListAssets \
    -d '{"limit": 10}'

# 3. Get specific asset
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/GetAsset \
    -d '{"asset_id": "<asset_id>", "include_data": true}'
```

### **Vector Search**
```bash
# Search for similar assets
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/VectorSearch \
    -d '{
        "query_embedding": "<base64_embedding>",
        "k": 5,
        "filter": {"kind": "BLOB"}
    }'
```

### **Snapshot Operations**
```bash
# Create snapshot
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/CreateSnapshot \
    -d '{
        "namespace": "default",
        "asset_ids": ["<asset_id1>", "<asset_id2>"],
        "metadata": {"description": "Test snapshot"}
    }'

# Get snapshot
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/GetSnapshot \
    -d '{"snapshot_id": "<snapshot_id>"}'
```

## 🔧 **Advanced Usage**

### **Custom gRPC Options**
```bash
# Increase message size limits
grpcurl -plaintext \
    -H "grpc-max-receive-message-length: 100000000" \
    localhost:50051 aifs.v1.AIFS/ListAssets
```

### **Streaming Operations**
```bash
# Subscribe to events
grpcurl -plaintext -H "authorization: Bearer <token>" \
    localhost:50051 aifs.v1.AIFS/SubscribeEvents \
    -d '{"include_lineage": true, "include_drift": true}'
```

### **Performance Testing**
```bash
# Test with multiple concurrent requests
for i in {1..10}; do
    grpcurl -plaintext localhost:50051 aifs.v1.Health/Check &
done
wait
```

## 🐛 **Troubleshooting**

### **Common Issues**

1. **"Server does not support reflection"**
   ```bash
   # Start server in dev mode
   aifs server --dev --port 50051
   ```

2. **"UNAUTHENTICATED" errors**
   ```bash
   # Generate and use auth token
   ./grpc_explorer.sh token
   export AUTH_TOKEN="<generated_token>"
   ```

3. **"Connection refused"**
   ```bash
   # Check if server is running
   ./grpc_explorer.sh health
   ```

4. **"Method not found"**
   ```bash
   # Check available methods
   ./grpc_explorer.sh services
   ./grpc_explorer.sh methods aifs.v1.AIFS
   ```

### **Debug Mode**
```bash
# Enable verbose logging
export GRPC_VERBOSITY=DEBUG
export GRPC_TRACE=all

# Run tests with debug info
./grpc_explorer.sh test
```

## 📚 **Additional Resources**

- **API Documentation**: `API.md`
- **Missing Features**: `../implementation/MISSING_FEATURES.md`
- **gRPC Explorer Guide**: `grpc_exploration_guide.md`
- **Docker Usage**: `dockerhub/README.md`

## 🤝 **Contributing**

To add new exploration tools or improve existing ones:

1. Follow the existing patterns in the tools
2. Add comprehensive error handling
3. Include usage examples
4. Update this guide with new features
5. Test with both development and production servers
