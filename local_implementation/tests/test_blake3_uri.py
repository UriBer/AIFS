#!/usr/bin/env python3
"""Tests for BLAKE3 hashing and URI schemes."""

import unittest
import tempfile
import os
from pathlib import Path

from aifs.storage import StorageBackend
from aifs.uri import AIFSUri, asset_uri, snapshot_uri, parse_asset_uri, parse_snapshot_uri


class TestBLAKE3Hashing(unittest.TestCase):
    """Test BLAKE3 hashing implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_blake3_hash_generation(self):
        """Test that BLAKE3 hashes are generated correctly."""
        test_data = b"Hello, AIFS!"
        hash_hex = self.storage.put(test_data)
        
        # BLAKE3 hash should be 64 hex characters
        self.assertEqual(len(hash_hex), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_hex))
        
        # Same data should produce same hash
        hash_hex2 = self.storage.put(test_data)
        self.assertEqual(hash_hex, hash_hex2)
    
    def test_blake3_deterministic(self):
        """Test that BLAKE3 is deterministic."""
        test_data = b"Deterministic test data"
        hash1 = self.storage.put(test_data)
        hash2 = self.storage.put(test_data)
        self.assertEqual(hash1, hash2)
    
    def test_blake3_different_data(self):
        """Test that different data produces different hashes."""
        data1 = b"Data 1"
        data2 = b"Data 2"
        
        hash1 = self.storage.put(data1)
        hash2 = self.storage.put(data2)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_blake3_retrieval(self):
        """Test that data can be retrieved using BLAKE3 hash."""
        test_data = b"Test data for retrieval"
        hash_hex = self.storage.put(test_data)
        
        retrieved_data = self.storage.get(hash_hex)
        self.assertEqual(retrieved_data, test_data)


class TestURISchemes(unittest.TestCase):
    """Test AIFS URI schemes."""
    
    def test_asset_uri_creation(self):
        """Test creating asset URIs."""
        # Valid BLAKE3 hash
        asset_id = "a" * 64  # 64 hex characters
        uri = AIFSUri.asset_id_to_uri(asset_id)
        self.assertEqual(uri, f"aifs://{asset_id}")
    
    def test_snapshot_uri_creation(self):
        """Test creating snapshot URIs."""
        # Valid BLAKE3 hash
        snapshot_id = "b" * 64  # 64 hex characters
        uri = AIFSUri.snapshot_id_to_uri(snapshot_id)
        self.assertEqual(uri, f"aifs-snap://{snapshot_id}")
    
    def test_invalid_hash_uri_creation(self):
        """Test that invalid hashes raise errors."""
        # Invalid hash (too short)
        with self.assertRaises(ValueError):
            AIFSUri.asset_id_to_uri("short")
        
        # Invalid hash (invalid characters)
        with self.assertRaises(ValueError):
            AIFSUri.asset_id_to_uri("G" * 64)  # Invalid character
    
    def test_asset_uri_parsing(self):
        """Test parsing asset URIs."""
        asset_id = "a" * 64
        uri = f"aifs://{asset_id}"
        
        parsed_id = AIFSUri.parse_asset_uri(uri)
        self.assertEqual(parsed_id, asset_id)
        
        # Test with leading slash
        uri_with_slash = f"aifs:///{asset_id}"
        parsed_id = AIFSUri.parse_asset_uri(uri_with_slash)
        self.assertEqual(parsed_id, asset_id)
    
    def test_snapshot_uri_parsing(self):
        """Test parsing snapshot URIs."""
        snapshot_id = "b" * 64
        uri = f"aifs-snap://{snapshot_id}"
        
        parsed_id = AIFSUri.parse_snapshot_uri(uri)
        self.assertEqual(parsed_id, snapshot_id)
    
    def test_invalid_uri_parsing(self):
        """Test parsing invalid URIs."""
        # Wrong scheme
        self.assertIsNone(AIFSUri.parse_asset_uri("http://example.com"))
        self.assertIsNone(AIFSUri.parse_snapshot_uri("aifs://invalid"))
        
        # Invalid hash in URI
        self.assertIsNone(AIFSUri.parse_asset_uri("aifs://invalid"))
        self.assertIsNone(AIFSUri.parse_snapshot_uri("aifs-snap://invalid"))
    
    def test_uri_validation(self):
        """Test URI validation."""
        # Valid URIs
        self.assertTrue(AIFSUri.validate_uri("aifs://" + "a" * 64))
        self.assertTrue(AIFSUri.validate_uri("aifs-snap://" + "b" * 64))
        
        # Invalid URIs
        self.assertFalse(AIFSUri.validate_uri("http://example.com"))
        self.assertFalse(AIFSUri.validate_uri("aifs://invalid"))
        self.assertFalse(AIFSUri.validate_uri("aifs-snap://invalid"))
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        asset_id = "a" * 64
        snapshot_id = "b" * 64
        
        # Test asset URI convenience function
        uri = asset_uri(asset_id)
        self.assertEqual(uri, f"aifs://{asset_id}")
        
        # Test snapshot URI convenience function
        uri = snapshot_uri(snapshot_id)
        self.assertEqual(uri, f"aifs-snap://{snapshot_id}")
        
        # Test parsing convenience functions
        parsed_asset = parse_asset_uri(f"aifs://{asset_id}")
        self.assertEqual(parsed_asset, asset_id)
        
        parsed_snapshot = parse_snapshot_uri(f"aifs-snap://{snapshot_id}")
        self.assertEqual(parsed_snapshot, snapshot_id)


class TestURIIntegration(unittest.TestCase):
    """Test URI integration with storage."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_storage_uri_roundtrip(self):
        """Test that storage and URI work together."""
        test_data = b"URI integration test"
        
        # Store data and get hash
        asset_id = self.storage.put(test_data)
        
        # Create URI
        uri = AIFSUri.asset_id_to_uri(asset_id)
        
        # Parse URI back to asset ID
        parsed_id = AIFSUri.parse_asset_uri(uri)
        
        # Should be the same
        self.assertEqual(asset_id, parsed_id)
        
        # Should be able to retrieve data
        retrieved_data = self.storage.get(parsed_id)
        self.assertEqual(retrieved_data, test_data)


if __name__ == '__main__':
    unittest.main()
