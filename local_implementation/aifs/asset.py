"""AIFS Asset Management

Implements core asset management functionality with proper Merkle trees and signatures.
Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
"""

import os
import pathlib
from typing import Dict, List, Optional, Union, BinaryIO, Any
import numpy as np

from .storage import StorageBackend
from .vector_db import VectorDB
from .metadata import MetadataStore
from .merkle import MerkleTree
from .crypto import CryptoManager


class AssetManager:
    """Asset manager for AIFS.
    
    Integrates storage, vector database, metadata components, and cryptographic operations.
    Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], embedding_dim: int = 128,
                 private_key: Optional[bytes] = None):
        """Initialize asset manager.
        
        Args:
            root_dir: Root directory for storage
            embedding_dim: Dimension of embedding vectors (default: 128 for testing)
            private_key: Optional Ed25519 private key for signing snapshots
        """
        self.root_dir = pathlib.Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.storage = StorageBackend(self.root_dir / "storage")
        self.vector_db = VectorDB(str(self.root_dir / "vectors"), dimension=embedding_dim)
        self.metadata_db = MetadataStore(str(self.root_dir / "metadata.db"))
        self.crypto_manager = CryptoManager(private_key)
    
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
            Asset ID (SHA-256 hash)
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
            asset_id: Asset ID (SHA-256 hash)
            
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
        """Create a snapshot of assets with proper Merkle tree and Ed25519 signature.
        
        Args:
            namespace: Namespace for the snapshot
            asset_ids: List of asset IDs to include
            metadata: Optional metadata dictionary
            
        Returns:
            Snapshot ID
        """
        from datetime import datetime
        
        # Create Merkle tree from asset IDs
        merkle_tree = MerkleTree(asset_ids)
        merkle_root = merkle_tree.get_root_hash()
        
        # Get current timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Sign the snapshot with Ed25519
        signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
            merkle_root, timestamp, namespace
        )
        
        # Create snapshot with signature
        snapshot_id = self.metadata_db.create_snapshot(
            namespace, merkle_root, metadata, signature_hex, timestamp
        )
        
        # Add assets to snapshot
        for asset_id in asset_ids:
            self.metadata_db.add_asset_to_snapshot(snapshot_id, asset_id)
        
        return snapshot_id
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot with verification information.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot dictionary or None if not found
        """
        snapshot = self.metadata_db.get_snapshot(snapshot_id)
        if not snapshot:
            return None
        
        # Add Merkle tree information
        asset_ids = [asset["asset_id"] for asset in snapshot["assets"]]
        merkle_tree = MerkleTree(asset_ids)
        
        snapshot["merkle_tree"] = merkle_tree.get_tree_structure()
        snapshot["merkle_proofs"] = {}
        
        # Generate proofs for each asset
        for asset_id in asset_ids:
            proof = merkle_tree.get_proof(asset_id)
            if proof:
                snapshot["merkle_proofs"][asset_id] = proof
        
        return snapshot
    
    def verify_snapshot(self, snapshot_id: str, public_key: bytes) -> bool:
        """Verify a snapshot's Ed25519 signature.
        
        Args:
            snapshot_id: Snapshot ID
            public_key: Public key for verification
            
        Returns:
            True if signature is valid, False otherwise
        """
        snapshot = self.metadata_db.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        
        # Verify signature
        return self.crypto_manager.verify_snapshot_signature(
            bytes.fromhex(snapshot["signature"]),
            snapshot["merkle_root"],
            snapshot["created_at"],
            snapshot["namespace"],
            public_key
        )
    
    def get_public_key(self) -> bytes:
        """Get the public key for snapshot verification.
        
        Returns:
            Public key bytes
        """
        return self.crypto_manager.get_public_key()
    
    def get_public_key_hex(self) -> str:
        """Get the public key as hex string.
        
        Returns:
            Public key as hex string
        """
        return self.crypto_manager.get_public_key_hex()