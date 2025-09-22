#!/usr/bin/env python3
"""
AIFS Python Client Example

This script demonstrates how to use the AIFS Python client to interact with
the AIFS server running in a Docker container.

Prerequisites:
- AIFS server running in Docker (see quick-start.sh)
- Python 3.9+ with grpcio and protobuf installed
"""

import sys
import json
import time
from typing import List, Dict, Any

try:
    from aifs.client import AIFSClient
except ImportError:
    print("❌ AIFS client not found. Please install the AIFS package:")
    print("   pip install -e .")
    sys.exit(1)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_asset(asset: Dict[str, Any], index: int = None):
    """Print asset information in a formatted way."""
    prefix = f"{index}. " if index is not None else ""
    print(f"{prefix}Asset ID: {asset['asset_id']}")
    print(f"   Kind: {asset['kind']}")
    print(f"   Size: {asset['size']} bytes")
    print(f"   Metadata: {json.dumps(asset['metadata'], indent=6)}")
    if 'uri' in asset:
        print(f"   URI: {asset['uri']}")


def main():
    """Main demonstration function."""
    print("🚀 AIFS Python Client Example")
    print("This example demonstrates the AIFS Python client API")
    
    # Configuration
    server_host = "localhost"
    server_port = 50051
    server_address = f"{server_host}:{server_port}"
    
    print(f"\n📡 Connecting to AIFS server at {server_address}")
    
    try:
        # Initialize the client
        client = AIFSClient(server_address)
        print("✅ Connected to AIFS server")
    except Exception as e:
        print(f"❌ Failed to connect to AIFS server: {e}")
        print("\nMake sure the AIFS server is running:")
        print("   docker run -d --name aifs-server -p 50051:50051 uriber/aifs:latest")
        sys.exit(1)
    
    # Test 1: Health Check
    print_section("Health Check")
    try:
        # Note: Health check is typically done via gRPC directly
        # For this example, we'll just try to list assets as a health check
        assets = client.list_assets()
        print("✅ AIFS server is healthy and responding")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)
    
    # Test 2: Store Assets
    print_section("Storing Sample Assets")
    
    sample_assets = [
        {
            "data": b"Welcome to AIFS! This is a sample document for demonstration purposes.",
            "kind": "blob",
            "metadata": {
                "title": "Welcome to AIFS",
                "description": "A sample document for the Python client example",
                "author": "AIFS Demo",
                "type": "text/plain",
                "tags": ["demo", "welcome", "sample"]
            }
        },
        {
            "data": b"This document contains information about artificial intelligence and machine learning technologies.",
            "kind": "blob",
            "metadata": {
                "title": "AI and ML Overview",
                "description": "An overview of artificial intelligence and machine learning",
                "author": "AIFS Demo",
                "type": "text/plain",
                "tags": ["ai", "machine learning", "technology"],
                "category": "technical"
            }
        },
        {
            "data": b"Data science is an interdisciplinary field that uses scientific methods, processes, algorithms and systems to extract knowledge and insights from data.",
            "kind": "blob",
            "metadata": {
                "title": "Data Science Introduction",
                "description": "Introduction to data science concepts and practices",
                "author": "AIFS Demo",
                "type": "text/plain",
                "tags": ["data science", "analytics", "statistics"],
                "category": "educational"
            }
        }
    ]
    
    stored_assets = []
    for i, asset_data in enumerate(sample_assets, 1):
        try:
            print(f"Storing asset {i}...")
            asset_id = client.put_asset(
                data=asset_data["data"],
                kind=asset_data["kind"],
                metadata=asset_data["metadata"]
            )
            stored_assets.append(asset_id)
            print(f"✅ Stored asset {i} with ID: {asset_id}")
        except Exception as e:
            print(f"❌ Failed to store asset {i}: {e}")
    
    print(f"\n📊 Successfully stored {len(stored_assets)} assets")
    
    # Test 3: List Assets
    print_section("Listing All Assets")
    
    try:
        assets = client.list_assets()
        print(f"Found {len(assets)} total assets in the system:")
        
        for i, asset in enumerate(assets, 1):
            print_asset(asset, i)
            
    except Exception as e:
        print(f"❌ Failed to list assets: {e}")
    
    # Test 4: Retrieve Specific Assets
    print_section("Retrieving Specific Assets")
    
    for i, asset_id in enumerate(stored_assets, 1):
        try:
            print(f"Retrieving asset {i} (ID: {asset_id})...")
            asset = client.get_asset(asset_id)
            print(f"✅ Retrieved asset {i}:")
            print(f"   Data: {asset['data'].decode('utf-8')}")
            print(f"   Metadata: {json.dumps(asset['metadata'], indent=6)}")
            if 'uri' in asset:
                print(f"   URI: {asset['uri']}")
        except Exception as e:
            print(f"❌ Failed to retrieve asset {i}: {e}")
    
    # Test 5: Search Assets (if vector search is available)
    print_section("Vector Search (if available)")
    
    try:
        # Generate a simple query embedding (this is a placeholder)
        # In a real implementation, you would use a proper embedding model
        query_text = "artificial intelligence machine learning"
        print(f"Searching for: '{query_text}'")
        
        # Note: This is a placeholder. In the real implementation,
        # you would generate proper embeddings for the query
        print("ℹ️  Vector search requires proper embedding generation")
        print("   This would typically involve:")
        print("   1. Generating embeddings for stored assets")
        print("   2. Creating a query embedding")
        print("   3. Performing similarity search")
        print("   4. Returning ranked results")
        
    except Exception as e:
        print(f"ℹ️  Vector search not available: {e}")
    
    # Test 6: Create a Snapshot
    print_section("Creating a Snapshot")
    
    try:
        if stored_assets:
            print(f"Creating snapshot with {len(stored_assets)} assets...")
            snapshot = client.create_snapshot(
                namespace="demo",
                asset_ids=stored_assets,
                metadata={
                    "description": "Demo snapshot with sample assets",
                    "created_by": "python_client_example",
                    "version": "1.0"
                }
            )
            print(f"✅ Created snapshot: {snapshot['snapshot_id']}")
            print(f"   Merkle root: {snapshot['merkle_root']}")
            print(f"   Asset count: {len(snapshot['asset_ids'])}")
        else:
            print("ℹ️  No assets available for snapshot creation")
    except Exception as e:
        print(f"❌ Failed to create snapshot: {e}")
    
    # Test 7: System Information
    print_section("System Information")
    
    try:
        assets = client.list_assets()
        total_size = sum(asset['size'] for asset in assets)
        
        print(f"📊 AIFS System Status:")
        print(f"   Total assets: {len(assets)}")
        print(f"   Total size: {total_size:,} bytes ({total_size/1024:.2f} KB)")
        print(f"   Server: {server_address}")
        print(f"   Client: Python {sys.version.split()[0]}")
        
    except Exception as e:
        print(f"❌ Failed to get system information: {e}")
    
    # Summary
    print_section("Example Complete")
    print("🎉 AIFS Python client example completed successfully!")
    print("\n📚 What you learned:")
    print("   ✅ How to connect to an AIFS server")
    print("   ✅ How to store assets with metadata")
    print("   ✅ How to list and retrieve assets")
    print("   ✅ How to create snapshots")
    print("   ✅ How to handle errors gracefully")
    
    print("\n🔗 Next steps:")
    print("   📖 Read the full API documentation")
    print("   🧪 Try the vector search features")
    print("   🔧 Explore the gRPC API directly")
    print("   🐳 Deploy AIFS in your own environment")
    
    print(f"\n🛑 To stop the AIFS server:")
    print(f"   docker stop aifs-server")


if __name__ == "__main__":
    main()
