# 🔍 AIFS gRPC API Exploration Guide

## ✅ **Working Methods (No Reflection Required)**

Since reflection may not be working, here are the methods that work directly:

### **1. Direct gRPC Calls with Proto Files**

```bash
# Health check (works without reflection)
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto localhost:50051 aifs.v1.Health/Check

# List all services (if reflection works)
grpcurl -plaintext localhost:50051 list

# List AIFS methods (if reflection works)
grpcurl -plaintext localhost:50051 list aifs.v1.AIFS
```

### **2. Using Python Client**

```python
from aifs.client import AIFSClient

# Connect to server
client = AIFSClient("localhost:50051")

# Test health
health_client = client.get_health_client()
response = health_client.Check()
print(f"Health: {response}")
```

### **3. Using grpcurl with Proto Files**

```bash
# Health check
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto localhost:50051 aifs.v1.Health/Check

# List assets (requires authentication)
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto \
  -d '{"limit": 10}' localhost:50051 aifs.v1.AIFS/ListAssets

# Get asset (requires authentication)
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto \
  -d '{"asset_id": "your_asset_id"}' localhost:50051 aifs.v1.AIFS/GetAsset
```

## 🛠️ **Available Services & Methods**

### **AIFS Service (Main)**
- `PutAsset` - Store assets with streaming
- `GetAsset` - Retrieve assets
- `DeleteAsset` - Delete assets
- `ListAssets` - List all assets
- `VectorSearch` - Search similar assets
- `CreateSnapshot` - Create snapshots
- `GetSnapshot` - Get snapshot info
- `SubscribeEvents` - Real-time events
- `ListNamespaces` - List namespaces
- `GetNamespace` - Get namespace info
- `VerifyAsset` - Verify asset integrity
- `VerifySnapshot` - Verify snapshots

### **Built-in Services**
- `Health/Check` - Health status
- `Introspect/GetInfo` - System info
- `Admin/CreateNamespace` - Create namespaces
- `Admin/PruneSnapshot` - Prune snapshots
- `Admin/ManagePolicy` - Manage policies
- `Metrics/GetMetrics` - System metrics
- `Format/FormatStorage` - Format storage

## 🔐 **Authentication**

All AIFS methods require authentication:

```bash
# Include authorization header
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto \
  -H "authorization: Bearer your_token" \
  localhost:50051 aifs.v1.AIFS/ListAssets
```

## 🎯 **Quick Test Commands**

```bash
# 1. Test server is running
grpcurl -plaintext -import-path aifs/proto -proto aifs.proto localhost:50051 aifs.v1.Health/Check

# 2. Test with Python
python -c "from aifs.client import AIFSClient; client = AIFSClient('localhost:50051'); print('Connected!')"

# 3. Test web interface
python grpc_web_interface.py
# Open http://localhost:5000
```

## 📚 **Alternative Exploration Methods**

### **1. Postman (GUI)**
- Open Postman
- Create new gRPC request
- Server: `localhost:50051`
- Import proto file: `aifs/proto/aifs.proto`

### **2. BloomRPC (GUI)**
```bash
brew install --cask bloomrpc
# Open BloomRPC and import aifs.proto
```

### **3. Evans (CLI)**
```bash
brew install evans
evans --host localhost --port 50051 --proto aifs/proto/aifs.proto
```

### **4. Web Interface**
```bash
python grpc_web_interface.py
# Open http://localhost:5000
```

## 🚀 **Getting Started**

1. **Start the server:**
   ```bash
   python start_server.py
   ```

2. **Test connectivity:**
   ```bash
   grpcurl -plaintext -import-path aifs/proto -proto aifs.proto localhost:50051 aifs.v1.Health/Check
   ```

3. **Explore with your preferred tool:**
   - Command line: grpcurl
   - GUI: Postman or BloomRPC
   - Web: grpc_web_interface.py

## 📖 **Proto File Location**

The proto file is at: `aifs/proto/aifs.proto`

This contains all the service definitions, message types, and method signatures.
