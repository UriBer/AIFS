# AIFS Local Implementation

This directory contains a local implementation of the AI-Native File System (AIFS) for MacOS. This implementation demonstrates the core concepts of AIFS including content addressing, vector-first metadata, versioned snapshots, and lineage tracking.

## 🚀 **Status: Fully Operational**

The AIFS local implementation is now fully operational with:
- ✅ Content-addressed storage
- ✅ Vector similarity search with embeddings
- ✅ Metadata management and lineage tracking
- ✅ Snapshot creation and management
- ✅ CLI interface for all operations
- ✅ gRPC server for programmatic access

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
2. **Vector Database**: Uses FAISS for vector similarity search with 128-dimensional embeddings
3. **Metadata Store**: Uses SQLite for metadata and lineage tracking
4. **gRPC Server**: Implements the AIFS protocol
5. **FUSE Layer**: Optional POSIX-compatible view
6. **Embedding System**: Simple text-to-vector conversion for semantic search

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
# Start the AIFS server
python start_server.py

# Or use the CLI command
python aifs_cli.py server
```

### Mounting AIFS as a Filesystem

```bash
python -m aifs.fuse /aifs
```

## 🎯 **CLI Usage**

The AIFS CLI provides a comprehensive interface for all operations:

### Basic Asset Operations

```bash
# Store an asset
python aifs_cli.py put <file> [--kind blob] [--description "Description"]

# Store an asset with automatic embedding for vector search
python aifs_cli.py put <file> --with-embedding --description "Description"

# Store an asset with embedding (dedicated command)
python aifs_cli.py put-with-embedding <file> --description "Description"

# Retrieve an asset
python aifs_cli.py get <asset_id> [--output-file <path>] [--metadata-only]

# List assets (if implemented)
python aifs_cli.py list
```

### 🔍 **Vector Search Operations**

```bash
# Search for similar assets using a query file
python aifs_cli.py search <query_file> [--k 5] [--threshold 0.0]

# Examples:
python aifs_cli.py search documents/python_tutorial.txt
python aifs_cli.py search queries/ml_query.txt --k 10 --threshold 1.5
```

### Snapshot Operations

```bash
# Create a snapshot
python aifs_cli.py snapshot <asset_id1> <asset_id2> [--namespace default] [--description "Description"]

# Retrieve snapshot information
python aifs_cli.py get-snapshot <snapshot_id>
```

### Server Management

```bash
# Start server
python aifs_cli.py server [--host localhost] [--port 50051]

# Mount as filesystem
python aifs_cli.py mount <mount_point> [--server localhost:50051]
```

## 📚 **Usage Examples**

### Python API

```python
from aifs.client import AIFSClient

# Connect to local AIFS server
client = AIFSClient("localhost:50051")

# Store an asset with embedding
asset_id = client.put_asset(
    data=b"Hello, AIFS!",
    kind="blob",
    embedding=embedding_vector,  # 128-dimensional numpy array
    metadata={"description": "Sample text"}
)

# Retrieve an asset
asset = client.get_asset(asset_id)
print(f"Retrieved asset: {asset['data']}")

# Vector search
query_embedding = generate_embedding("search query")
results = client.vector_search(query_embedding, k=5)
for result in results:
    print(f"Asset ID: {result['asset_id']}, Score: {result['score']}")

# Create a snapshot
snapshot = client.create_snapshot("default", [asset_id], {"description": "Test snapshot"})
print(f"Created snapshot: {snapshot['snapshot_id']}")
```

### Embedding System

```python
from aifs.embedding import embed_file, embed_text

# Generate embeddings for files
file_embedding = embed_file("document.txt")  # 128-dimensional vector
text_embedding = embed_text("sample text")   # 128-dimensional vector

# Use in vector search
results = client.vector_search(file_embedding, k=5)
```

## 🔧 **Vector Search Features**

- **Automatic Embedding Generation**: Text files are automatically converted to 128-dimensional vectors
- **Semantic Similarity**: Find assets based on content similarity, not just exact matches
- **Configurable Results**: Set number of results (k) and similarity threshold
- **Rich Metadata**: Search results include asset kind, size, description, and similarity scores
- **File-based Queries**: Use any text file as a search query

## 📁 **File Structure**

```
local_implementation/
├── aifs/                    # Core AIFS implementation
│   ├── asset.py            # Asset management
│   ├── storage.py          # Storage backend
│   ├── vector_db.py        # Vector database (FAISS)
│   ├── metadata.py         # Metadata store
│   ├── embedding.py        # Text embedding utilities
│   ├── server.py           # gRPC server
│   └── client.py           # gRPC client
├── aifs_cli.py             # Command-line interface
├── start_server.py         # Server startup script
├── test_files/             # Test files for vector search
├── examples/               # Usage examples
└── tests/                  # Test suite
```

## 🧪 **Testing**

Run the comprehensive test suite:

```bash
# Run all tests
python run_tests.py

# Run specific test modules
python -m pytest tests/test_asset_manager.py
python -m pytest tests/test_vector_db.py
```

## 🚀 **Quick Start Demo**

1. **Start the server:**
   ```bash
   python start_server.py
   ```

2. **Store some test files:**
   ```bash
   python aifs_cli.py put-with-embedding test_files/python_tutorial.txt --description "Python tutorial"
   python aifs_cli.py put-with-embedding test_files/machine_learning.txt --description "ML guide"
   ```

3. **Perform vector search:**
   ```bash
   python aifs_cli.py search test_files/query_python.txt
   ```

## Implementation Notes

- This implementation focuses on functionality over performance
- Security features (encryption, authentication) are simplified for local use
- The implementation is modular to allow easy replacement of components
- Vector search uses simple hash-based embeddings (can be replaced with language models)
- Default embedding dimension is 128 (configurable)

## 🔮 **Roadmap & Future Enhancements**

### Completed ✅
1. Basic content-addressed storage with SHA-256 hashing
2. Vector embedding and search using FAISS
3. Snapshot functionality with Merkle trees
4. Lineage tracking for assets
5. CLI interface for all operations
6. Vector search with automatic embedding generation

### Planned 🚧
1. FUSE layer for POSIX compatibility
2. Performance optimizations
3. Advanced embedding models (OpenAI, BERT, etc.)
4. Batch operations and bulk import
5. Web interface for asset management
6. Advanced filtering and querying

### Production Considerations
- Replace simple embeddings with proper language models
- Add authentication and access control
- Implement backup and replication
- Add monitoring and metrics
- Optimize for large-scale deployments

## 🤝 **Contributing**

This is a reference implementation. For production use, consider:
- Replacing the simple embedding system with proper language models
- Adding comprehensive error handling and logging
- Implementing proper security measures
- Adding performance monitoring and optimization

## 📄 **License**

See the main project LICENSE file for details.