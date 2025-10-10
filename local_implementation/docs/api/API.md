# AIFS API Documentation

This document provides comprehensive API documentation for the AIFS (AI-Native File System) gRPC services.

## Overview

AIFS provides a high-performance gRPC API for content-addressed storage, vector search, and versioned snapshots. The API is designed for AI/ML workloads with semantic search capabilities.

## Quick Start

### Docker Hub (Recommended)
```bash
# Pull and run the latest version
docker pull uriber/aifs:latest
docker run -p 50051:50051 -v aifs-data:/data/aifs uriber/aifs:latest

# Test the API
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check
```

### Local Docker Build
```bash
# Start with Docker Compose
docker-compose up -d

# Test the API
grpcurl -plaintext localhost:50051 list
```

### Local Development
```bash
# Start server in development mode
python start_server.py --dev

# Test with grpcurl
grpcurl -plaintext localhost:50051 list
```

## Services

### 1. AIFS Service
Core asset management operations.

#### Methods

##### PutAsset
Store a new asset in the system.

**Request:**
```protobuf
message PutAssetRequest {
  repeated Chunk chunks = 1;
  AssetKind kind = 2;
  map<string, string> metadata = 3;
  bytes embedding = 4;
  repeated string parents = 5;
}
```

**Response:**
```protobuf
message PutAssetResponse {
  string asset_id = 1;
  string uri = 2;
  int64 size = 3;
  string hash = 4;
}
```

##### GetAsset
Retrieve an asset by ID.

**Request:**
```protobuf
message GetAssetRequest {
  string asset_id = 1;
  bool include_data = 2;
}
```

**Response:**
```protobuf
message GetAssetResponse {
  AssetMetadata metadata = 1;
  repeated ParentEdge parents = 2;
  repeated string children = 3;
  bytes data = 4;
  string uri = 5;
}
```

##### DeleteAsset
Remove an asset from the system.

**Request:**
```protobuf
message DeleteAssetRequest {
  string asset_id = 1;
}
```

**Response:**
```protobuf
message DeleteAssetResponse {
  bool success = 1;
}
```

##### ListAssets
List all assets with optional filtering.

**Request:**
```protobuf
message ListAssetsRequest {
  int32 page_size = 1;
  string page_token = 2;
  string filter = 3;
}
```

**Response:**
```protobuf
message ListAssetsResponse {
  repeated AssetSummary assets = 1;
  string next_page_token = 2;
}
```

##### VectorSearch
Search for similar assets using vector similarity.

**Request:**
```protobuf
message VectorSearchRequest {
  bytes query_embedding = 1;
  int32 k = 2;
  double threshold = 3;
  string filter = 4;
}
```

**Response:**
```protobuf
message VectorSearchResponse {
  repeated SearchResult results = 1;
}
```

### 2. Health Service
Health monitoring and status checks.

#### Methods

##### Check
Perform a health check.

**Request:**
```protobuf
message HealthCheckRequest {
  string service = 1;
}
```

**Response:**
```protobuf
message HealthCheckResponse {
  enum ServingStatus {
    UNKNOWN = 0;
    SERVING = 1;
    NOT_SERVING = 2;
  }
  ServingStatus status = 1;
}
```

### 3. Introspect Service
API introspection and discovery.

#### Methods

##### ListServices
List all available services.

**Request:**
```protobuf
message ListServicesRequest {}
```

**Response:**
```protobuf
message ListServicesResponse {
  repeated string services = 1;
}
```

##### DescribeService
Get detailed information about a service.

**Request:**
```protobuf
message DescribeServiceRequest {
  string service_name = 1;
}
```

**Response:**
```protobuf
message DescribeServiceResponse {
  string service_name = 1;
  repeated string methods = 2;
  string description = 3;
}
```

### 4. Admin Service
Administrative operations.

#### Methods

##### CreateSnapshot
Create a versioned snapshot of assets.

**Request:**
```protobuf
message CreateSnapshotRequest {
  repeated string asset_ids = 1;
  string namespace = 2;
  string description = 3;
}
```

**Response:**
```protobuf
message CreateSnapshotResponse {
  string snapshot_id = 1;
  string merkle_root = 2;
  int64 timestamp = 3;
}
```

##### GetSnapshot
Retrieve snapshot information.

**Request:**
```protobuf
message GetSnapshotRequest {
  string snapshot_id = 1;
}
```

**Response:**
```protobuf
message GetSnapshotResponse {
  SnapshotMetadata metadata = 1;
  repeated string asset_ids = 2;
  string merkle_root = 3;
  bytes signature = 4;
}
```

### 5. Metrics Service
Performance monitoring and metrics.

#### Methods

##### GetMetrics
Retrieve system metrics.

**Request:**
```protobuf
message GetMetricsRequest {
  string metric_name = 1;
  int64 start_time = 2;
  int64 end_time = 3;
}
```

**Response:**
```protobuf
message GetMetricsResponse {
  repeated MetricData metrics = 1;
}
```

### 6. Format Service
Data format conversion and validation.

#### Methods

##### ValidateFormat
Validate data format.

**Request:**
```protobuf
message ValidateFormatRequest {
  bytes data = 1;
  string format = 2;
}
```

**Response:**
```protobuf
message ValidateFormatResponse {
  bool valid = 1;
  string error_message = 2;
}
```

## Data Types

### AssetKind
```protobuf
enum AssetKind {
  UNKNOWN = 0;
  BLOB = 1;
  TENSOR = 2;
  EMBED = 3;
  ARTIFACT = 4;
}
```

### AssetMetadata
```protobuf
message AssetMetadata {
  string asset_id = 1;
  AssetKind kind = 2;
  int64 size = 3;
  string hash = 4;
  int64 created_at = 5;
  int64 updated_at = 6;
  map<string, string> metadata = 7;
  bytes embedding = 8;
}
```

### Chunk
```protobuf
message Chunk {
  bytes data = 1;
}
```

### ParentEdge
```protobuf
message ParentEdge {
  string parent_id = 1;
  string relationship = 2;
  int64 created_at = 3;
}
```

### SearchResult
```protobuf
message SearchResult {
  string asset_id = 1;
  double similarity = 2;
  AssetMetadata metadata = 3;
}
```

### SnapshotMetadata
```protobuf
message SnapshotMetadata {
  string snapshot_id = 1;
  string namespace = 2;
  string description = 3;
  int64 created_at = 4;
  string created_by = 5;
}
```

### MetricData
```protobuf
message MetricData {
  string name = 1;
  double value = 2;
  int64 timestamp = 3;
  map<string, string> labels = 4;
}
```

## Error Handling

All services use structured error responses with `google.rpc.Status`:

```protobuf
message Status {
  int32 code = 1;
  string message = 2;
  repeated google.protobuf.Any details = 3;
}
```

### Common Error Codes
- `INVALID_ARGUMENT` (3): Invalid request parameters
- `NOT_FOUND` (5): Resource not found
- `PERMISSION_DENIED` (7): Insufficient permissions
- `UNAUTHENTICATED` (16): Authentication required
- `INTERNAL` (13): Internal server error

## Authentication

AIFS uses Bearer token authentication with JSON Web Tokens (JWTs) or simple JSON tokens.

### Request Headers
```
Authorization: Bearer <token>
```

### Token Format
```json
{
  "permissions": ["put", "get", "delete", "list", "search", "snapshot"],
  "expires": 1640995200
}
```

## Usage Examples

### Python Client
```python
import grpc
from aifs.proto import aifs_pb2, aifs_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')

# Create client
client = aifs_pb2_grpc.AIFSStub(channel)

# Put an asset
request = aifs_pb2.PutAssetRequest()
chunk = request.chunks.add()
chunk.data = b"Hello, AIFS!"
request.kind = aifs_pb2.AssetKind.BLOB
request.metadata["description"] = "Test asset"

response = client.PutAsset(iter([request]))
print(f"Asset ID: {response.asset_id}")
```

### Command Line
```bash
# Start server in development mode
python start_server.py --dev --port 50051

# Use grpcurl for testing
grpcurl -plaintext localhost:50051 list
grpcurl -plaintext localhost:50051 aifs.AIFS/ListAssets
```

## Development Mode

When starting the server with `--dev` flag, gRPC reflection is enabled for API discovery:

```bash
python start_server.py --dev
```

This allows tools like `grpcurl` to discover and interact with the API without requiring `.proto` files.

## Performance Considerations

- **Chunking**: Large files are automatically chunked for efficient storage
- **Compression**: Gzip compression is enabled by default
- **Vector Indexing**: FAISS HNSW indexing provides fast similarity search
- **Concurrent Operations**: Multi-threaded server supports concurrent requests
- **Content Deduplication**: Automatic deduplication based on BLAKE3 hashes

## Security Features

- **Data Encryption**: All data encrypted with AES-256-GCM
- **Key Management**: KMS integration for envelope encryption
- **Digital Signatures**: Ed25519 signatures for snapshot integrity
- **Access Control**: Macaroon-based authorization
- **Secure Transport**: TLS support for encrypted communication
