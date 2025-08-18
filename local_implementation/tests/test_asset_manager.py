#!/usr/bin/env python3
"""Tests for AIFS Asset Manager with Merkle trees and signatures."""

import unittest
import tempfile
import os
from pathlib import Path
import numpy as np

# Import AIFS components
from aifs.asset import AssetManager
from aifs.crypto import CryptoManager


class TestAssetManager(unittest.TestCase):
    """Test asset manager functionality with cryptographic features."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.asset_manager = AssetManager(self.temp_dir.name)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_asset_manager_initialization(self):
        """Test asset manager initialization."""
        # Check that components were initialized
        self.assertIsNotNone(self.asset_manager.storage)
        self.assertIsNotNone(self.asset_manager.vector_db)
        self.assertIsNotNone(self.asset_manager.metadata_db)
        self.assertIsNotNone(self.asset_manager.crypto_manager)

    def test_basic_asset_operations(self):
        """Test basic asset operations."""
        # Test data
        test_data = b"Hello, AIFS! This is test asset data."
        
        # Store asset
        asset_id = self.asset_manager.put_asset(
            data=test_data,
            kind="blob",
            metadata={"description": "Test asset", "content_type": "text/plain"}
        )
        
        self.assertIsInstance(asset_id, str)
        self.assertEqual(len(asset_id), 64)  # SHA-256 hash
        
        # Retrieve asset
        asset = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["data"], test_data)
        self.assertEqual(asset["kind"], "blob")
        self.assertEqual(asset["size"], len(test_data))
        self.assertIn("description", asset["metadata"])

    def test_asset_with_embedding(self):
        """Test asset storage with embedding."""
        # Test data and embedding
        test_data = b"Data with embedding"
        embedding = np.random.rand(128).astype(np.float32)
        
        # Store asset with embedding
        asset_id = self.asset_manager.put_asset(
            data=test_data,
            kind="embed",
            embedding=embedding
        )
        
        # Retrieve asset
        asset = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["kind"], "embed")

    def test_asset_lineage(self):
        """Test asset lineage tracking."""
        # Create parent asset
        parent_data = b"Parent asset data"
        parent_id = self.asset_manager.put_asset(
            data=parent_data,
            kind="blob"
        )
        
        # Create child asset with lineage
        child_data = b"Child asset data"
        child_id = self.asset_manager.put_asset(
            data=child_data,
            kind="blob",
            parents=[{
                "asset_id": parent_id,
                "transform_name": "test_transform",
                "transform_digest": "transform_hash_123"
            }]
        )
        
        # Retrieve child asset
        child_asset = self.asset_manager.get_asset(child_id)
        self.assertIsNotNone(child_asset)
        self.assertEqual(len(child_asset["parents"]), 1)
        self.assertEqual(child_asset["parents"][0]["asset_id"], parent_id)
        self.assertEqual(child_asset["parents"][0]["transform_name"], "test_transform")
        
        # Check parent has child
        parent_asset = self.asset_manager.get_asset(parent_id)
        self.assertIsNotNone(parent_asset)
        self.assertEqual(len(parent_asset["children"]), 1)
        self.assertEqual(parent_asset["children"][0]["asset_id"], child_id)

    def test_vector_search(self):
        """Test vector search functionality."""
        # Create test embeddings
        embeddings = []
        asset_ids = []
        
        for i in range(5):
            embedding = np.random.rand(128).astype(np.float32)
            data = f"Asset {i} data".encode()
            
            asset_id = self.asset_manager.put_asset(
                data=data,
                kind="embed",
                embedding=embedding
            )
            
            embeddings.append(embedding)
            asset_ids.append(asset_id)
        
        # Search with first embedding
        query_embedding = embeddings[0]
        results = self.asset_manager.vector_search(query_embedding, k=3)
        
        # Should get results
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 3)
        
        # Check result structure
        for result in results:
            self.assertIn("score", result)
            self.assertIn("asset_id", result)
            self.assertIn("kind", result)

    def test_snapshot_creation(self):
        """Test snapshot creation with Merkle tree and signatures."""
        # Create test assets
        asset_ids = []
        for i in range(3):
            data = f"Asset {i} for snapshot".encode()
            asset_id = self.asset_manager.put_asset(data=data, kind="blob")
            asset_ids.append(asset_id)
        
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(
            namespace="test-namespace",
            asset_ids=asset_ids,
            metadata={"description": "Test snapshot"}
        )
        
        self.assertIsInstance(snapshot_id, str)
        
        # Get snapshot
        snapshot = self.asset_manager.get_snapshot(snapshot_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["namespace"], "test-namespace")
        self.assertEqual(len(snapshot["assets"]), 3)
        self.assertIn("merkle_root", snapshot)
        self.assertIn("signature", snapshot)
        self.assertIn("merkle_tree", snapshot)
        self.assertIn("merkle_proofs", snapshot)

    def test_snapshot_verification(self):
        """Test snapshot signature verification."""
        # Create test assets
        asset_ids = []
        for i in range(2):
            data = f"Asset {i} for verification".encode()
            asset_id = self.asset_manager.put_asset(data=data, kind="blob")
            asset_ids.append(asset_id)
        
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(
            namespace="verify-namespace",
            asset_ids=asset_ids
        )
        
        # Get public key
        public_key = self.asset_manager.get_public_key()
        self.assertIsInstance(public_key, bytes)
        
        # Verify snapshot
        is_valid = self.asset_manager.verify_snapshot(snapshot_id, public_key)
        self.assertTrue(is_valid)

    def test_merkle_proofs(self):
        """Test Merkle proof generation and verification."""
        # Create test assets
        asset_ids = []
        for i in range(4):
            data = f"Asset {i} for proofs".encode()
            asset_id = self.asset_manager.put_asset(data=data, kind="blob")
            asset_ids.append(asset_id)
        
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(
            namespace="proof-namespace",
            asset_ids=asset_ids
        )
        
        # Get snapshot with proofs
        snapshot = self.asset_manager.get_snapshot(snapshot_id)
        self.assertIn("merkle_proofs", snapshot)
        
        # Check that proofs exist for each asset
        for asset_id in asset_ids:
            self.assertIn(asset_id, snapshot["merkle_proofs"])
            proof = snapshot["merkle_proofs"][asset_id]
            self.assertIsInstance(proof, list)

    def test_namespace_management(self):
        """Test namespace creation and management."""
        # Create namespace
        namespace_id = self.asset_manager.metadata_db.create_namespace(
            "test-namespace",
            {"description": "Test namespace"}
        )
        
        # Get namespace
        namespace = self.asset_manager.metadata_db.get_namespace(namespace_id)
        self.assertIsNotNone(namespace)
        self.assertEqual(namespace["name"], "test-namespace")
        
        # List namespaces
        namespaces = self.asset_manager.metadata_db.list_namespaces()
        self.assertGreater(len(namespaces), 0)
        
        # Find our namespace
        found = False
        for ns in namespaces:
            if ns["namespace_id"] == namespace_id:
                found = True
                break
        self.assertTrue(found)

    def test_asset_kinds(self):
        """Test different asset kinds."""
        # Test blob
        blob_data = b"Blob data"
        blob_id = self.asset_manager.put_asset(data=blob_data, kind="blob")
        
        # Test tensor
        tensor_data = b"Tensor data"
        tensor_id = self.asset_manager.put_asset(data=tensor_data, kind="tensor")
        
        # Test embed
        embed_data = b"Embed data"
        embed_embedding = np.random.rand(128).astype(np.float32)
        embed_id = self.asset_manager.put_asset(
            data=embed_data, 
            kind="embed", 
            embedding=embed_embedding
        )
        
        # Test artifact
        artifact_data = b"Artifact data"
        artifact_id = self.asset_manager.put_asset(data=artifact_data, kind="artifact")
        
        # Verify all were created
        self.assertIsNotNone(self.asset_manager.get_asset(blob_id))
        self.assertIsNotNone(self.asset_manager.get_asset(tensor_id))
        self.assertIsNotNone(self.asset_manager.get_asset(embed_id))
        self.assertIsNotNone(self.asset_manager.get_asset(artifact_id))

    def test_large_asset_handling(self):
        """Test handling of large assets."""
        # Create large test data
        large_data = b"Large asset data. " * 10000
        
        # Store large asset
        asset_id = self.asset_manager.put_asset(
            data=large_data,
            kind="blob",
            metadata={"size_category": "large"}
        )
        
        # Retrieve large asset
        asset = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["data"], large_data)
        self.assertEqual(asset["size"], len(large_data))

    def test_asset_metadata(self):
        """Test asset metadata handling."""
        # Create asset with rich metadata
        metadata = {
            "description": "Test asset with metadata",
            "content_type": "text/plain",
            "tags": ["test", "metadata", "aifs"],
            "version": "1.0.0",
            "author": "Test User"
        }
        
        asset_id = self.asset_manager.put_asset(
            data=b"Metadata test data",
            kind="blob",
            metadata=metadata
        )
        
        # Retrieve and verify metadata
        asset = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(asset)
        
        for key, value in metadata.items():
            self.assertIn(key, asset["metadata"])
            self.assertEqual(asset["metadata"][key], value)

    def test_error_handling(self):
        """Test error handling in asset manager."""
        # Test with invalid asset ID
        invalid_asset = self.asset_manager.get_asset("invalid" * 16)
        self.assertIsNone(invalid_asset)
        
        # Test with invalid snapshot ID
        invalid_snapshot = self.asset_manager.get_snapshot("invalid" * 16)
        self.assertIsNone(invalid_snapshot)

    def test_crypto_manager_integration(self):
        """Test integration with crypto manager."""
        # Get public key
        public_key = self.asset_manager.get_public_key()
        self.assertIsInstance(public_key, bytes)
        self.assertEqual(len(public_key), 32)  # Ed25519 public key
        
        # Get hex representation
        public_key_hex = self.asset_manager.get_public_key_hex()
        self.assertIsInstance(public_key_hex, str)
        self.assertEqual(len(public_key_hex), 64)  # 32 bytes = 64 hex chars


if __name__ == "__main__":
    unittest.main()
