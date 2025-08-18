"""AIFS Merkle Tree Implementation

Implements Merkle tree functionality for snapshots.
Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
"""

import hashlib
from typing import List, Dict, Optional, Tuple


class MerkleNode:
    """Represents a node in the Merkle tree."""
    
    def __init__(self, hash_value: str, left: Optional['MerkleNode'] = None, 
                 right: Optional['MerkleNode'] = None, is_leaf: bool = False):
        self.hash_value = hash_value
        self.left = left
        self.right = right
        self.is_leaf = is_leaf
    
    def __repr__(self):
        return f"MerkleNode(hash={self.hash_value[:8]}..., leaf={self.is_leaf})"


class MerkleTree:
    """Merkle tree implementation for AIFS snapshots.
    
    Builds a binary Merkle tree from asset IDs and provides methods for
    verification and proof generation.
    Note: Using SHA-256 instead of BLAKE3 to avoid Rust dependency.
    """
    
    def __init__(self, asset_ids: List[str]):
        """Initialize Merkle tree with asset IDs.
        
        Args:
            asset_ids: List of asset IDs (SHA-256 hashes)
        """
        # Sort asset IDs for deterministic tree structure
        self.asset_ids = sorted(asset_ids)
        self.root = self._build_tree()
    
    def _build_tree(self) -> MerkleNode:
        """Build Merkle tree from asset IDs.
        
        Returns:
            Root node of the Merkle tree
        """
        if not self.asset_ids:
            # Empty tree
            empty_hash = hashlib.sha256(b"").hexdigest()
            return MerkleNode(empty_hash, is_leaf=True)
        
        if len(self.asset_ids) == 1:
            # Single leaf
            return MerkleNode(self.asset_ids[0], is_leaf=True)
        
        # Create leaf nodes
        leaves = [MerkleNode(asset_id, is_leaf=True) for asset_id in self.asset_ids]
        
        # Build tree bottom-up
        current_level = leaves
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Compute parent hash
                parent_hash = self._hash_pair(left.hash_value, right.hash_value)
                parent = MerkleNode(parent_hash, left, right)
                next_level.append(parent)
            
            current_level = next_level
        
        return current_level[0]
    
    def _hash_pair(self, left_hash: str, right_hash: str) -> str:
        """Hash a pair of hashes.
        
        Args:
            left_hash: Left hash value
            right_hash: Right hash value
            
        Returns:
            Hash of the concatenated pair
        """
        # Concatenate hashes and compute SHA-256
        combined = f"{left_hash}:{right_hash}".encode()
        return hashlib.sha256(combined).hexdigest()
    
    def get_root_hash(self) -> str:
        """Get the root hash of the Merkle tree.
        
        Returns:
            Root hash as hex string
        """
        return self.root.hash_value
    
    def get_proof(self, asset_id: str) -> Optional[List[Tuple[str, bool]]]:
        """Get Merkle proof for an asset ID.
        
        Args:
            asset_id: Asset ID (SHA-256 hash)
            
        Returns:
            List of (hash, is_right) tuples representing the proof path,
            or None if asset not found
        """
        if asset_id not in self.asset_ids:
            return None
        
        proof = []
        current = self.root
        
        # Navigate to the leaf node
        while not current.is_leaf:
            if current.left and asset_id in self._get_leaf_hashes(current.left):
                # Asset is in left subtree
                if current.right:
                    proof.append((current.right.hash_value, True))  # Right sibling
                current = current.left
            elif current.right and asset_id in self._get_leaf_hashes(current.right):
                # Asset is in right subtree
                if current.left:
                    proof.append((current.left.hash_value, False))  # Left sibling
                current = current.right
            else:
                # Asset not found in this subtree
                return None
        
        return proof
    
    def _get_leaf_hashes(self, node: MerkleNode) -> List[str]:
        """Get all leaf hashes under a node.
        
        Args:
            node: Node to get leaves from
            
        Returns:
            List of leaf hashes
        """
        if node.is_leaf:
            return [node.hash_value]
        
        leaves = []
        if node.left:
            leaves.extend(self._get_leaf_hashes(node.left))
        if node.right:
            leaves.extend(self._get_leaf_hashes(node.right))
        return leaves
    
    def verify_proof(self, asset_id: str, proof: List[Tuple[str, bool]], root_hash: str) -> bool:
        """Verify a Merkle proof.
        
        Args:
            asset_id: Asset ID being proven
            proof: Merkle proof from get_proof()
            root_hash: Expected root hash
            
        Returns:
            True if proof is valid, False otherwise
        """
        current_hash = asset_id
        
        for sibling_hash, is_right in proof:
            if is_right:
                # Sibling is on the right, so current is on the left
                current_hash = self._hash_pair(current_hash, sibling_hash)
            else:
                # Sibling is on the left, so current is on the right
                current_hash = self._hash_pair(sibling_hash, current_hash)
        
        return current_hash == root_hash
    
    def get_tree_structure(self) -> Dict:
        """Get a representation of the tree structure for debugging.
        
        Returns:
            Dictionary representing the tree structure
        """
        def _node_to_dict(node: MerkleNode) -> Dict:
            if node.is_leaf:
                return {
                    "hash": node.hash_value[:8] + "...",
                    "type": "leaf"
                }
            else:
                return {
                    "hash": node.hash_value[:8] + "...",
                    "type": "internal",
                    "left": _node_to_dict(node.left) if node.left else None,
                    "right": _node_to_dict(node.right) if node.right else None
                }
        
        return _node_to_dict(self.root)
