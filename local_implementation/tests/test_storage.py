#!/usr/bin/env python3
"""Tests for AIFS Storage Backend with BLAKE3 and encryption."""

import unittest
import tempfile
import os
from pathlib import Path

# Import AIFS components
from aifs.storage import StorageBackend


class TestStorageBackend(unittest.TestCase):
    """Test storage backend functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "storage"
        self.storage = StorageBackend(self.storage_path)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_storage_initialization(self):
        """Test storage backend initialization."""
        # Check that directories were created
        self.assertTrue(self.storage_path.exists())
        self.assertTrue((self.storage_path / "chunks").exists())

    def test_basic_storage_operations(self):
        """Test basic storage operations."""
        # Test data
        test_data = b"Hello, AIFS! This is test data for storage."
        
        # Store data
        asset_id = self.storage.put(test_data)
        self.assertIsInstance(asset_id, str)
        self.assertEqual(len(asset_id), 64)  # BLAKE3 hash is 64 hex chars
        
        # Check if data exists
        self.assertTrue(self.storage.exists(asset_id))
        
        # Retrieve data
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(retrieved_data, test_data)

    def test_content_addressed_storage(self):
        """Test content-addressed storage behavior."""
        # Store same data twice
        test_data = b"Duplicate data"
        
        asset_id1 = self.storage.put(test_data)
        asset_id2 = self.storage.put(test_data)
        
        # Should get same hash for same content
        self.assertEqual(asset_id1, asset_id2)
        
        # Both should exist
        self.assertTrue(self.storage.exists(asset_id1))
        self.assertTrue(self.storage.exists(asset_id2))

    def test_different_data_different_hashes(self):
        """Test that different data produces different hashes."""
        data1 = b"First piece of data"
        data2 = b"Second piece of data"
        
        hash1 = self.storage.put(data1)
        hash2 = self.storage.put(data2)
        
        # Should be different
        self.assertNotEqual(hash1, hash2)

    def test_storage_deletion(self):
        """Test storage deletion."""
        # Store data
        test_data = b"Data to be deleted"
        asset_id = self.storage.put(test_data)
        
        # Verify it exists
        self.assertTrue(self.storage.exists(asset_id))
        
        # Delete it
        success = self.storage.delete(asset_id)
        self.assertTrue(success)
        
        # Verify it's gone
        self.assertFalse(self.storage.exists(asset_id))
        
        # Try to delete non-existent data
        success = self.storage.delete("nonexistent" * 16)
        self.assertFalse(success)

    def test_encryption(self):
        """Test that data is encrypted."""
        # Store data
        test_data = b"Sensitive data that should be encrypted"
        asset_id = self.storage.put(test_data)
        
        # Get the raw encrypted file
        encrypted_file_path = self.storage._hash_to_path(asset_id)
        encrypted_data = encrypted_file_path.read_bytes()
        
        # Encrypted data should not contain original data
        self.assertNotIn(test_data, encrypted_data)
        
        # But we should still be able to retrieve it
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(retrieved_data, test_data)

    def test_hash_to_path_sharding(self):
        """Test hash to path conversion with sharding."""
        # Create a test hash
        test_hash = "a" * 64
        
        path = self.storage._hash_to_path(test_hash)
        
        # Should create sharded path structure
        self.assertIn("aaaa", str(path))
        self.assertTrue(str(path).endswith(test_hash))

    def test_chunk_info(self):
        """Test getting chunk information."""
        # Store data
        test_data = b"Data for chunk info test"
        asset_id = self.storage.put(test_data)
        
        # Get chunk info
        info = self.storage.get_chunk_info(asset_id)
        self.assertIsNotNone(info)
        self.assertIn("size", info)
        self.assertIn("created", info)
        self.assertIn("modified", info)
        
        # Size should be greater than original due to encryption overhead
        self.assertGreater(info["size"], len(test_data))

    def test_large_data_storage(self):
        """Test storage of large data."""
        # Create large test data
        large_data = b"Large data test. " * 10000
        
        # Store large data
        asset_id = self.storage.put(large_data)
        
        # Verify storage
        self.assertTrue(self.storage.exists(asset_id))
        
        # Retrieve and verify
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(retrieved_data, large_data)

    def test_empty_data_storage(self):
        """Test storage of empty data."""
        empty_data = b""
        
        # Store empty data
        asset_id = self.storage.put(empty_data)
        
        # Verify storage
        self.assertTrue(self.storage.exists(asset_id))
        
        # Retrieve and verify
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(retrieved_data, empty_data)

    def test_unicode_data_storage(self):
        """Test storage of Unicode data."""
        # Test Unicode string
        unicode_string = "Hello, 世界! 🌍 This is a test with Unicode characters."
        unicode_data = unicode_string.encode('utf-8')
        
        # Store Unicode data
        asset_id = self.storage.put(unicode_data)
        
        # Verify storage
        self.assertTrue(self.storage.exists(asset_id))
        
        # Retrieve and verify
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(retrieved_data, unicode_data)
        self.assertEqual(retrieved_data.decode('utf-8'), unicode_string)

    def test_custom_encryption_key(self):
        """Test storage with custom encryption key."""
        # Create custom key
        custom_key = b"custom-encryption-key-32-bytes!!"
        
        # Create storage with custom key
        custom_storage = StorageBackend(self.storage_path / "custom", custom_key)
        
        # Store data
        test_data = b"Data with custom encryption"
        asset_id = custom_storage.put(test_data)
        
        # Verify storage
        self.assertTrue(custom_storage.exists(asset_id))
        
        # Retrieve and verify
        retrieved_data = custom_storage.get(asset_id)
        self.assertEqual(retrieved_data, test_data)

    def test_storage_persistence(self):
        """Test that storage persists across instances."""
        test_data = b"Persistent test data"
        asset_id = self.storage.put(test_data)
        
        # Verify data was stored
        self.assertTrue(self.storage.exists(asset_id))
        retrieved_data = self.storage.get(asset_id)
        self.assertEqual(test_data, retrieved_data)
        
        # Create new storage instance with same directory and encryption key
        new_storage = StorageBackend(
            self.storage.root_dir, 
            encryption_key=self.storage.encryption_key
        )
        
        # Verify data persists
        self.assertTrue(new_storage.exists(asset_id))
        retrieved_data = new_storage.get(asset_id)
        self.assertEqual(test_data, retrieved_data)

    def test_invalid_hash_retrieval(self):
        """Test retrieval with invalid hash."""
        # Try to get non-existent hash
        retrieved_data = self.storage.get("invalid" * 16)
        self.assertIsNone(retrieved_data)
        
        # Try to get info for non-existent hash
        info = self.storage.get_chunk_info("invalid" * 16)
        self.assertIsNone(info)

    def test_storage_cleanup(self):
        """Test storage cleanup on deletion."""
        # Store multiple pieces of data
        data1 = b"First piece"
        data2 = b"Second piece"
        
        hash1 = self.storage.put(data1)
        hash2 = self.storage.put(data2)
        
        # Delete first piece
        self.storage.delete(hash1)
        
        # First should be gone
        self.assertFalse(self.storage.exists(hash1))
        
        # Second should still exist
        self.assertTrue(self.storage.exists(hash2))


if __name__ == "__main__":
    unittest.main()
