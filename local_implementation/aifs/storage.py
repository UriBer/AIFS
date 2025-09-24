"""AIFS Storage Backend

Implements content-addressed storage using BLAKE3 hashing and AES-256-GCM encryption.
"""

import os
import json
import pathlib
import shutil
import blake3
from typing import Dict, List, Optional, Union, BinaryIO
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from .compression import CompressionService
from .kms import KMS, KMSKey


class StorageBackend:
    """Content-addressed storage backend for AIFS.
    
    Stores assets as files named by their BLAKE3 hash in a directory structure.
    Implements AES-256-GCM encryption for all chunks.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], encryption_key: Optional[bytes] = None,
                 kms_key_id: Optional[str] = None, compression_level: int = 1,
                 kms: Optional[KMS] = None):
        """Initialize the storage backend.
        
        Args:
            root_dir: Root directory for storage
            encryption_key: Optional encryption key (generated if None)
            kms_key_id: Optional KMS key ID for envelope encryption
            compression_level: zstd compression level (1-22, default 1 as per spec)
            kms: Optional KMS instance for envelope encryption
        """
        self.root_dir = pathlib.Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize KMS for envelope encryption
        self.kms = kms or KMS(str(self.root_dir / "kms"))
        self.kms_key_id = kms_key_id or "aifs-default-key"
        
        # Ensure KMS key exists
        if not self.kms.get_key(self.kms_key_id):
            self.kms.create_key(self.kms_key_id, key_type="AES-256")
        
        # Generate encryption key if not provided (for backward compatibility)
        if encryption_key is None:
            encryption_key = os.urandom(32)  # 256-bit key for AES-256
        
        self.encryption_key = encryption_key
        
        # Initialize compression service
        self.compression_service = CompressionService(compression_level)
        
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
        # Compute BLAKE3 hash of original data (before compression)
        hash_hex = blake3.blake3(data).hexdigest()
        
        # Create path with parent directories
        path = self._hash_to_path(hash_hex)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only write if doesn't exist (content-addressed, so same hash = same content)
        if not path.exists():
            # Compress data with zstd
            compressed_data = self.compression_service.compress(data)
            
            # Encrypt compressed data with AES-256-GCM
            encrypted_data = self._encrypt_chunk(compressed_data)
            path.write_bytes(encrypted_data)
            
            # Store KMS key ID in metadata file
            metadata_path = path.with_suffix('.meta')
            with open(metadata_path, 'w') as f:
                f.write(f"kms_key_id={self.kms_key_id}\n")
                f.write(f"encryption=AES-256-GCM\n")
                f.write(f"hash_algorithm=BLAKE3\n")
        
        return hash_hex
    
    def _encrypt_chunk(self, data: bytes) -> bytes:
        """Encrypt a chunk of data using AES-256-GCM with KMS envelope encryption.
        
        Args:
            data: Raw data to encrypt
            
        Returns:
            Encrypted data with envelope encryption metadata
        """
        if not data:
            return b""
        
        # Generate a new data key for this chunk
        data_key, encrypted_data_key, envelope_nonce = self.kms.generate_data_key(self.kms_key_id)
        
        # Generate a new nonce for the chunk encryption
        chunk_nonce = os.urandom(12)
        
        # Create cipher with the data key
        cipher = AESGCM(data_key)
        
        # Encrypt the data
        ciphertext = cipher.encrypt(chunk_nonce, data, None)
        
        # Create envelope with metadata
        envelope = {
            "kms_key_id": self.kms_key_id,
            "encrypted_data_key": encrypted_data_key.hex(),
            "envelope_nonce": envelope_nonce.hex(),
            "chunk_nonce": chunk_nonce.hex(),
            "ciphertext": ciphertext.hex()
        }
        
        # Serialize envelope
        envelope_json = json.dumps(envelope).encode('utf-8')
        
        # Return envelope length + envelope + ciphertext
        envelope_length = len(envelope_json)
        return envelope_length.to_bytes(4, 'big') + envelope_json + ciphertext
    
    def _decrypt_chunk(self, encrypted_data: bytes) -> bytes:
        """Decrypt a chunk of data using AES-256-GCM with KMS envelope encryption.
        
        Args:
            encrypted_data: Encrypted data with envelope encryption metadata
            
        Returns:
            Decrypted data
        """
        if not encrypted_data:
            return b""
        
        try:
            # Check if this is new envelope format or legacy format
            if len(encrypted_data) < 4:
                return b""
            
            # Try to read envelope length
            envelope_length = int.from_bytes(encrypted_data[:4], 'big')
            
            # Check if this looks like envelope format
            if envelope_length > 0 and envelope_length < len(encrypted_data) - 4:
                # New envelope format
                envelope_json = encrypted_data[4:4 + envelope_length]
                ciphertext = encrypted_data[4 + envelope_length:]
                
                # Parse envelope
                envelope = json.loads(envelope_json.decode('utf-8'))
                
                # Decrypt the data key
                encrypted_data_key = bytes.fromhex(envelope["encrypted_data_key"])
                envelope_nonce = bytes.fromhex(envelope["envelope_nonce"])
                chunk_nonce = bytes.fromhex(envelope["chunk_nonce"])
                
                data_key = self.kms.decrypt_data_key(
                    encrypted_data_key, envelope_nonce, envelope["kms_key_id"]
                )
                
                # Create cipher with the data key
                cipher = AESGCM(data_key)
                
                # Decrypt the data
                return cipher.decrypt(chunk_nonce, ciphertext, None)
            else:
                # Legacy format - try old decryption method
                if len(encrypted_data) >= 12:
                    nonce = encrypted_data[:12]
                    ciphertext = encrypted_data[12:]
                    
                    # Create cipher with legacy key
                    cipher = AESGCM(self.encryption_key)
                    
                    # Decrypt the data
                    return cipher.decrypt(nonce, ciphertext, None)
                else:
                    return b""
            
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
            # Decrypt data
            compressed_data = self._decrypt_chunk(encrypted_data)
            if compressed_data is None:
                return None
            
            # Decompress data with zstd
            try:
                return self.compression_service.decompress(compressed_data)
            except Exception:
                # If decompression fails, try to return raw data (backward compatibility)
                return compressed_data
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