#!/usr/bin/env python3
"""Basic functionality tests for AIFS."""

import unittest
import tempfile
import os
from pathlib import Path

# Import AIFS components
from aifs.storage import StorageBackend
from aifs.vector_db import VectorDB
from aifs.metadata import MetadataStore
from aifs.merkle import MerkleTree
from aifs.crypto import CryptoManager


class TestBasicFunctionality(unittest.TestCase):
    """Test basic AIFS functionality."""
    
    def setUp(self):
        """Set up test environment."""
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
    
    def test_storage_basic(self):
        """Test basic storage operations."""
        test_data = b"Hello, AIFS!"
        asset_id = self.storage.put(test_data)
        
        # Verify content addressing
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(test_data, retrieved_data)
    
    def test_vector_db_basic(self):
        """Test basic vector database operations."""
        import numpy as np
        
        # Create test embedding
        embedding = np.random.rand(128).astype(np.float32)
        asset_id = "test_asset_123"
        
        # Add to vector database
        self.vector_db.add(asset_id, embedding)
        
        # Search for similar vectors
        results = self.vector_db.search(embedding, k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], asset_id)
    
    def test_metadata_basic(self):
        """Test basic metadata operations."""
        # Create namespace
        namespace_id = self.metadata.create_namespace("test-namespace", "Test namespace")
        self.assertIsNotNone(namespace_id)
        
        # Get namespace
        namespace = self.metadata.get_namespace(namespace_id)
        self.assertEqual(namespace["name"], "test-namespace")
    
    def test_merkle_tree_basic(self):
        """Test basic Merkle tree operations."""
        asset_ids = ["asset1", "asset2", "asset3"]
        
        # Create tree
        tree = MerkleTree(asset_ids)
        root_hash = tree.get_root_hash()
        
        # Verify tree structure
        self.assertIsNotNone(root_hash)
        self.assertEqual(len(tree.asset_ids), 3)
    
    def test_crypto_basic(self):
        """Test basic cryptographic operations."""
        # Generate keys
        private_key = self.crypto.generate_private_key()
        public_key = self.crypto.get_public_key()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        
        # Test signing
        data = b"test data"
        signature_bytes, signature_hex = self.crypto.sign_data(data)
        self.assertIsNotNone(signature_bytes)
        self.assertIsNotNone(signature_hex)
        
        # Test verification
        is_valid = self.crypto.verify_signature(data, signature_bytes, public_key)
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()