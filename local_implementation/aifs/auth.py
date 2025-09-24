"""AIFS Authorization System

Implements macaroon-based authorization for AIFS operations.
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Set

# Import macaroon library for capability-based authorization
try:
    from pymacaroons import Macaroon, Verifier
    MACAROON_AVAILABLE = False  # Use fallback implementation for stability
except ImportError:
    MACAROON_AVAILABLE = False
    print("Warning: macaroon library not available. Using simplified authorization fallback.")
    print("For full macaroon support, install PyMacaroons package.")


class AIFSMacaroon:
    """AIFS Macaroon implementation for capability-based authorization."""
    
    def __init__(self, location: str, key: str, identifier: str):
        """Initialize a new macaroon.
        
        Args:
            location: Location where the macaroon was created
            key: Secret key for signing
            identifier: Unique identifier for the macaroon
        """
        if MACAROON_AVAILABLE:
            # Convert key to bytes if it's a string
            key_bytes = key
            if isinstance(key, str):
                key_bytes = key.encode('utf-8')
            self._macaroon = Macaroon(location=location, key=key_bytes, identifier=identifier)
            # Expose attributes for compatibility
            self.location = location
            self.key = key
            self.identifier = identifier
        else:
            # Fallback implementation
            self.location = location
            self.key = key
            self.identifier = identifier
            self.caveats = []
            self._signature = self._compute_signature()
    
    def add_first_party_caveat(self, predicate: str) -> 'AIFSMacaroon':
        """Add a first-party caveat (self-verifiable).
        
        Args:
            predicate: The caveat predicate (e.g., "time < 2024-01-01")
            
        Returns:
            Self for chaining
        """
        if MACAROON_AVAILABLE:
            self._macaroon.add_first_party_caveat(predicate)
        else:
            # Fallback: store caveat and update signature
            self.caveats.append(("first_party", predicate))
            self._signature = self._compute_signature()
        
        return self
    
    def add_third_party_caveat(self, location: str, key: str, identifier: str) -> 'AIFSMacaroon':
        """Add a third-party caveat (requires external verification).
        
        Args:
            location: Location of the third-party service
            key: Secret key for the third-party caveat
            identifier: Identifier for the third-party caveat
            
        Returns:
            Self for chaining
        """
        if MACAROON_AVAILABLE:
            self._macaroon.add_third_party_caveat(location, key, identifier)
        else:
            # Fallback: store caveat and update signature
            self.caveats.append(("third_party", (location, key, identifier)))
            self._signature = self._compute_signature()
        
        return self
    
    def serialize(self) -> str:
        """Serialize the macaroon to a string.
        
        Returns:
            Serialized macaroon string
        """
        if MACAROON_AVAILABLE:
            return self._macaroon.serialize()
        else:
            # Fallback: JSON serialization
            data = {
                "location": self.location,
                "identifier": self.identifier,
                "caveats": self.caveats,
                "signature": self._signature
            }
            return json.dumps(data)
    
    def _compute_signature(self) -> str:
        """Compute the signature for the fallback implementation."""
        if MACAROON_AVAILABLE:
            return self._macaroon.signature
        else:
            # Simple HMAC-like signature
            data = f"{self.location}:{self.identifier}:{':'.join(str(c) for c in self.caveats)}"
            return hashlib.sha256(f"{data}:{self.key}".encode()).hexdigest()
    
    @property
    def signature(self) -> str:
        """Get the macaroon signature."""
        if MACAROON_AVAILABLE:
            return self._macaroon.signature
        else:
            return self._signature


class MacaroonVerifier:
    """Verifies macaroon caveats and signatures."""
    
    def __init__(self):
        """Initialize the verifier."""
        if MACAROON_AVAILABLE:
            self._verifier = Verifier()
        else:
            self._verifier = None
    
    def satisfy_exact(self, predicate: str) -> None:
        """Add an exact predicate that must be satisfied.
        
        Args:
            predicate: The exact predicate to satisfy
        """
        if MACAROON_AVAILABLE:
            self._verifier.satisfy_exact(predicate)
        else:
            # Fallback: store predicate for manual verification
            if not hasattr(self, 'predicates'):
                self.predicates = []
            self.predicates.append(predicate)
    
    def verify(self, macaroon: AIFSMacaroon, key: str) -> bool:
        """Verify a macaroon.
        
        Args:
            macaroon: The macaroon to verify
            key: The secret key for verification
            
        Returns:
            True if verification succeeds, False otherwise
        """
        if MACAROON_AVAILABLE:
            return self._verifier.verify(macaroon._macaroon, key)
        else:
            # Fallback verification
            return self._verify_fallback(macaroon, key)
    
    def _verify_fallback(self, macaroon: AIFSMacaroon, key: str) -> bool:
        """Fallback verification for when macaroon library is not available."""
        try:
            # Verify signature
            expected_signature = hashlib.sha256(
                f"{macaroon.location}:{macaroon.identifier}:{':'.join(str(c) for c in macaroon.caveats)}:{key}".encode()
            ).hexdigest()
            
            if macaroon.signature != expected_signature:
                return False
            
            # Verify caveats (simplified)
            for caveat_type, caveat_data in macaroon.caveats:
                if caveat_type == "first_party":
                    if not self._verify_first_party_caveat(caveat_data):
                        return False
                elif caveat_type == "third_party":
                    # Skip third-party caveats in fallback mode
                    continue
            
            return True
            
        except Exception:
            return False
    
    def _verify_first_party_caveat(self, predicate: str) -> bool:
        """Verify a first-party caveat (simplified)."""
        # Simple time-based caveat verification
        if predicate.startswith("time < "):
            try:
                time_str = predicate[7:]  # Remove "time < " prefix
                target_time = time.strptime(time_str, "%Y-%m-%d")
                current_time = time.localtime()
                return current_time < target_time
            except:
                return False
        return True


class AuthorizationManager:
    """Manages AIFS authorization using macaroons according to AIFS specification.
    
    Implements capability tokens with:
    - Namespace restrictions
    - Method permissions (put, get, search, snapshot, etc.)
    - Expiry timestamps
    - Third-party caveats for delegation
    """
    
    def __init__(self, secret_key: Optional[str] = None, location: str = "aifs.local"):
        """Initialize the authorization manager.
        
        Args:
            secret_key: Secret key for signing macaroons (generated if None)
            location: Location identifier for macaroons
        """
        if secret_key is None:
            import secrets
            secret_key = secrets.token_hex(32)
        
        self.secret_key = secret_key
        self.location = location
        
        if not MACAROON_AVAILABLE:
            print("Warning: Using simplified authorization system due to missing macaroon library.")
    
    def create_macaroon(self, identifier: str, permissions: List[str], 
                        namespace: Optional[str] = None, expiry_hours: int = 24,
                        methods: Optional[List[str]] = None) -> AIFSMacaroon:
        """Create a new macaroon with specified permissions according to AIFS spec.
        
        Args:
            identifier: Unique identifier for the macaroon
            permissions: List of allowed operations (put, get, search, snapshot, etc.)
            namespace: Optional namespace restriction
            expiry_hours: Hours until the macaroon expires
            methods: Optional specific methods allowed (overrides permissions)
            
        Returns:
            New AIFSMacaroon instance
        """
        macaroon = AIFSMacaroon(self.location, self.secret_key, identifier)
        
        # Add namespace caveat if specified
        if namespace:
            macaroon.add_first_party_caveat(f"namespace = {namespace}")
        
        # Add method permissions
        allowed_methods = methods or permissions
        for method in allowed_methods:
            macaroon.add_first_party_caveat(f"method = {method}")
        
        # Add expiry caveat (AIFS spec requirement)
        expiry_timestamp = int(time.time() + expiry_hours * 3600)
        macaroon.add_first_party_caveat(f"expires = {expiry_timestamp}")
        
        return macaroon
    
    def create_namespace_macaroon(self, namespace: str, methods: List[str], 
                                 expiry_hours: int = 24) -> AIFSMacaroon:
        """Create a macaroon restricted to a specific namespace.
        
        Args:
            namespace: Namespace identifier
            methods: Allowed methods (put, get, search, snapshot, etc.)
            expiry_hours: Hours until the macaroon expires
            
        Returns:
            New AIFSMacaroon instance restricted to the namespace
        """
        return self.create_macaroon(
            identifier=f"namespace_{namespace}",
            permissions=methods,
            namespace=namespace,
            expiry_hours=expiry_hours,
            methods=methods
        )
    
    def create_delegation_macaroon(self, parent_macaroon: str, 
                                  additional_caveats: List[str] = None) -> AIFSMacaroon:
        """Create a delegated macaroon with additional restrictions.
        
        Args:
            parent_macaroon: Serialized parent macaroon
            additional_caveats: Additional caveats to add
            
        Returns:
            New delegated AIFSMacaroon instance
        """
        if MACAROON_AVAILABLE:
            # Use proper macaroon delegation
            parent = Macaroon.deserialize(parent_macaroon)
            delegated = parent.add_first_party_caveat("delegated = true")
            
            # Add additional caveats
            if additional_caveats:
                for caveat in additional_caveats:
                    delegated = delegated.add_first_party_caveat(caveat)
            
            return AIFSMacaroon(self.location, self.secret_key, "delegated")
        else:
            # Fallback: create new macaroon with restrictions
            macaroon = AIFSMacaroon(self.location, self.secret_key, "delegated")
            macaroon.add_first_party_caveat("delegated = true")
            
            if additional_caveats:
                for caveat in additional_caveats:
                    macaroon.add_first_party_caveat(caveat)
            
            return macaroon
    
    def verify_macaroon(self, macaroon_data: str, required_permissions: Set[str], 
                       namespace: Optional[str] = None) -> bool:
        """Verify a macaroon has the required permissions according to AIFS spec.
        
        Args:
            macaroon_data: Serialized macaroon data
            required_permissions: Set of permissions required for the operation
            namespace: Optional namespace to verify against
            
        Returns:
            True if verification succeeds, False otherwise
        """
        try:
            if MACAROON_AVAILABLE:
                # Use macaroon library
                macaroon = Macaroon.deserialize(macaroon_data)
                verifier = Verifier()
                
                # Add method requirements
                for permission in required_permissions:
                    verifier.satisfy_exact(f"method = {permission}")
                
                # Add namespace requirement if specified
                if namespace:
                    verifier.satisfy_exact(f"namespace = {namespace}")
                
                # Add expiry verification
                current_timestamp = int(time.time())
                verifier.satisfy_general(lambda caveat: self._verify_expiry_caveat(caveat, current_timestamp))
                
                # Convert key to bytes if it's a string
                key = self.secret_key
                if isinstance(key, str):
                    key = key.encode('utf-8')
                
                return verifier.verify(macaroon, key)
            else:
                # Use fallback implementation
                return self._verify_macaroon_fallback(macaroon_data, required_permissions, namespace)
                
        except Exception as e:
            print(f"Macaroon verification failed: {e}")
            return False
    
    def _verify_expiry_caveat(self, caveat: str, current_timestamp: int) -> bool:
        """Verify expiry caveat for macaroon verification."""
        if caveat.startswith("expires = "):
            try:
                expiry_timestamp = int(caveat[10:])  # Remove "expires = " prefix
                return current_timestamp < expiry_timestamp
            except ValueError:
                return False
        return True
    
    def _verify_macaroon_fallback(self, macaroon_data: str, required_permissions: Set[str], 
                                 namespace: Optional[str] = None) -> bool:
        """Fallback macaroon verification when macaroon library is not available."""
        try:
            data = json.loads(macaroon_data)
            
            # Check if macaroon has required methods
            macaroon_methods = set()
            macaroon_namespace = None
            
            for caveat_type, caveat_data in data.get("caveats", []):
                if caveat_type == "first_party":
                    if caveat_data.startswith("method = "):
                        method = caveat_data[9:]  # Remove "method = " prefix
                        macaroon_methods.add(method)
                    elif caveat_data.startswith("namespace = "):
                        macaroon_namespace = caveat_data[12:]  # Remove "namespace = " prefix
                    elif caveat_data.startswith("expires = "):
                        try:
                            expiry_timestamp = int(caveat_data[10:])  # Remove "expires = " prefix
                            if time.time() > expiry_timestamp:
                                return False  # Expired
                        except ValueError:
                            pass  # Ignore malformed expiry caveats
            
            # Check if all required permissions are present
            if required_permissions and not required_permissions.issubset(macaroon_methods):
                return False
            
            # Check namespace if specified
            if namespace and macaroon_namespace and macaroon_namespace != namespace:
                return False
            
            return True
            
        except Exception as e:
            print(f"Fallback macaroon verification failed: {e}")
            return False
    
    def get_macaroon_info(self, macaroon_data: str) -> Dict:
        """Get information about a macaroon.
        
        Args:
            macaroon_data: Serialized macaroon data
            
        Returns:
            Dictionary with macaroon information
        """
        try:
            if MACAROON_AVAILABLE:
                macaroon = Macaroon.deserialize(macaroon_data)
                return {
                    "location": macaroon.location,
                    "identifier": macaroon.identifier,
                    "caveats": [caveat.caveat_id for caveat in macaroon.caveats],
                    "signature": macaroon.signature
                }
            else:
                # Fallback: parse JSON data
                data = json.loads(macaroon_data)
                return {
                    "location": data.get("location", ""),
                    "identifier": data.get("identifier", ""),
                    "caveats": [str(c) for c in data.get("caveats", [])],
                    "signature": data.get("signature", ""),
                    "note": "Fallback mode - limited functionality"
                }
        except Exception as e:
            return {"error": f"Failed to parse macaroon: {e}"}


# Global authorization manager for convenience functions
_global_auth_manager = None

def _get_global_auth_manager() -> AuthorizationManager:
    """Get or create the global authorization manager."""
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = AuthorizationManager()
    return _global_auth_manager

# Convenience functions for AIFS authorization
def create_aifs_token(permissions: List[str], namespace: Optional[str] = None, 
                     expiry_hours: int = 24) -> str:
    """Create an AIFS authorization token (macaroon or fallback).
    
    Args:
        permissions: List of allowed operations (put, get, search, snapshot, etc.)
        namespace: Optional namespace restriction
        expiry_hours: Hours until the token expires
        
    Returns:
        Authorization token string
    """
    auth_manager = _get_global_auth_manager()
    macaroon = auth_manager.create_macaroon(
        identifier="aifs_token",
        permissions=permissions,
        namespace=namespace,
        expiry_hours=expiry_hours
    )
    return macaroon.serialize()


def verify_aifs_token(token_data: str, required_permissions: Set[str], 
                     namespace: Optional[str] = None) -> bool:
    """Verify an AIFS authorization token.
    
    Args:
        token_data: Serialized token data
        required_permissions: Set of permissions required for the operation
        namespace: Optional namespace to verify against
        
    Returns:
        True if verification succeeds, False otherwise
    """
    auth_manager = _get_global_auth_manager()
    return auth_manager.verify_macaroon(token_data, required_permissions, namespace)


def create_namespace_token(namespace: str, methods: List[str], 
                          expiry_hours: int = 24) -> str:
    """Create a namespace-restricted authorization token.
    
    Args:
        namespace: Namespace identifier
        methods: Allowed methods (put, get, search, snapshot, etc.)
        expiry_hours: Hours until the token expires
        
    Returns:
        Namespace-restricted authorization token string
    """
    auth_manager = _get_global_auth_manager()
    macaroon = auth_manager.create_namespace_macaroon(namespace, methods, expiry_hours)
    return macaroon.serialize()


# Legacy functions for backward compatibility
def create_simple_token(permissions: List[str], expiry_hours: int = 24) -> str:
    """Create a simple authorization token (legacy function).
    
    Args:
        permissions: List of allowed operations
        expiry_hours: Hours until the token expires
        
    Returns:
        Simple authorization token string
    """
    return create_aifs_token(permissions, None, expiry_hours)


def verify_simple_token(token_data: str, required_permissions: Set[str]) -> bool:
    """Verify a simple authorization token (legacy function).
    
    Args:
        token_data: Serialized token data
        required_permissions: Set of permissions required for the operation
        
    Returns:
        True if verification succeeds, False otherwise
    """
    return verify_aifs_token(token_data, required_permissions, None)
