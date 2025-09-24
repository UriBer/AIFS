"""
Test suite for Macaroon-based Authorization in AIFS.

Tests the AuthorizationManager and macaroon implementation according to the AIFS specification.
"""

import unittest
import time
import json
from typing import Set, List, Optional

from aifs.auth import (
    AuthorizationManager, AIFSMacaroon, MacaroonVerifier,
    create_aifs_token, verify_aifs_token, create_namespace_token,
    create_simple_token, verify_simple_token, MACAROON_AVAILABLE
)


class TestAIFSMacaroon(unittest.TestCase):
    """Test the AIFSMacaroon implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.location = "test.aifs.local"
        self.key = "test_secret_key"
        self.identifier = "test_macaroon"
    
    def test_macaroon_creation(self):
        """Test basic macaroon creation."""
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        
        self.assertEqual(macaroon.location, self.location)
        self.assertEqual(macaroon.identifier, self.identifier)
        self.assertIsNotNone(macaroon.signature)
    
    def test_first_party_caveats(self):
        """Test adding first-party caveats."""
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        
        # Add permission caveat
        macaroon.add_first_party_caveat("method = put")
        macaroon.add_first_party_caveat("namespace = test_namespace")
        
        # Verify caveats were added
        if not MACAROON_AVAILABLE:
            self.assertEqual(len(macaroon.caveats), 2)
            self.assertIn(("first_party", "method = put"), macaroon.caveats)
            self.assertIn(("first_party", "namespace = test_namespace"), macaroon.caveats)
    
    def test_third_party_caveats(self):
        """Test adding third-party caveats."""
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        
        # Add third-party caveat
        macaroon.add_third_party_caveat("auth.service.com", "third_party_key", "third_party_id")
        
        # Verify caveat was added
        if not MACAROON_AVAILABLE:
            self.assertEqual(len(macaroon.caveats), 1)
            self.assertEqual(macaroon.caveats[0][0], "third_party")
    
    def test_macaroon_serialization(self):
        """Test macaroon serialization and deserialization."""
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        macaroon.add_first_party_caveat("method = get")
        macaroon.add_first_party_caveat("expires = 1234567890")
        
        # Serialize
        serialized = macaroon.serialize()
        self.assertIsInstance(serialized, str)
        self.assertGreater(len(serialized), 0)
        
        # For fallback mode, verify JSON structure
        if not MACAROON_AVAILABLE:
            data = json.loads(serialized)
            self.assertEqual(data["location"], self.location)
            self.assertEqual(data["identifier"], self.identifier)
            self.assertIn("caveats", data)
            self.assertIn("signature", data)
    
    def test_signature_computation(self):
        """Test signature computation."""
        macaroon1 = AIFSMacaroon(self.location, self.key, self.identifier)
        macaroon2 = AIFSMacaroon(self.location, self.key, self.identifier)
        
        # Same macaroons should have same signature
        self.assertEqual(macaroon1.signature, macaroon2.signature)
        
        # Different caveats should produce different signatures
        macaroon1.add_first_party_caveat("method = put")
        macaroon2.add_first_party_caveat("method = get")
        
        self.assertNotEqual(macaroon1.signature, macaroon2.signature)


class TestMacaroonVerifier(unittest.TestCase):
    """Test the MacaroonVerifier implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.verifier = MacaroonVerifier()
        self.location = "test.aifs.local"
        self.key = "test_secret_key"
        self.identifier = "test_macaroon"
    
    def test_exact_predicate_satisfaction(self):
        """Test exact predicate satisfaction."""
        self.verifier.satisfy_exact("method = put")
        self.verifier.satisfy_exact("namespace = test")
        
        if not MACAROON_AVAILABLE:
            self.assertIn("method = put", self.verifier.predicates)
            self.assertIn("namespace = test", self.verifier.predicates)
    
    def test_macaroon_verification(self):
        """Test macaroon verification."""
        # Create a macaroon with caveats
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        macaroon.add_first_party_caveat("method = put")
        macaroon.add_first_party_caveat("expires = 9999999999")  # Far future
        
        # Verify with correct key
        verifier = MacaroonVerifier()
        verifier.satisfy_exact("method = put")
        
        result = verifier.verify(macaroon, self.key)
        self.assertTrue(result)
        
        # Verify with wrong key
        result = verifier.verify(macaroon, "wrong_key")
        self.assertFalse(result)
    
    def test_expiry_verification(self):
        """Test expiry caveat verification."""
        # Create macaroon with past expiry
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        macaroon.add_first_party_caveat("time < 2020-01-01")  # Past date
        
        verifier = MacaroonVerifier()
        result = verifier.verify(macaroon, self.key)
        self.assertFalse(result)  # Should fail due to expiry
        
        # Create macaroon with future expiry
        macaroon = AIFSMacaroon(self.location, self.key, self.identifier)
        macaroon.add_first_party_caveat("time < 2030-01-01")  # Future date
        
        result = verifier.verify(macaroon, self.key)
        self.assertTrue(result)  # Should pass


class TestAuthorizationManager(unittest.TestCase):
    """Test the AuthorizationManager implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.auth_manager = AuthorizationManager(secret_key="test_secret_key")
    
    def test_authorization_manager_initialization(self):
        """Test AuthorizationManager initialization."""
        self.assertEqual(self.auth_manager.secret_key, "test_secret_key")
        self.assertEqual(self.auth_manager.location, "aifs.local")
        
        # Test with generated key
        auth_manager2 = AuthorizationManager()
        self.assertIsNotNone(auth_manager2.secret_key)
        self.assertGreater(len(auth_manager2.secret_key), 0)
    
    def test_create_macaroon(self):
        """Test macaroon creation with permissions."""
        permissions = ["put", "get", "search"]
        macaroon = self.auth_manager.create_macaroon(
            identifier="test_user",
            permissions=permissions,
            namespace="test_namespace",
            expiry_hours=24
        )
        
        self.assertIsInstance(macaroon, AIFSMacaroon)
        self.assertEqual(macaroon.identifier, "test_user")
        
        # Verify caveats were added
        if not MACAROON_AVAILABLE:
            caveat_strings = [str(c) for c in macaroon.caveats]
            self.assertTrue(any("namespace = test_namespace" in c for c in caveat_strings))
            self.assertTrue(any("method = put" in c for c in caveat_strings))
            self.assertTrue(any("method = get" in c for c in caveat_strings))
            self.assertTrue(any("method = search" in c for c in caveat_strings))
            self.assertTrue(any("expires = " in c for c in caveat_strings))
    
    def test_create_namespace_macaroon(self):
        """Test namespace-restricted macaroon creation."""
        methods = ["put", "get"]
        macaroon = self.auth_manager.create_namespace_macaroon(
            namespace="restricted_namespace",
            methods=methods,
            expiry_hours=12
        )
        
        self.assertIsInstance(macaroon, AIFSMacaroon)
        self.assertEqual(macaroon.identifier, "namespace_restricted_namespace")
        
        # Verify namespace restriction
        if not MACAROON_AVAILABLE:
            caveat_strings = [str(c) for c in macaroon.caveats]
            self.assertTrue(any("namespace = restricted_namespace" in c for c in caveat_strings))
    
    def test_macaroon_verification(self):
        """Test macaroon verification."""
        # Create a macaroon
        macaroon = self.auth_manager.create_macaroon(
            identifier="test_user",
            permissions=["put", "get"],
            namespace="test_namespace",
            expiry_hours=24
        )
        
        serialized = macaroon.serialize()
        
        # Verify with correct permissions
        result = self.auth_manager.verify_macaroon(
            serialized, 
            {"put", "get"}, 
            "test_namespace"
        )
        self.assertTrue(result)
        
        # Verify with insufficient permissions
        result = self.auth_manager.verify_macaroon(
            serialized, 
            {"put", "get", "admin"}, 
            "test_namespace"
        )
        self.assertFalse(result)
        
        # Verify with wrong namespace
        result = self.auth_manager.verify_macaroon(
            serialized, 
            {"put", "get"}, 
            "wrong_namespace"
        )
        self.assertFalse(result)
    
    def test_expired_macaroon_verification(self):
        """Test verification of expired macaroons."""
        # Create a macaroon with very short expiry
        macaroon = self.auth_manager.create_macaroon(
            identifier="test_user",
            permissions=["put"],
            expiry_hours=0  # Expired immediately
        )
        
        serialized = macaroon.serialize()
        
        # Should fail due to expiry
        result = self.auth_manager.verify_macaroon(serialized, {"put"})
        self.assertFalse(result)
    
    def test_delegation_macaroon(self):
        """Test macaroon delegation."""
        # Create parent macaroon
        parent_macaroon = self.auth_manager.create_macaroon(
            identifier="parent",
            permissions=["put", "get"],
            expiry_hours=24
        )
        
        parent_serialized = parent_macaroon.serialize()
        
        # Create delegated macaroon
        delegated = self.auth_manager.create_delegation_macaroon(
            parent_serialized,
            additional_caveats=["method = get"]  # Restrict to get only
        )
        
        self.assertIsInstance(delegated, AIFSMacaroon)
        
        # Verify delegation caveat was added
        if not MACAROON_AVAILABLE:
            caveat_strings = [str(c) for c in delegated.caveats]
            self.assertTrue(any("delegated = true" in c for c in caveat_strings))
    
    def test_get_macaroon_info(self):
        """Test getting macaroon information."""
        macaroon = self.auth_manager.create_macaroon(
            identifier="info_test",
            permissions=["put", "get"],
            namespace="test_namespace"
        )
        
        serialized = macaroon.serialize()
        info = self.auth_manager.get_macaroon_info(serialized)
        
        self.assertIsInstance(info, dict)
        self.assertIn("location", info)
        self.assertIn("identifier", info)
        self.assertIn("caveats", info)
        self.assertIn("signature", info)
        
        if not MACAROON_AVAILABLE:
            self.assertEqual(info["identifier"], "info_test")
            self.assertIn("namespace = test_namespace", str(info["caveats"]))


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for token creation and verification."""
    
    def test_create_aifs_token(self):
        """Test AIFS token creation."""
        permissions = ["put", "get", "search"]
        token = create_aifs_token(permissions, namespace="test_namespace", expiry_hours=12)
        
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
        
        # Verify the token
        result = verify_aifs_token(token, {"put", "get"}, "test_namespace")
        self.assertTrue(result)
        
        # Test with wrong namespace
        result = verify_aifs_token(token, {"put", "get"}, "wrong_namespace")
        self.assertFalse(result)
    
    def test_create_namespace_token(self):
        """Test namespace token creation."""
        methods = ["put", "get"]
        token = create_namespace_token("restricted_namespace", methods, expiry_hours=6)
        
        self.assertIsInstance(token, str)
        
        # Verify the token
        result = verify_aifs_token(token, {"put"}, "restricted_namespace")
        self.assertTrue(result)
        
        # Test with wrong namespace
        result = verify_aifs_token(token, {"put"}, "other_namespace")
        self.assertFalse(result)
    
    def test_legacy_functions(self):
        """Test legacy token functions for backward compatibility."""
        permissions = ["put", "get"]
        token = create_simple_token(permissions, expiry_hours=24)
        
        self.assertIsInstance(token, str)
        
        # Verify using legacy function
        result = verify_simple_token(token, {"put", "get"})
        self.assertTrue(result)
        
        # Verify using new function
        result = verify_aifs_token(token, {"put", "get"})
        self.assertTrue(result)
    
    def test_token_expiry(self):
        """Test token expiry functionality."""
        # Create token with very short expiry
        token = create_aifs_token(["put"], expiry_hours=0)
        
        # Should fail due to expiry
        result = verify_aifs_token(token, {"put"})
        self.assertFalse(result)
        
        # Create token with normal expiry
        token = create_aifs_token(["put"], expiry_hours=24)
        
        # Should pass
        result = verify_aifs_token(token, {"put"})
        self.assertTrue(result)


class TestMacaroonEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.auth_manager = AuthorizationManager()
    
    def test_invalid_macaroon_verification(self):
        """Test verification of invalid macaroons."""
        # Test with invalid JSON
        result = self.auth_manager.verify_macaroon("invalid_json", {"put"})
        self.assertFalse(result)
        
        # Test with empty string
        result = self.auth_manager.verify_macaroon("", {"put"})
        self.assertFalse(result)
        
        # Test with None
        result = self.auth_manager.verify_macaroon(None, {"put"})
        self.assertFalse(result)
    
    def test_macaroon_with_no_permissions(self):
        """Test macaroon with no permissions."""
        macaroon = self.auth_manager.create_macaroon(
            identifier="no_perms",
            permissions=[],
            expiry_hours=24
        )
        
        serialized = macaroon.serialize()
        
        # Should fail for any required permissions
        result = self.auth_manager.verify_macaroon(serialized, {"put"})
        self.assertFalse(result)
        
        # Should pass for no required permissions
        result = self.auth_manager.verify_macaroon(serialized, set())
        self.assertTrue(result)
    
    def test_macaroon_with_malformed_caveats(self):
        """Test macaroon with malformed caveats."""
        if not MACAROON_AVAILABLE:
            # Create macaroon with malformed expiry
            macaroon = AIFSMacaroon("test", "key", "test")
            macaroon.add_first_party_caveat("expires = invalid_timestamp")
            
            serialized = macaroon.serialize()
            
            # Should handle malformed caveats gracefully
            result = self.auth_manager.verify_macaroon(serialized, {"put"})
            # Behavior depends on implementation, but should not crash
            self.assertIsInstance(result, bool)
    
    def test_large_macaroon(self):
        """Test macaroon with many caveats."""
        permissions = [f"method_{i}" for i in range(100)]
        macaroon = self.auth_manager.create_macaroon(
            identifier="large_macaroon",
            permissions=permissions,
            expiry_hours=24
        )
        
        serialized = macaroon.serialize()
        
        # Should still work with many caveats
        result = self.auth_manager.verify_macaroon(serialized, {"method_0"})
        self.assertTrue(result)
        
        # Should fail for non-existent method
        result = self.auth_manager.verify_macaroon(serialized, {"nonexistent_method"})
        self.assertFalse(result)


class TestMacaroonPerformance(unittest.TestCase):
    """Test macaroon performance characteristics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.auth_manager = AuthorizationManager()
    
    def test_macaroon_creation_performance(self):
        """Test macaroon creation performance."""
        import time
        
        start_time = time.time()
        
        # Create many macaroons
        for i in range(100):
            macaroon = self.auth_manager.create_macaroon(
                identifier=f"perf_test_{i}",
                permissions=["put", "get", "search"],
                expiry_hours=24
            )
            serialized = macaroon.serialize()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 100 macaroons)
        self.assertLess(duration, 1.0)
    
    def test_macaroon_verification_performance(self):
        """Test macaroon verification performance."""
        import time
        
        # Create a macaroon
        macaroon = self.auth_manager.create_macaroon(
            identifier="perf_test",
            permissions=["put", "get", "search"],
            expiry_hours=24
        )
        serialized = macaroon.serialize()
        
        start_time = time.time()
        
        # Verify many times
        for i in range(1000):
            result = self.auth_manager.verify_macaroon(serialized, {"put", "get"})
            self.assertTrue(result)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 1000 verifications)
        self.assertLess(duration, 1.0)


if __name__ == '__main__':
    unittest.main()
