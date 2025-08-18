#!/usr/bin/env python3
"""Tests for AIFS Cryptographic Functions."""

import unittest
import tempfile
import os
from pathlib import Path

# Import AIFS components
from aifs.crypto import CryptoManager


class TestCryptoManager(unittest.TestCase):
    """Test cryptographic functionality."""

    def setUp(self):
        """Set up test environment."""
        self.crypto_manager = CryptoManager()

    def test_key_generation(self):
        """Test Ed25519 key generation."""
        # Test that we can get public key
        public_key = self.crypto_manager.get_public_key()
        self.assertIsInstance(public_key, bytes)
        self.assertEqual(len(public_key), 32)  # Ed25519 public key is 32 bytes
        
        # Test hex representation
        public_key_hex = self.crypto_manager.get_public_key_hex()
        self.assertIsInstance(public_key_hex, str)
        self.assertEqual(len(public_key_hex), 64)  # 32 bytes = 64 hex chars

    def test_snapshot_signing(self):
        """Test snapshot signing and verification."""
        merkle_root = "a" * 64
        timestamp = "2025-01-01T00:00:00"
        namespace = "test-namespace"
        
        # Sign snapshot
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        self.assertIsInstance(signature_bytes, bytes)
        self.assertIsInstance(signature_hex, str)
        self.assertEqual(len(signature_bytes), 64)  # Ed25519 signature is 64 bytes
        
        # Verify signature
        public_key = self.crypto_manager.get_public_key()
        is_valid = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(is_valid)

    def test_snapshot_verification_failure(self):
        """Test snapshot signature verification failure cases."""
        merkle_root = "a" * 64
        timestamp = "2025-01-01T00:00:00"
        namespace = "test-namespace"
        
        # Sign snapshot
        signature_bytes, _ = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        public_key = self.crypto_manager.get_public_key()
        
        # Test wrong merkle root
        wrong_root = "b" * 64
        is_valid = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, wrong_root, timestamp, namespace, public_key
        )
        self.assertFalse(is_valid)
        
        # Test wrong timestamp
        wrong_timestamp = "2025-01-02T00:00:00"
        is_valid = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, wrong_timestamp, namespace, public_key
        )
        self.assertFalse(is_valid)
        
        # Test wrong namespace
        wrong_namespace = "wrong-namespace"
        is_valid = self.crypto_manager.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, wrong_namespace, public_key
        )
        self.assertFalse(is_valid)

    def test_asset_signing(self):
        """Test asset signing and verification."""
        asset_id = "a" * 64
        metadata = "test-metadata"
        
        # Sign asset
        signature_bytes, signature_hex = self.crypto_manager.sign_asset_id(
            asset_id, metadata
        )
        
        self.assertIsInstance(signature_bytes, bytes)
        self.assertIsInstance(signature_hex, str)
        self.assertEqual(len(signature_bytes), 64)
        
        # Verify signature
        public_key = self.crypto_manager.get_public_key()
        is_valid = self.crypto_manager.verify_asset_signature(
            signature_bytes, asset_id, metadata, public_key
        )
        self.assertTrue(is_valid)

    def test_asset_verification_failure(self):
        """Test asset signature verification failure cases."""
        asset_id = "a" * 64
        metadata = "test-metadata"
        
        # Sign asset
        signature_bytes, _ = self.crypto_manager.sign_asset_id(
            asset_id, metadata
        )
        
        public_key = self.crypto_manager.get_public_key()
        
        # Test wrong asset ID
        wrong_asset_id = "b" * 64
        is_valid = self.crypto_manager.verify_asset_signature(
            signature_bytes, wrong_asset_id, metadata, public_key
        )
        self.assertFalse(is_valid)
        
        # Test wrong metadata
        wrong_metadata = "wrong-metadata"
        is_valid = self.crypto_manager.verify_asset_signature(
            signature_bytes, asset_id, wrong_metadata, public_key
        )
        self.assertFalse(is_valid)

    def test_static_key_generation(self):
        """Test static key generation methods."""
        # Test generate_key_pair
        private_key, public_key = CryptoManager.generate_key_pair()
        self.assertIsInstance(private_key, bytes)
        self.assertIsInstance(public_key, bytes)
        self.assertEqual(len(private_key), 32)
        self.assertEqual(len(public_key), 32)
        
        # Test key_from_seed
        seed = b"test-seed-32-bytes-long-string!!"
        derived_key = CryptoManager.key_from_seed(seed)
        self.assertIsInstance(derived_key, bytes)
        self.assertEqual(len(derived_key), 32)

    def test_seed_validation(self):
        """Test seed validation for key generation."""
        # Test wrong seed length
        wrong_seed = b"too-short"
        with self.assertRaises(ValueError):
            CryptoManager.key_from_seed(wrong_seed)

    def test_custom_private_key(self):
        """Test using a custom private key."""
        # Generate a key pair
        private_key, public_key = CryptoManager.generate_key_pair()
        
        # Create crypto manager with custom key
        custom_crypto = CryptoManager(private_key)
        
        # Verify it uses the same public key
        self.assertEqual(custom_crypto.get_public_key(), public_key)
        
        # Test signing works
        merkle_root = "a" * 64
        timestamp = "2025-01-01T00:00:00"
        namespace = "test-namespace"
        
        signature_bytes, _ = custom_crypto.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Verify with original public key
        is_valid = custom_crypto.verify_snapshot_signature(
            signature_bytes, merkle_root, timestamp, namespace, public_key
        )
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
