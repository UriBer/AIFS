"""Tests for AIFS built-in services."""

import unittest
from unittest.mock import Mock, patch
import os

# Import AIFS components
from aifs.storage import StorageBackend
from aifs.vector_db import VectorDB
from aifs.metadata import MetadataStore
from aifs.merkle import MerkleTree
from aifs.crypto import CryptoManager


class TestBuiltinServices(unittest.TestCase):
    """Test built-in AIFS services."""
    
    def setUp(self):
        """Set up test environment."""
        import tempfile
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.test_dir)
        self.vector_db = VectorDB(self.test_dir, dimension=128)
        
        # Create a proper database path within the test directory
        self.db_path = os.path.join(self.test_dir, "metadata.db")
        self.metadata = MetadataStore(self.db_path)
        
        self.crypto = CryptoManager()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_storage_service(self):
        """Test storage service functionality."""
        # Test basic storage operations
        test_data = b"Test data for storage service"
        asset_id = self.storage.put(test_data)
        
        # Verify storage
        self.assertTrue(self.storage.exists(asset_id))
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(test_data, retrieved_data)
        
        # Test deletion
        self.storage.delete(asset_id)
        self.assertFalse(self.storage.exists(asset_id))
    
    def test_vector_service(self):
        """Test vector service functionality."""
        import numpy as np
        
        # Test vector operations
        embedding = np.random.rand(128).astype(np.float32)
        asset_id = "test_vector_asset"
        
        # Add vector
        self.vector_db.add(asset_id, embedding)
        
        # Search vector
        results = self.vector_db.search(embedding, k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], asset_id)
        
        # Get stats
        stats = self.vector_db.get_stats()
        self.assertIn("total_vectors", stats)
        self.assertIn("backend", stats)
    
    def test_metadata_service(self):
        """Test metadata service functionality."""
        # Test namespace operations
        namespace_id = self.metadata.create_namespace("test", "Test namespace")
        self.assertIsNotNone(namespace_id)
        
        namespace = self.metadata.get_namespace(namespace_id)
        self.assertEqual(namespace["name"], "test")
        
        # Test asset operations
        asset_id = "test_asset"
        self.metadata.add_asset(asset_id, "blob", 100, {"test": "data"})
        
        asset = self.metadata.get_asset(asset_id)
        self.assertEqual(asset["asset_id"], asset_id)
        self.assertEqual(asset["kind"], "blob")
    
    def test_merkle_service(self):
        """Test Merkle tree service functionality."""
        # Test tree creation
        asset_ids = ["asset1", "asset2", "asset3", "asset4"]
        tree = MerkleTree(asset_ids)
        
        root_hash = tree.get_root_hash()
        self.assertIsNotNone(root_hash)
        
        # Test proof generation
        proof = tree.get_proof("asset2")
        self.assertIsNotNone(proof)
        
        # Test proof verification
        is_valid = tree.verify_proof("asset2", proof, root_hash)
        self.assertTrue(is_valid)
    
    def test_crypto_service(self):
        """Test cryptographic service functionality."""
        # Test key generation
        private_key = self.crypto.generate_private_key()
        public_key = self.crypto.get_public_key()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        
        # Test signing and verification
        data = b"Test data for signing"
        signature_bytes, signature_hex = self.crypto.sign_data(data)
        
        is_valid = self.crypto.verify_signature(data, signature_bytes, public_key)
        self.assertTrue(is_valid)
        
        # Test snapshot signing
        merkle_root = "test_merkle_root"
        timestamp = "2024-01-01T00:00:00"
        namespace = "test"
        
        signature_bytes, signature_hex = self.crypto.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        self.assertIsNotNone(signature_bytes)
        self.assertIsNotNone(signature_hex)
        
        # Test snapshot verification
        is_valid = self.crypto.verify_snapshot_signature(
            signature_hex, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
