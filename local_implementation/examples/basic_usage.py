#!/usr/bin/env python3
"""Basic usage example for AIFS client API.

This script demonstrates how to use the AIFS client API for common operations.
"""

import os
import sys
import numpy as np

# Add the parent directory to the Python path so we can import aifs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aifs.client import AIFSClient
from aifs.embedding import embed_text


def main():
    """Run basic AIFS operations."""
    try:
        # Connect to AIFS server
        print("Connecting to AIFS server...")
        client = AIFSClient("localhost:50051")
        print("✅ Connected to AIFS server")
        
        # Store a simple text asset
        print("\n📝 Storing text asset...")
        text_data = b"Hello, AIFS! This is a test asset."
        text_metadata = {"content_type": "text/plain", "description": "Test text asset"}
        text_asset_id = client.put_asset(text_data, kind="blob", metadata=text_metadata)
        print(f"✅ Stored text asset with ID: {text_asset_id[:12]}...")
        
        # Store an image asset with embedding
        print("\n🖼️  Storing image asset with embedding...")
        image_data = os.urandom(1024)  # Simulated image data
        # Generate a proper 128-dimensional embedding for the image data
        image_text = str(image_data[:100])  # Convert first 100 bytes to text for embedding
        image_embedding = embed_text(image_text)  # This will be 128-dimensional
        image_metadata = {"content_type": "image/jpeg", "description": "Test image asset"}
        image_asset_id = client.put_asset(
            image_data, 
            kind="blob", 
            embedding=image_embedding, 
            metadata=image_metadata
        )
        print(f"✅ Stored image asset with ID: {image_asset_id[:12]}...")
        
        # Store a derived asset with lineage
        print("\n🔗 Storing derived asset with lineage...")
        derived_data = b"This is derived from the text asset."
        derived_metadata = {"content_type": "text/plain", "description": "Derived asset"}
        parents = [{
            "asset_id": text_asset_id,
            "transform_name": "text_processor",
            "transform_digest": "blake3:1234567890abcdef"
        }]
        derived_asset_id = client.put_asset(
            derived_data,
            kind="blob",
            metadata=derived_metadata,
            parents=parents
        )
        print(f"✅ Stored derived asset with ID: {derived_asset_id[:12]}...")
        
        # Retrieve an asset
        print("\n📖 Retrieving asset...")
        asset = client.get_asset(text_asset_id)
        print(f"✅ Retrieved asset: {text_asset_id[:12]}...")
        print(f"   Kind: {asset['kind']}")
        print(f"   Size: {asset['size']} bytes")
        print(f"   Created at: {asset['created_at']}")
        print(f"   Metadata: {asset['metadata']}")
        print(f"   Data: {asset['data'].decode()}")
        
        # Vector search
        print("\n🔍 Performing vector search...")
        # Generate a proper 128-dimensional query embedding
        query_text = "test asset hello"
        query_embedding = embed_text(query_text)  # This will be 128-dimensional
        results = client.vector_search(query_embedding, k=5)
        print(f"✅ Vector search results ({len(results)} found):")
        for i, result in enumerate(results):
            print(f"   Result {i+1}: Asset ID: {result['asset_id'][:12]}..., Score: {result['score']:.4f}")
        
        # Create a snapshot
        print("\n📸 Creating snapshot...")
        asset_ids = [text_asset_id, image_asset_id, derived_asset_id]
        snapshot = client.create_snapshot("default", asset_ids, {"description": "Test snapshot"})
        print(f"✅ Created snapshot: {snapshot['snapshot_id'][:12]}...")
        print(f"   Merkle root: {snapshot['merkle_root']}")
        
        # Retrieve a snapshot
        print("\n📋 Retrieving snapshot...")
        snapshot_info = client.get_snapshot(snapshot['snapshot_id'])
        print(f"✅ Retrieved snapshot: {snapshot_info['snapshot_id'][:12]}...")
        print(f"   Namespace: {snapshot_info['namespace']}")
        print(f"   Created at: {snapshot_info['created_at']}")
        print(f"   Metadata: {snapshot_info['metadata']}")
        print(f"   Assets: {len(snapshot_info['asset_ids'])}")
        
        # Close client
        client.close()
        print("\n✅ Closed AIFS client")
        print("\n🎉 All operations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure the AIFS server is running:")
        print("   python start_server.py")
        print("\n   Or from the local_implementation directory:")
        print("   cd local_implementation && python start_server.py")
        sys.exit(1)


if __name__ == "__main__":
    main()