"""AIFS Storage Backend

Implements content-addressed storage using SHA-256 hashing and AES-256-GCM encryption.
Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
"""

import os
import pathlib
import shutil
import hashlib
from typing import Dict, List, Optional, Union, BinaryIO
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class StorageBackend:
    """Content-addressed storage backend for AIFS.
    
    Stores assets as files named by their SHA-256 hash in a directory structure.
    Implements AES-256-GCM encryption for all chunks.
    Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], encryption_key: Optional[bytes] = None):
        """Initialize storage backend.
        
        Args:
            root_dir: Root directory for storage
            encryption_key: Optional encryption key (32 bytes for AES-256)
        """
        self.root_dir = pathlib.Path(root_dir)
        self.chunks_dir = self.root_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption
        if encryption_key is None:
            # Generate a random key for testing (in production, this should come from KMS)
            encryption_key = os.urandom(32)
        self.encryption_key = encryption_key
        
        # Derive chunk encryption keys using HKDF
        self.chunk_key = self._derive_chunk_key()
    
    def _derive_chunk_key(self) -> bytes:
        """Derive chunk encryption key using HKDF."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"aifs-chunk-encryption",
            info=b"chunk-key",
        )
        return hkdf.derive(self.encryption_key)
    
    def _hash_to_path(self, hash_hex: str) -> pathlib.Path:
        """Convert hash to path with sharding.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            Path to the chunk file
        """
        # Use first 4 chars as directory to avoid too many files in one dir
        return self.chunks_dir / hash_hex[:4] / hash_hex
    
    def put(self, data: bytes) -> str:
        """Store data and return its content hash.
        
        Args:
            data: Binary data to store
            
        Returns:
            Hex-encoded SHA-256 hash of the data
        """
        # Compute SHA-256 hash (using standard library to avoid Rust dependency)
        hash_obj = hashlib.sha256(data)
        hash_hex = hash_obj.hexdigest()
        
        # Create path with parent directories
        path = self._hash_to_path(hash_hex)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only write if doesn't exist (content-addressed, so same hash = same content)
        if not path.exists():
            # Encrypt data with AES-256-GCM
            encrypted_data = self._encrypt_chunk(data)
            path.write_bytes(encrypted_data)
        
        return hash_hex
    
    def _encrypt_chunk(self, data: bytes) -> bytes:
        """Encrypt chunk data with AES-256-GCM.
        
        Args:
            data: Raw data to encrypt
            
        Returns:
            Encrypted data with nonce and tag
        """
        aesgcm = AESGCM(self.chunk_key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        encrypted_data = aesgcm.encrypt(nonce, data, None)
        return nonce + encrypted_data
    
    def _decrypt_chunk(self, encrypted_data: bytes) -> bytes:
        """Decrypt chunk data with AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted data with nonce and tag
            
        Returns:
            Decrypted data
        """
        aesgcm = AESGCM(self.chunk_key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)
    
    def get(self, hash_hex: str) -> Optional[bytes]:
        """Retrieve data by its content hash.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            Binary data or None if not found
        """
        path = self._hash_to_path(hash_hex)
        if path.exists():
            encrypted_data = path.read_bytes()
            return self._decrypt_chunk(encrypted_data)
        return None
    
    def exists(self, hash_hex: str) -> bool:
        """Check if data with given hash exists.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            True if data exists, False otherwise
        """
        return self._hash_to_path(hash_hex).exists()
    
    def delete(self, hash_hex: str) -> bool:
        """Delete data with given hash.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            True if data was deleted, False if not found
        """
        path = self._hash_to_path(hash_hex)
        if path.exists():
            path.unlink()
            # Try to remove parent directory if empty
            try:
                path.parent.rmdir()
            except OSError:
                # Directory not empty, ignore
                pass
            return True
        return False
    
    def get_chunk_info(self, hash_hex: str) -> Optional[Dict]:
        """Get information about a chunk without decrypting.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            Dictionary with chunk info or None if not found
        """
        path = self._hash_to_path(hash_hex)
        if not path.exists():
            return None
        
        stat_info = path.stat()
        return {
            "size": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime
        }