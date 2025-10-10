# AIFS API Reference

This document provides a comprehensive reference for the AIFS gRPC API.

## 🚀 **Server Endpoints**

- **Production**: `localhost:50051` (gRPC reflection disabled)
- **Development**: `localhost:50052` (gRPC reflection enabled)

## 📋 **Available Services**

### **1. Health Service (`aifs.v1.Health`)**
- **Purpose**: Health checks and server status
- **Methods**:
  - `Check()` - Check server health

### **2. Main AIFS Service (`aifs.v1.AIFS`)**
- **Purpose**: Core AIFS operations
- **Methods**: See detailed list below

### **3. Admin Service (`aifs.v1.Admin`)**
- **Purpose**: Administrative operations
- **Methods**: Server management and configuration

### **4. Format Service (`aifs.v1.Format`)**
- **Purpose**: Storage formatting and maintenance
- **Methods**: Disk operations and cleanup

### **5. Introspect Service (`aifs.v1.Introspect`)**
- **Purpose**: Server introspection and debugging
- **Methods**: Internal state inspection

### **6. Metrics Service (`aifs.v1.Metrics`)**
- **Purpose**: Performance metrics and monitoring
- **Methods**: Statistics and monitoring data

## 🔧 **Core AIFS Methods**

### **Asset Management**

#### **PutAsset** (Streaming)
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/PutAsset \
  -d '{
    "asset": {
      "namespace": "default",
      "name": "my-file.txt",
      "kind": "BLOB",
      "metadata": {
        "content_type": "text/plain",
        "description": "My test file"
      }
    },
    "data": "SGVsbG8gV29ybGQh"  # Base64 encoded data
  }'
```

#### **GetAsset**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetAsset \
  -d '{"uri": "aifs://default/my-file.txt"}'
```

#### **ListAssets**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListAssets \
  -d '{
    "namespace": "default",
    "limit": 100,
    "offset": 0
  }'
```

#### **DeleteAsset**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/DeleteAsset \
  -d '{"uri": "aifs://default/my-file.txt"}'
```

#### **VerifyAsset**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/VerifyAsset \
  -d '{"uri": "aifs://default/my-file.txt"}'
```

### **Snapshot Management**

#### **CreateSnapshot**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/CreateSnapshot \
  -d '{
    "namespace": "default",
    "description": "My snapshot",
    "metadata": {
      "version": "1.0.0"
    }
  }'
```

#### **GetSnapshot**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetSnapshot \
  -d '{"snapshot_id": "snapshot-id-here"}'
```

#### **VerifySnapshot**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/VerifySnapshot \
  -d '{"snapshot_id": "snapshot-id-here"}'
```

### **Branch Management**

#### **CreateBranch**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/CreateBranch \
  -d '{
    "branch_name": "main",
    "namespace": "default",
    "snapshot_id": "snapshot-id-here",
    "metadata": {
      "description": "Main branch"
    }
  }'
```

#### **GetBranch**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetBranch \
  -d '{
    "branch_name": "main",
    "namespace": "default"
  }'
```

#### **ListBranches**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListBranches \
  -d '{"namespace": "default"}'
```

#### **GetBranchHistory**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetBranchHistory \
  -d '{
    "branch_name": "main",
    "namespace": "default"
  }'
```

#### **DeleteBranch**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/DeleteBranch \
  -d '{
    "branch_name": "main",
    "namespace": "default"
  }'
```

### **Tag Management**

#### **CreateTag**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/CreateTag \
  -d '{
    "tag_name": "v1.0.0",
    "namespace": "default",
    "snapshot_id": "snapshot-id-here",
    "metadata": {
      "description": "Version 1.0.0 release"
    }
  }'
```

#### **GetTag**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetTag \
  -d '{
    "tag_name": "v1.0.0",
    "namespace": "default"
  }'
```

#### **ListTags**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListTags \
  -d '{"namespace": "default"}'
```

#### **DeleteTag**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/DeleteTag \
  -d '{
    "tag_name": "v1.0.0",
    "namespace": "default"
  }'
```

### **Namespace Management**

#### **GetNamespace**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetNamespace \
  -d '{"namespace": "default"}'
```

#### **ListNamespaces**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListNamespaces
```

### **Vector Search**

#### **VectorSearch**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/VectorSearch \
  -d '{
    "namespace": "default",
    "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
    "limit": 10,
    "threshold": 0.8
  }'
```

### **Event Subscription**

#### **SubscribeEvents**
```bash
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/SubscribeEvents \
  -d '{
    "namespace": "default",
    "event_types": ["ASSET_CREATED", "ASSET_UPDATED"]
  }'
```

## 🔐 **Authentication**

Most AIFS operations require authentication. You can use the CLI to generate tokens:

```bash
# Generate a token
aifs auth create-token --namespace default --permissions "read,write"

# Use token in API calls
grpcurl -plaintext -H "authorization: Bearer your-token-here" \
  localhost:50052 aifs.v1.AIFS/ListAssets \
  -d '{"namespace": "default"}'
```

## 📊 **Asset Kinds**

AIFS supports different asset kinds:

- **BLOB**: Binary data (files, images, etc.)
- **TENSOR**: Numerical arrays (ML models, datasets)
- **EMBED**: Vector embeddings
- **ARTIFACT**: Complex structured data (ZIP files, etc.)

## 🌐 **URI Schemes**

- **Assets**: `aifs://namespace/asset-name`
- **Snapshots**: `aifs-snap://namespace/snapshot-id`

## 🔧 **Error Handling**

AIFS uses standard gRPC status codes:

- **OK (0)**: Success
- **INVALID_ARGUMENT (3)**: Invalid request parameters
- **NOT_FOUND (5)**: Resource not found
- **PERMISSION_DENIED (7)**: Authentication/authorization failed
- **INTERNAL (13)**: Server error

## 📝 **Example Workflow**

```bash
# 1. Check server health
grpcurl -plaintext localhost:50052 aifs.v1.Health/Check

# 2. List namespaces
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListNamespaces

# 3. Create an asset
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/PutAsset \
  -d '{
    "asset": {
      "namespace": "default",
      "name": "hello.txt",
      "kind": "BLOB",
      "metadata": {"content_type": "text/plain"}
    },
    "data": "SGVsbG8gV29ybGQh"
  }'

# 4. List assets
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListAssets \
  -d '{"namespace": "default"}'

# 5. Get the asset
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/GetAsset \
  -d '{"uri": "aifs://default/hello.txt"}'

# 6. Create a snapshot
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/CreateSnapshot \
  -d '{
    "namespace": "default",
    "description": "Initial snapshot"
  }'
```

## 🚀 **Production vs Development**

- **Development Server** (`localhost:50052`):
  - gRPC reflection enabled
  - Debug logging
  - Use for API exploration and testing

- **Production Server** (`localhost:50051`):
  - gRPC reflection disabled (more secure)
  - Optimized performance
  - Use for actual operations

## 📚 **Additional Resources**

- [CLI Usage Guide](../guides/CLI_USAGE.md)
- [API Exploration Guide](../guides/API_EXPLORATION_GUIDE.md)
- [Docker Usage Guide](../docker/DOCKER_USAGE.md)
- [Main Documentation](../../README.md)
