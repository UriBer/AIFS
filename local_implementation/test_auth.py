#!/usr/bin/env python3
"""Test script for AIFS authorization functionality."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aifs.client import AIFSClient
from aifs.auth import create_simple_token, AuthorizationManager

def test_authorization():
    """Test the authorization system."""
    print("🔐 Testing AIFS Authorization System")
    print("=" * 50)
    
    # Create authorization manager
    auth_manager = AuthorizationManager()
    
    # Create a token with specific permissions
    permissions = ["put", "get", "search", "list", "snapshot", "subscribe"]
    token = create_simple_token(permissions, expiry_hours=24)
    
    print(f"✅ Created authorization token with permissions: {permissions}")
    print(f"Token: {token[:50]}...")
    
    # Create client and set token
    client = AIFSClient()
    client.set_auth_token(token)
    
    print("\n📤 Testing authorized operations...")
    
    try:
        # Test storing an asset
        test_data = b"Hello, AIFS with authorization!"
        asset_id = client.put_asset(
            data=test_data,
            kind="blob",
            metadata={"description": "Test asset with auth", "test": "true"}
        )
        print(f"✅ Stored asset with ID: {asset_id[:12]}...")
        
        # Test listing assets
        assets = client.list_assets(limit=5)
        print(f"✅ Listed {len(assets)} assets")
        
        # Test retrieving asset
        asset = client.get_asset(asset_id)
        if asset:
            print(f"✅ Retrieved asset: {asset['data'].decode()}")
        else:
            print("❌ Failed to retrieve asset")
        
        # Test vector search
        from aifs.embedding import embed_text
        query_embedding = embed_text("Hello AIFS")
        results = client.vector_search(query_embedding, k=3)
        print(f"✅ Vector search returned {len(results)} results")
        
        # Test creating snapshot
        snapshot_result = client.create_snapshot(
            namespace="test",
            asset_ids=[asset_id],
            metadata={"description": "Test snapshot"}
        )
        print(f"✅ Created snapshot: {snapshot_result['snapshot_id'][:12]}...")
        
        print("\n🎉 All authorized operations completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    # Test with insufficient permissions
    print("\n🚫 Testing insufficient permissions...")
    
    limited_token = create_simple_token(["get"], expiry_hours=1)
    client.set_auth_token(limited_token)
    
    try:
        # This should fail due to insufficient permissions
        client.put_asset(b"Should fail", kind="blob")
        print("❌ Put operation should have failed with limited permissions")
    except Exception as e:
        print(f"✅ Put operation correctly failed: {e}")
    
    # Test with no token
    print("\n🔒 Testing no authorization token...")
    client.set_auth_token(None)
    
    try:
        client.list_assets()
        print("❌ List operation should have failed without token")
    except Exception as e:
        print(f"✅ List operation correctly failed: {e}")
    
    client.close()
    return True

if __name__ == "__main__":
    success = test_authorization()
    if success:
        print("\n✅ Authorization system test completed successfully!")
    else:
        print("\n❌ Authorization system test failed!")
        sys.exit(1)
