"""AIFS Asset Management

Implements core asset management functionality.
"""

import os
import pathlib
from typing import Dict, List, Optional, Union, BinaryIO, Any
import numpy as np

from .storage import StorageBackend
from .vector_db import VectorDB
from .metadata import MetadataStore


class AssetManager:
    """Asset manager for AIFS.
    
    Integrates storage, vector database, and metadata components.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], embedding_dim: int = 128):
        """Initialize asset manager.
        
        Args:
            root_dir: Root directory for storage
            embedding_dim: Dimension of embedding vectors (default: 128 for testing)
        """
        self.root_dir = pathlib.Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.storage = StorageBackend(self.root_dir / "storage")
        self.vector_db = VectorDB(str(self.root_dir / "vectors"), dimension=embedding_dim)
        self.metadata_db = MetadataStore(str(self.root_dir / "metadata.db"))
    
    def put_asset(self, data: bytes, kind: str = "blob", 
                 embedding: Optional[np.ndarray] = None,
                 metadata: Optional[Dict] = None,
                 parents: Optional[List[Dict]] = None) -> str:
        """Store an asset.
        
        Args:
            data: Asset data
            kind: Asset kind (blob, tensor, embed, artifact)
            embedding: Optional embedding vector
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets with transform info
                     [{"asset_id": str, "transform_name": str, "transform_digest": str}]
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Store data and get content hash
        asset_id = self.storage.put(data)
        
        # Store metadata
        self.metadata_db.add_asset(asset_id, kind, len(data), metadata)
        
        # Store embedding if provided
        if embedding is not None:
            self.vector_db.add(asset_id, embedding)
        
        # Add lineage information if parents provided
        if parents:
            for parent in parents:
                parent_id = parent["asset_id"]
                transform_name = parent.get("transform_name")
                transform_digest = parent.get("transform_digest")
                
                self.metadata_db.add_lineage(
                    child_id=asset_id,
                    parent_id=parent_id,
                    transform_name=transform_name,
                    transform_digest=transform_digest
                )
        
        return asset_id
    
    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Retrieve an asset.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            
        Returns:
            Asset dictionary or None if not found
        """
        # Get data from storage
        data = self.storage.get(asset_id)
        if data is None:
            return None
        
        # Get metadata
        metadata = self.metadata_db.get_asset(asset_id)
        if metadata is None:
            # This shouldn't happen if storage has the data
            # But handle it gracefully
            metadata = {
                "asset_id": asset_id,
                "kind": "blob",
                "size": len(data),
                "created_at": None,
                "metadata": {}
            }
        
        # Get lineage
        parents = self.metadata_db.get_parents(asset_id)
        children = self.metadata_db.get_children(asset_id)
        
        # Combine everything
        return {
            **metadata,
            "data": data,
            "parents": parents,
            "children": children
        }
    
    def vector_search(self, query_embedding: np.ndarray, k: int = 10) -> List[Dict]:
        """Search for similar assets.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            List of asset dictionaries with similarity scores
        """
        # Search vector database
        results = self.vector_db.search(query_embedding, k)
        
        # Get full asset metadata for each result
        assets = []
        for asset_id, score in results:
            asset = self.get_asset(asset_id)
            if asset:
                asset["score"] = score
                assets.append(asset)
        
        return assets
    
    def create_snapshot(self, namespace: str, asset_ids: List[str], 
                       metadata: Optional[Dict] = None) -> str:
        """Create a snapshot of assets.
        
        Args:
            namespace: Namespace for the snapshot
            asset_ids: List of asset IDs to include
            metadata: Optional metadata dictionary
            
        Returns:
            Snapshot ID
        """
        import hashlib
        
        # Sort asset IDs for deterministic merkle root
        sorted_ids = sorted(asset_ids)
        
        # Compute merkle root (simplified for this implementation)
        # In a full implementation, you'd build a proper merkle tree
        merkle_input = ":".join(sorted_ids).encode()
        merkle_root = hashlib.sha256(merkle_input).hexdigest()
        
        # Create snapshot
        snapshot_id = self.metadata_db.create_snapshot(namespace, merkle_root, metadata)
        
        # Add assets to snapshot
        for asset_id in asset_ids:
            self.metadata_db.add_asset_to_snapshot(snapshot_id, asset_id)
        
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot dictionary or None if not found
        """
        return self.metadata_db.get_snapshot(snapshot_id)