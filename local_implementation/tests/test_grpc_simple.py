"""Simplified gRPC server tests.

These tests focus on core gRPC functionality without complex server setup.
"""

import unittest
import tempfile
import time
import threading
import os
import json
import struct
from unittest.mock import Mock

import grpc
import numpy as np

# Import AIFS modules
from aifs.asset import AssetManager
from aifs.server import serve
from aifs.proto import aifs_pb2, aifs_pb2_grpc


class TestGRPCSimple(unittest.TestCase):
    """Simplified gRPC server tests."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        
        # Create asset manager directly
        self.asset_manager = AssetManager(self.test_dir)
        
        # Start server in background
        self.server_thread = threading.Thread(
            target=serve,
            args=(self.test_dir, 50053),  # Use different port for testing
            daemon=True
        )
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Create client
        self.channel = grpc.insecure_channel('localhost:50053')
        self.aifs_stub = aifs_pb2_grpc.AIFSStub(self.channel)
        self.health_stub = aifs_pb2_grpc.HealthStub(self.channel)
        
        # Create auth metadata
        import time as time_module
        token_data = json.dumps({
            "permissions": ["put", "get", "delete", "list", "search", "snapshot"],
            "expires": time_module.time() + 3600  # 1 hour from now
        })
        self.auth_metadata = [('authorization', f'Bearer {token_data}')]
    
    def tearDown(self):
        """Clean up test environment."""
        self.channel.close()
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_health_check(self):
        """Test health check endpoint."""
        request = aifs_pb2.HealthCheckRequest()
        response = self.health_stub.Check(request)
        
        self.assertTrue(response.healthy)
        self.assertEqual(response.status, "SERVING")
    
    def test_put_asset_direct(self):
        """Test putting an asset using direct AssetManager."""
        # Test data
        test_data = b"Test asset data"
        
        # Use AssetManager directly
        asset_id = self.asset_manager.put_asset(
            data=test_data,
            kind="blob",
            metadata={"test_key": "test_value"}
        )
        
        # Verify asset was created
        self.assertIsNotNone(asset_id)
        self.assertEqual(len(asset_id), 64)  # BLAKE3 hash length
        
        # Verify we can retrieve it
        asset = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["asset_id"], asset_id)
        self.assertEqual(asset["kind"], "blob")
        self.assertEqual(asset["size"], len(test_data))
    
    def test_grpc_put_asset(self):
        """Test gRPC PutAsset with proper database initialization."""
        # Ensure database is initialized by calling a simple operation first
        try:
            list_request = aifs_pb2.ListAssetsRequest()
            self.aifs_stub.ListAssets(list_request, metadata=self.auth_metadata)
        except Exception:
            pass  # Database will be initialized on first real operation
        
        # Test data
        test_data = b"Test asset data for gRPC"
        
        # Create request
        request = aifs_pb2.PutAssetRequest()
        chunk = request.chunks.add()
        chunk.data = test_data
        request.kind = aifs_pb2.AssetKind.BLOB
        request.metadata["test_key"] = "test_value"
        
        # Send request
        response = self.aifs_stub.PutAsset(iter([request]), metadata=self.auth_metadata)
        
        # Check response
        self.assertIsNotNone(response.asset_id)
        self.assertEqual(len(response.asset_id), 64)  # BLAKE3 hash length
    
    def test_grpc_get_asset(self):
        """Test gRPC GetAsset."""
        # First put an asset
        test_data = b"Test asset for retrieval"
        
        put_request = aifs_pb2.PutAssetRequest()
        chunk = put_request.chunks.add()
        chunk.data = test_data
        put_request.kind = aifs_pb2.AssetKind.BLOB
        put_request.metadata["test_key"] = "test_value"
        
        put_response = self.aifs_stub.PutAsset(iter([put_request]), metadata=self.auth_metadata)
        asset_id = put_response.asset_id
        
        # Now get the asset
        get_request = aifs_pb2.GetAssetRequest()
        get_request.asset_id = asset_id
        get_request.include_data = True
        
        get_response = self.aifs_stub.GetAsset(get_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertEqual(get_response.metadata.asset_id, asset_id)
        self.assertEqual(get_response.metadata.kind, aifs_pb2.AssetKind.BLOB)
        self.assertEqual(get_response.metadata.size, len(test_data))
        self.assertEqual(get_response.data, test_data)
        self.assertIn("aifs://", get_response.uri)
    
    def test_grpc_list_assets(self):
        """Test gRPC ListAssets."""
        # Put a few assets
        for i in range(3):
            test_data = f"Test asset {i}".encode()
            
            request = aifs_pb2.PutAssetRequest()
            chunk = request.chunks.add()
            chunk.data = test_data
            request.kind = aifs_pb2.AssetKind.BLOB
            request.metadata["index"] = str(i)
            
            self.aifs_stub.PutAsset(iter([request]), metadata=self.auth_metadata)
        
        # List assets
        list_request = aifs_pb2.ListAssetsRequest()
        list_response = self.aifs_stub.ListAssets(list_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertGreaterEqual(len(list_response.assets), 3)
        for asset in list_response.assets:
            self.assertIsNotNone(asset.asset_id)
            self.assertEqual(len(asset.asset_id), 64)
    
    def test_grpc_vector_search(self):
        """Test gRPC VectorSearch."""
        # Put an asset with embedding
        test_data = b"Test asset for vector search"
        embedding = [0.1] * 128  # 128-dimensional embedding
        
        request = aifs_pb2.PutAssetRequest()
        chunk = request.chunks.add()
        chunk.data = test_data
        request.kind = aifs_pb2.AssetKind.BLOB
        # Serialize embedding as bytes (assuming 32-bit floats)
        request.embedding = struct.pack('f' * len(embedding), *embedding)
        
        put_response = self.aifs_stub.PutAsset(iter([request]), metadata=self.auth_metadata)
        
        # Search for similar assets
        search_request = aifs_pb2.VectorSearchRequest()
        search_request.query_embedding = struct.pack('f' * len(embedding), *embedding)
        search_request.k = 5
        
        search_response = self.aifs_stub.VectorSearch(search_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertGreaterEqual(len(search_response.results), 1)
        self.assertEqual(search_response.results[0].asset_id, put_response.asset_id)
        self.assertGreater(search_response.results[0].score, 0.0)
    
    def test_grpc_create_snapshot(self):
        """Test gRPC CreateSnapshot."""
        # Put an asset first
        test_data = b"Test asset for snapshot"
        
        request = aifs_pb2.PutAssetRequest()
        chunk = request.chunks.add()
        chunk.data = test_data
        request.kind = aifs_pb2.AssetKind.BLOB
        
        put_response = self.aifs_stub.PutAsset(iter([request]), metadata=self.auth_metadata)
        asset_id = put_response.asset_id
        
        # Create snapshot
        snapshot_request = aifs_pb2.CreateSnapshotRequest()
        snapshot_request.namespace = "test"
        snapshot_request.asset_ids.append(asset_id)
        snapshot_request.metadata["test_snapshot"] = "true"
        
        snapshot_response = self.aifs_stub.CreateSnapshot(snapshot_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertIsNotNone(snapshot_response.snapshot_id)
        self.assertEqual(len(snapshot_response.snapshot_id), 32)  # 128-bit hash
        self.assertIsNotNone(snapshot_response.merkle_root)


if __name__ == '__main__':
    unittest.main()
