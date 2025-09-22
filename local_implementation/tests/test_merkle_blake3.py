#!/usr/bin/env python3
"""Tests for Merkle tree with BLAKE3 hashing."""

import unittest
import tempfile
import os
from pathlib import Path

from aifs.merkle import MerkleTree, MerkleNode


class TestMerkleTreeBLAKE3(unittest.TestCase):
    """Test Merkle tree implementation with BLAKE3."""
    
    def test_empty_tree(self):
        """Test empty Merkle tree."""
        tree = MerkleTree([])
        # Empty tree should have a root node with empty hash
        self.assertIsNotNone(tree.root)
        self.assertTrue(tree.root.is_leaf)
        self.assertEqual(len(tree.get_root_hash()), 64)  # BLAKE3 hash length
    
    def test_single_asset(self):
        """Test Merkle tree with single asset."""
        asset_id = "a" * 64  # 64 hex characters
        tree = MerkleTree([asset_id])
        
        self.assertIsNotNone(tree.root)
        self.assertTrue(tree.root.is_leaf)
        self.assertEqual(tree.root.hash_value, asset_id)
        self.assertEqual(tree.get_root_hash(), asset_id)
    
    def test_two_assets(self):
        """Test Merkle tree with two assets."""
        asset1 = "a" * 64
        asset2 = "b" * 64
        tree = MerkleTree([asset1, asset2])
        
        self.assertIsNotNone(tree.root)
        self.assertFalse(tree.root.is_leaf)
        self.assertIsNotNone(tree.root.left)
        self.assertIsNotNone(tree.root.right)
        
        # Root hash should be different from individual asset hashes
        root_hash = tree.get_root_hash()
        self.assertNotEqual(root_hash, asset1)
        self.assertNotEqual(root_hash, asset2)
        self.assertEqual(len(root_hash), 64)
    
    def test_three_assets(self):
        """Test Merkle tree with three assets."""
        assets = ["a" * 64, "b" * 64, "c" * 64]
        tree = MerkleTree(assets)
        
        self.assertIsNotNone(tree.root)
        self.assertFalse(tree.root.is_leaf)
        
        # Should have proper tree structure
        root_hash = tree.get_root_hash()
        self.assertEqual(len(root_hash), 64)
        self.assertNotEqual(root_hash, assets[0])
        self.assertNotEqual(root_hash, assets[1])
        self.assertNotEqual(root_hash, assets[2])
    
    def test_deterministic_ordering(self):
        """Test that assets are sorted deterministically."""
        assets = ["c" * 64, "a" * 64, "b" * 64]
        tree = MerkleTree(assets)
        
        # Should be sorted alphabetically
        self.assertEqual(tree.asset_ids, ["a" * 64, "b" * 64, "c" * 64])
    
    def test_deterministic_root_hash(self):
        """Test that same assets produce same root hash."""
        assets = ["a" * 64, "b" * 64, "c" * 64]
        tree1 = MerkleTree(assets)
        tree2 = MerkleTree(assets)
        
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())
    
    def test_different_ordering_same_hash(self):
        """Test that different ordering produces same hash."""
        assets1 = ["a" * 64, "b" * 64, "c" * 64]
        assets2 = ["c" * 64, "a" * 64, "b" * 64]
        
        tree1 = MerkleTree(assets1)
        tree2 = MerkleTree(assets2)
        
        # Should produce same hash due to sorting
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())
    
    def test_proof_generation(self):
        """Test Merkle proof generation."""
        assets = ["a" * 64, "b" * 64, "c" * 64, "d" * 64]
        tree = MerkleTree(assets)
        
        # Generate proof for first asset
        proof = tree.generate_proof(assets[0])
        self.assertIsNotNone(proof)
        self.assertGreater(len(proof), 0)
        
        # Verify proof
        root_hash = tree.get_root_hash()
        self.assertTrue(tree.verify_proof(assets[0], proof, root_hash))
    
    def test_proof_verification(self):
        """Test Merkle proof verification."""
        assets = ["a" * 64, "b" * 64, "c" * 64]
        tree = MerkleTree(assets)
        
        # Generate proof for middle asset
        proof = tree.generate_proof(assets[1])
        root_hash = tree.get_root_hash()
        
        # Should verify correctly
        self.assertTrue(tree.verify_proof(assets[1], proof, root_hash))
        
        # Should fail with wrong asset
        self.assertFalse(tree.verify_proof(assets[0], proof, root_hash))
        
        # Should fail with wrong root hash
        wrong_root = "x" * 64
        self.assertFalse(tree.verify_proof(assets[1], proof, wrong_root))
    
    def test_large_tree(self):
        """Test Merkle tree with many assets."""
        # Create 100 assets
        assets = [f"asset_{i:03d}" + "x" * (64 - 8) for i in range(100)]
        
        tree = MerkleTree(assets)
        
        # Should have valid root
        root_hash = tree.get_root_hash()
        self.assertEqual(len(root_hash), 64)
        
        # Should be able to generate proofs
        proof = tree.generate_proof(assets[50])
        self.assertTrue(tree.verify_proof(assets[50], proof, root_hash))
    
    def test_leaf_hashes(self):
        """Test getting leaf hashes."""
        assets = ["a" * 64, "b" * 64, "c" * 64]
        tree = MerkleTree(assets)
        
        leaf_hashes = tree.get_leaf_hashes()
        # Should have 3 unique assets
        self.assertEqual(len(set(leaf_hashes)), 3)
        self.assertEqual(set(leaf_hashes), set(assets))
    
    def test_tree_structure(self):
        """Test tree structure properties."""
        assets = ["a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64]
        tree = MerkleTree(assets)
        
        # Root should not be leaf
        self.assertFalse(tree.root.is_leaf)
        
        # All leaves should have is_leaf=True
        def check_leaves(node):
            if node.is_leaf:
                self.assertTrue(node.is_leaf)
                self.assertIsNone(node.left)
                self.assertIsNone(node.right)
            else:
                self.assertFalse(node.is_leaf)
                if node.left:
                    check_leaves(node.left)
                if node.right:
                    check_leaves(node.right)
        
        check_leaves(tree.root)
    
    def test_blake3_hashing(self):
        """Test that BLAKE3 is used for hashing."""
        # Test the hash_pair method directly
        tree = MerkleTree(["a" * 64, "b" * 64])
        
        # The hash_pair method should use BLAKE3
        hash1 = "a" * 64
        hash2 = "b" * 64
        combined_hash = tree._hash_pair(hash1, hash2)
        
        # Should be 64 hex characters
        self.assertEqual(len(combined_hash), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in combined_hash))
        
        # Should be different from input hashes
        self.assertNotEqual(combined_hash, hash1)
        self.assertNotEqual(combined_hash, hash2)
    
    def test_consistency_with_storage(self):
        """Test that Merkle tree is consistent with storage hashing."""
        from aifs.storage import StorageBackend
        
        # Create storage backend
        test_dir = tempfile.mkdtemp()
        storage = StorageBackend(test_dir)
        
        try:
            # Store some data
            data1 = b"Data 1"
            data2 = b"Data 2"
            
            hash1 = storage.put(data1)
            hash2 = storage.put(data2)
            
            # Create Merkle tree with these hashes
            tree = MerkleTree([hash1, hash2])
            root_hash = tree.get_root_hash()
            
            # Root hash should be valid BLAKE3 hash
            self.assertEqual(len(root_hash), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in root_hash))
            
        finally:
            import shutil
            shutil.rmtree(test_dir)


if __name__ == '__main__':
    unittest.main()
