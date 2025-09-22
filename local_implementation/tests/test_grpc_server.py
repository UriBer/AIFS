#!/usr/bin/env python3
"""Tests for gRPC server functionality."""

import unittest
import tempfile
import os
import time
import threading
from pathlib import Path

import grpc
from aifs.proto import aifs_pb2, aifs_pb2_grpc
from aifs.asset import AssetManager
from aifs.server import serve


class TestGRPCServer(unittest.TestCase):
    """Test gRPC server functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        
        # Start server in background
        self.server_thread = threading.Thread(
            target=serve,
            args=(self.test_dir, 50052),  # Use different port for testing
            daemon=True
        )
        self.server_thread.start()
        
        # Wait for server to start and database to initialize
        time.sleep(3)
        
        # Create client with authentication
        self.channel = grpc.insecure_channel('localhost:50052')
        self.health_stub = aifs_pb2_grpc.HealthStub(self.channel)
        self.aifs_stub = aifs_pb2_grpc.AIFSStub(self.channel)
        
        # Add authentication metadata with proper token format
        import json
        import time as time_module
        token_data = json.dumps({
            "permissions": ["put", "get", "delete", "list", "search", "snapshot"],
            "expires": time_module.time() + 3600  # 1 hour from now
        })
        self.auth_metadata = [('authorization', f'Bearer {token_data}')]
        
        # Initialize the metadata database by calling a simple operation
        # This ensures the database tables are created
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Try to list assets to initialize the database
                list_request = aifs_pb2.ListAssetsRequest()
                self.aifs_stub.ListAssets(list_request, metadata=self.auth_metadata)
                break  # Success, database is initialized
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait before retry
                    continue
                else:
                    # If all retries fail, try a health check
                    try:
                        health_request = aifs_pb2.HealthCheckRequest()
                        self.health_stub.Check(health_request, metadata=self.auth_metadata)
                    except Exception:
                        pass  # Database will be initialized on first real operation
    
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
    
    def test_put_asset(self):
        """Test putting an asset."""
        # Create test data
        test_data = b"Test asset data"
        
        # Create request
        request = aifs_pb2.PutAssetRequest()
        chunk = request.chunks.add()
        chunk.data = test_data
        request.kind = aifs_pb2.AssetKind.BLOB
        request.metadata["test_key"] = "test_value"
        
        # Send request with authentication
        response = self.aifs_stub.PutAsset(iter([request]), metadata=self.auth_metadata)
        
        # Check response
        self.assertIsNotNone(response.asset_id)
        self.assertEqual(len(response.asset_id), 64)  # BLAKE3 hash length
    
    def test_get_asset(self):
        """Test getting an asset."""
        # First, put an asset
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
        self.assertEqual(get_response.data, test_data)
        self.assertIn("aifs://", get_response.uri)
    
    def test_get_nonexistent_asset(self):
        """Test getting a non-existent asset."""
        get_request = aifs_pb2.GetAssetRequest()
        get_request.asset_id = "nonexistent" * 8  # 64 chars
        get_request.include_data = True
        
        with self.assertRaises(grpc.RpcError) as context:
            self.aifs_stub.GetAsset(get_request)
        
        self.assertEqual(context.exception.code(), grpc.StatusCode.NOT_FOUND)
    
    def test_list_assets(self):
        """Test listing assets."""
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
        list_request.limit = 10
        
        list_response = self.aifs_stub.ListAssets(list_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertGreaterEqual(len(list_response.assets), 3)
        for asset in list_response.assets:
            self.assertIsNotNone(asset.asset_id)
            self.assertEqual(len(asset.asset_id), 64)
    
    def test_vector_search(self):
        """Test vector search."""
        # Put an asset with embedding
        test_data = b"Test asset for vector search"
        embedding = [0.1] * 128  # 128-dimensional embedding
        
        request = aifs_pb2.PutAssetRequest()
        chunk = request.chunks.add()
        chunk.data = test_data
        request.kind = aifs_pb2.AssetKind.BLOB
        # Serialize embedding as bytes (assuming 32-bit floats)
        import struct
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
    
    def test_create_snapshot(self):
        """Test creating a snapshot."""
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
    
    def test_get_snapshot(self):
        """Test getting a snapshot."""
        # Create a snapshot first
        test_data = b"Test asset for snapshot retrieval"
        
        put_request = aifs_pb2.PutAssetRequest()
        chunk = put_request.chunks.add()
        chunk.data = test_data
        put_request.kind = aifs_pb2.AssetKind.BLOB
        
        put_response = self.aifs_stub.PutAsset(iter([put_request]), metadata=self.auth_metadata)
        asset_id = put_response.asset_id
        
        snapshot_request = aifs_pb2.CreateSnapshotRequest()
        snapshot_request.namespace = "test"
        snapshot_request.asset_ids.append(asset_id)
        
        snapshot_response = self.aifs_stub.CreateSnapshot(snapshot_request, metadata=self.auth_metadata)
        snapshot_id = snapshot_response.snapshot_id
        
        # Get the snapshot
        get_request = aifs_pb2.GetSnapshotRequest()
        get_request.snapshot_id = snapshot_id
        
        get_response = self.aifs_stub.GetSnapshot(get_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertEqual(get_response.snapshot_id, snapshot_id)
        self.assertEqual(get_response.namespace, "test")
        self.assertIn(asset_id, get_response.asset_ids)
        self.assertIn("aifs-snap://", get_response.uri)
    
    def test_delete_asset(self):
        """Test deleting an asset."""
        # Put an asset first
        test_data = b"Test asset for deletion"
        
        put_request = aifs_pb2.PutAssetRequest()
        chunk = put_request.chunks.add()
        chunk.data = test_data
        put_request.kind = aifs_pb2.AssetKind.BLOB
        
        put_response = self.aifs_stub.PutAsset(iter([put_request]), metadata=self.auth_metadata)
        asset_id = put_response.asset_id
        
        # Delete the asset
        delete_request = aifs_pb2.DeleteAssetRequest()
        delete_request.asset_id = asset_id
        
        delete_response = self.aifs_stub.DeleteAsset(delete_request, metadata=self.auth_metadata)
        
        # Check response
        self.assertTrue(delete_response.success)
        
        # Verify asset is deleted
        get_request = aifs_pb2.GetAssetRequest()
        get_request.asset_id = asset_id
        
        with self.assertRaises(grpc.RpcError) as context:
            self.aifs_stub.GetAsset(get_request)
        
        self.assertEqual(context.exception.code(), grpc.StatusCode.NOT_FOUND)


if __name__ == '__main__':
    unittest.main()
