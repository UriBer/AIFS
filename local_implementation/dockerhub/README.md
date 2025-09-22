# AIFS - AI-Native File System

[![Docker Pulls](https://img.shields.io/docker/pulls/uriber/aifs)](https://hub.docker.com/r/uriber/aifs)
[![Docker Image Size](https://img.shields.io/docker/image-size/uriber/aifs)](https://hub.docker.com/r/uriber/aifs)
[![Docker Stars](https://img.shields.io/docker/stars/uriber/aifs)](https://hub.docker.com/r/uriber/aifs)

A production-ready AI-Native File System with content addressing, vector search, and versioned snapshots. Perfect for AI/ML workloads requiring semantic search and data lineage tracking.

## 🚀 Quick Start

### Pull and Run
```bash
# Pull the latest image
docker pull uriber/aifs:latest

# Run with default settings
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

### Development Mode (with gRPC reflection)
```bash
# Run with gRPC reflection enabled
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest \
  python start_server.py --dev --storage-dir /data/aifs --port 50051

# Explore the API with grpcurl
grpcurl -plaintext localhost:50051 list
```

## 📋 Available Tags

| Tag | Description | Use Case |
|-----|-------------|----------|
| `latest` | Latest stable release | Production |
| `dev` | Development build with gRPC reflection | Development |
| `v0.1.0-alpha` | Specific version | Version pinning |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIFS_DATA_DIR` | `/data/aifs` | Data storage directory |
| `AIFS_PORT` | `50051` | gRPC server port |
| `AIFS_HOST` | `0.0.0.0` | Server bind address |
| `AIFS_LOG_LEVEL` | `INFO` | Logging level |

### Volume Mounts

| Host Path | Container Path | Description |
|-----------|----------------|-------------|
| `aifs-data` | `/data/aifs` | Persistent data storage |
| `./logs` | `/app/logs` | Log files (optional) |

## 🐳 Docker Compose

### Production Setup
```yaml
version: '3.8'
services:
  aifs:
    image: uriber/aifs:latest
    container_name: aifs-server
    ports:
      - "50051:50051"
    volumes:
      - aifs-data:/data/aifs
    environment:
      - AIFS_LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "/app/healthcheck.sh"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  aifs-data:
```

### Development Setup
```yaml
version: '3.8'
services:
  aifs-dev:
    image: uriber/aifs:dev
    container_name: aifs-dev
    ports:
      - "50051:50051"
    volumes:
      - aifs-dev-data:/data/aifs
      - ./logs:/app/logs
    environment:
      - AIFS_LOG_LEVEL=DEBUG
    command: python start_server.py --dev --storage-dir /data/aifs --port 50051
    restart: unless-stopped

volumes:
  aifs-dev-data:
```

## 🧪 Testing

### Health Check
```bash
# Check if the server is running
docker exec aifs-server /app/healthcheck.sh

# Or use grpcurl
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check
```

### Basic API Test
```bash
# Store an asset
docker exec aifs-server python -c "
from aifs.client import AIFSClient
client = AIFSClient('localhost:50051')
asset_id = client.put_asset(b'Hello, AIFS!', 'blob', metadata={'test': 'true'})
print(f'Stored asset: {asset_id}')
"

# List assets
docker exec aifs-server python -c "
from aifs.client import AIFSClient
client = AIFSClient('localhost:50051')
assets = client.list_assets()
print(f'Found {len(assets)} assets')
"
```

## 🔍 API Exploration

### With grpcurl (Development Mode)
```bash
# List all services
grpcurl -plaintext localhost:50051 list

# List AIFS service methods
grpcurl -plaintext localhost:50051 list aifs.AIFS

# Call a method
grpcurl -plaintext localhost:50051 aifs.AIFS/ListAssets
```

### With Python Client
```python
from aifs.client import AIFSClient

# Connect to the server
client = AIFSClient("localhost:50051")

# Store an asset
asset_id = client.put_asset(
    data=b"Hello, AIFS!",
    kind="blob",
    metadata={"description": "Test asset"}
)

# Retrieve the asset
asset = client.get_asset(asset_id)
print(f"Retrieved: {asset['data']}")

# Vector search (if embeddings are available)
results = client.vector_search(query_embedding, k=5)
```

## 📊 Monitoring

### View Logs
```bash
# Follow logs
docker logs -f aifs-server

# View recent logs
docker logs --tail 100 aifs-server
```

### Resource Usage
```bash
# Check container stats
docker stats aifs-server

# Check disk usage
docker exec aifs-server du -sh /data/aifs
```

## 🛠️ Development

### Build from Source
```bash
# Clone the repository
git clone https://github.com/UriBer/AIFS.git
cd AIFS/local_implementation

# Build the image
docker build -t aifs:local .

# Run the local build
docker run -p 50051:50051 -v aifs-data:/data/aifs aifs:local
```

### Debug Mode
```bash
# Run with debug logging
docker run -d --name aifs-debug \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  -e AIFS_LOG_LEVEL=DEBUG \
  uriber/aifs:latest

# Attach to container for debugging
docker exec -it aifs-debug /bin/bash
```

## 🔒 Security

### Production Considerations
- The container runs as a non-root user (`aifs`)
- Data is encrypted at rest with AES-256-GCM
- gRPC reflection is disabled in production builds
- Health checks ensure service availability

### Network Security
```bash
# Run on internal network only
docker run -d --name aifs-server \
  --network internal \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest
```

## 📚 Documentation

- [Full Documentation](https://github.com/UriBer/AIFS)
- [API Reference](https://github.com/UriBer/AIFS/blob/main/local_implementation/API.md)
- [Architecture Spec](https://github.com/UriBer/AIFS/blob/main/docs/spec/rfc/0001-aifs-architecture.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://github.com/UriBer/AIFS/blob/main/CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the terms specified in the [LICENSE](https://github.com/UriBer/AIFS/blob/main/LICENSE) file.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/UriBer/AIFS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UriBer/AIFS/discussions)
- **Documentation**: [Project Wiki](https://github.com/UriBer/AIFS/wiki)

---

**Ready to get started?** Pull the image and run your first AIFS container in under 30 seconds!