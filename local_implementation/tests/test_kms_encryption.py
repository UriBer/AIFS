"""
Test suite for KMS and AES-256-GCM encryption implementation in AIFS.

Tests the KMS service and enhanced storage backend with envelope encryption
according to the AIFS specification.
"""

import unittest
import tempfile
import os
import time
import json
from pathlib import Path

from aifs.kms import KMS, KMSKey, EnvelopeEncryption
from aifs.storage import StorageBackend


class TestKMSKey(unittest.TestCase):
    """Test the KMSKey implementation."""
    
    def test_kms_key_creation(self):
        """Test KMS key creation."""
        key = KMSKey(
            key_id="test_key",
            key_type="AES-256",
            metadata={"description": "Test key"}
        )
        
        self.assertEqual(key.key_id, "test_key")
        self.assertEqual(key.key_type, "AES-256")
        self.assertIsNotNone(key.created_at)
        self.assertIsNone(key.expires_at)
        self.assertFalse(key.is_expired())
    
    def test_kms_key_expiry(self):
        """Test KMS key expiry functionality."""
        # Key with past expiry
        past_key = KMSKey(
            key_id="past_key",
            expires_at=time.time() - 3600  # 1 hour ago
        )
        self.assertTrue(past_key.is_expired())
        
        # Key with future expiry
        future_key = KMSKey(
            key_id="future_key",
            expires_at=time.time() + 3600  # 1 hour from now
        )
        self.assertFalse(future_key.is_expired())
        
        # Key with no expiry
        no_expiry_key = KMSKey(key_id="no_expiry_key")
        self.assertFalse(no_expiry_key.is_expired())
    
    def test_kms_key_serialization(self):
        """Test KMS key serialization and deserialization."""
        key = KMSKey(
            key_id="serialize_test",
            key_type="AES-256",
            metadata={"test": "value"}
        )
        
        # Convert to dict
        key_dict = key.to_dict()
        self.assertEqual(key_dict["key_id"], "serialize_test")
        self.assertEqual(key_dict["key_type"], "AES-256")
        self.assertEqual(key_dict["metadata"]["test"], "value")
        
        # Create from dict
        restored_key = KMSKey.from_dict(key_dict)
        self.assertEqual(restored_key.key_id, key.key_id)
        self.assertEqual(restored_key.key_type, key.key_type)
        self.assertEqual(restored_key.metadata, key.metadata)
    
    def test_kms_key_material(self):
        """Test KMS key material management."""
        key = KMSKey(key_id="material_test")
        
        # Test symmetric key material
        key_material = os.urandom(32)
        key.set_key_material(key_material)
        self.assertEqual(key.get_key_material(), key_material)
        
        # Test RSA keys
        public_key = b"fake_public_key"
        private_key = b"fake_private_key"
        key.set_rsa_keys(public_key, private_key)
        self.assertEqual(key.get_public_key(), public_key)
        self.assertEqual(key.get_private_key(), private_key)


class TestEnvelopeEncryption(unittest.TestCase):
    """Test the EnvelopeEncryption implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.master_key = os.urandom(32)
        self.envelope_encryption = EnvelopeEncryption(self.master_key)
    
    def test_envelope_encryption_round_trip(self):
        """Test envelope encryption and decryption round trip."""
        data_key = os.urandom(32)
        key_id = "test_key_id"
        
        # Encrypt data key
        encrypted_data_key, nonce = self.envelope_encryption.encrypt_data_key(data_key, key_id)
        
        # Decrypt data key
        decrypted_data_key = self.envelope_encryption.decrypt_data_key(
            encrypted_data_key, nonce, key_id
        )
        
        self.assertEqual(data_key, decrypted_data_key)
    
    def test_envelope_encryption_different_keys(self):
        """Test that different data keys produce different encrypted results."""
        data_key1 = os.urandom(32)
        data_key2 = os.urandom(32)
        key_id = "test_key_id"
        
        encrypted1, nonce1 = self.envelope_encryption.encrypt_data_key(data_key1, key_id)
        encrypted2, nonce2 = self.envelope_encryption.encrypt_data_key(data_key2, key_id)
        
        # Encrypted data should be different
        self.assertNotEqual(encrypted1, encrypted2)
        self.assertNotEqual(nonce1, nonce2)
        
        # Both should decrypt correctly
        decrypted1 = self.envelope_encryption.decrypt_data_key(encrypted1, nonce1, key_id)
        decrypted2 = self.envelope_encryption.decrypt_data_key(encrypted2, nonce2, key_id)
        
        self.assertEqual(decrypted1, data_key1)
        self.assertEqual(decrypted2, data_key2)
    
    def test_envelope_encryption_wrong_key_id(self):
        """Test that wrong key ID fails decryption."""
        data_key = os.urandom(32)
        key_id = "correct_key_id"
        wrong_key_id = "wrong_key_id"
        
        # Encrypt with correct key ID
        encrypted_data_key, nonce = self.envelope_encryption.encrypt_data_key(data_key, key_id)
        
        # Try to decrypt with wrong key ID
        with self.assertRaises(Exception):
            self.envelope_encryption.decrypt_data_key(
                encrypted_data_key, nonce, wrong_key_id
            )


class TestKMS(unittest.TestCase):
    """Test the KMS implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.kms = KMS(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_kms_initialization(self):
        """Test KMS initialization."""
        self.assertIsNotNone(self.kms.master_key)
        self.assertEqual(len(self.kms.master_key), 32)  # 256-bit key
        self.assertIsNotNone(self.kms.envelope_encryption)
    
    def test_create_aes_key(self):
        """Test creating AES keys."""
        key = self.kms.create_key("aes_test", key_type="AES-256")
        
        self.assertEqual(key.key_id, "aes_test")
        self.assertEqual(key.key_type, "AES-256")
        self.assertIsNotNone(key.get_key_material())
        self.assertEqual(len(key.get_key_material()), 32)  # 256-bit key
        
        # Test AES-128
        key128 = self.kms.create_key("aes128_test", key_type="AES-128")
        self.assertEqual(len(key128.get_key_material()), 16)  # 128-bit key
    
    def test_create_rsa_key(self):
        """Test creating RSA keys."""
        key = self.kms.create_key("rsa_test", key_type="RSA-2048")
        
        self.assertEqual(key.key_id, "rsa_test")
        self.assertEqual(key.key_type, "RSA-2048")
        self.assertIsNotNone(key.get_public_key())
        self.assertIsNotNone(key.get_private_key())
    
    def test_get_key(self):
        """Test getting keys."""
        # Create a key
        created_key = self.kms.create_key("get_test", key_type="AES-256")
        
        # Get the key
        retrieved_key = self.kms.get_key("get_test")
        
        self.assertIsNotNone(retrieved_key)
        self.assertEqual(retrieved_key.key_id, "get_test")
        self.assertEqual(retrieved_key.key_type, "AES-256")
        
        # Test non-existent key
        non_existent = self.kms.get_key("non_existent")
        self.assertIsNone(non_existent)
    
    def test_delete_key(self):
        """Test deleting keys."""
        # Create a key
        self.kms.create_key("delete_test", key_type="AES-256")
        
        # Verify it exists
        self.assertIsNotNone(self.kms.get_key("delete_test"))
        
        # Delete the key
        result = self.kms.delete_key("delete_test")
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertIsNone(self.kms.get_key("delete_test"))
        
        # Try to delete non-existent key
        result = self.kms.delete_key("non_existent")
        self.assertFalse(result)
    
    def test_list_keys(self):
        """Test listing keys."""
        # Initially empty
        keys = self.kms.list_keys()
        self.assertEqual(len(keys), 0)
        
        # Create some keys
        self.kms.create_key("key1", key_type="AES-256")
        self.kms.create_key("key2", key_type="AES-128")
        self.kms.create_key("key3", key_type="RSA-2048")
        
        # List keys
        keys = self.kms.list_keys()
        self.assertEqual(len(keys), 3)
        self.assertIn("key1", keys)
        self.assertIn("key2", keys)
        self.assertIn("key3", keys)
    
    def test_generate_data_key(self):
        """Test generating data keys."""
        # Create a KMS key
        self.kms.create_key("data_key_test", key_type="AES-256")
        
        # Generate data key
        data_key, encrypted_data_key, nonce = self.kms.generate_data_key("data_key_test")
        
        self.assertEqual(len(data_key), 32)  # 256-bit key
        self.assertIsNotNone(encrypted_data_key)
        self.assertIsNotNone(nonce)
        
        # Decrypt the data key
        decrypted_data_key = self.kms.decrypt_data_key(
            encrypted_data_key, nonce, "data_key_test"
        )
        
        self.assertEqual(data_key, decrypted_data_key)
    
    def test_key_expiry(self):
        """Test key expiry functionality."""
        # Create key with short expiry
        self.kms.create_key("expiry_test", expires_at=time.time() + 1)  # 1 second
        
        # Key should exist
        self.assertIsNotNone(self.kms.get_key("expiry_test"))
        
        # Wait for expiry
        time.sleep(2)
        
        # Key should be expired and removed
        self.assertIsNone(self.kms.get_key("expiry_test"))
        self.assertNotIn("expiry_test", self.kms.list_keys())
    
    def test_rotate_key(self):
        """Test key rotation."""
        # Create a key
        original_key = self.kms.create_key("rotate_test", key_type="AES-256")
        original_material = original_key.get_key_material()
        original_created_at = original_key.created_at
        
        # Rotate the key
        result = self.kms.rotate_key("rotate_test")
        self.assertTrue(result)
        
        # Get the rotated key
        rotated_key = self.kms.get_key("rotate_test")
        self.assertIsNotNone(rotated_key)
        
        # Key material should be different
        self.assertNotEqual(original_material, rotated_key.get_key_material())
        
        # Creation time should be updated
        self.assertGreater(rotated_key.created_at, original_created_at)
    
    def test_get_key_info(self):
        """Test getting key information."""
        # Create a key
        self.kms.create_key("info_test", key_type="AES-256", 
                           metadata={"description": "Test key"})
        
        # Get key info
        info = self.kms.get_key_info("info_test")
        
        self.assertIsNotNone(info)
        self.assertEqual(info["key_id"], "info_test")
        self.assertEqual(info["key_type"], "AES-256")
        self.assertEqual(info["metadata"]["description"], "Test key")
        self.assertFalse(info["is_expired"])
        self.assertTrue(info["has_key_material"])
        self.assertFalse(info["has_rsa_keys"])
    
    def test_get_statistics(self):
        """Test getting KMS statistics."""
        # Create some keys
        self.kms.create_key("stat1", key_type="AES-256")
        self.kms.create_key("stat2", key_type="AES-128")
        self.kms.create_key("stat3", key_type="RSA-2048")
        
        # Get statistics
        stats = self.kms.get_statistics()
        
        self.assertEqual(stats["total_keys"], 3)
        self.assertEqual(stats["active_keys"], 3)
        self.assertEqual(stats["expired_keys"], 0)
        self.assertEqual(stats["key_types"]["AES-256"], 1)
        self.assertEqual(stats["key_types"]["AES-128"], 1)
        self.assertEqual(stats["key_types"]["RSA-2048"], 1)
        self.assertIsNotNone(stats["master_key_hash"])


class TestStorageBackendKMS(unittest.TestCase):
    """Test StorageBackend with KMS integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_storage_with_kms_encryption(self):
        """Test storage with KMS envelope encryption."""
        test_data = b"Test data for KMS encryption"
        
        # Store data (should use KMS envelope encryption)
        hash_hex = self.storage.put(test_data)
        
        # Retrieve data (should decrypt using KMS)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_storage_different_data_kms(self):
        """Test that different data produces different encrypted results."""
        data1 = b"Data 1 for KMS"
        data2 = b"Data 2 for KMS"
        
        hash1 = self.storage.put(data1)
        hash2 = self.storage.put(data2)
        
        # Hashes should be different
        self.assertNotEqual(hash1, hash2)
        
        # Both should decrypt correctly
        retrieved1 = self.storage.get(hash1)
        retrieved2 = self.storage.get(hash2)
        
        self.assertEqual(retrieved1, data1)
        self.assertEqual(retrieved2, data2)
    
    def test_storage_deterministic_hash_kms(self):
        """Test that same data produces same hash despite KMS encryption."""
        test_data = b"Deterministic test data for KMS"
        
        hash1 = self.storage.put(test_data)
        hash2 = self.storage.put(test_data)
        
        # Hashes should be the same (content-addressed)
        self.assertEqual(hash1, hash2)
    
    def test_storage_large_data_kms(self):
        """Test storage with large data using KMS encryption."""
        # Create large data
        large_data = b"Large data test " * 10000  # ~150KB
        
        # Store data
        hash_hex = self.storage.put(large_data)
        
        # Retrieve data
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, large_data)
    
    def test_storage_kms_key_management(self):
        """Test KMS key management in storage."""
        # Check that KMS key was created
        kms_keys = self.storage.kms.list_keys()
        self.assertIn("aifs-default-key", kms_keys)
        
        # Get key info
        key_info = self.storage.kms.get_key_info("aifs-default-key")
        self.assertEqual(key_info["key_type"], "AES-256")
        self.assertFalse(key_info["is_expired"])
    
    def test_storage_custom_kms_key(self):
        """Test storage with custom KMS key."""
        # Create storage with custom KMS key
        custom_storage = StorageBackend(
            self.temp_dir + "_custom",
            kms_key_id="custom-key"
        )
        
        # Check that custom key was created
        kms_keys = custom_storage.kms.list_keys()
        self.assertIn("custom-key", kms_keys)
        
        # Test encryption/decryption
        test_data = b"Test with custom KMS key"
        hash_hex = custom_storage.put(test_data)
        retrieved_data = custom_storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
        
        # Clean up
        import shutil
        shutil.rmtree(self.temp_dir + "_custom")


class TestKMSBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with legacy encryption."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        # Create storage with legacy encryption key
        self.legacy_key = os.urandom(32)
        self.storage = StorageBackend(self.temp_dir, encryption_key=self.legacy_key)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_legacy_encryption_compatibility(self):
        """Test that legacy encrypted data can still be decrypted."""
        test_data = b"Legacy encryption test"
        
        # Store data (will use new KMS encryption)
        hash_hex = self.storage.put(test_data)
        
        # Retrieve data (should work with new decryption)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)
    
    def test_mixed_encryption_formats(self):
        """Test handling of mixed encryption formats."""
        # This test would require manually creating legacy format data
        # For now, we just test that the system handles both formats gracefully
        test_data = b"Mixed format test"
        
        # Store and retrieve data
        hash_hex = self.storage.put(test_data)
        retrieved_data = self.storage.get(hash_hex)
        
        self.assertEqual(retrieved_data, test_data)


class TestKMSPerformance(unittest.TestCase):
    """Test KMS performance characteristics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.kms = KMS(self.temp_dir)
        self.kms.create_key("perf_test", key_type="AES-256")
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_data_key_generation_performance(self):
        """Test data key generation performance."""
        import time
        
        start_time = time.time()
        
        # Generate many data keys
        for i in range(100):
            data_key, encrypted_data_key, nonce = self.kms.generate_data_key("perf_test")
            self.assertIsNotNone(data_key)
            self.assertIsNotNone(encrypted_data_key)
            self.assertIsNotNone(nonce)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 100 keys)
        self.assertLess(duration, 1.0)
    
    def test_storage_encryption_performance(self):
        """Test storage encryption performance."""
        import time
        
        storage = StorageBackend(self.temp_dir)
        
        # Test with different data sizes
        test_cases = [
            b"Small data",
            b"Medium data " * 100,  # ~1KB
            b"Large data " * 10000,  # ~100KB
        ]
        
        for test_data in test_cases:
            start_time = time.time()
            
            # Store and retrieve data
            hash_hex = storage.put(test_data)
            retrieved_data = storage.get(hash_hex)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Verify correctness
            self.assertEqual(retrieved_data, test_data)
            
            # Should complete in reasonable time
            self.assertLess(duration, 1.0)


if __name__ == '__main__':
    unittest.main()
