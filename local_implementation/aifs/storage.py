"""AIFS Storage Backend

Implements content-addressed storage using SHA-256 hashing.
"""

import os
import pathlib
import shutil
import hashlib
from typing import Dict, List, Optional, Union, BinaryIO


class StorageBackend:
    """Content-addressed storage backend for AIFS.
    
    Stores assets as files named by their SHA-256 hash in a directory structure.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path]):
        """Initialize storage backend.
        
        Args:
            root_dir: Root directory for storage
        """
        self.root_dir = pathlib.Path(root_dir)
        self.chunks_dir = self.root_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
    
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
        # Compute SHA-256 hash
        hash_obj = hashlib.sha256(data)
        hash_hex = hash_obj.hexdigest()
        
        # Create path with parent directories
        path = self._hash_to_path(hash_hex)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Only write if doesn't exist (content-addressed, so same hash = same content)
        if not path.exists():
            path.write_bytes(data)
        
        return hash_hex
    
    def get(self, hash_hex: str) -> Optional[bytes]:
        """Retrieve data by its content hash.
        
        Args:
            hash_hex: Hex-encoded SHA-256 hash
            
        Returns:
            Binary data or None if not found
        """
        path = self._hash_to_path(hash_hex)
        if path.exists():
            return path.read_bytes()
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