"""AIFS Asset Management

Implements core asset management functionality with proper Merkle trees and signatures.
Uses BLAKE3 for content addressing as specified in the AIFS architecture.
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
from .uri import AIFSUri


class AssetManager:
    """Asset manager for AIFS.
    
    Integrates storage, vector database, metadata components, and cryptographic operations.
    Uses BLAKE3 for content addressing as specified in the AIFS architecture.
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
            Asset ID (BLAKE3 hash)
        """
        # Store data and get content hash
        asset_id = self.storage.put(data)
        
        # Validate that we got a proper BLAKE3 hash
        if not AIFSUri.is_valid_blake3_hash(asset_id):
            raise ValueError(f"Storage returned invalid hash: {asset_id}")
        
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
    
    def list_assets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List assets.
        
        Args:
            limit: Maximum number of assets to return
            offset: Number of assets to skip
            
        Returns:
            List of asset metadata dictionaries
        """
        return self.metadata_db.list_assets(limit=limit, offset=offset)
    
    def get_asset_uri(self, asset_id: str) -> str:
        """Get aifs:// URI for an asset.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            
        Returns:
            aifs:// URI string
        """
        return AIFSUri.asset_id_to_uri(asset_id)
    
    def get_snapshot_uri(self, snapshot_id: str) -> str:
        """Get aifs-snap:// URI for a snapshot.
        
        Args:
            snapshot_id: Snapshot ID (BLAKE3 hash)
            
        Returns:
            aifs-snap:// URI string
        """
        return AIFSUri.snapshot_id_to_uri(snapshot_id)
    
    def parse_asset_uri(self, uri: str) -> Optional[str]:
        """Parse aifs:// URI to get asset ID.
        
        Args:
            uri: aifs:// URI string
            
        Returns:
            Asset ID or None if invalid
        """
        return AIFSUri.parse_asset_uri(uri)
    
    def parse_snapshot_uri(self, uri: str) -> Optional[str]:
        """Parse aifs-snap:// URI to get snapshot ID.
        
        Args:
            uri: aifs-snap:// URI string
            
        Returns:
            Snapshot ID or None if invalid
        """
        return AIFSUri.parse_snapshot_uri(uri)
    
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
    
    def verify_snapshot(self, snapshot_id: str, public_key: bytes = None) -> bool:
        """Verify a snapshot's signature.
        
        Args:
            snapshot_id: ID of the snapshot to verify
            public_key: Public key for verification (uses default if None)
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            snapshot = self.metadata_db.get_snapshot(snapshot_id)
            if not snapshot:
                return False
            
            # Get the public key to use
            if public_key is None:
                public_key = self.crypto_manager.get_public_key()
            
            # Extract signature and data
            signature_hex = snapshot.get("signature")
            if not signature_hex:
                return False
            
            # Reconstruct the data that was signed
            merkle_root = snapshot.get("merkle_root", "")
            timestamp = snapshot.get("created_at", "")
            namespace = snapshot.get("namespace", "")
            
            # Verify the signature
            is_valid = self.crypto_manager.verify_snapshot_signature(
                signature_hex, merkle_root, timestamp, namespace, public_key
            )
            
            return is_valid
            
        except Exception as e:
            print(f"Snapshot verification failed: {e}")
            return False
    
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
    
    def delete_asset(self, asset_id: str, force: bool = False) -> bool:
        """Delete an asset.
        
        Args:
            asset_id: Asset ID to delete
            force: If True, delete even if referenced by other assets
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Check if asset exists
            asset = self.get_asset(asset_id)
            if not asset:
                return False
            
            # Check if asset is referenced by other assets (unless force=True)
            if not force:
                children = self.metadata_db.get_children(asset_id)
                if children:
                    raise ValueError(f"Asset {asset_id} is referenced by {len(children)} other assets. Use force=True to delete anyway.")
            
            # Remove from vector database if it has an embedding
            try:
                self.vector_db.remove(asset_id)
            except:
                pass  # Ignore if not in vector DB
            
            # Remove from storage
            self.storage.delete(asset_id)
            
            # Remove from metadata database
            # Note: This would need a delete_asset method in metadata_db
            # For now, we'll just mark it as deleted in metadata
            self.metadata_db.add_asset(asset_id, "deleted", 0, {"deleted": True})
            
            return True
        except Exception as e:
            logging.error(f"Error deleting asset {asset_id}: {e}")
            return False