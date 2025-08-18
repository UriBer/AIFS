#!/usr/bin/env python3
"""Tests for AIFS Authorization System."""

import unittest
import time
from unittest.mock import patch

from aifs.auth import (
    AIFSMacaroon, MacaroonVerifier, AuthorizationManager,
    create_simple_token, verify_simple_token
)


class TestAIFSAuthorization(unittest.TestCase):
    """Test cases for AIFS authorization system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.secret_key = "test_secret_key_32_bytes_long"
        self.location = "test-location"
        self.identifier = "test-identifier"
        self.auth_manager = AuthorizationManager(self.secret_key)
    
    def test_macaroon_creation(self):
        """Test basic macaroon creation."""
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read", "write"]
        )
        
        self.assertIsNotNone(macaroon)
        self.assertEqual(macaroon.identifier, self.identifier)
    
    def test_namespace_caveat(self):
        """Test adding namespace caveat."""
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        
        # Add namespace restriction
        macaroon.add_first_party_caveat("namespace = test-namespace")
        
        # Verify the caveat was added
        serialized = macaroon.serialize()
        self.assertIn("test-namespace", serialized)
    
    def test_method_caveat(self):
        """Test adding method caveat."""
        methods = ["put", "get", "search"]
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=methods
        )
        
        # Add method restriction
        macaroon.add_first_party_caveat(f"methods = {','.join(methods)}")
        
        # Verify the caveat was added
        serialized = macaroon.serialize()
        for method in methods:
            self.assertIn(method, serialized)
    
    def test_expiry_caveat(self):
        """Test adding expiry caveat."""
        expiry_timestamp = int(time.time()) + 3600  # 1 hour from now
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        
        # Add expiry caveat
        macaroon.add_first_party_caveat(f"expires = {expiry_timestamp}")
        
        # Verify the caveat was added
        serialized = macaroon.serialize()
        self.assertIn(str(expiry_timestamp), serialized)
    
    def test_asset_caveat(self):
        """Test adding asset caveat."""
        asset_ids = ["asset1", "asset2", "asset3"]
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        
        # Add asset restriction
        macaroon.add_first_party_caveat(f"assets = {','.join(asset_ids)}")
        
        # Verify the caveat was added
        serialized = macaroon.serialize()
        for asset_id in asset_ids:
            self.assertIn(asset_id, serialized)
    
    def test_macaroon_chaining(self):
        """Test macaroon method chaining."""
        macaroon = (self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read", "write"]
        )
        .add_first_party_caveat("namespace = test-namespace")
        .add_first_party_caveat("methods = put,get")
        .add_first_party_caveat("expires = 1234567890"))
        
        self.assertIsNotNone(macaroon)
        serialized = macaroon.serialize()
        self.assertIn("test-namespace", serialized)
        self.assertIn("put,get", serialized)
        self.assertIn("1234567890", serialized)
    
    def test_macaroon_serialization(self):
        """Test macaroon serialization and deserialization."""
        original = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        original.add_first_party_caveat("namespace = test-namespace")
        
        # Serialize
        serialized = original.serialize()
        self.assertIsInstance(serialized, str)
        self.assertIn("test-namespace", serialized)
        
        # Verify we can parse it back
        info = self.auth_manager.get_macaroon_info(serialized)
        self.assertNotIn("error", info)
    
    def test_verifier_basic(self):
        """Test basic macaroon verification."""
        verifier = MacaroonVerifier()
        
        # Create a macaroon with specific permissions
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read", "write"]
        )
        
        # Verify it has the required permissions
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"read", "write"}
        )
        self.assertTrue(is_valid)
    
    def test_verifier_methods(self):
        """Test method verification."""
        verifier = MacaroonVerifier()
        
        # Create a macaroon with specific methods
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["put", "get"]
        )
        macaroon.add_first_party_caveat("methods = put,get")
        
        # Verify it allows the required methods
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"put"}
        )
        self.assertTrue(is_valid)
    
    def test_verifier_namespace(self):
        """Test namespace verification."""
        verifier = MacaroonVerifier()
        
        # Create a macaroon with namespace restriction
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        macaroon.add_first_party_caveat("namespace = test-namespace")
        
        # Verify it's valid for the namespace
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"read"}
        )
        self.assertTrue(is_valid)
    
    def test_verifier_expiry(self):
        """Test expiry verification."""
        verifier = MacaroonVerifier()
        
        # Create a macaroon with future expiry
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        future_time = time.strftime("%Y-%m-%d", time.localtime(time.time() + 3600))
        macaroon.add_first_party_caveat(f"time < {future_time}")
        
        # Verify it's valid (not expired)
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"read"}
        )
        self.assertTrue(is_valid)
    
    def test_authorization_manager(self):
        """Test authorization manager."""
        # Test creating macaroon with permissions
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read", "write"],
            expiry_hours=1
        )
        
        self.assertIsNotNone(macaroon)
        self.assertEqual(macaroon.identifier, self.identifier)
        
        # Test verification
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"read"}
        )
        self.assertTrue(is_valid)
    
    def test_operation_verification(self):
        """Test operation verification."""
        # Create a macaroon with specific permissions
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["put", "get"]
        )
        
        # Verify it allows the required operations
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"put", "get"}
        )
        self.assertTrue(is_valid)
        
        # Verify it doesn't allow unauthorized operations
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"delete"}
        )
        self.assertFalse(is_valid)
    
    def test_macaroon_without_caveats(self):
        """Test macaroon without restrictions."""
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        
        # Should be valid for basic operations
        is_valid = self.auth_manager.verify_macaroon(
            macaroon.serialize(),
            {"read"}
        )
        self.assertTrue(is_valid)
    
    def test_invalid_macaroon(self):
        """Test handling of invalid macaroons."""
        # Test with invalid serialized data
        is_allowed = self.auth_manager.verify_macaroon(
            "invalid_macaroon_data",
            {"read"}
        )
        self.assertFalse(is_allowed)
    
    def test_simple_token_fallback(self):
        """Test simple token fallback when macaroon is not available."""
        # Test token creation
        token = create_simple_token(["read", "write"], expiry_hours=1)
        self.assertIsInstance(token, str)
        
        # Test token verification
        is_valid = verify_simple_token(token, {"read"})
        self.assertTrue(is_valid)
        
        # Test expired token
        expired_token = create_simple_token(["read"], expiry_hours=0)
        time.sleep(0.1)  # Ensure token is expired
        is_valid = verify_simple_token(expired_token, {"read"})
        self.assertFalse(is_valid)
    
    def test_macaroon_info(self):
        """Test getting macaroon information."""
        macaroon = self.auth_manager.create_macaroon(
            identifier=self.identifier,
            permissions=["read"]
        )
        macaroon.add_first_party_caveat("namespace = test-namespace")
        
        info = self.auth_manager.get_macaroon_info(macaroon.serialize())
        self.assertNotIn("error", info)
        self.assertEqual(info["identifier"], self.identifier)


if __name__ == "__main__":
    unittest.main()
