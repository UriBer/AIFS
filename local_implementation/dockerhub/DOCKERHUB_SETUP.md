# AIFS Docker Hub Publishing Setup

This directory contains all the necessary files and scripts for publishing AIFS to Docker Hub, making it easy for users to pull, test, and use the AIFS solution.

## 📁 Directory Structure

```
dockerhub/
├── README.md                           # Docker Hub README (main documentation)
├── DOCKERHUB_SETUP.md                  # This setup guide
├── Makefile                            # Convenient make commands
├── .gitignore                          # Git ignore rules
├── publish.sh                          # Script to build and push images
├── test.sh                             # Script to test published images
├── docker-compose.production.yml       # Production Docker Compose
├── docker-compose.development.yml      # Development Docker Compose
├── docker-compose.testing.yml          # Testing Docker Compose
└── examples/                           # Usage examples
    ├── quick-start.sh                  # Quick start demo script
    ├── python-client-example.py        # Python client example
    └── grpc-exploration.sh             # gRPC API exploration script
```

## 🚀 Quick Start for Users

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

### Development Mode
```bash
# Run with gRPC reflection enabled
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  uriber/aifs:dev

# Explore the API
grpcurl -plaintext localhost:50051 list
```

## 🛠️ Publishing Workflow

### 1. Build and Test Locally
```bash
# Build the image
make build VERSION=v0.1.0

# Test the image
make test VERSION=v0.1.0

# Or use the scripts directly
./publish.sh v0.1.0
```

### 2. Publish to Docker Hub
```bash
# Publish the image
make publish VERSION=v0.1.0

# Or use the script directly
./publish.sh v0.1.0
```

### 3. Verify Publication
```bash
# Test the published image
make test VERSION=v0.1.0

# Or use the test script
./test.sh v0.1.0
```

## 📋 Available Commands

### Make Commands
```bash
make help                    # Show all available commands
make build                   # Build Docker image
make test                    # Test Docker image
make publish                 # Publish to Docker Hub
make dev                     # Build and test development image
make prod                    # Build and test production image
make clean                   # Clean up Docker resources
make status                  # Show Docker status
make quick-start             # Run quick start demo
make grpc-explore            # Explore gRPC API
make python-example          # Run Python client example
```

### Docker Compose Commands
```bash
make compose-up              # Start production services
make compose-up-dev          # Start development services
make compose-down            # Stop all services
make compose-logs            # Show service logs
```

## 🐳 Docker Images

### Available Tags
- `uriber/aifs:latest` - Latest stable release
- `uriber/aifs:dev` - Development build with gRPC reflection
- `uriber/aifs:v0.1.0-alpha` - Specific version tags

### Image Features
- **Multi-platform**: Supports linux/amd64 and linux/arm64
- **Production-ready**: Optimized for production deployment
- **Security**: Runs as non-root user with proper permissions
- **Health checks**: Built-in health monitoring
- **Logging**: Configurable log levels
- **Volumes**: Persistent data storage

## 📚 Examples and Demos

### 1. Quick Start Demo
```bash
# Run the interactive demo
./examples/quick-start.sh
```
This script will:
- Pull the AIFS Docker image
- Start the server
- Demonstrate basic operations
- Keep the server running for interactive use

### 2. Python Client Example
```bash
# Run the Python client example
./examples/python-client-example.py
```
This script demonstrates:
- Connecting to the AIFS server
- Storing and retrieving assets
- Working with metadata
- Error handling

### 3. gRPC API Exploration
```bash
# Explore the gRPC API
./examples/grpc-exploration.sh
```
This script shows:
- Available gRPC services
- Service methods
- Interactive API exploration

## 🔧 Configuration

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `AIFS_DATA_DIR` | `/data/aifs` | Data storage directory |
| `AIFS_PORT` | `50051` | gRPC server port |
| `AIFS_HOST` | `0.0.0.0` | Server bind address |
| `AIFS_LOG_LEVEL` | `INFO` | Logging level |

### Docker Compose Profiles
- **Production**: `docker-compose -f docker-compose.production.yml up -d`
- **Development**: `docker-compose -f docker-compose.development.yml up -d`
- **Testing**: `docker-compose -f docker-compose.testing.yml up -d`

## 🧪 Testing

### Automated Testing
```bash
# Test the latest image
./test.sh

# Test a specific version
./test.sh v0.1.0

# Test on different port
./test.sh latest 50052
```

### Manual Testing
```bash
# Health check
docker exec aifs-server /app/healthcheck.sh

# API test
docker exec aifs-server python -c "
from aifs.client import AIFSClient
client = AIFSClient('localhost:50051')
assets = client.list_assets()
print(f'Found {len(assets)} assets')
"
```

## 📊 Monitoring

### Container Status
```bash
# Check running containers
docker ps | grep aifs

# Check container logs
docker logs aifs-server

# Check resource usage
docker stats aifs-server
```

### Health Monitoring
```bash
# Built-in health check
docker exec aifs-server /app/healthcheck.sh

# gRPC health check
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check
```

## 🔒 Security

### Production Security
- **Non-root user**: Container runs as `aifs` user
- **Encrypted storage**: All data encrypted with AES-256-GCM
- **No reflection**: gRPC reflection disabled in production
- **Health checks**: Automatic service monitoring

### Network Security
```bash
# Run on internal network
docker run -d --name aifs-server \
  --network internal \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest
```

## 📈 Performance

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 512M
      cpus: '0.5'
```

### Optimization
- **Multi-stage build**: Optimized image size
- **Layer caching**: Efficient builds
- **Health checks**: Fast startup detection
- **Logging**: Configurable verbosity

## 🆘 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker logs aifs-server

# Check port conflicts
lsof -i :50051

# Try different port
docker run -p 50052:50051 uriber/aifs:latest
```

#### Health Check Fails
```bash
# Check container status
docker ps -a

# Check logs
docker logs aifs-server

# Restart container
docker restart aifs-server
```

#### API Connection Issues
```bash
# Test connectivity
telnet localhost 50051

# Check firewall
sudo ufw status

# Test with grpcurl
grpcurl -plaintext localhost:50051 list
```

### Debug Mode
```bash
# Run with debug logging
docker run -d --name aifs-debug \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  -e AIFS_LOG_LEVEL=DEBUG \
  uriber/aifs:latest

# Attach to container
docker exec -it aifs-debug /bin/bash
```

## 📚 Documentation

### User Documentation
- [Docker Hub README](README.md) - Main user documentation
- [API Reference](../API.md) - Complete API documentation
- [Architecture Spec](../../docs/spec/rfc/0001-aifs-architecture.md) - Technical specification

### Developer Documentation
- [Contributing Guide](../../CONTRIBUTING.md) - Development guidelines
- [Changelog](../../CHANGELOG.md) - Version history
- [Project README](../../README.md) - Project overview

## 🤝 Contributing

### Adding New Examples
1. Create new example in `examples/` directory
2. Make it executable: `chmod +x examples/new-example.sh`
3. Add to Makefile if needed
4. Update documentation

### Improving Scripts
1. Follow existing patterns
2. Add proper error handling
3. Include help documentation
4. Test thoroughly

### Updating Documentation
1. Keep examples current
2. Test all code snippets
3. Update version numbers
4. Maintain consistency

## 📄 License

This Docker Hub publishing setup is part of the AIFS project and follows the same license terms. See the main project LICENSE file for details.

---

**Ready to publish?** Run `make publish VERSION=v0.1.0` to build and publish your first AIFS Docker image!
