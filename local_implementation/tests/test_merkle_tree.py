#!/usr/bin/env python3
"""Tests for AIFS Merkle Tree implementation."""

import unittest
import tempfile
import os
from pathlib import Path

# Import AIFS components
from aifs.merkle import MerkleTree, MerkleNode


class TestMerkleTree(unittest.TestCase):
    """Test Merkle tree functionality."""

    def setUp(self):
        """Set up test environment."""
        # Test asset IDs (BLAKE3 hashes)
        self.asset_ids = [
            "a" * 64,  # 64-char hex string
            "b" * 64,
            "c" * 64,
            "d" * 64,
            "e" * 64
        ]

    def test_empty_tree(self):
        """Test creating an empty Merkle tree."""
        tree = MerkleTree([])
        self.assertIsNotNone(tree.root)
        self.assertTrue(tree.root.is_leaf)
        self.assertEqual(len(tree.asset_ids), 0)

    def test_single_asset_tree(self):
        """Test creating a tree with a single asset."""
        tree = MerkleTree([self.asset_ids[0]])
        self.assertIsNotNone(tree.root)
        self.assertTrue(tree.root.is_leaf)
        self.assertEqual(tree.root.hash_value, self.asset_ids[0])
        self.assertEqual(len(tree.asset_ids), 1)

    def test_two_asset_tree(self):
        """Test creating a tree with two assets."""
        tree = MerkleTree(self.asset_ids[:2])
        self.assertIsNotNone(tree.root)
        self.assertFalse(tree.root.is_leaf)
        self.assertEqual(len(tree.asset_ids), 2)
        
        # Should have left and right children
        self.assertIsNotNone(tree.root.left)
        self.assertIsNotNone(tree.root.right)
        self.assertTrue(tree.root.left.is_leaf)
        self.assertTrue(tree.root.right.is_leaf)

    def test_five_asset_tree(self):
        """Test creating a tree with five assets."""
        tree = MerkleTree(self.asset_ids)
        self.assertIsNotNone(tree.root)
        self.assertFalse(tree.root.is_leaf)
        self.assertEqual(len(tree.asset_ids), 5)
        
        # Verify all assets are in the tree
        for asset_id in self.asset_ids:
            self.assertIn(asset_id, tree.asset_ids)

    def test_deterministic_tree(self):
        """Test that tree structure is deterministic."""
        tree1 = MerkleTree(self.asset_ids)
        tree2 = MerkleTree(self.asset_ids)
        
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())

    def test_merkle_proofs(self):
        """Test Merkle proof generation and verification."""
        tree = MerkleTree(self.asset_ids)
        
        # Test proof for first asset
        proof = tree.get_proof(self.asset_ids[0])
        self.assertIsNotNone(proof)
        self.assertIsInstance(proof, list)
        
        # Verify the proof
        is_valid = tree.verify_proof(self.asset_ids[0], proof, tree.get_root_hash())
        self.assertTrue(is_valid)

    def test_merkle_proof_verification(self):
        """Test Merkle proof verification."""
        tree = MerkleTree(self.asset_ids)
        root_hash = tree.get_root_hash()
        
        # Test valid proof
        proof = tree.get_proof(self.asset_ids[1])
        self.assertTrue(tree.verify_proof(self.asset_ids[1], proof, root_hash))
        
        # Test invalid proof (wrong asset)
        self.assertFalse(tree.verify_proof(self.asset_ids[0], proof, root_hash))
        
        # Test invalid proof (wrong root)
        wrong_root = "f" * 64
        self.assertFalse(tree.verify_proof(self.asset_ids[1], proof, wrong_root))

    def test_tree_structure(self):
        """Test tree structure representation."""
        tree = MerkleTree(self.asset_ids[:3])
        structure = tree.get_tree_structure()
        
        self.assertIsInstance(structure, dict)
        self.assertIn("hash", structure)
        self.assertIn("type", structure)
        self.assertEqual(structure["type"], "internal")

    def test_asset_not_found(self):
        """Test behavior when asset is not in tree."""
        tree = MerkleTree(self.asset_ids[:2])
        
        # Try to get proof for asset not in tree
        proof = tree.get_proof(self.asset_ids[4])
        self.assertIsNone(proof)

    def test_odd_number_assets(self):
        """Test tree creation with odd number of assets."""
        odd_asset_ids = self.asset_ids[:3]  # 3 assets
        tree = MerkleTree(odd_asset_ids)
        
        # Should still create a valid tree
        self.assertIsNotNone(tree.root)
        self.assertFalse(tree.root.is_leaf)
        self.assertEqual(len(tree.asset_ids), 3)

    def test_large_tree(self):
        """Test creating a larger tree."""
        # Create 10 test asset IDs
        large_asset_ids = [f"{i:064d}" for i in range(10)]
        tree = MerkleTree(large_asset_ids)
        
        self.assertIsNotNone(tree.root)
        self.assertEqual(len(tree.asset_ids), 10)
        
        # Test proof for middle asset
        middle_asset = large_asset_ids[5]
        proof = tree.get_proof(middle_asset)
        self.assertIsNotNone(proof)
        self.assertTrue(tree.verify_proof(middle_asset, proof, tree.get_root_hash()))


if __name__ == "__main__":
    unittest.main()
