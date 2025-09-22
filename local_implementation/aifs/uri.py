"""AIFS URI Schemes

Implements canonical identifiers as specified in the AIFS architecture:
- aifs://<blake3-hash> for Asset IDs
- aifs-snap://<blake3-hash> for Snapshot IDs
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


class AIFSUri:
    """AIFS URI parser and generator."""
    
    # BLAKE3 hash pattern (64 hex characters, lowercase)
    BLAKE3_PATTERN = re.compile(r'^[a-f0-9]{64}$')
    
    @staticmethod
    def is_valid_blake3_hash(hash_str: str) -> bool:
        """Check if string is a valid BLAKE3 hash.
        
        Args:
            hash_str: String to validate
            
        Returns:
            True if valid BLAKE3 hash, False otherwise
        """
        return bool(AIFSUri.BLAKE3_PATTERN.match(hash_str))
    
    @staticmethod
    def asset_id_to_uri(asset_id: str) -> str:
        """Convert Asset ID to aifs:// URI.
        
        Args:
            asset_id: BLAKE3 hash of the asset
            
        Returns:
            aifs:// URI string
            
        Raises:
            ValueError: If asset_id is not a valid BLAKE3 hash
        """
        if not AIFSUri.is_valid_blake3_hash(asset_id):
            raise ValueError(f"Invalid BLAKE3 hash: {asset_id}")
        
        return f"aifs://{asset_id}"
    
    @staticmethod
    def snapshot_id_to_uri(snapshot_id: str) -> str:
        """Convert Snapshot ID to aifs-snap:// URI.
        
        Args:
            snapshot_id: BLAKE3 hash of the snapshot
            
        Returns:
            aifs-snap:// URI string
            
        Raises:
            ValueError: If snapshot_id is not a valid BLAKE3 hash
        """
        if not AIFSUri.is_valid_blake3_hash(snapshot_id):
            raise ValueError(f"Invalid BLAKE3 hash: {snapshot_id}")
        
        return f"aifs-snap://{snapshot_id}"
    
    @staticmethod
    def parse_asset_uri(uri: str) -> Optional[str]:
        """Parse aifs:// URI to extract Asset ID.
        
        Args:
            uri: aifs:// URI string
            
        Returns:
            Asset ID (BLAKE3 hash) or None if invalid
        """
        try:
            parsed = urlparse(uri)
            if parsed.scheme != 'aifs':
                return None
            
            # Remove leading slash if present
            asset_id = parsed.path.lstrip('/')
            
            # Handle case where there's no path (just scheme://)
            if not asset_id and parsed.netloc:
                asset_id = parsed.netloc
            
            if AIFSUri.is_valid_blake3_hash(asset_id):
                return asset_id
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def parse_snapshot_uri(uri: str) -> Optional[str]:
        """Parse aifs-snap:// URI to extract Snapshot ID.
        
        Args:
            uri: aifs-snap:// URI string
            
        Returns:
            Snapshot ID (BLAKE3 hash) or None if invalid
        """
        try:
            parsed = urlparse(uri)
            if parsed.scheme != 'aifs-snap':
                return None
            
            # Remove leading slash if present
            snapshot_id = parsed.path.lstrip('/')
            
            # Handle case where there's no path (just scheme://)
            if not snapshot_id and parsed.netloc:
                snapshot_id = parsed.netloc
            
            if AIFSUri.is_valid_blake3_hash(snapshot_id):
                return snapshot_id
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def parse_uri(uri: str) -> Tuple[Optional[str], str]:
        """Parse any AIFS URI to extract ID and type.
        
        Args:
            uri: AIFS URI string
            
        Returns:
            Tuple of (ID, type) where type is 'asset', 'snapshot', or 'unknown'
        """
        # Try asset URI first
        asset_id = AIFSUri.parse_asset_uri(uri)
        if asset_id:
            return asset_id, 'asset'
        
        # Try snapshot URI
        snapshot_id = AIFSUri.parse_snapshot_uri(uri)
        if snapshot_id:
            return snapshot_id, 'snapshot'
        
        return None, 'unknown'
    
    @staticmethod
    def validate_uri(uri: str) -> bool:
        """Validate if URI is a valid AIFS URI.
        
        Args:
            uri: URI string to validate
            
        Returns:
            True if valid AIFS URI, False otherwise
        """
        id_val, uri_type = AIFSUri.parse_uri(uri)
        return uri_type in ['asset', 'snapshot']


# Convenience functions for common operations
def asset_uri(asset_id: str) -> str:
    """Create aifs:// URI for asset ID."""
    return AIFSUri.asset_id_to_uri(asset_id)


def snapshot_uri(snapshot_id: str) -> str:
    """Create aifs-snap:// URI for snapshot ID."""
    return AIFSUri.snapshot_id_to_uri(snapshot_id)


def parse_asset_uri(uri: str) -> Optional[str]:
    """Parse aifs:// URI to get asset ID."""
    return AIFSUri.parse_asset_uri(uri)


def parse_snapshot_uri(uri: str) -> Optional[str]:
    """Parse aifs-snap:// URI to get snapshot ID."""
    return AIFSUri.parse_snapshot_uri(uri)
