# AIFS Docker Hub Publishing Makefile
# This Makefile provides convenient commands for building, testing, and publishing AIFS Docker images

.PHONY: help build test publish clean dev prod

# Configuration
DOCKERHUB_USERNAME = uriber
IMAGE_NAME = aifs
VERSION ?= latest
PLATFORMS = linux/amd64,linux/arm64

# Colors
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

help: ## Show this help message
	@echo "AIFS Docker Hub Publishing Commands"
	@echo ""
	@echo "Usage: make [target] [VERSION=version]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make build                    # Build latest image"
	@echo "  make build VERSION=v0.1.0     # Build specific version"
	@echo "  make test                     # Test the latest image"
	@echo "  make publish VERSION=v0.1.0   # Publish specific version"
	@echo "  make dev                      # Build and test development image"
	@echo "  make prod                     # Build and test production image"

build: ## Build the Docker image
	@echo "$(BLUE)🔨 Building AIFS Docker image...$(NC)"
	@cd .. && docker build -t $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):$(VERSION) .
	@echo "$(GREEN)✅ Image built: $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):$(VERSION)$(NC)"

build-multi: ## Build multi-platform Docker image
	@echo "$(BLUE)🔨 Building multi-platform AIFS Docker image...$(NC)"
	@cd .. && docker buildx build --platform $(PLATFORMS) -t $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):$(VERSION) .
	@echo "$(GREEN)✅ Multi-platform image built: $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):$(VERSION)$(NC)"

test: ## Test the Docker image
	@echo "$(BLUE)🧪 Testing AIFS Docker image...$(NC)"
	@./test.sh $(VERSION)
	@echo "$(GREEN)✅ Tests completed successfully$(NC)"

publish: ## Publish the Docker image to Docker Hub
	@echo "$(BLUE)📤 Publishing AIFS Docker image to Docker Hub...$(NC)"
	@./publish.sh $(VERSION)
	@echo "$(GREEN)✅ Image published successfully$(NC)"

dev: ## Build and test development image
	@echo "$(BLUE)🔧 Building and testing development image...$(NC)"
	@$(MAKE) build VERSION=dev
	@$(MAKE) test VERSION=dev
	@echo "$(GREEN)✅ Development image ready$(NC)"

prod: ## Build and test production image
	@echo "$(BLUE)🏭 Building and testing production image...$(NC)"
	@$(MAKE) build VERSION=$(VERSION)
	@$(MAKE) test VERSION=$(VERSION)
	@echo "$(GREEN)✅ Production image ready$(NC)"

clean: ## Clean up Docker resources
	@echo "$(YELLOW)🧹 Cleaning up Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-images: ## Remove AIFS Docker images
	@echo "$(YELLOW)🗑️  Removing AIFS Docker images...$(NC)"
	@docker rmi $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):latest 2>/dev/null || true
	@docker rmi $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):dev 2>/dev/null || true
	@docker rmi $(DOCKERHUB_USERNAME)/$(IMAGE_NAME):$(VERSION) 2>/dev/null || true
	@echo "$(GREEN)✅ Images removed$(NC)"

clean-containers: ## Remove AIFS containers
	@echo "$(YELLOW)🗑️  Removing AIFS containers...$(NC)"
	@docker stop aifs-server aifs-dev aifs-test 2>/dev/null || true
	@docker rm aifs-server aifs-dev aifs-test 2>/dev/null || true
	@echo "$(GREEN)✅ Containers removed$(NC)"

clean-volumes: ## Remove AIFS volumes
	@echo "$(YELLOW)🗑️  Removing AIFS volumes...$(NC)"
	@docker volume rm aifs-data aifs-dev-data aifs-test-data 2>/dev/null || true
	@echo "$(GREEN)✅ Volumes removed$(NC)"

status: ## Show Docker status
	@echo "$(BLUE)📊 Docker Status$(NC)"
	@echo ""
	@echo "Images:"
	@docker images | grep $(IMAGE_NAME) || echo "No AIFS images found"
	@echo ""
	@echo "Containers:"
	@docker ps -a | grep aifs || echo "No AIFS containers found"
	@echo ""
	@echo "Volumes:"
	@docker volume ls | grep aifs || echo "No AIFS volumes found"

logs: ## Show logs for running containers
	@echo "$(BLUE)📋 AIFS Container Logs$(NC)"
	@docker logs aifs-server 2>/dev/null || echo "No aifs-server container found"
	@docker logs aifs-dev 2>/dev/null || echo "No aifs-dev container found"

quick-start: ## Run quick start demo
	@echo "$(BLUE)🚀 Running AIFS Quick Start Demo$(NC)"
	@./examples/quick-start.sh

grpc-explore: ## Explore gRPC API
	@echo "$(BLUE)🔍 Exploring AIFS gRPC API$(NC)"
	@./examples/grpc-exploration.sh

python-example: ## Run Python client example
	@echo "$(BLUE)🐍 Running Python Client Example$(NC)"
	@./examples/python-client-example.py

# Docker Compose targets
compose-up: ## Start with Docker Compose (production)
	@echo "$(BLUE)🐳 Starting AIFS with Docker Compose (production)$(NC)"
	@docker-compose -f docker-compose.production.yml up -d
	@echo "$(GREEN)✅ AIFS started in production mode$(NC)"

compose-up-dev: ## Start with Docker Compose (development)
	@echo "$(BLUE)🐳 Starting AIFS with Docker Compose (development)$(NC)"
	@docker-compose -f docker-compose.development.yml up -d
	@echo "$(GREEN)✅ AIFS started in development mode$(NC)"

compose-down: ## Stop Docker Compose services
	@echo "$(YELLOW)🛑 Stopping AIFS Docker Compose services$(NC)"
	@docker-compose -f docker-compose.production.yml down 2>/dev/null || true
	@docker-compose -f docker-compose.development.yml down 2>/dev/null || true
	@echo "$(GREEN)✅ Services stopped$(NC)"

compose-logs: ## Show Docker Compose logs
	@echo "$(BLUE)📋 Docker Compose Logs$(NC)"
	@docker-compose -f docker-compose.production.yml logs 2>/dev/null || true
	@docker-compose -f docker-compose.development.yml logs 2>/dev/null || true

# Full workflow targets
all: clean build test ## Clean, build, and test
	@echo "$(GREEN)🎉 Full workflow completed successfully$(NC)"

release: clean build test publish ## Full release workflow
	@echo "$(GREEN)🎉 Release completed successfully$(NC)"

# Default target
.DEFAULT_GOAL := help
