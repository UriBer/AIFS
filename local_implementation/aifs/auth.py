"""AIFS Authorization System

Implements macaroon-based authorization for AIFS operations.
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Set

# Try to import macaroon, provide fallback if not available
try:
    from macaroon import Macaroon, Verifier
    MACAROON_AVAILABLE = True
except ImportError:
    MACAROON_AVAILABLE = False
    print("Warning: macaroon library not available. Using simplified authorization fallback.")
    print("For full macaroon support, install macaroon package or use Python 3.11/3.12.")


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
            self._macaroon = Macaroon(location=location, key=key, identifier=identifier)
        else:
            # Fallback implementation
            self.location = location
            self.key = key
            self.identifier = identifier
            self.caveats = []
            self.signature = self._compute_signature()
    
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
            self.signature = self._compute_signature()
        
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
            self.signature = self._compute_signature()
        
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
                "signature": self.signature
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
    """Manages AIFS authorization using macaroons."""
    
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize the authorization manager.
        
        Args:
            secret_key: Secret key for signing macaroons (generated if None)
        """
        if secret_key is None:
            import secrets
            secret_key = secrets.token_hex(32)
        
        self.secret_key = secret_key
        self.location = "aifs.local"
        
        if not MACAROON_AVAILABLE:
            print("Warning: Using simplified authorization system due to missing macaroon library.")
    
    def create_macaroon(self, identifier: str, permissions: List[str], 
                        expiry_hours: int = 24) -> AIFSMacaroon:
        """Create a new macaroon with specified permissions.
        
        Args:
            identifier: Unique identifier for the macaroon
            permissions: List of allowed operations
            expiry_hours: Hours until the macaroon expires
            
        Returns:
            New AIFSMacaroon instance
        """
        macaroon = AIFSMacaroon(self.location, self.secret_key, identifier)
        
        # Add permission caveats
        for permission in permissions:
            macaroon.add_first_party_caveat(f"permission = {permission}")
        
        # Add expiry caveat
        expiry_time = time.strftime("%Y-%m-%d", time.localtime(time.time() + expiry_hours * 3600))
        macaroon.add_first_party_caveat(f"time < {expiry_time}")
        
        return macaroon
    
    def verify_macaroon(self, macaroon_data: str, required_permissions: Set[str]) -> bool:
        """Verify a macaroon has the required permissions.
        
        Args:
            macaroon_data: Serialized macaroon data
            required_permissions: Set of permissions required for the operation
            
        Returns:
            True if verification succeeds, False otherwise
        """
        try:
            if MACAROON_AVAILABLE:
                # Use macaroon library
                macaroon = Macaroon.deserialize(macaroon_data)
                verifier = Verifier()
                
                # Add permission requirements
                for permission in required_permissions:
                    verifier.satisfy_exact(f"permission = {permission}")
                
                return verifier.verify(macaroon, self.secret_key)
            else:
                # Use fallback implementation
                data = json.loads(macaroon_data)
                
                # Check if macaroon has required permissions
                macaroon_permissions = set()
                for caveat_type, caveat_data in data.get("caveats", []):
                    if caveat_type == "first_party" and caveat_data.startswith("permission = "):
                        permission = caveat_data[13:]  # Remove "permission = " prefix
                        macaroon_permissions.add(permission)
                
                # Check if all required permissions are present
                if not required_permissions.issubset(macaroon_permissions):
                    return False
                
                # Check expiry
                for caveat_type, caveat_data in data.get("caveats", []):
                    if caveat_type == "first_party" and caveat_data.startswith("time < "):
                        time_str = caveat_data[7:]  # Remove "time < " prefix
                        try:
                            target_time = time.strptime(time_str, "%Y-%m-%d")
                            current_time = time.localtime()
                            # Convert to date objects for comparison
                            target_date = time.strftime("%Y-%m-%d", target_time)
                            current_date = time.strftime("%Y-%m-%d", current_time)
                            if current_date > target_date:  # Use string comparison for dates
                                return False  # Expired
                        except:
                            pass  # Ignore malformed time caveats
                
                return True
                
        except Exception as e:
            print(f"Macaroon verification failed: {e}")
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
                    "caveats": [caveat.caveatId for caveat in macaroon.caveats],
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


# Convenience functions for when macaroon library is not available
def create_simple_token(permissions: List[str], expiry_hours: int = 24) -> str:
    """Create a simple authorization token when macaroon is not available.
    
    Args:
        permissions: List of allowed operations
        expiry_hours: Hours until the token expires
        
    Returns:
        Simple authorization token string
    """
    if MACAROON_AVAILABLE:
        # Use proper macaroon if available
        auth_manager = AuthorizationManager()
        macaroon = auth_manager.create_macaroon("simple", permissions, expiry_hours)
        return macaroon.serialize()
    else:
        # Fallback: simple JSON token
        import secrets
        token_data = {
            "id": secrets.token_hex(16),
            "permissions": permissions,
            "expires": time.time() + expiry_hours * 3600,
            "type": "simple_token"
        }
        return json.dumps(token_data)


def verify_simple_token(token_data: str, required_permissions: Set[str]) -> bool:
    """Verify a simple authorization token.
    
    Args:
        token_data: Serialized token data
        required_permissions: Set of permissions required for the operation
        
    Returns:
        True if verification succeeds, False otherwise
    """
    if MACAROON_AVAILABLE:
        # Use proper macaroon verification if available
        auth_manager = AuthorizationManager()
        return auth_manager.verify_macaroon(token_data, required_permissions)
    else:
        # Fallback: simple JSON token verification
        try:
            token = json.loads(token_data)
            
            # Check expiry
            if time.time() > token.get("expires", 0):
                return False
            
            # Check permissions
            token_permissions = set(token.get("permissions", []))
            return required_permissions.issubset(token_permissions)
            
        except Exception:
            return False
