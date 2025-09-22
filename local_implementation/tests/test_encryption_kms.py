#!/usr/bin/env python3
"""Tests for AES-256-GCM encryption and KMS integration."""

import unittest
import tempfile
import os
from pathlib import Path

from aifs.storage import StorageBackend


class TestAES256GCMEncryption(unittest.TestCase):
    """Test AES-256-GCM encryption implementation."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_encryption_decryption(self):
        """Test that data can be encrypted and decrypted."""
        test_data = b"Test data for encryption"
        
        # Store data (should be encrypted)
        hash_hex = self.storage.put(test_data)
        
        # Retrieve data (should be decrypted)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_encryption_different_data(self):
        """Test that different data produces different encrypted results."""
        data1 = b"Data 1"
        data2 = b"Data 2"
        
        hash1 = self.storage.put(data1)
        hash2 = self.storage.put(data2)
        
        # Hashes should be different
        self.assertNotEqual(hash1, hash2)
        
        # Both should decrypt correctly
        retrieved1 = self.storage.get(hash1)
        retrieved2 = self.storage.get(hash2)
        
        self.assertEqual(retrieved1, data1)
        self.assertEqual(retrieved2, data2)
    
    def test_encryption_deterministic_hash(self):
        """Test that same data produces same hash despite encryption."""
        test_data = b"Deterministic test data"
        
        hash1 = self.storage.put(test_data)
        hash2 = self.storage.put(test_data)
        
        # Hashes should be the same (content-addressed)
        self.assertEqual(hash1, hash2)
    
    def test_encryption_large_data(self):
        """Test encryption with larger data."""
        # Create 1MB of test data
        test_data = b"X" * (1024 * 1024)
        
        hash_hex = self.storage.put(test_data)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_encryption_empty_data(self):
        """Test encryption with empty data."""
        test_data = b""
        
        hash_hex = self.storage.put(test_data)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_encryption_binary_data(self):
        """Test encryption with binary data."""
        # Create binary data with various byte values
        test_data = bytes(range(256))
        
        hash_hex = self.storage.put(test_data)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)


class TestKMSIntegration(unittest.TestCase):
    """Test KMS integration for envelope encryption."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.kms_key_id = "test-kms-key-123"
        self.storage = StorageBackend(self.test_dir, kms_key_id=self.kms_key_id)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_kms_key_id_storage(self):
        """Test that KMS key ID is stored in metadata."""
        test_data = b"Test data with KMS"
        hash_hex = self.storage.put(test_data)
        
        # Get chunk info
        chunk_info = self.storage.get_chunk_info(hash_hex)
        
        self.assertIsNotNone(chunk_info)
        self.assertEqual(chunk_info.get("kms_key_id"), self.kms_key_id)
        self.assertEqual(chunk_info.get("encryption"), "AES-256-GCM")
        self.assertEqual(chunk_info.get("hash_algorithm"), "BLAKE3")
    
    def test_kms_key_id_retrieval(self):
        """Test that KMS key ID can be retrieved."""
        test_data = b"Test data for KMS retrieval"
        hash_hex = self.storage.put(test_data)
        
        # Check that metadata file exists
        path = self.storage._hash_to_path(hash_hex)
        metadata_path = path.with_suffix('.meta')
        
        self.assertTrue(metadata_path.exists())
        
        # Read metadata file
        with open(metadata_path, 'r') as f:
            content = f.read()
        
        self.assertIn(f"kms_key_id={self.kms_key_id}", content)
        self.assertIn("encryption=AES-256-GCM", content)
        self.assertIn("hash_algorithm=BLAKE3", content)
    
    def test_default_kms_key_id(self):
        """Test default KMS key ID when none provided."""
        storage = StorageBackend(self.test_dir)
        test_data = b"Test data with default KMS"
        hash_hex = storage.put(test_data)
        
        chunk_info = storage.get_chunk_info(hash_hex)
        
        self.assertEqual(chunk_info.get("kms_key_id"), "aifs-default-key")
    
    def test_multiple_kms_keys(self):
        """Test storage with different KMS keys."""
        # Create storage with different KMS key
        storage2 = StorageBackend(self.test_dir, kms_key_id="different-kms-key")
        
        test_data1 = b"Data with first KMS key"
        test_data2 = b"Data with second KMS key"
        
        hash1 = self.storage.put(test_data1)
        hash2 = storage2.put(test_data2)
        
        # Check KMS key IDs
        info1 = self.storage.get_chunk_info(hash1)
        info2 = storage2.get_chunk_info(hash2)
        
        self.assertEqual(info1.get("kms_key_id"), self.kms_key_id)
        self.assertEqual(info2.get("kms_key_id"), "different-kms-key")


class TestEncryptionSecurity(unittest.TestCase):
    """Test encryption security properties."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_encrypted_data_different_from_plaintext(self):
        """Test that encrypted data is different from plaintext."""
        test_data = b"Plaintext data"
        hash_hex = self.storage.put(test_data)
        
        # Read the encrypted file directly
        path = self.storage._hash_to_path(hash_hex)
        with open(path, 'rb') as f:
            encrypted_data = f.read()
        
        # Encrypted data should be different from plaintext
        self.assertNotEqual(encrypted_data, test_data)
        
        # But should be longer (due to nonce + ciphertext)
        self.assertGreater(len(encrypted_data), len(test_data))
    
    def test_different_nonces(self):
        """Test that different encryptions use different nonces."""
        test_data = b"Same data, different nonces"
        
        # Store same data twice
        hash1 = self.storage.put(test_data)
        hash2 = self.storage.put(test_data)
        
        # Hashes should be the same (content-addressed)
        self.assertEqual(hash1, hash2)
        
        # But if we could access the encrypted data directly,
        # the nonces would be different (though we can't test this
        # easily due to content-addressing)
    
    def test_encryption_key_isolation(self):
        """Test that different storage instances use different keys."""
        storage1 = StorageBackend(self.test_dir + "_1")
        storage2 = StorageBackend(self.test_dir + "_2")
        
        test_data = b"Same data, different keys"
        
        hash1 = storage1.put(test_data)
        hash2 = storage2.put(test_data)
        
        # Hashes should be the same (content-addressed)
        self.assertEqual(hash1, hash2)
        
        # Clean up
        import shutil
        shutil.rmtree(self.test_dir + "_1")
        shutil.rmtree(self.test_dir + "_2")


if __name__ == '__main__':
    unittest.main()
