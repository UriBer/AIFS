# AIFS Examples

This directory contains example scripts demonstrating how to use the AIFS system.

## Quick Start

### Option 1: Run from local_implementation directory
```bash
cd local_implementation
python examples/basic_usage.py
```

### Option 2: Use the convenience script
```bash
cd local_implementation
python run_example.py
```

## Examples

### basic_usage.py
Demonstrates the core AIFS functionality:
- ✅ Connecting to the AIFS server
- ✅ Storing assets (text, binary, with embeddings)
- ✅ Asset lineage and metadata
- ✅ Vector similarity search
- ✅ Snapshot creation and retrieval
- ✅ Error handling and user feedback

## Prerequisites

1. **AIFS Server**: The server must be running
   ```bash
   python start_server.py
   ```

2. **Dependencies**: All required packages must be installed
   ```bash
   pip install -r requirements.txt
   ```

## Troubleshooting

### "ModuleNotFoundError: No module named 'aifs'"
- Make sure you're running from the `local_implementation` directory
- The script automatically adds the correct path, but the server must be running

### "Connection refused" or "Failed to connect"
- Make sure the AIFS server is running: `python start_server.py`
- Check that the server is listening on `localhost:50051`

### "Embedding dimension mismatch"
- The example now uses the correct 128-dimensional embeddings
- This should be automatically handled by the `embed_text()` function

## Customization

You can modify the examples to:
- Use different file types and data
- Test different embedding strategies
- Experiment with various metadata schemas
- Test different search queries and thresholds

## Next Steps

After running the basic example, try:
1. Using the CLI commands: `python aifs_cli.py --help`
2. Storing your own files: `python aifs_cli.py put-with-embedding <your_file>`
3. Performing vector searches: `python aifs_cli.py search <query_file>`
