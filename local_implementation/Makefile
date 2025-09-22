# Makefile for AIFS local implementation

.PHONY: all install dev clean test proto server client mount docker-build docker-run docker-stop docker-logs docker-clean

# Default target
all: install

# Install package
install:
	pip install -e .

# Install package with development dependencies
dev:
	pip install -e ".[dev,fuse]"

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/ __pycache__/ aifs/__pycache__/ tests/__pycache__/
	rm -rf aifs/proto/*_pb2.py aifs/proto/*_pb2_grpc.py

# Run tests
test:
	python -m pytest tests/

# Compile protobuf definitions
proto:
	python compile_proto.py

# Start server
server:
	python start_server.py

# Run example client
client:
	python examples/basic_usage.py

# Mount FUSE filesystem
mount:
	mkdir -p aifs_mount
	python -c "from aifs_cli import mount_fuse; mount_fuse('aifs_mount', foreground=True)"

# Docker targets
docker-build:
	@echo "🐳 Building AIFS Docker image..."
	./docker-build.sh

docker-build-dev:
	@echo "🐳 Building AIFS Docker image for development..."
	./docker-build.sh --tag aifs --version dev

docker-run:
	@echo "🚀 Running AIFS Docker container..."
	./docker-run.sh

docker-run-dev:
	@echo "🚀 Running AIFS Docker container in development mode..."
	./docker-run.sh --dev

docker-stop:
	@echo "🛑 Stopping AIFS Docker containers..."
	docker stop aifs-server aifs-dev 2>/dev/null || true
	docker rm aifs-server aifs-dev 2>/dev/null || true

docker-logs:
	@echo "📋 Showing AIFS Docker logs..."
	docker logs -f aifs-server

docker-logs-dev:
	@echo "📋 Showing AIFS development Docker logs..."
	docker logs -f aifs-dev

docker-compose-up:
	@echo "🚀 Starting AIFS with Docker Compose..."
	docker-compose up -d

docker-compose-down:
	@echo "🛑 Stopping AIFS with Docker Compose..."
	docker-compose down

docker-compose-dev:
	@echo "🚀 Starting AIFS development with Docker Compose..."
	docker-compose --profile dev up -d

docker-clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Production deployment
docker-prod: docker-build docker-compose-up
	@echo "✅ AIFS production deployment complete!"

# Development deployment
docker-dev: docker-build-dev docker-compose-dev
	@echo "✅ AIFS development deployment complete!"

# Help
help:
	@echo "AIFS Makefile Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install          Install AIFS package"
	@echo "  dev              Install with development dependencies"
	@echo "  test             Run test suite"
	@echo "  proto            Compile protobuf definitions"
	@echo "  server           Start local server"
	@echo "  client           Run example client"
	@echo "  mount            Mount FUSE filesystem"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-build-dev Build development Docker image"
	@echo "  docker-run       Run Docker container (production)"
	@echo "  docker-run-dev   Run Docker container (development)"
	@echo "  docker-stop      Stop Docker containers"
	@echo "  docker-logs      Show container logs"
	@echo "  docker-logs-dev  Show development container logs"
	@echo "  docker-clean     Clean up Docker resources"
	@echo ""
	@echo "Docker Compose:"
	@echo "  docker-compose-up    Start with Docker Compose"
	@echo "  docker-compose-down  Stop Docker Compose services"
	@echo "  docker-compose-dev   Start development with Docker Compose"
	@echo ""
	@echo "Deployment:"
	@echo "  docker-prod      Full production deployment"
	@echo "  docker-dev       Full development deployment"