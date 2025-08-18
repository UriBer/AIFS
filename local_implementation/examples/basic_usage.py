#!/usr/bin/env python3
"""Basic usage example for AIFS client API.

This script demonstrates how to use the AIFS client API for common operations.
"""

import os
import numpy as np
from aifs.client import AIFSClient


def main():
    """Run basic AIFS operations."""
    # Connect to AIFS server
    client = AIFSClient("localhost:50051")
    print("Connected to AIFS server")
    
    # Store a simple text asset
    text_data = b"Hello, AIFS! This is a test asset."
    text_metadata = {"content_type": "text/plain", "description": "Test text asset"}
    text_asset_id = client.put_asset(text_data, kind="blob", metadata=text_metadata)
    print(f"Stored text asset with ID: {text_asset_id}")
    
    # Store an image asset with embedding
    # In a real application, you'd load an actual image and compute a proper embedding
    image_data = os.urandom(1024)  # Simulated image data
    image_embedding = np.random.rand(1536).astype(np.float32)  # Simulated embedding
    image_metadata = {"content_type": "image/jpeg", "description": "Test image asset"}
    image_asset_id = client.put_asset(
        image_data, 
        kind="blob", 
        embedding=image_embedding, 
        metadata=image_metadata
    )
    print(f"Stored image asset with ID: {image_asset_id}")
    
    # Store a derived asset with lineage
    derived_data = b"This is derived from the text asset."
    derived_metadata = {"content_type": "text/plain", "description": "Derived asset"}
    parents = [{
        "asset_id": text_asset_id,
        "transform_name": "text_processor",
        "transform_digest": "sha256:1234567890abcdef"
    }]
    derived_asset_id = client.put_asset(
        derived_data,
        kind="blob",
        metadata=derived_metadata,
        parents=parents
    )
    print(f"Stored derived asset with ID: {derived_asset_id}")
    
    # Retrieve an asset
    asset = client.get_asset(text_asset_id)
    print(f"\nRetrieved asset: {text_asset_id}")
    print(f"Kind: {asset['kind']}")
    print(f"Size: {asset['size']} bytes")
    print(f"Created at: {asset['created_at']}")
    print(f"Metadata: {asset['metadata']}")
    print(f"Data: {asset['data'].decode()}")
    
    # Vector search
    # In a real application, you'd compute a proper query embedding
    query_embedding = np.random.rand(1536).astype(np.float32)  # Simulated query
    results = client.vector_search(query_embedding, k=5)
    print(f"\nVector search results:")
    for i, result in enumerate(results):
        print(f"Result {i+1}: Asset ID: {result['asset_id']}, Score: {result['score']}")
    
    # Create a snapshot
    asset_ids = [text_asset_id, image_asset_id, derived_asset_id]
    snapshot = client.create_snapshot("default", asset_ids, {"description": "Test snapshot"})
    print(f"\nCreated snapshot: {snapshot['snapshot_id']}")
    print(f"Merkle root: {snapshot['merkle_root']}")
    
    # Retrieve a snapshot
    snapshot_info = client.get_snapshot(snapshot['snapshot_id'])
    print(f"\nRetrieved snapshot: {snapshot_info['snapshot_id']}")
    print(f"Namespace: {snapshot_info['namespace']}")
    print(f"Created at: {snapshot_info['created_at']}")
    print(f"Metadata: {snapshot_info['metadata']}")
    print(f"Assets: {len(snapshot_info['asset_ids'])}")
    
    # Close client
    client.close()
    print("\nClosed AIFS client")


if __name__ == "__main__":
    main()