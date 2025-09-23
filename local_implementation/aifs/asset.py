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
from .asset_kinds_simple import SimpleAssetKindEncoder as AssetKindEncoder, SimpleAssetKindValidator as AssetKindValidator, AssetKind, TensorData, EmbeddingData, ArtifactData
from .transaction import TransactionManager, StrongCausalityManager


class AssetManager:
    """Asset manager for AIFS.
    
    Integrates storage, vector database, metadata components, and cryptographic operations.
    Uses BLAKE3 for content addressing as specified in the AIFS architecture.
    """
    
    def __init__(self, root_dir: Union[str, pathlib.Path], embedding_dim: int = 128,
                 private_key: Optional[bytes] = None, enable_strong_causality: bool = True):
        """Initialize asset manager.
        
        Args:
            root_dir: Root directory for storage
            embedding_dim: Dimension of embedding vectors (default: 128 for testing)
            private_key: Optional Ed25519 private key for signing snapshots
            enable_strong_causality: Enable strong causality guarantees
        """
        self.root_dir = pathlib.Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.storage = StorageBackend(self.root_dir / "storage")
        self.vector_db = VectorDB(str(self.root_dir / "vectors"), dimension=embedding_dim)
        self.metadata_db = MetadataStore(str(self.root_dir / "metadata.db"))
        self.crypto_manager = CryptoManager(private_key)
        
        # Transaction and strong causality management
        self.enable_strong_causality = enable_strong_causality
        if enable_strong_causality:
            self.transaction_manager = TransactionManager(str(self.root_dir / "transactions.db"))
            self.causality_manager = StrongCausalityManager(self.transaction_manager, self.metadata_db)
        else:
            self.transaction_manager = None
            self.causality_manager = None
    
    def put_asset(self, data: bytes, kind: str = "blob", 
                 embedding: Optional[np.ndarray] = None,
                 metadata: Optional[Dict] = None,
                 parents: Optional[List[Dict]] = None,
                 transaction_id: Optional[str] = None) -> str:
        """Store an asset.
        
        Args:
            data: Asset data
            kind: Asset kind (blob, tensor, embed, artifact)
            embedding: Optional embedding vector
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets with transform info
                     [{"asset_id": str, "transform_name": str, "transform_digest": str}]
            transaction_id: Optional transaction ID for strong causality
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Validate asset kind and data
        if not self._validate_asset_kind(kind, data):
            raise ValueError(f"Invalid {kind} asset data")
        
        # Store data and get content hash
        asset_id = self.storage.put(data)
        
        # Validate that we got a proper BLAKE3 hash
        if not AIFSUri.is_valid_blake3_hash(asset_id):
            raise ValueError(f"Storage returned invalid hash: {asset_id}")
        
        # Use strong causality if enabled
        if self.enable_strong_causality and self.causality_manager:
            # Store asset with strong causality
            asset_data = {
                "kind": kind,
                "size": len(data),
                "metadata": metadata or {}
            }
            
            if transaction_id is None:
                transaction_id = self.causality_manager.put_asset_with_causality(
                    asset_id=asset_id,
                    asset_data=asset_data,
                    parents=parents
                )
                # Auto-commit the transaction for immediate visibility
                success = self.transaction_manager.commit_transaction(transaction_id)
                if not success:
                    state = self.transaction_manager.get_transaction_state(transaction_id)
                    deps_committed = self.transaction_manager.check_dependencies_committed(transaction_id)
                    raise RuntimeError(f"Failed to commit asset {asset_id} for immediate visibility. State: {state}, Dependencies committed: {deps_committed}")
            else:
                # Add to existing transaction
                success = self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
                if not success:
                    raise ValueError(f"Failed to add asset {asset_id} to transaction {transaction_id}")
                
                if parents:
                    for parent in parents:
                        self.transaction_manager.add_dependency(transaction_id, parent["asset_id"])
                
                # Store metadata (not visible yet)
                self.metadata_db.add_asset(asset_id, kind, len(data), metadata)
                
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
            
            # Store embedding if provided
            if embedding is not None:
                self.vector_db.add(asset_id, embedding)
            
            return asset_id
        else:
            # Legacy behavior without strong causality
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
    
    def begin_transaction(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Begin a new transaction for atomic operations.
        
        Args:
            metadata: Optional transaction metadata
            
        Returns:
            Transaction ID
        """
        if not self.enable_strong_causality or not self.transaction_manager:
            raise RuntimeError("Strong causality is not enabled")
        
        return self.transaction_manager.begin_transaction(metadata)
    
    def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a transaction and make assets visible.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enable_strong_causality or not self.transaction_manager:
            raise RuntimeError("Strong causality is not enabled")
        
        return self.transaction_manager.commit_transaction(transaction_id)
    
    def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback a transaction.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enable_strong_causality or not self.transaction_manager:
            raise RuntimeError("Strong causality is not enabled")
        
        return self.transaction_manager.rollback_transaction(transaction_id)
    
    def is_asset_visible(self, asset_id: str) -> bool:
        """Check if an asset is visible (strong causality).
        
        Args:
            asset_id: Asset ID
            
        Returns:
            True if asset is visible, False otherwise
        """
        if not self.enable_strong_causality or not self.transaction_manager:
            # Without strong causality, all assets are immediately visible
            return True
        
        return self.transaction_manager.is_asset_visible(asset_id)
    
    def get_visible_assets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get only visible assets (strong causality).
        
        Args:
            limit: Maximum number of assets to return
            offset: Number of assets to skip
            
        Returns:
            List of visible asset metadata
        """
        if not self.enable_strong_causality or not self.causality_manager:
            # Without strong causality, return all assets
            return self.metadata_db.list_assets(limit=limit, offset=offset)
        
        return self.causality_manager.get_visible_assets(limit=limit, offset=offset)
    
    def get_asset_with_causality(self, asset_id: str) -> Optional[Dict]:
        """Get an asset only if it's visible (strong causality).
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Asset metadata if visible, None otherwise
        """
        if not self.enable_strong_causality or not self.causality_manager:
            # Without strong causality, return asset if it exists
            return self.metadata_db.get_asset(asset_id)
        
        return self.causality_manager.get_asset_with_causality(asset_id)
    
    def wait_for_dependencies(self, transaction_id: str, timeout_seconds: float = 30.0) -> bool:
        """Wait for all dependencies to be committed.
        
        Args:
            transaction_id: Transaction ID
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if all dependencies committed, False if timeout
        """
        if not self.enable_strong_causality or not self.causality_manager:
            raise RuntimeError("Strong causality is not enabled")
        
        return self.causality_manager.wait_for_dependencies(transaction_id, timeout_seconds)
    
    def put_tensor(self, tensor_data: TensorData, 
                   embedding: Optional[np.ndarray] = None,
                   metadata: Optional[Dict] = None,
                   parents: Optional[List[Dict]] = None) -> str:
        """Store a tensor asset.
        
        Args:
            tensor_data: TensorData object with tensor information
            embedding: Optional embedding vector
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Encode tensor data
        encoded_data = AssetKindEncoder.encode_tensor(tensor_data)
        
        # Merge tensor metadata with provided metadata
        combined_metadata = tensor_data.metadata or {}
        if metadata:
            combined_metadata.update(metadata)
        
        return self.put_asset(encoded_data, "tensor", embedding, combined_metadata, parents)
    
    def put_embedding(self, embedding_data: EmbeddingData,
                     metadata: Optional[Dict] = None,
                     parents: Optional[List[Dict]] = None) -> str:
        """Store an embedding asset.
        
        Args:
            embedding_data: EmbeddingData object with embedding information
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Encode embedding data
        encoded_data = AssetKindEncoder.encode_embedding(embedding_data)
        
        # Create metadata from embedding data
        combined_metadata = {
            'model': embedding_data.model,
            'dimension': embedding_data.dimension,
            'distance_metric': embedding_data.distance_metric,
            'model_version': embedding_data.model_version,
            'framework': embedding_data.framework,
            'confidence': embedding_data.confidence
        }
        if metadata:
            combined_metadata.update(metadata)
        
        return self.put_asset(encoded_data, "embed", None, combined_metadata, parents)
    
    def put_artifact(self, artifact_data: ArtifactData,
                    metadata: Optional[Dict] = None,
                    parents: Optional[List[Dict]] = None) -> str:
        """Store an artifact asset.
        
        Args:
            artifact_data: ArtifactData object with artifact information
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Encode artifact data
        encoded_data = AssetKindEncoder.encode_artifact(artifact_data)
        
        # Merge artifact manifest with provided metadata
        combined_metadata = artifact_data.manifest.copy()
        if metadata:
            combined_metadata.update(metadata)
        
        return self.put_asset(encoded_data, "artifact", None, combined_metadata, parents)
    
    def get_tensor(self, asset_id: str) -> Optional[TensorData]:
        """Get a tensor asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            TensorData object or None if not found
        """
        asset = self.get_asset(asset_id)
        if not asset or asset.get("kind") != "tensor":
            return None
        
        try:
            return AssetKindEncoder.decode_tensor(asset["data"])
        except Exception as e:
            print(f"Error decoding tensor: {e}")
            return None
    
    def get_embedding(self, asset_id: str) -> Optional[EmbeddingData]:
        """Get an embedding asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            EmbeddingData object or None if not found
        """
        asset = self.get_asset(asset_id)
        if not asset or asset.get("kind") != "embed":
            return None
        
        try:
            return AssetKindEncoder.decode_embedding(asset["data"])
        except Exception as e:
            print(f"Error decoding embedding: {e}")
            return None
    
    def get_artifact(self, asset_id: str) -> Optional[ArtifactData]:
        """Get an artifact asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            ArtifactData object or None if not found
        """
        asset = self.get_asset(asset_id)
        if not asset or asset.get("kind") != "artifact":
            return None
        
        try:
            return AssetKindEncoder.decode_artifact(asset["data"])
        except Exception as e:
            print(f"Error decoding artifact: {e}")
            return None
    
    def _validate_asset_kind(self, kind: str, data: bytes) -> bool:
        """Validate asset data according to its kind.
        
        Args:
            kind: Asset kind
            data: Asset data
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if kind == "blob":
                return AssetKindValidator.validate_blob(data)
            elif kind == "tensor":
                return AssetKindValidator.validate_tensor(data)
            elif kind == "embed":
                return AssetKindValidator.validate_embedding(data)
            elif kind == "artifact":
                return AssetKindValidator.validate_artifact(data)
            else:
                return False
        except Exception:
            return False
    
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