"""Tests for Ed25519 Signature Implementation

Tests the Ed25519 signature generation and verification functionality
according to the AIFS architecture specification.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime

from aifs.crypto import CryptoManager
from aifs.metadata import MetadataStore
from aifs.asset import AssetManager


class TestCryptoManager(unittest.TestCase):
    """Test the CryptoManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.key_db_path = os.path.join(self.temp_dir, "keys.db")
        self.crypto_manager = CryptoManager(key_db_path=self.key_db_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_key_generation(self):
        """Test Ed25519 key pair generation."""
        # Test that we can generate a key pair
        private_key, public_key = CryptoManager.generate_key_pair()
        
        self.assertEqual(len(private_key), 32)
        self.assertEqual(len(public_key), 32)
        
        # Test that we can create a crypto manager with the private key
        crypto_manager = CryptoManager(private_key)
        self.assertEqual(bytes(crypto_manager.verify_key), public_key)
    
    def test_key_from_seed(self):
        """Test generating Ed25519 key from seed."""
        seed = b"test_seed_32_bytes_long_exactly!"
        self.assertEqual(len(seed), 32)
        
        private_key = CryptoManager.key_from_seed(seed)
        self.assertEqual(len(private_key), 32)
        
        # Test that the same seed produces the same key
        private_key2 = CryptoManager.key_from_seed(seed)
        self.assertEqual(private_key, private_key2)
    
    def test_signature_generation(self):
        """Test Ed25519 signature generation."""
        merkle_root = "abc123def456"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "test_namespace"
        
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        self.assertEqual(len(signature_bytes), 64)  # Ed25519 signature length
        self.assertEqual(len(signature_hex), 128)   # 64 bytes * 2 hex chars
        self.assertEqual(signature_bytes.hex(), signature_hex)
    
    def test_signature_verification(self):
        """Test Ed25519 signature verification."""
        merkle_root = "abc123def456"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "test_namespace"
        
        # Sign the snapshot
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Verify with bytes
        public_key = self.crypto_manager.get_public_key()
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(result)
        
        # Verify with hex string
        result = self.crypto_manager.verify_snapshot_signature(
            signature_hex, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(result)
    
    def test_signature_verification_failure(self):
        """Test Ed25519 signature verification failure."""
        merkle_root = "abc123def456"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "test_namespace"
        
        # Sign the snapshot
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        public_key = self.crypto_manager.get_public_key()
        
        # Test with wrong merkle root
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, "wrong_root", timestamp, namespace, public_key
        )
        self.assertFalse(result)
        
        # Test with wrong timestamp
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, "wrong_timestamp", namespace, public_key
        )
        self.assertFalse(result)
        
        # Test with wrong namespace
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, "wrong_namespace", public_key
        )
        self.assertFalse(result)
    
    def test_namespace_key_management(self):
        """Test namespace-based key management."""
        namespace = "test_namespace"
        metadata = {"description": "Test namespace"}
        
        # Register namespace key
        public_key_hex = self.crypto_manager.register_namespace_key(namespace, metadata)
        self.assertIsNotNone(public_key_hex)
        
        # Retrieve namespace key
        retrieved_key = self.crypto_manager.get_namespace_key(namespace)
        self.assertEqual(retrieved_key, public_key_hex)
        
        # List namespace keys
        keys = self.crypto_manager.list_namespace_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["namespace"], namespace)
        self.assertEqual(keys[0]["public_key_hex"], public_key_hex)
        self.assertEqual(keys[0]["metadata"], metadata)
    
    def test_trusted_key_management(self):
        """Test trusted key management."""
        key_id = "trusted_key_1"
        public_key_hex = self.crypto_manager.get_public_key_hex()
        namespace = "test_namespace"
        metadata = {"description": "Trusted key for testing"}
        
        # Pin trusted key
        self.crypto_manager.pin_trusted_key(key_id, public_key_hex, namespace, metadata)
        
        # Retrieve trusted key
        retrieved_key = self.crypto_manager.get_trusted_key(key_id)
        self.assertEqual(retrieved_key, public_key_hex)
        
        # List trusted keys
        keys = self.crypto_manager.list_trusted_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["key_id"], key_id)
        self.assertEqual(keys[0]["public_key_hex"], public_key_hex)
        self.assertEqual(keys[0]["namespace"], namespace)
        self.assertEqual(keys[0]["metadata"], metadata)
    
    def test_namespace_signature_verification(self):
        """Test signature verification using namespace keys."""
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        timestamp = "2024-01-01T12:00:00Z"
        
        # Register namespace key
        self.crypto_manager.register_namespace_key(namespace)
        
        # Sign snapshot
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Verify using namespace key
        result = self.crypto_manager.verify_snapshot_with_namespace_key(
            signature_hex, merkle_root, timestamp, namespace
        )
        self.assertTrue(result)
    
    def test_trusted_key_signature_verification(self):
        """Test signature verification using trusted keys."""
        key_id = "trusted_key_1"
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        timestamp = "2024-01-01T12:00:00Z"
        
        # Pin trusted key
        public_key_hex = self.crypto_manager.get_public_key_hex()
        self.crypto_manager.pin_trusted_key(key_id, public_key_hex, namespace)
        
        # Sign snapshot
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Verify using trusted key
        result = self.crypto_manager.verify_snapshot_with_trusted_key(
            signature_hex, merkle_root, timestamp, namespace, key_id
        )
        self.assertTrue(result)


class TestMetadataStoreEd25519(unittest.TestCase):
    """Test MetadataStore with Ed25519 integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.metadata_db_path = os.path.join(self.temp_dir, "metadata.db")
        self.key_db_path = os.path.join(self.temp_dir, "keys.db")
        
        self.crypto_manager = CryptoManager(key_db_path=self.key_db_path)
        self.metadata_store = MetadataStore(self.metadata_db_path, self.crypto_manager)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_snapshot_creation_with_auto_sign(self):
        """Test snapshot creation with automatic signing."""
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        metadata = {"description": "Test snapshot"}
        
        # Create snapshot with auto-signing
        snapshot_id = self.metadata_store.create_snapshot(
            namespace, merkle_root, metadata, auto_sign=True
        )
        
        self.assertIsNotNone(snapshot_id)
        
        # Verify the snapshot was created
        snapshot = self.metadata_store.get_snapshot(snapshot_id)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["namespace"], namespace)
        self.assertEqual(snapshot["merkle_root"], merkle_root)
        self.assertIsNotNone(snapshot["signature"])
        
        # Verify the signature is valid
        self.assertTrue(self.metadata_store.verify_snapshot_signature(snapshot_id))
    
    def test_snapshot_creation_without_auto_sign(self):
        """Test snapshot creation without automatic signing."""
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        metadata = {"description": "Test snapshot"}
        
        # Create snapshot without auto-signing
        snapshot_id = self.metadata_store.create_snapshot(
            namespace, merkle_root, metadata, auto_sign=False
        )
        
        self.assertIsNotNone(snapshot_id)
        
        # Verify the snapshot was created but not signed
        snapshot = self.metadata_store.get_snapshot(snapshot_id)
        self.assertIsNotNone(snapshot)
        self.assertIsNone(snapshot["signature"])
        
        # Verify signature verification fails
        self.assertFalse(self.metadata_store.verify_snapshot_signature(snapshot_id))
    
    def test_snapshot_creation_with_precomputed_signature(self):
        """Test snapshot creation with precomputed signature."""
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        metadata = {"description": "Test snapshot"}
        timestamp = "2024-01-01T12:00:00Z"
        
        # Precompute signature
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Create snapshot with precomputed signature
        snapshot_id = self.metadata_store.create_snapshot(
            namespace, merkle_root, metadata, signature=signature_hex, 
            created_at=timestamp, auto_sign=False
        )
        
        self.assertIsNotNone(snapshot_id)
        
        # Verify the signature is valid
        self.assertTrue(self.metadata_store.verify_snapshot_signature(snapshot_id))
    
    def test_verified_snapshot_retrieval(self):
        """Test retrieval of verified snapshots only."""
        namespace = "test_namespace"
        merkle_root = "abc123def456"
        
        # Create signed snapshot
        snapshot_id1 = self.metadata_store.create_snapshot(
            namespace, merkle_root, auto_sign=True
        )
        
        # Create unsigned snapshot
        snapshot_id2 = self.metadata_store.create_snapshot(
            namespace, merkle_root + "_unsigned", auto_sign=False
        )
        
        # Test get_verified_snapshot
        verified_snapshot = self.metadata_store.get_verified_snapshot(snapshot_id1)
        self.assertIsNotNone(verified_snapshot)
        self.assertEqual(verified_snapshot["snapshot_id"], snapshot_id1)
        
        # Test that unsigned snapshot is not returned
        verified_snapshot = self.metadata_store.get_verified_snapshot(snapshot_id2)
        self.assertIsNone(verified_snapshot)
    
    def test_list_verified_snapshots(self):
        """Test listing of verified snapshots only."""
        namespace = "test_namespace"
        
        # Create multiple snapshots (some signed, some unsigned)
        signed_snapshots = []
        for i in range(3):
            snapshot_id = self.metadata_store.create_snapshot(
                namespace, f"merkle_root_{i}", auto_sign=True
            )
            signed_snapshots.append(snapshot_id)
        
        unsigned_snapshots = []
        for i in range(2):
            snapshot_id = self.metadata_store.create_snapshot(
                namespace, f"unsigned_root_{i}", auto_sign=False
            )
            unsigned_snapshots.append(snapshot_id)
        
        # List verified snapshots
        verified_snapshots = self.metadata_store.list_verified_snapshots(namespace)
        
        # Should only return signed snapshots
        self.assertEqual(len(verified_snapshots), 3)
        verified_ids = [s["snapshot_id"] for s in verified_snapshots]
        
        for signed_id in signed_snapshots:
            self.assertIn(signed_id, verified_ids)
        
        for unsigned_id in unsigned_snapshots:
            self.assertNotIn(unsigned_id, verified_ids)


class TestAssetManagerEd25519(unittest.TestCase):
    """Test AssetManager with Ed25519 integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir, enable_strong_causality=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_namespace_key_registration(self):
        """Test namespace key registration through AssetManager."""
        namespace = "test_namespace"
        metadata = {"description": "Test namespace"}
        
        # Register namespace key
        public_key_hex = self.asset_manager.register_namespace_key(namespace, metadata)
        self.assertIsNotNone(public_key_hex)
        
        # Retrieve namespace key
        retrieved_key = self.asset_manager.get_namespace_key(namespace)
        self.assertEqual(retrieved_key, public_key_hex)
        
        # List namespace keys
        keys = self.asset_manager.list_namespace_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["namespace"], namespace)
    
    def test_trusted_key_management(self):
        """Test trusted key management through AssetManager."""
        key_id = "trusted_key_1"
        namespace = "test_namespace"
        metadata = {"description": "Trusted key"}
        
        # Get current public key
        public_key_hex = self.asset_manager.crypto_manager.get_public_key_hex()
        
        # Pin trusted key
        self.asset_manager.pin_trusted_key(key_id, public_key_hex, namespace, metadata)
        
        # List trusted keys
        keys = self.asset_manager.list_trusted_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["key_id"], key_id)
        self.assertEqual(keys[0]["namespace"], namespace)
    
    def test_snapshot_creation_with_signature(self):
        """Test snapshot creation with automatic signing."""
        namespace = "test_namespace"
        
        # Create some assets first
        asset_id1 = self.asset_manager.put_asset(b"test data 1")
        asset_id2 = self.asset_manager.put_asset(b"test data 2")
        
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(namespace, [asset_id1, asset_id2])
        
        self.assertIsNotNone(snapshot_id)
        
        # Verify signature
        self.assertTrue(self.asset_manager.verify_snapshot_signature(snapshot_id))
        
        # Get verified snapshot
        verified_snapshot = self.asset_manager.get_verified_snapshot(snapshot_id)
        self.assertIsNotNone(verified_snapshot)
        self.assertEqual(verified_snapshot["snapshot_id"], snapshot_id)
    
    def test_snapshot_verification_before_exposure(self):
        """Test that snapshots are only exposed if signatures are valid."""
        namespace = "test_namespace"
        
        # Create assets
        asset_id = self.asset_manager.put_asset(b"test data")
        
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(namespace, [asset_id])
        
        # Test verified snapshot listing
        verified_snapshots = self.asset_manager.list_verified_snapshots(namespace)
        self.assertEqual(len(verified_snapshots), 1)
        self.assertEqual(verified_snapshots[0]["snapshot_id"], snapshot_id)
        
        # Test that get_verified_snapshot only returns valid snapshots
        verified_snapshot = self.asset_manager.get_verified_snapshot(snapshot_id)
        self.assertIsNotNone(verified_snapshot)
        
        # Test with invalid snapshot ID
        invalid_snapshot = self.asset_manager.get_verified_snapshot("invalid_id")
        self.assertIsNone(invalid_snapshot)


class TestEd25519EdgeCases(unittest.TestCase):
    """Test edge cases for Ed25519 implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.crypto_manager = CryptoManager()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_empty_message_signature(self):
        """Test signing and verification of empty messages."""
        merkle_root = ""
        timestamp = ""
        namespace = ""
        
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        public_key = self.crypto_manager.get_public_key()
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(result)
    
    def test_very_long_message_signature(self):
        """Test signing and verification of very long messages."""
        merkle_root = "a" * 1000
        timestamp = "b" * 1000
        namespace = "c" * 1000
        
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        public_key = self.crypto_manager.get_public_key()
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(result)
    
    def test_unicode_message_signature(self):
        """Test signing and verification of Unicode messages."""
        merkle_root = "测试中文"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "测试命名空间"
        
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        public_key = self.crypto_manager.get_public_key()
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(result)
    
    def test_invalid_signature_format(self):
        """Test handling of invalid signature formats."""
        merkle_root = "abc123"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "test"
        public_key = self.crypto_manager.get_public_key()
        
        # Test with invalid hex string
        result = self.crypto_manager.verify_snapshot_signature(
            "invalid_hex", merkle_root, timestamp, namespace, public_key
        )
        self.assertFalse(result)
        
        # Test with wrong length signature
        result = self.crypto_manager.verify_snapshot_signature(
            "a" * 64, merkle_root, timestamp, namespace, public_key
        )
        self.assertFalse(result)
    
    def test_invalid_public_key(self):
        """Test handling of invalid public keys."""
        merkle_root = "abc123"
        timestamp = "2024-01-01T12:00:00Z"
        namespace = "test"
        
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Test with invalid public key
        invalid_public_key = b"invalid_key"
        result = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, invalid_public_key
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
