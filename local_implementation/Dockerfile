# Dockerfile for AIFS production deployment
FROM python:3.12-slim

# Add comprehensive labels for Docker Hub
LABEL maintainer="urib@even-derech-it.com"
LABEL org.opencontainers.image.title="AIFS - AI-Native File System"
LABEL org.opencontainers.image.description="A production-ready AI-Native File System with content addressing, vector search, and versioned snapshots. Perfect for AI/ML workloads requiring semantic search and data lineage tracking."
LABEL org.opencontainers.image.url="https://github.com/UriBer/aifs"
LABEL org.opencontainers.image.source="https://github.com/UriBer/aifs"
LABEL org.opencontainers.image.vendor="AIFS Team"
LABEL org.opencontainers.image.version="0.1.0-alpha"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.documentation="https://github.com/UriBer/aifs/blob/main/local_implementation/dockerhub/README.md"
LABEL org.opencontainers.image.keywords="ai,ml,machine-learning,file-system,content-addressing,vector-search,semantic-search,grpc,blake3,merkle-tree,versioning,data-lineage"
LABEL org.opencontainers.image.categories="ai,ml,storage,database,search,development"
LABEL ai.native.file-system.version="0.1.0-alpha"
LABEL ai.native.file-system.features="content-addressing,vector-search,versioned-snapshots,merkle-trees,grpc-api,blake3-hashing"
LABEL ai.native.file-system.architecture="microservices,content-addressed-storage,vector-database"

# Install system dependencies including Rust for blake3
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    libopenblas-dev \
    libomp-dev \
    libopenblas0 \
    libomp5 \
    curl \
    && apt-get install -y --only-upgrade libexpat1 expat \
    && apt-get dist-upgrade -y \
    && apt-get autoremove -y \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Rust for blake3 compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create non-root user for security
RUN groupadd -r aifs && useradd -r -g aifs aifs

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (includes docker-entrypoint.sh)
COPY . .

# Setup entrypoint script
RUN chmod +x /app/docker-entrypoint.sh

# Compile protobuf definitions
RUN python compile_proto.py

# Install AIFS package
RUN pip install -e .

# Create data directory with proper permissions
RUN mkdir -p /data/aifs && \
    chown -R aifs:aifs /data/aifs && \
    chown -R aifs:aifs /app

# Switch to non-root user
USER aifs

# Create health check script
RUN echo '#!/bin/bash\n\
python -c "import grpc; from aifs.proto import aifs_pb2, aifs_pb2_grpc; channel = grpc.insecure_channel(\"localhost:50051\"); stub = aifs_pb2_grpc.HealthStub(channel); stub.Check(aifs_pb2.HealthCheckRequest())"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Expose gRPC port
EXPOSE 50051

# Set volume for persistent storage
VOLUME ["/data/aifs"]

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV AIFS_DATA_DIR=/data/aifs
ENV AIFS_PORT=50051
ENV AIFS_HOST=0.0.0.0
ENV AIFS_MODE=production
ENV AIFS_STORAGE_DIR=/data/aifs
ENV AIFS_MAX_WORKERS=10
ENV AIFS_COMPRESSION_LEVEL=1

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]