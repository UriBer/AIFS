# AIFS Docker Deployment Guide

This guide covers deploying AIFS using Docker containers for production and development environments.

## 🐳 Quick Start

### Production Deployment
```bash
# Build and run production container
./docker-build.sh
./docker-run.sh

# Or use docker-compose
docker-compose up -d
```

### Development Deployment
```bash
# Run with gRPC reflection enabled
./docker-run.sh --dev

# Or use docker-compose with dev profile
docker-compose --profile dev up -d
```

## 📋 Prerequisites

- Docker 20.10+ with BuildKit support
- Docker Compose 2.0+
- At least 2GB RAM available for the container
- 10GB+ disk space for data volumes

## 🏗️ Building the Image

### Using the Build Script
```bash
# Basic build
./docker-build.sh

# Build with custom tag and version
./docker-build.sh --tag myregistry/aifs --version v1.0.0

# Build for multiple platforms
./docker-build.sh --platform linux/amd64,linux/arm64

# Build and push to registry
./docker-build.sh --push --tag myregistry/aifs --version v1.0.0
```

### Manual Build
```bash
# Build production image
docker build --target production -t aifs:latest .

# Build with specific platform
docker buildx build --platform linux/amd64 --target production -t aifs:latest .
```

## 🚀 Running Containers

### Using the Run Script
```bash
# Production mode
./docker-run.sh

# Development mode with gRPC reflection
./docker-run.sh --dev

# Custom configuration
./docker-run.sh --port 8080 --data-dir /custom/path --name my-aifs

# Interactive mode
./docker-run.sh --interactive
```

### Manual Docker Run
```bash
# Production container
docker run -d \
  --name aifs-server \
  -p 50051:50051 \
  -v aifs-data:/data/aifs \
  --restart unless-stopped \
  aifs:latest

# Development container with gRPC reflection
docker run -d \
  --name aifs-dev \
  -p 50052:50051 \
  -v aifs-dev-data:/data/aifs \
  --restart unless-stopped \
  aifs:latest \
  python start_server.py --dev --storage-dir /data/aifs --port 50051
```

### Using Docker Compose
```bash
# Production deployment
docker-compose up -d

# Development deployment
docker-compose --profile dev up -d

# CLI access
docker-compose --profile cli run aifs-cli python aifs_cli.py --help

# View logs
docker-compose logs -f aifs-server
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AIFS_DATA_DIR` | `/data/aifs` | Data storage directory |
| `AIFS_PORT` | `50051` | gRPC server port |
| `AIFS_HOST` | `0.0.0.0` | Server bind address |
| `AIFS_LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `PYTHONUNBUFFERED` | `1` | Python output buffering |

### Volume Mounts

| Host Path | Container Path | Description |
|-----------|----------------|-------------|
| `./aifs-data` | `/data/aifs` | Persistent data storage |
| `./logs` | `/app/logs` | Application logs |

### Port Mappings

| Container Port | Host Port | Description |
|----------------|-----------|-------------|
| `50051` | `50051` | gRPC API endpoint |

## 🏥 Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker ps

# View health check logs
docker inspect aifs-server | jq '.[0].State.Health'

# Manual health check
docker exec aifs-server /app/healthcheck.sh
```

## 📊 Monitoring

### View Logs
```bash
# Follow logs
docker logs -f aifs-server

# View last 100 lines
docker logs --tail 100 aifs-server

# View logs with timestamps
docker logs -t aifs-server
```

### Container Stats
```bash
# Real-time stats
docker stats aifs-server

# One-time stats
docker stats --no-stream aifs-server
```

### Resource Usage
```bash
# Container resource usage
docker exec aifs-server ps aux

# Disk usage
docker exec aifs-server df -h
```

## 🔒 Security

### Production Security Features
- **Non-root User**: Container runs as `aifs` user
- **Read-only Filesystem**: Application code is read-only
- **Minimal Attack Surface**: Multi-stage build removes build tools
- **No gRPC Reflection**: Disabled in production mode
- **Resource Limits**: CPU and memory limits enforced

### Security Best Practices
```bash
# Run with security options
docker run -d \
  --name aifs-server \
  --read-only \
  --tmpfs /tmp \
  --tmpfs /data/aifs \
  --user aifs \
  --cap-drop ALL \
  --no-new-privileges \
  aifs:latest
```

## 🔄 Updates and Maintenance

### Updating the Container
```bash
# Pull latest image
docker pull aifs:latest

# Stop and remove old container
docker stop aifs-server
docker rm aifs-server

# Run new container
./docker-run.sh
```

### Backup and Restore
```bash
# Backup data volume
docker run --rm -v aifs-data:/data -v $(pwd):/backup alpine tar czf /backup/aifs-backup.tar.gz -C /data .

# Restore data volume
docker run --rm -v aifs-data:/data -v $(pwd):/backup alpine tar xzf /backup/aifs-backup.tar.gz -C /data
```

### Cleanup
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a
```

## 🐛 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker logs aifs-server

# Check container status
docker ps -a

# Check resource usage
docker stats aifs-server
```

#### Permission Issues
```bash
# Fix data directory permissions
sudo chown -R 1000:1000 ./aifs-data

# Check container user
docker exec aifs-server id
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep 50051

# Use different port
./docker-run.sh --port 8080
```

#### Database Issues
```bash
# Check database file
docker exec aifs-server ls -la /data/aifs/

# Reset database (WARNING: Data loss)
docker exec aifs-server rm -f /data/aifs/metadata.db
```

### Debug Mode
```bash
# Run with debug logging
docker run -e AIFS_LOG_LEVEL=DEBUG aifs:latest

# Interactive debugging
docker run -it --entrypoint /bin/bash aifs:latest
```

## 📈 Performance Tuning

### Resource Limits
```yaml
# docker-compose.yml
services:
  aifs-server:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

### Storage Optimization
```bash
# Use SSD storage for better performance
docker run -v /ssd/aifs-data:/data/aifs aifs:latest

# Enable compression
docker run -e AIFS_COMPRESSION=true aifs:latest
```

## 🌐 Network Configuration

### Custom Networks
```bash
# Create custom network
docker network create aifs-network

# Run with custom network
docker run --network aifs-network aifs:latest
```

### Load Balancing
```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - aifs-server
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [AIFS API Documentation](../api/API.md)
- [AIFS Architecture](../../README.md)

## 🤝 Support

For issues and questions:
- Check the troubleshooting section above
- Review container logs
- Open an issue on GitHub
- Check the AIFS documentation
