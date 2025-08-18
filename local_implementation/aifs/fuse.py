"""AIFS FUSE Layer

Provides POSIX compatibility for AIFS using FUSE.
"""

import os
import stat
import errno
from datetime import datetime
from typing import Dict, List, Optional, Union

from fuse import FUSE, FuseOSError, Operations

from .client import AIFSClient


class AIFSFuse(Operations):
    """FUSE operations for AIFS.
    
    Exposes AIFS assets as a POSIX-compatible filesystem.
    """
    
    def __init__(self, client: AIFSClient, namespace: str = "default"):
        """Initialize FUSE operations.
        
        Args:
            client: AIFS client
            namespace: AIFS namespace to expose
        """
        self.client = client
        self.namespace = namespace
        self.fd = 0
        self.asset_cache = {}  # Cache for asset metadata
    
    def _parse_path(self, path: str) -> Dict:
        """Parse path into components.
        
        Args:
            path: Path string
            
        Returns:
            Dictionary with path components
        """
        # Remove leading slash
        if path.startswith("/"):
            path = path[1:]
        
        # Split path
        parts = path.split("/")
        
        if not parts or parts[0] == "":
            # Root directory
            return {"type": "root"}
        
        if len(parts) == 1:
            # Asset ID
            return {"type": "asset", "asset_id": parts[0]}
        
        # Invalid path
        return {"type": "invalid"}
    
    def getattr(self, path: str, fh=None) -> Dict:
        """Get file attributes.
        
        Args:
            path: File path
            fh: File handle
            
        Returns:
            Dictionary with file attributes
        """
        now = int(datetime.now().timestamp())
        parsed = self._parse_path(path)
        
        if parsed["type"] == "root":
            # Root directory
            return {
                "st_mode": stat.S_IFDIR | 0o755,
                "st_nlink": 2,
                "st_size": 0,
                "st_ctime": now,
                "st_mtime": now,
                "st_atime": now
            }
        
        if parsed["type"] == "asset":
            # Asset file
            asset_id = parsed["asset_id"]
            
            # Check cache
            if asset_id in self.asset_cache:
                asset = self.asset_cache[asset_id]
            else:
                # Get asset metadata
                asset = self.client.get_asset(asset_id, include_data=False)
                if not asset:
                    raise FuseOSError(errno.ENOENT)
                
                # Cache asset metadata
                self.asset_cache[asset_id] = asset
            
            # Parse created_at timestamp
            if asset["created_at"]:
                try:
                    created_at = datetime.fromisoformat(asset["created_at"]).timestamp()
                except ValueError:
                    created_at = now
            else:
                created_at = now
            
            return {
                "st_mode": stat.S_IFREG | 0o444,  # Read-only file
                "st_nlink": 1,
                "st_size": asset["size"],
                "st_ctime": created_at,
                "st_mtime": created_at,
                "st_atime": now
            }
        
        # Invalid path
        raise FuseOSError(errno.ENOENT)
    
    def readdir(self, path: str, fh) -> List[str]:
        """Read directory contents.
        
        Args:
            path: Directory path
            fh: File handle
            
        Returns:
            List of directory entries
        """
        parsed = self._parse_path(path)
        
        if parsed["type"] == "root":
            # Get latest snapshot for namespace
            # In a real implementation, you'd have a proper way to list assets
            # For this demo, we'll just return a few hardcoded asset IDs
            return [".", "..", "README.md", "example.txt"]
        
        # Not a directory
        raise FuseOSError(errno.ENOTDIR)
    
    def open(self, path: str, flags) -> int:
        """Open a file.
        
        Args:
            path: File path
            flags: Open flags
            
        Returns:
            File handle
        """
        parsed = self._parse_path(path)
        
        if parsed["type"] != "asset":
            raise FuseOSError(errno.ENOENT)
        
        # Check if asset exists
        asset_id = parsed["asset_id"]
        asset = self.client.get_asset(asset_id, include_data=False)
        if not asset:
            raise FuseOSError(errno.ENOENT)
        
        # Cache asset metadata
        self.asset_cache[asset_id] = asset
        
        # Return file handle
        self.fd += 1
        return self.fd
    
    def read(self, path: str, size: int, offset: int, fh) -> bytes:
        """Read from a file.
        
        Args:
            path: File path
            size: Number of bytes to read
            offset: Offset to start reading from
            fh: File handle
            
        Returns:
            Bytes read
        """
        parsed = self._parse_path(path)
        
        if parsed["type"] != "asset":
            raise FuseOSError(errno.ENOENT)
        
        # Get asset
        asset_id = parsed["asset_id"]
        asset = self.client.get_asset(asset_id, include_data=True)
        if not asset or "data" not in asset:
            raise FuseOSError(errno.ENOENT)
        
        # Return data slice
        return asset["data"][offset:offset+size]


def mount(mountpoint: str, server_address: str = "localhost:50051", namespace: str = "default", foreground: bool = True):
    """Mount AIFS as a POSIX filesystem.
    
    Args:
        mountpoint: Directory to mount AIFS at
        server_address: Address of the AIFS server
        namespace: AIFS namespace to expose
        foreground: Whether to run in foreground
    """
    # Create client
    client = AIFSClient(server_address)
    
    # Create FUSE operations
    operations = AIFSFuse(client, namespace)
    
    # Mount filesystem
    FUSE(operations, mountpoint, foreground=foreground, nothreads=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Mount AIFS as a POSIX filesystem")
    parser.add_argument("mountpoint", type=str, help="Directory to mount AIFS at")
    parser.add_argument("--server", type=str, default="localhost:50051", help="Address of the AIFS server")
    parser.add_argument("--namespace", type=str, default="default", help="AIFS namespace to expose")
    parser.add_argument("--background", action="store_true", help="Run in background")
    
    args = parser.parse_args()
    
    mount(args.mountpoint, args.server, args.namespace, not args.background)