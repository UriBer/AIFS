# Dockerfile for AIFS local implementation

FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Compile protobuf definitions
RUN python compile_proto.py

# Install package
RUN pip install -e .

# Create data directory
RUN mkdir -p /data/aifs

# Expose gRPC port
EXPOSE 50051

# Set volume for persistent storage
VOLUME ["/data/aifs"]

# Run server
CMD ["python", "start_server.py", "--host", "0.0.0.0", "--storage-dir", "/data/aifs"]