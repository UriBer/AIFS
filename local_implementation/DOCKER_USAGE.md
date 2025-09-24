# AIFS Docker Usage Guide

This guide explains how to run AIFS using Docker with different configurations for development and production.

## 🚀 Quick Start

### Production Mode (Default)
```bash
# Run in production mode (gRPC reflection disabled)
docker run -d --name aifs-server \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  uriber/aifs:latest
```

### Development Mode (gRPC reflection enabled)
```bash
# Run in development mode (gRPC reflection enabled)
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  -e AIFS_MODE=development \
  uriber/aifs:latest
```

## 🔧 Environment Variables

The AIFS Docker container supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AIFS_MODE` | `production` | Server mode: `production` or `development` |
| `AIFS_HOST` | `0.0.0.0` | Server host address |
| `AIFS_PORT` | `50051` | Server port |
| `AIFS_STORAGE_DIR` | `/data/aifs` | Storage directory path |
| `AIFS_MAX_WORKERS` | `10` | Maximum worker threads |
| `AIFS_COMPRESSION_LEVEL` | `1` | zstd compression level (1-22) |

## 📋 Usage Examples

### 1. Production Deployment
```bash
# Basic production setup
docker run -d --name aifs-prod \
  -p 50051:50051 \
  -v aifs-prod-data:/data/aifs \
  -e AIFS_MODE=production \
  -e AIFS_MAX_WORKERS=20 \
  -e AIFS_COMPRESSION_LEVEL=3 \
  uriber/aifs:latest
```

### 2. Development with gRPC Reflection
```bash
# Development setup with reflection enabled
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-dev-data:/data/aifs \
  -e AIFS_MODE=development \
  -e AIFS_MAX_WORKERS=5 \
  uriber/aifs:latest

# Test gRPC reflection
grpcurl -plaintext localhost:50051 list
```

### 3. Custom Configuration
```bash
# Custom port and storage
docker run -d --name aifs-custom \
  -p 8080:8080 \
  -v /host/path:/data/aifs \
  -e AIFS_MODE=production \
  -e AIFS_PORT=8080 \
  -e AIFS_HOST=0.0.0.0 \
  -e AIFS_MAX_WORKERS=15 \
  -e AIFS_COMPRESSION_LEVEL=5 \
  uriber/aifs:latest
```

### 4. High-Performance Production
```bash
# High-performance production setup
docker run -d --name aifs-hp \
  -p 50051:50051 \
  -v aifs-hp-data:/data/aifs \
  -e AIFS_MODE=production \
  -e AIFS_MAX_WORKERS=50 \
  -e AIFS_COMPRESSION_LEVEL=1 \
  --cpus="4.0" \
  --memory="8g" \
  uriber/aifs:latest
```

## 🐳 Docker Compose

### Run Both Dev and Production
```bash
# Start both development and production servers
docker-compose up -d

# Production server: localhost:50051
# Development server: localhost:50052
```

### Development Only
```bash
# Start only development server
docker-compose up -d aifs-dev
```

### Production Only
```bash
# Start only production server
docker-compose up -d aifs-prod
```

## 🔍 Testing and Debugging

### Check Server Status
```bash
# Check container status
docker ps | grep aifs

# Check logs
docker logs aifs-dev
docker logs aifs-prod
```

### Test gRPC Reflection (Development Mode Only)
```bash
# List all services
grpcurl -plaintext localhost:50051 list

# List AIFS service methods
grpcurl -plaintext localhost:50051 list aifs.v1.AIFS

# Get method details
grpcurl -plaintext localhost:50051 describe aifs.v1.AIFS.PutAsset
```

### Health Check
```bash
# Test health endpoint
curl -X POST http://localhost:50051/grpc.health.v1.Health/Check
```

## 🛠️ Development Workflow

### 1. Start Development Server
```bash
docker run -d --name aifs-dev \
  -p 50051:50051 \
  -v aifs-dev-data:/data/aifs \
  -e AIFS_MODE=development \
  uriber/aifs:latest
```

### 2. Explore API with grpcurl
```bash
# List services
grpcurl -plaintext localhost:50051 list

# Test health
grpcurl -plaintext localhost:50051 aifs.v1.Health/Check

# List assets (requires auth token)
grpcurl -plaintext -H "authorization: Bearer your-token" \
  localhost:50051 aifs.v1.AIFS/ListAssets
```

### 3. Stop Development Server
```bash
docker stop aifs-dev
docker rm aifs-dev
```

## 🚀 Production Deployment

### 1. Production Server
```bash
docker run -d --name aifs-prod \
  -p 50051:50051 \
  -v aifs-prod-data:/data/aifs \
  -e AIFS_MODE=production \
  -e AIFS_MAX_WORKERS=20 \
  --restart=unless-stopped \
  uriber/aifs:latest
```

### 2. Monitor Production
```bash
# Check health
docker exec aifs-prod /app/healthcheck.sh

# Monitor logs
docker logs -f aifs-prod

# Check resource usage
docker stats aifs-prod
```

## 🔒 Security Considerations

### Production Mode
- ✅ gRPC reflection **disabled** (more secure)
- ✅ Optimized for performance
- ✅ Production-ready logging
- ✅ Health checks enabled

### Development Mode
- ⚠️ gRPC reflection **enabled** (for API exploration)
- ⚠️ Debug logging enabled
- ⚠️ Not recommended for production

## 📊 Performance Tuning

### Environment Variables for Performance
```bash
# High-performance settings
-e AIFS_MAX_WORKERS=50          # More worker threads
-e AIFS_COMPRESSION_LEVEL=1     # Fastest compression
-e AIFS_MODE=production         # Production optimizations
```

### Docker Resource Limits
```bash
# Resource-constrained environment
docker run -d --name aifs \
  --cpus="2.0" \
  --memory="4g" \
  --memory-swap="4g" \
  -e AIFS_MAX_WORKERS=10 \
  uriber/aifs:latest
```

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Use different port
   docker run -d --name aifs \
     -p 50052:50051 \
     uriber/aifs:latest
   ```

2. **Permission Issues**
   ```bash
   # Check volume permissions
   docker exec aifs ls -la /data/aifs
   ```

3. **gRPC Reflection Not Working**
   ```bash
   # Ensure development mode
   docker run -d --name aifs \
     -e AIFS_MODE=development \
     uriber/aifs:latest
   ```

### Debug Commands
```bash
# Check container logs
docker logs aifs-dev

# Execute shell in container
docker exec -it aifs-dev /bin/bash

# Check environment variables
docker exec aifs-dev env | grep AIFS

# Test health check
docker exec aifs-dev /app/healthcheck.sh
```

## 📚 Additional Resources

- [AIFS Documentation](../README.md)
- [API Reference](../API.md)
- [Testing Guide](../TESTING_GUIDE.md)
- [Docker Hub Repository](https://hub.docker.com/r/uriber/aifs)

## 🆘 Support

For issues and questions:
- Check the [troubleshooting section](#-troubleshooting)
- Review container logs: `docker logs <container-name>`
- Test health endpoint: `docker exec <container-name> /app/healthcheck.sh`
