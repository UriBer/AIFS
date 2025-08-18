# AIFS Local Implementation

This directory contains a local implementation of the AI-Native File System (AIFS) for MacOS. This implementation demonstrates the core concepts of AIFS including content addressing, vector-first metadata, versioned snapshots, and lineage tracking.

## Architecture

The local implementation follows a simplified version of the architecture described in the RFC:

```
+---------------------------+
|  Python Client API         |
+---------------------------+
|  Local gRPC Server         |
+---------------------------+
|  Vector DB (FAISS/HNSW)    |
+---------------------------+
|  Local Storage Backend     |
+---------------------------+
|  Optional FUSE Mount       |
+---------------------------+
```

## Components

1. **Storage Backend**: Uses local filesystem with content-addressed storage
2. **Vector Database**: Uses FAISS for vector similarity search
3. **Metadata Store**: Uses SQLite for metadata and lineage tracking
4. **gRPC Server**: Implements the AIFS protocol
5. **FUSE Layer**: Optional POSIX-compatible view

## Getting Started

### Prerequisites

- Python 3.9+
- Rust (for FUSE implementation)
- macFUSE (for POSIX compatibility)

### Installation

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install macFUSE (if needed for POSIX compatibility)
brew install --cask macfuse
```

### Running the Server

```bash
python -m aifs.server
```

### Mounting AIFS as a Filesystem

```bash
python -m aifs.fuse /aifs
```

## Usage Examples

```python
from aifs.client import AIFSClient

# Connect to local AIFS server
client = AIFSClient("localhost:50051")

# Store an asset
asset_id = client.put_asset(b"Hello, AIFS!")
print(f"Stored asset with ID: {asset_id}")

# Retrieve an asset
asset = client.get_asset(asset_id)
print(f"Retrieved asset: {asset.data}")

# Vector search
results = client.vector_search("hello world", k=5)
for result in results:
    print(f"Asset ID: {result.asset_id}, Score: {result.score}")

# Create a snapshot
snapshot_id = client.create_snapshot("default")
print(f"Created snapshot: {snapshot_id}")
```

## Implementation Notes

- This implementation focuses on functionality over performance
- Security features (encryption, authentication) are simplified for local use
- The implementation is modular to allow easy replacement of components

## Roadmap

1. Basic content-addressed storage with sha256 hashing
2. Vector embedding and search using FAISS
3. Snapshot functionality with Merkle trees
4. Lineage tracking for assets
5. FUSE layer for POSIX compatibility
6. Performance optimizations