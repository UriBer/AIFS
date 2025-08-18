"""AIFS Cryptographic Functions

Implements Ed25519 signatures for snapshots.
"""

import os
from typing import Tuple, Optional
from nacl.signing import SigningKey, VerifyKey
from nacl.public import PrivateKey, PublicKey


class CryptoManager:
    """Manages cryptographic operations for AIFS.
    
    Handles Ed25519 key generation, signing, and verification for snapshots.
    """
    
    def __init__(self, private_key: Optional[bytes] = None):
        """Initialize crypto manager.
        
        Args:
            private_key: Optional private key bytes (32 bytes for Ed25519)
        """
        if private_key is None:
            # Generate new key pair for testing
            # In production, this should come from secure key management
            self.signing_key = SigningKey.generate()
        else:
            self.signing_key = SigningKey(private_key)
        
        self.verify_key = self.signing_key.verify_key
    
    def get_public_key(self) -> bytes:
        """Get the public key for verification.
        
        Returns:
            Public key bytes
        """
        return bytes(self.verify_key)
    
    def get_public_key_hex(self) -> str:
        """Get the public key as hex string.
        
        Returns:
            Public key as hex string
        """
        return self.verify_key.encode().hex()
    
    def sign_snapshot(self, merkle_root: str, timestamp: str, namespace: str) -> Tuple[bytes, str]:
        """Sign a snapshot with Ed25519.
        
        Args:
            merkle_root: Merkle root hash
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            
        Returns:
            Tuple of (signature_bytes, signature_hex)
        """
        # Create message to sign
        message = f"{merkle_root}:{timestamp}:{namespace}".encode()
        
        # Sign the message
        signature = self.signing_key.sign(message)
        
        return signature.signature, signature.signature.hex()
    
    def verify_snapshot_signature(self, signature: bytes, merkle_root: str, 
                                timestamp: str, namespace: str, public_key: bytes) -> bool:
        """Verify a snapshot signature.
        
        Args:
            signature: Signature bytes
            merkle_root: Merkle root hash
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            public_key: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            verify_key = VerifyKey(public_key)
            
            # Create message that was signed
            message = f"{merkle_root}:{timestamp}:{namespace}".encode()
            
            # Verify signature
            verify_key.verify(message, signature)
            return True
            
        except Exception:
            return False
    
    def sign_asset_id(self, asset_id: str, metadata: str) -> Tuple[bytes, str]:
        """Sign an asset ID with metadata.
        
        Args:
            asset_id: Asset ID (SHA-256 hash)
            metadata: Metadata string
            
        Returns:
            Tuple of (signature_bytes, signature_hex)
        """
        message = f"{asset_id}:{metadata}".encode()
        signature = self.signing_key.sign(message)
        
        return signature.signature, signature.signature.hex()
    
    def verify_asset_signature(self, signature: bytes, asset_id: str, 
                             metadata: str, public_key: bytes) -> bool:
        """Verify an asset signature.
        
        Args:
            signature: Signature bytes
            asset_id: Asset ID (SHA-256 hash)
            metadata: Metadata string
            public_key: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            verify_key = VerifyKey(public_key)
            message = f"{asset_id}:{metadata}".encode()
            verify_key.verify(message, signature)
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def generate_key_pair() -> Tuple[bytes, bytes]:
        """Generate a new Ed25519 key pair.
        
        Returns:
            Tuple of (private_key_bytes, public_key_bytes)
        """
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        
        return bytes(signing_key), bytes(verify_key)
    
    @staticmethod
    def key_from_seed(seed: bytes) -> bytes:
        """Generate Ed25519 private key from seed.
        
        Args:
            seed: 32-byte seed
            
        Returns:
            Private key bytes
        """
        if len(seed) != 32:
            raise ValueError("Seed must be exactly 32 bytes")
        
        signing_key = SigningKey(seed)
        return bytes(signing_key)
