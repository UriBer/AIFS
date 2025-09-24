# Docker Hub Repository Description

## Repository Description

**AIFS - AI-Native File System**

A production-ready AI-Native File System with content addressing, vector search, and versioned snapshots. Perfect for AI/ML workloads requiring semantic search and data lineage tracking.

## Short Description (for Docker Hub)

A production-ready AI-Native File System with content addressing, vector search, and versioned snapshots. Perfect for AI/ML workloads requiring semantic search and data lineage tracking.

## Full Description

### 🚀 What is AIFS?

AIFS (AI-Native File System) is a next-generation file system designed from the ground up for AI/ML workloads. It provides content-addressed storage, vector-first metadata, versioned snapshots, and semantic search capabilities.

### ✨ Key Features

- **🔗 Content Addressing**: BLAKE3-based deduplication and integrity verification
- **🔍 Vector Search**: Semantic similarity search with FAISS integration
- **🔒 Strong Causality**: Transaction system ensuring "Asset B SHALL NOT be visible until A is fully committed"
- **🌳 Versioned Snapshots**: Merkle tree-based snapshots with Ed25519 signatures
- **🔐 Enterprise Security**: AES-256-GCM encryption with KMS envelope encryption
- **🎫 Capability Authorization**: Macaroon-based tokens with namespace and method restrictions
- **🌿 Branch & Tag System**: Atomic branch updates and immutable tags for audit-grade provenance
- **🌐 gRPC API**: High-performance RPC interface with reflection support
- **📊 Data Lineage**: Complete tracking of asset transformations and dependencies
- **🗜️ Compression**: zstd compression for optimal storage efficiency
- **🐳 Docker Ready**: Production-ready containerization with health checks

### 🎯 Use Cases

- **AI/ML Data Management**: Store and search through datasets, models, and artifacts
- **RAG Systems**: Build retrieval-augmented generation pipelines
- **Data Versioning**: Track changes and maintain data lineage with branches and tags
- **Content Deduplication**: Eliminate redundant storage across projects
- **Semantic Search**: Find content by meaning, not just keywords
- **Research Reproducibility**: Maintain complete data provenance with immutable tags
- **Enterprise Security**: Secure data with encryption and capability-based authorization
- **Regulatory Compliance**: Audit-grade provenance with immutable tags and branch history
- **Multi-tenant Systems**: Namespace isolation with macaroon-based access control

### 🚀 Quick Start

```bash
# Pull and run
docker pull uriber/aifs:latest
docker run -d --name aifs-server \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest

# Test the server
docker exec aifs-server python -c "
import grpc
from aifs.proto import aifs_pb2, aifs_pb2_grpc
channel = grpc.insecure_channel('localhost:50051')
stub = aifs_pb2_grpc.HealthStub(channel)
response = stub.Check(aifs_pb2.HealthCheckRequest())
print(f'✅ AIFS is running: {response.status}')
"
```

### 📋 Available Tags

| Tag | Description | Use Case |
|-----|-------------|----------|
| `latest` | Latest stable release | Production |
| `v0.1.0-alpha` | Alpha release | Development/Testing |

### 🔧 Configuration

- **Port**: 50051 (gRPC)
- **Storage**: `/data/aifs` (persistent volume)
- **Health Check**: Built-in gRPC health service
- **Logs**: Structured logging with configurable levels

### 📚 Documentation

- [Full Documentation](https://github.com/UriBer/aifs)
- [API Reference](https://github.com/UriBer/aifs/blob/main/local_implementation/API.md)
- [Docker Guide](https://github.com/UriBer/aifs/blob/main/local_implementation/dockerhub/README.md)
- [Architecture Spec](https://github.com/UriBer/aifs/blob/main/docs/spec/rfc/0001-aifs-architecture.md)

### 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   gRPC API      │    │  Vector Search  │    │ Content Storage │
│   (Port 50051)  │◄──►│   (FAISS)       │◄──►│   (BLAKE3)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Metadata      │    │   Snapshots     │    │   Encryption    │
│   (SQLite)      │    │  (Merkle Tree)  │    │  (AES-256-GCM)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🔒 Security Features

- **Content Addressing**: BLAKE3 cryptographic hashing
- **Encryption**: AES-256-GCM for data at rest
- **Signatures**: Ed25519 for snapshot verification
- **Authorization**: Macaroon-based capability tokens
- **Isolation**: Namespace-based multi-tenancy

### 📊 Performance

- **Content Deduplication**: Eliminates redundant storage
- **Vector Search**: Sub-second similarity queries
- **Compression**: Gzip transport compression
- **Streaming**: Efficient large file handling
- **Caching**: Intelligent metadata caching

### 🛠️ Development

```bash
# Development mode with gRPC reflection
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest \
  python start_server.py --dev --storage-dir /data/aifs --port 50051

# Explore the API
grpcurl -plaintext localhost:50051 list
```

### 📈 Monitoring

- **Health Checks**: Built-in gRPC health service
- **Metrics**: Prometheus-compatible metrics endpoint
- **Logs**: Structured JSON logging
- **Tracing**: Distributed tracing support

### 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/UriBer/aifs/blob/main/CONTRIBUTING.md) for details.

### 📄 License

MIT License - see [LICENSE](https://github.com/UriBer/aifs/blob/main/LICENSE) for details.

### 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/UriBer/aifs/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UriBer/aifs/discussions)
- **Documentation**: [Full Docs](https://github.com/UriBer/aifs)

---

**Keywords**: ai, ml, machine-learning, file-system, content-addressing, vector-search, semantic-search, grpc, blake3, merkle-tree, versioning, data-lineage, storage, database, search, development

**Categories**: AI, ML, Storage, Database, Search, Development
