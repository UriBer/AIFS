# Dockerfile for AIFS production deployment
FROM python:3.11-slim

# Install system dependencies including Rust for blake3
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    libopenblas-dev \
    libomp-dev \
    libopenblas0 \
    libomp5 \
    curl \
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

# Copy source code
COPY . .

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

# Run server
CMD ["python", "start_server.py", "--storage-dir", "/data/aifs", "--port", "50051"]