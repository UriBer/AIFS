"""
AIFS Key Management Service (KMS)

Implements envelope encryption for AES-256-GCM data keys as required by the AIFS specification.
"""

import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend


class KMSKey:
    """Represents a KMS key with metadata."""
    
    def __init__(self, key_id: str, key_type: str = "AES-256", 
                 created_at: Optional[float] = None, 
                 expires_at: Optional[float] = None,
                 metadata: Optional[Dict] = None):
        """Initialize a KMS key.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key (AES-256, RSA-2048, etc.)
            created_at: Creation timestamp
            expires_at: Expiration timestamp (None for no expiration)
            metadata: Additional metadata
        """
        self.key_id = key_id
        self.key_type = key_type
        self.created_at = created_at or time.time()
        self.expires_at = expires_at
        self.metadata = metadata or {}
        self._key_material = None
        self._public_key = None
        self._private_key = None
    
    def set_key_material(self, key_material: bytes):
        """Set the key material (for symmetric keys)."""
        self._key_material = key_material
    
    def get_key_material(self) -> Optional[bytes]:
        """Get the key material."""
        return self._key_material
    
    def set_rsa_keys(self, public_key: bytes, private_key: bytes):
        """Set RSA key pair."""
        self._public_key = public_key
        self._private_key = private_key
    
    def get_public_key(self) -> Optional[bytes]:
        """Get the public key."""
        return self._public_key
    
    def get_private_key(self) -> Optional[bytes]:
        """Get the private key."""
        return self._private_key
    
    def is_expired(self) -> bool:
        """Check if the key is expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict:
        """Convert key to dictionary for storage."""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'KMSKey':
        """Create key from dictionary."""
        key = cls(
            key_id=data["key_id"],
            key_type=data.get("key_type", "AES-256"),
            created_at=data.get("created_at"),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {})
        )
        return key


class EnvelopeEncryption:
    """Implements envelope encryption for data keys."""
    
    def __init__(self, master_key: bytes):
        """Initialize envelope encryption.
        
        Args:
            master_key: Master key for encrypting data keys
        """
        self.master_key = master_key
    
    def encrypt_data_key(self, data_key: bytes, key_id: str) -> Tuple[bytes, bytes]:
        """Encrypt a data key using the master key.
        
        Args:
            data_key: The data key to encrypt
            key_id: Key identifier for additional context
            
        Returns:
            Tuple of (encrypted_data_key, nonce)
        """
        # Generate nonce
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = AESGCM(self.master_key)
        
        # Encrypt data key with key_id as additional authenticated data
        ciphertext = cipher.encrypt(nonce, data_key, key_id.encode('utf-8'))
        
        return ciphertext, nonce
    
    def decrypt_data_key(self, encrypted_data_key: bytes, nonce: bytes, 
                        key_id: str) -> bytes:
        """Decrypt a data key using the master key.
        
        Args:
            encrypted_data_key: The encrypted data key
            nonce: The nonce used for encryption
            key_id: Key identifier for additional context
            
        Returns:
            Decrypted data key
        """
        # Create cipher
        cipher = AESGCM(self.master_key)
        
        # Decrypt data key
        return cipher.decrypt(nonce, encrypted_data_key, key_id.encode('utf-8'))


class KMS:
    """Key Management Service for AIFS.
    
    Implements envelope encryption for per-chunk data keys as required by the AIFS specification.
    """
    
    def __init__(self, storage_path: str, master_key: Optional[bytes] = None):
        """Initialize the KMS.
        
        Args:
            storage_path: Path to store KMS data
            master_key: Master key for envelope encryption (generated if None)
        """
        self.storage_path = storage_path
        self.keys: Dict[str, KMSKey] = {}
        self.envelope_encryption = None
        
        # Generate master key if not provided
        if master_key is None:
            master_key = os.urandom(32)  # 256-bit master key
        
        self.master_key = master_key
        self.envelope_encryption = EnvelopeEncryption(master_key)
        
        # Load existing keys
        self._load_keys()
    
    def _load_keys(self):
        """Load keys from storage."""
        try:
            keys_file = os.path.join(self.storage_path, "kms_keys.json")
            if os.path.exists(keys_file):
                with open(keys_file, 'r') as f:
                    keys_data = json.load(f)
                
                for key_data in keys_data.get("keys", []):
                    key = KMSKey.from_dict(key_data)
                    self.keys[key.key_id] = key
        except Exception as e:
            print(f"Warning: Failed to load KMS keys: {e}")
    
    def _save_keys(self):
        """Save keys to storage."""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            keys_file = os.path.join(self.storage_path, "kms_keys.json")
            
            keys_data = {
                "keys": [key.to_dict() for key in self.keys.values()],
                "master_key_hash": hashlib.sha256(self.master_key).hexdigest()
            }
            
            with open(keys_file, 'w') as f:
                json.dump(keys_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save KMS keys: {e}")
    
    def create_key(self, key_id: str, key_type: str = "AES-256", 
                   expires_at: Optional[float] = None,
                   metadata: Optional[Dict] = None) -> KMSKey:
        """Create a new KMS key.
        
        Args:
            key_id: Unique identifier for the key
            key_type: Type of key to create
            expires_at: Expiration timestamp (None for no expiration)
            metadata: Additional metadata
            
        Returns:
            Created KMSKey instance
        """
        if key_id in self.keys:
            raise ValueError(f"Key {key_id} already exists")
        
        key = KMSKey(
            key_id=key_id,
            key_type=key_type,
            expires_at=expires_at,
            metadata=metadata
        )
        
        # Generate key material based on type
        if key_type == "AES-256":
            key.set_key_material(os.urandom(32))  # 256-bit key
        elif key_type == "AES-128":
            key.set_key_material(os.urandom(16))  # 128-bit key
        elif key_type == "RSA-2048":
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            key.set_rsa_keys(public_pem, private_pem)
        else:
            raise ValueError(f"Unsupported key type: {key_type}")
        
        self.keys[key_id] = key
        self._save_keys()
        
        return key
    
    def get_key(self, key_id: str) -> Optional[KMSKey]:
        """Get a KMS key by ID.
        
        Args:
            key_id: Key identifier
            
        Returns:
            KMSKey instance or None if not found
        """
        key = self.keys.get(key_id)
        if key and key.is_expired():
            # Remove expired key
            del self.keys[key_id]
            self._save_keys()
            return None
        return key
    
    def delete_key(self, key_id: str) -> bool:
        """Delete a KMS key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if key was deleted, False if not found
        """
        if key_id in self.keys:
            del self.keys[key_id]
            self._save_keys()
            return True
        return False
    
    def list_keys(self) -> List[str]:
        """List all key IDs.
        
        Returns:
            List of key IDs
        """
        # Remove expired keys
        expired_keys = [key_id for key_id, key in self.keys.items() if key.is_expired()]
        for key_id in expired_keys:
            del self.keys[key_id]
        
        if expired_keys:
            self._save_keys()
        
        return list(self.keys.keys())
    
    def encrypt_data_key(self, data_key: bytes, key_id: str) -> Tuple[bytes, bytes]:
        """Encrypt a data key using envelope encryption.
        
        Args:
            data_key: The data key to encrypt
            key_id: KMS key ID to use for encryption
            
        Returns:
            Tuple of (encrypted_data_key, nonce)
        """
        if not self.envelope_encryption:
            raise RuntimeError("Envelope encryption not initialized")
        
        return self.envelope_encryption.encrypt_data_key(data_key, key_id)
    
    def decrypt_data_key(self, encrypted_data_key: bytes, nonce: bytes, 
                        key_id: str) -> bytes:
        """Decrypt a data key using envelope encryption.
        
        Args:
            encrypted_data_key: The encrypted data key
            nonce: The nonce used for encryption
            key_id: KMS key ID used for encryption
            
        Returns:
            Decrypted data key
        """
        if not self.envelope_encryption:
            raise RuntimeError("Envelope encryption not initialized")
        
        return self.envelope_encryption.decrypt_data_key(
            encrypted_data_key, nonce, key_id
        )
    
    def generate_data_key(self, key_id: str) -> Tuple[bytes, bytes, bytes]:
        """Generate a new data key and encrypt it.
        
        Args:
            key_id: KMS key ID to use for encryption
            
        Returns:
            Tuple of (data_key, encrypted_data_key, nonce)
        """
        # Generate new data key
        data_key = os.urandom(32)  # 256-bit key for AES-256
        
        # Encrypt the data key
        encrypted_data_key, nonce = self.encrypt_data_key(data_key, key_id)
        
        return data_key, encrypted_data_key, nonce
    
    def get_key_info(self, key_id: str) -> Optional[Dict]:
        """Get information about a key.
        
        Args:
            key_id: Key identifier
            
        Returns:
            Dictionary with key information or None if not found
        """
        key = self.get_key(key_id)
        if not key:
            return None
        
        info = key.to_dict()
        info["is_expired"] = key.is_expired()
        info["has_key_material"] = key.get_key_material() is not None
        info["has_rsa_keys"] = key.get_public_key() is not None
        
        return info
    
    def rotate_key(self, key_id: str) -> bool:
        """Rotate a key by generating new key material.
        
        Args:
            key_id: Key identifier
            
        Returns:
            True if key was rotated, False if not found
        """
        key = self.get_key(key_id)
        if not key:
            return False
        
        # Generate new key material
        if key.key_type in ["AES-256", "AES-128"]:
            key_size = 32 if key.key_type == "AES-256" else 16
            key.set_key_material(os.urandom(key_size))
        elif key.key_type == "RSA-2048":
            # Generate new RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            key.set_rsa_keys(public_pem, private_pem)
        
        # Update creation time
        key.created_at = time.time()
        
        self._save_keys()
        return True
    
    def get_statistics(self) -> Dict:
        """Get KMS statistics.
        
        Returns:
            Dictionary with KMS statistics
        """
        total_keys = len(self.keys)
        expired_keys = sum(1 for key in self.keys.values() if key.is_expired())
        active_keys = total_keys - expired_keys
        
        key_types = {}
        for key in self.keys.values():
            key_types[key.key_type] = key_types.get(key.key_type, 0) + 1
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "key_types": key_types,
            "master_key_hash": hashlib.sha256(self.master_key).hexdigest()
        }


# Global KMS instance for convenience
_global_kms = None

def get_global_kms() -> KMS:
    """Get or create the global KMS instance."""
    global _global_kms
    if _global_kms is None:
        _global_kms = KMS("/tmp/aifs_kms")
    return _global_kms

def set_global_kms(kms: KMS):
    """Set the global KMS instance."""
    global _global_kms
    _global_kms = kms
