#!/usr/bin/env python3
"""Start AIFS server.

This script starts the AIFS server and demonstrates its usage.
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path

from aifs.server import serve


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Start AIFS server")
    parser.add_argument(
        "--host", type=str, default="localhost",
        help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=50051,
        help="Server port (default: 50051)"
    )
    parser.add_argument(
        "--storage-dir", type=str, default="./aifs_data",
        help="Storage directory (default: ./aifs_data)"
    )
    parser.add_argument(
        "--dev", action="store_true",
        help="Enable development mode (gRPC reflection, debug features)"
    )
    return parser.parse_args()


def main():
    """Start AIFS server."""
    # Parse arguments
    args = parse_args()
    
    # Create storage directory if it doesn't exist
    storage_dir = Path(args.storage_dir).absolute()
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Print server info
    mode = "development" if args.dev else "production"
    print(f"Starting AIFS server on {args.host}:{args.port} ({mode} mode)")
    print(f"Storage directory: {storage_dir}")
    print("Press Ctrl+C to stop")
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\nStopping AIFS server...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start server
    serve(root_dir=storage_dir, port=args.port, max_workers=10, dev_mode=args.dev)


if __name__ == "__main__":
    main()