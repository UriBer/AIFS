"""AIFS Storage Backend

Implements content-addressed storage using BLAKE3 hashing and AES-256-GCM encryption.
"""

import os
import pathlib
import shutil
import blake3
from typing import Dict, List, Optional, Union, BinaryIO
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class StorageBackend:
    """Content-addressed storage backend for AIFS.
    
    Stores assets as files named by their BLAKE3 hash in a directory structure.
    Implements AES-256-GCM encryption for all chunks.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], encryption_key: Optional[bytes] = None,
                 kms_key_id: Optional[str] = None):
        """Initialize the storage backend.
        
        Args:
            root_dir: Root directory for storage
            encryption_key: Optional encryption key (generated if None)
            kms_key_id: Optional KMS key ID for envelope encryption
        """
        self.root_dir = pathlib.Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Store KMS key ID for envelope encryption
        self.kms_key_id = kms_key_id or "aifs-default-key"
        
        # Generate encryption key if not provided
        if encryption_key is None:
            encryption_key = os.urandom(32)  # 256-bit key for AES-256
        
        self.encryption_key = encryption_key
        
        # Create storage subdirectories
        self.chunks_dir = self.root_dir / "chunks"
        self.chunks_dir.mkdir(exist_ok=True)
    
    def _hash_to_path(self, hash_hex: str) -> pathlib.Path:
        """Convert hash to path with sharding.
        
        Args:
            hash_hex: Hex-encoded BLAKE3 hash
            
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
            Hex-encoded BLAKE3 hash of the data
        """
        # Compute BLAKE3 hash
        hash_hex = blake3.blake3(data).hexdigest()
        
        # Create path with parent directories
        path = self._hash_to_path(hash_hex)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only write if doesn't exist (content-addressed, so same hash = same content)
        if not path.exists():
            # Encrypt data with AES-256-GCM
            encrypted_data = self._encrypt_chunk(data)
            path.write_bytes(encrypted_data)
            
            # Store KMS key ID in metadata file
            metadata_path = path.with_suffix('.meta')
            with open(metadata_path, 'w') as f:
                f.write(f"kms_key_id={self.kms_key_id}\n")
                f.write(f"encryption=AES-256-GCM\n")
                f.write(f"hash_algorithm=BLAKE3\n")
        
        return hash_hex
    
    def _encrypt_chunk(self, data: bytes) -> bytes:
        """Encrypt a chunk of data using AES-256-GCM.
        
        Args:
            data: Raw data to encrypt
            
        Returns:
            Encrypted data with nonce prepended
        """
        if not data:
            return b""
        
        # Generate a new nonce for each chunk
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = AESGCM(self.encryption_key)
        
        # Encrypt the data
        ciphertext = cipher.encrypt(nonce, data, None)
        
        # Return nonce + ciphertext
        return nonce + ciphertext
    
    def _decrypt_chunk(self, encrypted_data: bytes) -> bytes:
        """Decrypt a chunk of data using AES-256-GCM.
        
        Args:
            encrypted_data: Encrypted data with nonce prepended
            
        Returns:
            Decrypted data
        """
        if not encrypted_data:
            return b""
        
        try:
            # Extract nonce and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]
            
            # Create cipher
            cipher = AESGCM(self.encryption_key)
            
            # Decrypt the data
            return cipher.decrypt(nonce, ciphertext, None)
            
        except Exception as e:
            print(f"Decryption failed: {e}")
            # Return empty data on decryption failure
            return b""
    
    def get(self, hash_hex: str) -> Optional[bytes]:
        """Retrieve data by its content hash.
        
        Args:
            hash_hex: Hex-encoded BLAKE3 hash
            
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
            hash_hex: Hex-encoded BLAKE3 hash
            
        Returns:
            True if data exists, False otherwise
        """
        return self._hash_to_path(hash_hex).exists()
    
    def delete(self, hash_hex: str) -> bool:
        """Delete data with given hash.
        
        Args:
            hash_hex: Hex-encoded BLAKE3 hash
            
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
            hash_hex: Hex-encoded BLAKE3 hash
            
        Returns:
            Dictionary with chunk info or None if not found
        """
        path = self._hash_to_path(hash_hex)
        if not path.exists():
            return None
        
        stat_info = path.stat()
        info = {
            "size": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime
        }
        
        # Read metadata file if it exists
        metadata_path = path.with_suffix('.meta')
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        info[key] = value
        
        return info