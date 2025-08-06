# Makefile for AIFS local implementation

.PHONY: all install dev clean test proto server client mount

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