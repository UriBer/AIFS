"""AIFS Cryptographic Functions

Implements Ed25519 signatures for snapshots according to RFC8032.
Ensures snapshot root authenticity and integrity as specified in the AIFS architecture.
"""

import os
import json
import sqlite3
from typing import Tuple, Optional, Union, Dict, List
from nacl.signing import SigningKey, VerifyKey
from nacl.public import PrivateKey, PublicKey


class CryptoManager:
    """Manages cryptographic operations for AIFS.
    
    Handles Ed25519 key generation, signing, and verification for snapshots.
    Supports namespace-based key management and public key pinning as per AIFS spec.
    """
    
    def __init__(self, private_key: Optional[bytes] = None, key_db_path: Optional[str] = None):
        """Initialize crypto manager.
        
        Args:
            private_key: Optional private key bytes (32 bytes for Ed25519)
            key_db_path: Optional path to key management database
        """
        if private_key is None:
            # Generate new key pair for testing
            # In production, this should come from secure key management
            self.signing_key = SigningKey.generate()
        else:
            self.signing_key = SigningKey(private_key)
        
        self.verify_key = self.signing_key.verify_key
        
        # Initialize key management database
        self.key_db_path = key_db_path or ":memory:"
        self._init_key_db()
    
    def _init_key_db(self):
        """Initialize the key management database."""
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        # Create namespace keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS namespace_keys (
                namespace TEXT PRIMARY KEY,
                public_key_hex TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create trusted keys table for public key pinning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trusted_keys (
                key_id TEXT PRIMARY KEY,
                public_key_hex TEXT NOT NULL,
                namespace TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
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
    
    def register_namespace_key(self, namespace: str, metadata: Optional[Dict] = None) -> str:
        """Register the current public key for a namespace.
        
        Args:
            namespace: Namespace identifier
            metadata: Optional metadata dictionary
            
        Returns:
            Public key hex string
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        public_key_hex = self.get_public_key_hex()
        metadata_str = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT OR REPLACE INTO namespace_keys (namespace, public_key_hex, metadata) VALUES (?, ?, ?)",
            (namespace, public_key_hex, metadata_str)
        )
        
        conn.commit()
        conn.close()
        
        return public_key_hex
    
    def get_namespace_key(self, namespace: str) -> Optional[str]:
        """Get the public key for a namespace.
        
        Args:
            namespace: Namespace identifier
            
        Returns:
            Public key hex string or None if not found
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT public_key_hex FROM namespace_keys WHERE namespace = ?",
            (namespace,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def pin_trusted_key(self, key_id: str, public_key_hex: str, namespace: Optional[str] = None, 
                       metadata: Optional[Dict] = None) -> None:
        """Pin a trusted public key for verification.
        
        Args:
            key_id: Unique identifier for the key
            public_key_hex: Public key as hex string
            namespace: Optional namespace for the key
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        metadata_str = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT OR REPLACE INTO trusted_keys (key_id, public_key_hex, namespace, metadata) VALUES (?, ?, ?, ?)",
            (key_id, public_key_hex, namespace, metadata_str)
        )
        
        conn.commit()
        conn.close()
    
    def get_trusted_key(self, key_id: str) -> Optional[str]:
        """Get a trusted public key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Public key hex string or None if not found
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT public_key_hex FROM trusted_keys WHERE key_id = ?",
            (key_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def list_namespace_keys(self) -> List[Dict]:
        """List all namespace keys.
        
        Returns:
            List of namespace key dictionaries
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT namespace, public_key_hex, created_at, metadata FROM namespace_keys ORDER BY created_at DESC"
        )
        
        keys = []
        for row in cursor.fetchall():
            namespace, public_key_hex, created_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            keys.append({
                "namespace": namespace,
                "public_key_hex": public_key_hex,
                "created_at": created_at,
                "metadata": metadata
            })
        
        conn.close()
        return keys
    
    def list_trusted_keys(self) -> List[Dict]:
        """List all trusted keys.
        
        Returns:
            List of trusted key dictionaries
        """
        conn = sqlite3.connect(self.key_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT key_id, public_key_hex, namespace, created_at, metadata FROM trusted_keys ORDER BY created_at DESC"
        )
        
        keys = []
        for row in cursor.fetchall():
            key_id, public_key_hex, namespace, created_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            keys.append({
                "key_id": key_id,
                "public_key_hex": public_key_hex,
                "namespace": namespace,
                "created_at": created_at,
                "metadata": metadata
            })
        
        conn.close()
        return keys
    
    def sign_snapshot(self, merkle_root: str, timestamp: str, namespace: str) -> Tuple[bytes, str]:
        """Sign a snapshot with Ed25519 according to RFC8032.
        
        Creates a deterministic signature of the snapshot root for authenticity verification.
        The signature covers the merkle root, timestamp, and namespace to prevent replay attacks.
        
        Args:
            merkle_root: Merkle root hash (BLAKE3)
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            
        Returns:
            Tuple of (signature_bytes, signature_hex)
        """
        # Create deterministic message to sign (RFC8032 compliant)
        # Format: "AIFS_SNAPSHOT:{merkle_root}:{timestamp}:{namespace}"
        message = f"AIFS_SNAPSHOT:{merkle_root}:{timestamp}:{namespace}".encode('utf-8')
        
        # Sign the message with Ed25519
        signature = self.signing_key.sign(message)
        
        return signature.signature, signature.signature.hex()
    
    def verify_snapshot_signature(self, signature: Union[bytes, str], merkle_root: str, 
                                timestamp: str, namespace: str, public_key: bytes) -> bool:
        """Verify a snapshot signature according to RFC8032.
        
        Verifies that the signature was created by the holder of the private key
        corresponding to the provided public key, and that the message format matches
        the expected AIFS snapshot signature format.
        
        Args:
            signature: Signature bytes or hex string
            merkle_root: Merkle root hash (BLAKE3)
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            public_key: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            verify_key = VerifyKey(public_key)
            
            # Convert hex string to bytes if needed
            if isinstance(signature, str):
                signature_bytes = bytes.fromhex(signature)
            else:
                signature_bytes = signature
            
            # Create the same message that was signed (RFC8032 compliant)
            message = f"AIFS_SNAPSHOT:{merkle_root}:{timestamp}:{namespace}".encode('utf-8')
            
            # Verify signature
            verify_key.verify(message, signature_bytes)
            return True
            
        except Exception:
            return False
    
    def verify_snapshot_with_namespace_key(self, signature: Union[bytes, str], merkle_root: str, 
                                         timestamp: str, namespace: str) -> bool:
        """Verify a snapshot signature using the namespace's registered key.
        
        This method implements the AIFS specification requirement that clients
        SHOULD pin public keys by namespace.
        
        Args:
            signature: Signature bytes or hex string
            merkle_root: Merkle root hash (BLAKE3)
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            
        Returns:
            True if signature is valid and namespace key is trusted, False otherwise
        """
        # Get the namespace's public key
        public_key_hex = self.get_namespace_key(namespace)
        if not public_key_hex:
            return False
        
        # Convert hex to bytes
        public_key = bytes.fromhex(public_key_hex)
        
        # Verify the signature
        return self.verify_snapshot_signature(signature, merkle_root, timestamp, namespace, public_key)
    
    def verify_snapshot_with_trusted_key(self, signature: Union[bytes, str], merkle_root: str, 
                                       timestamp: str, namespace: str, key_id: str) -> bool:
        """Verify a snapshot signature using a trusted key.
        
        Args:
            signature: Signature bytes or hex string
            merkle_root: Merkle root hash (BLAKE3)
            timestamp: ISO timestamp string
            namespace: Namespace identifier
            key_id: Trusted key identifier
            
        Returns:
            True if signature is valid and key is trusted, False otherwise
        """
        # Get the trusted public key
        public_key_hex = self.get_trusted_key(key_id)
        if not public_key_hex:
            return False
        
        # Convert hex to bytes
        public_key = bytes.fromhex(public_key_hex)
        
        # Verify the signature
        return self.verify_snapshot_signature(signature, merkle_root, timestamp, namespace, public_key)
    
    def sign_data(self, data: bytes) -> Tuple[bytes, str]:
        """Sign arbitrary data.
        
        Args:
            data: Data to sign
            
        Returns:
            Tuple of (signature_bytes, signature_hex)
        """
        message = data
        signature = self.signing_key.sign(message)
        
        return signature.signature, signature.signature.hex()
    
    def sign_asset_id(self, asset_id: str, metadata: str) -> Tuple[bytes, str]:
        """Sign an asset ID with metadata.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            metadata: Metadata string
            
        Returns:
            Tuple of (signature_bytes, signature_hex)
        """
        message = f"{asset_id}:{metadata}".encode()
        signature = self.signing_key.sign(message)
        
        return signature.signature, signature.signature.hex()
    
    def verify_signature(self, data: bytes, signature: Union[bytes, str], public_key: bytes) -> bool:
        """Verify a signature for arbitrary data.
        
        Args:
            data: Data that was signed
            signature: Signature bytes or hex string
            public_key: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            verify_key = VerifyKey(public_key)
            
            # Convert hex string to bytes if needed
            if isinstance(signature, str):
                signature_bytes = bytes.fromhex(signature)
            else:
                signature_bytes = signature
            
            # Verify signature
            verify_key.verify(data, signature_bytes)
            return True
            
        except Exception:
            return False
    
    def verify_asset_signature(self, signature: bytes, asset_id: str, 
                             metadata: str, public_key: bytes) -> bool:
        """Verify an asset signature.
        
        Args:
            signature: Signature bytes
            asset_id: Asset ID (BLAKE3 hash)
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
    
    def generate_private_key(self) -> bytes:
        """Generate a new Ed25519 private key.
        
        Returns:
            Private key bytes
        """
        return self.generate_key_pair()[0]
    
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
