# AIFS CLI Usage Guide

The AIFS CLI provides a convenient command-line interface for interacting with the AIFS system without needing to type `python` commands.

## Installation

After installing the AIFS package in development mode, the `aifs` command becomes available globally:

```bash
# Install in development mode
pip install -e .

# Verify installation
aifs --help
```

## Available Commands

### Server Management

```bash
# Start AIFS server
aifs server

# Start server with custom settings
aifs server --host 0.0.0.0 --port 50052 --storage-dir /path/to/storage

# Start server in development mode (with gRPC reflection)
python start_server.py --dev
```

### Asset Operations

```bash
# Store an asset
aifs put /path/to/file.txt

# Store with metadata and embedding
aifs put /path/to/file.txt --description "My document" --with-embedding

# Store with custom kind and content type
aifs put /path/to/file.txt --kind model --content-type "application/octet-stream"

# Store with parent assets (lineage)
aifs put /path/to/file.txt --parent-ids "hash1" "hash2" --transform-name "preprocessing"

# Store with metadata from JSON file
aifs put /path/to/file.txt --metadata-file metadata.json
```

### Asset Retrieval

```bash
# Get asset by ID
aifs get <asset-id>

# Get asset and save to file
aifs get <asset-id> --output-file /path/to/output.txt

# Get only metadata (no content)
aifs get <asset-id> --metadata-only
```

### Vector Search

```bash
# Search using a file as query
aifs search /path/to/query.txt

# Search with custom parameters
aifs search /path/to/query.txt --k 10 --threshold 0.7

# Store asset with embedding for search
aifs put-with-embedding /path/to/file.txt --description "Searchable document"
```

### Snapshots

```bash
# Create snapshot
aifs snapshot "asset1" "asset2" "asset3" --description "My snapshot"

# Create snapshot with metadata
aifs snapshot "asset1" "asset2" --metadata-file snapshot_metadata.json

# Get snapshot
aifs get-snapshot <snapshot-id>
```

### FUSE Mount (Optional)

```bash
# Mount AIFS as filesystem
aifs mount /path/to/mount/point

# Mount with custom settings
aifs mount /path/to/mount/point --server localhost:50052 --namespace my-namespace
```

## Examples

### Basic Workflow

```bash
# 1. Start server
aifs server &

# 2. Store some files
aifs put-with-embedding document1.txt --description "Machine learning tutorial"
aifs put-with-embedding document2.txt --description "Python programming guide"

# 3. Search for similar content
aifs search query.txt

# 4. Create a snapshot
aifs snapshot <asset-id-1> <asset-id-2> --description "ML documentation set"
```

### Advanced Usage

```bash
# Store with complex metadata
cat > metadata.json << EOF
{
  "author": "John Doe",
  "version": "1.0",
  "tags": ["tutorial", "python", "ml"],
  "license": "MIT"
}
EOF

aifs put document.txt --metadata-file metadata.json --with-embedding

# Search with high precision
aifs search query.txt --k 5 --threshold 0.8

# Get asset and save with original filename
aifs get <asset-id> --output-file retrieved_document.txt
```

## Configuration

### Server Options

- `--host`: Server host (default: localhost)
- `--port`: Server port (default: 50051)
- `--storage-dir`: Storage directory (default: ./aifs_data)

### Client Options

- `--server`: Server address (default: localhost:50051)

### Global Options

- `--help`: Show help message
- `--install-completion`: Install shell completion
- `--show-completion`: Show completion script

## Tips

1. **Use `put-with-embedding`** for files you want to search later
2. **Add descriptions** to make search results more meaningful
3. **Use snapshots** to create versioned collections of assets
4. **Check server status** with `grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check`
5. **Enable gRPC reflection** in development mode for API exploration

## Troubleshooting

### Server Not Running
```bash
# Check if server is running
grpcurl -plaintext localhost:50051 grpc.health.v1.Health/Check

# Start server if needed
aifs server
```

### Permission Issues
```bash
# Make sure storage directory is writable
chmod 755 ./aifs_data

# Check file permissions
ls -la ./aifs_data
```

### Connection Issues
```bash
# Test connection
aifs get <some-asset-id>  # This will show connection error if server is down

# Check server logs
# Server logs are displayed in the terminal where you started it
```
