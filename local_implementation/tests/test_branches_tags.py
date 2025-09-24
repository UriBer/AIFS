"""Tests for AIFS Branches and Tags Implementation

Tests the atomic branch updates and immutable tags functionality according to the AIFS specification.
"""

import os
import tempfile
import unittest
import time
from unittest.mock import patch, MagicMock

from aifs.asset import AssetManager
from aifs.metadata import MetadataStore
from aifs.crypto import CryptoManager


class TestBranchManagement(unittest.TestCase):
    """Test branch management functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
        
        # Create a test snapshot first
        self.namespace = "test_namespace"
        self.snapshot_id = self.asset_manager.create_snapshot(
            self.namespace, 
            ["test_asset_1", "test_asset_2"],
            {"description": "Test snapshot"}
        )
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_branch_success(self):
        """Test successful branch creation."""
        branch_name = "main"
        metadata = {"description": "Main branch"}
        
        success = self.asset_manager.create_branch(
            branch_name, self.namespace, self.snapshot_id, metadata
        )
        
        self.assertTrue(success)
        
        # Verify branch was created
        branch = self.asset_manager.get_branch(branch_name, self.namespace)
        self.assertIsNotNone(branch)
        self.assertEqual(branch["branch_name"], branch_name)
        self.assertEqual(branch["namespace"], self.namespace)
        self.assertEqual(branch["snapshot_id"], self.snapshot_id)
        self.assertEqual(branch["metadata"]["description"], "Main branch")
    
    def test_create_branch_nonexistent_snapshot(self):
        """Test branch creation with nonexistent snapshot."""
        branch_name = "main"
        nonexistent_snapshot_id = "nonexistent_snapshot"
        
        success = self.asset_manager.create_branch(
            branch_name, self.namespace, nonexistent_snapshot_id
        )
        
        self.assertFalse(success)
        
        # Verify branch was not created
        branch = self.asset_manager.get_branch(branch_name, self.namespace)
        self.assertIsNone(branch)
    
    def test_update_branch_atomic(self):
        """Test atomic branch updates."""
        branch_name = "main"
        
        # Create initial branch
        success = self.asset_manager.create_branch(
            branch_name, self.namespace, self.snapshot_id
        )
        self.assertTrue(success)
        
        # Create another snapshot
        new_snapshot_id = self.asset_manager.create_snapshot(
            self.namespace, 
            ["test_asset_3", "test_asset_4"],
            {"description": "Updated snapshot"}
        )
        
        # Update branch
        success = self.asset_manager.create_branch(
            branch_name, self.namespace, new_snapshot_id
        )
        self.assertTrue(success)
        
        # Verify branch was updated
        branch = self.asset_manager.get_branch(branch_name, self.namespace)
        self.assertIsNotNone(branch)
        self.assertEqual(branch["snapshot_id"], new_snapshot_id)
        self.assertNotEqual(branch["created_at"], branch["updated_at"])
    
    def test_get_branch_nonexistent(self):
        """Test getting nonexistent branch."""
        branch = self.asset_manager.get_branch("nonexistent", self.namespace)
        self.assertIsNone(branch)
    
    def test_list_branches(self):
        """Test listing branches."""
        # Create multiple branches
        branches = ["main", "develop", "feature/test"]
        for branch_name in branches:
            self.asset_manager.create_branch(
                branch_name, self.namespace, self.snapshot_id
            )
        
        # List branches
        branch_list = self.asset_manager.list_branches(self.namespace)
        self.assertEqual(len(branch_list), 3)
        
        branch_names = [b["branch_name"] for b in branch_list]
        for branch_name in branches:
            self.assertIn(branch_name, branch_names)
    
    def test_list_branches_with_limit(self):
        """Test listing branches with limit."""
        # Create multiple branches
        branches = ["main", "develop", "feature/test", "hotfix/bug"]
        for branch_name in branches:
            self.asset_manager.create_branch(
                branch_name, self.namespace, self.snapshot_id
            )
        
        # List branches with limit
        branch_list = self.asset_manager.list_branches(self.namespace, limit=2)
        self.assertEqual(len(branch_list), 2)
    
    def test_branch_history_audit_trail(self):
        """Test branch history for audit trail."""
        branch_name = "main"
        
        # Create initial branch
        self.asset_manager.create_branch(
            branch_name, self.namespace, self.snapshot_id
        )
        
        # Create another snapshot and update branch
        new_snapshot_id = self.asset_manager.create_snapshot(
            self.namespace, 
            ["test_asset_5"],
            {"description": "Another snapshot"}
        )
        
        self.asset_manager.create_branch(
            branch_name, self.namespace, new_snapshot_id
        )
        
        # Get branch history
        history = self.asset_manager.get_branch_history(branch_name, self.namespace)
        self.assertEqual(len(history), 2)
        
        # Check history entries (history is ordered by updated_at DESC, so newest first)
        self.assertEqual(history[0]["old_snapshot_id"], self.snapshot_id)  # Latest update
        self.assertEqual(history[0]["new_snapshot_id"], new_snapshot_id)
        self.assertIsNone(history[1]["old_snapshot_id"])  # Initial creation
        self.assertEqual(history[1]["new_snapshot_id"], self.snapshot_id)
    
    def test_delete_branch(self):
        """Test branch deletion."""
        branch_name = "main"
        
        # Create branch
        self.asset_manager.create_branch(
            branch_name, self.namespace, self.snapshot_id
        )
        
        # Verify branch exists
        branch = self.asset_manager.get_branch(branch_name, self.namespace)
        self.assertIsNotNone(branch)
        
        # Delete branch
        success = self.asset_manager.delete_branch(branch_name, self.namespace)
        self.assertTrue(success)
        
        # Verify branch is deleted
        branch = self.asset_manager.get_branch(branch_name, self.namespace)
        self.assertIsNone(branch)
    
    def test_delete_nonexistent_branch(self):
        """Test deleting nonexistent branch."""
        success = self.asset_manager.delete_branch("nonexistent", self.namespace)
        self.assertFalse(success)


class TestTagManagement(unittest.TestCase):
    """Test tag management functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
        
        # Create a test snapshot first
        self.namespace = "test_namespace"
        self.snapshot_id = self.asset_manager.create_snapshot(
            self.namespace, 
            ["test_asset_1", "test_asset_2"],
            {"description": "Test snapshot"}
        )
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_tag_success(self):
        """Test successful tag creation."""
        tag_name = "v1.0.0"
        metadata = {"description": "First release", "version": "1.0.0"}
        
        success = self.asset_manager.create_tag(
            tag_name, self.namespace, self.snapshot_id, metadata
        )
        
        self.assertTrue(success)
        
        # Verify tag was created
        tag = self.asset_manager.get_tag(tag_name, self.namespace)
        self.assertIsNotNone(tag)
        self.assertEqual(tag["tag_name"], tag_name)
        self.assertEqual(tag["namespace"], self.namespace)
        self.assertEqual(tag["snapshot_id"], self.snapshot_id)
        self.assertEqual(tag["metadata"]["description"], "First release")
        self.assertEqual(tag["metadata"]["version"], "1.0.0")
    
    def test_create_tag_nonexistent_snapshot(self):
        """Test tag creation with nonexistent snapshot."""
        tag_name = "v1.0.0"
        nonexistent_snapshot_id = "nonexistent_snapshot"
        
        success = self.asset_manager.create_tag(
            tag_name, self.namespace, nonexistent_snapshot_id
        )
        
        self.assertFalse(success)
        
        # Verify tag was not created
        tag = self.asset_manager.get_tag(tag_name, self.namespace)
        self.assertIsNone(tag)
    
    def test_create_duplicate_tag_immutable(self):
        """Test that tags are immutable (cannot be recreated)."""
        tag_name = "v1.0.0"
        
        # Create initial tag
        success = self.asset_manager.create_tag(
            tag_name, self.namespace, self.snapshot_id
        )
        self.assertTrue(success)
        
        # Try to create same tag again (should fail)
        success = self.asset_manager.create_tag(
            tag_name, self.namespace, self.snapshot_id
        )
        self.assertFalse(success)
        
        # Verify original tag is unchanged
        tag = self.asset_manager.get_tag(tag_name, self.namespace)
        self.assertIsNotNone(tag)
        self.assertEqual(tag["snapshot_id"], self.snapshot_id)
    
    def test_get_tag_nonexistent(self):
        """Test getting nonexistent tag."""
        tag = self.asset_manager.get_tag("nonexistent", self.namespace)
        self.assertIsNone(tag)
    
    def test_list_tags(self):
        """Test listing tags."""
        # Create multiple tags
        tags = ["v1.0.0", "v1.1.0", "v2.0.0", "regulatory-export"]
        for tag_name in tags:
            self.asset_manager.create_tag(
                tag_name, self.namespace, self.snapshot_id
            )
        
        # List tags
        tag_list = self.asset_manager.list_tags(self.namespace)
        self.assertEqual(len(tag_list), 4)
        
        tag_names = [t["tag_name"] for t in tag_list]
        for tag_name in tags:
            self.assertIn(tag_name, tag_names)
    
    def test_list_tags_with_limit(self):
        """Test listing tags with limit."""
        # Create multiple tags
        tags = ["v1.0.0", "v1.1.0", "v2.0.0", "regulatory-export"]
        for tag_name in tags:
            self.asset_manager.create_tag(
                tag_name, self.namespace, self.snapshot_id
            )
        
        # List tags with limit
        tag_list = self.asset_manager.list_tags(self.namespace, limit=2)
        self.assertEqual(len(tag_list), 2)
    
    def test_delete_tag(self):
        """Test tag deletion."""
        tag_name = "v1.0.0"
        
        # Create tag
        self.asset_manager.create_tag(
            tag_name, self.namespace, self.snapshot_id
        )
        
        # Verify tag exists
        tag = self.asset_manager.get_tag(tag_name, self.namespace)
        self.assertIsNotNone(tag)
        
        # Delete tag
        success = self.asset_manager.delete_tag(tag_name, self.namespace)
        self.assertTrue(success)
        
        # Verify tag is deleted
        tag = self.asset_manager.get_tag(tag_name, self.namespace)
        self.assertIsNone(tag)
    
    def test_delete_nonexistent_tag(self):
        """Test deleting nonexistent tag."""
        success = self.asset_manager.delete_tag("nonexistent", self.namespace)
        self.assertFalse(success)


class TestBranchesTagsIntegration(unittest.TestCase):
    """Test integration between branches and tags."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
        self.namespace = "test_namespace"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_branch_and_tag_same_snapshot(self):
        """Test creating branch and tag pointing to same snapshot."""
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(
            self.namespace, 
            ["test_asset_1"],
            {"description": "Shared snapshot"}
        )
        
        # Create branch
        branch_success = self.asset_manager.create_branch(
            "main", self.namespace, snapshot_id
        )
        self.assertTrue(branch_success)
        
        # Create tag
        tag_success = self.asset_manager.create_tag(
            "v1.0.0", self.namespace, snapshot_id
        )
        self.assertTrue(tag_success)
        
        # Verify both point to same snapshot
        branch = self.asset_manager.get_branch("main", self.namespace)
        tag = self.asset_manager.get_tag("v1.0.0", self.namespace)
        
        self.assertEqual(branch["snapshot_id"], snapshot_id)
        self.assertEqual(tag["snapshot_id"], snapshot_id)
    
    def test_audit_grade_provenance(self):
        """Test audit-grade provenance with tags."""
        # Create multiple snapshots
        snapshots = []
        for i in range(3):
            snapshot_id = self.asset_manager.create_snapshot(
                self.namespace, 
                [f"test_asset_{i}"],
                {"description": f"Snapshot {i}"}
            )
            snapshots.append(snapshot_id)
        
        # Create tags for audit trail
        tags = ["v1.0.0", "v1.1.0", "regulatory-export"]
        for i, tag_name in enumerate(tags):
            success = self.asset_manager.create_tag(
                tag_name, self.namespace, snapshots[i]
            )
            self.assertTrue(success)
        
        # Verify audit trail
        tag_list = self.asset_manager.list_tags(self.namespace)
        self.assertEqual(len(tag_list), 3)
        
        # Check specific audit tags
        regulatory_tag = self.asset_manager.get_tag("regulatory-export", self.namespace)
        self.assertIsNotNone(regulatory_tag)
        self.assertEqual(regulatory_tag["snapshot_id"], snapshots[2])


class TestBranchesTagsAtomicity(unittest.TestCase):
    """Test atomicity guarantees for branches and tags."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
        self.namespace = "test_namespace"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_branch_update_atomicity(self):
        """Test that branch updates are atomic."""
        # Create initial snapshot and branch
        snapshot1 = self.asset_manager.create_snapshot(
            self.namespace, ["asset1"], {"version": "1"}
        )
        
        success = self.asset_manager.create_branch("main", self.namespace, snapshot1)
        self.assertTrue(success)
        
        # Create second snapshot
        snapshot2 = self.asset_manager.create_snapshot(
            self.namespace, ["asset2"], {"version": "2"}
        )
        
        # Update branch (should be atomic)
        success = self.asset_manager.create_branch("main", self.namespace, snapshot2)
        self.assertTrue(success)
        
        # Verify branch points to new snapshot
        branch = self.asset_manager.get_branch("main", self.namespace)
        self.assertEqual(branch["snapshot_id"], snapshot2)
        
        # Verify history shows the transition
        history = self.asset_manager.get_branch_history("main", self.namespace)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["old_snapshot_id"], snapshot1)
        self.assertEqual(history[0]["new_snapshot_id"], snapshot2)
    
    def test_tag_immutability(self):
        """Test that tags are truly immutable."""
        # Create snapshot and tag
        snapshot = self.asset_manager.create_snapshot(
            self.namespace, ["asset1"], {"version": "1"}
        )
        
        success = self.asset_manager.create_tag("v1.0.0", self.namespace, snapshot)
        self.assertTrue(success)
        
        # Try to recreate tag (should fail)
        success = self.asset_manager.create_tag("v1.0.0", self.namespace, snapshot)
        self.assertFalse(success)
        
        # Verify original tag is unchanged
        tag = self.asset_manager.get_tag("v1.0.0", self.namespace)
        self.assertIsNotNone(tag)
        self.assertEqual(tag["snapshot_id"], snapshot)


class TestBranchesTagsPerformance(unittest.TestCase):
    """Test performance characteristics of branches and tags."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
        self.namespace = "test_namespace"
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_branch_creation_performance(self):
        """Test branch creation performance."""
        # Create snapshot
        snapshot = self.asset_manager.create_snapshot(
            self.namespace, ["asset1"], {"version": "1"}
        )
        
        # Measure branch creation time
        start_time = time.time()
        
        for i in range(100):
            self.asset_manager.create_branch(f"branch_{i}", self.namespace, snapshot)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 100 branches in reasonable time (< 5 seconds)
        self.assertLess(creation_time, 5.0)
        
        # Verify all branches were created
        branches = self.asset_manager.list_branches(self.namespace, limit=200)
        self.assertEqual(len(branches), 100)
    
    def test_tag_creation_performance(self):
        """Test tag creation performance."""
        # Create snapshot
        snapshot = self.asset_manager.create_snapshot(
            self.namespace, ["asset1"], {"version": "1"}
        )
        
        # Measure tag creation time
        start_time = time.time()
        
        for i in range(100):
            self.asset_manager.create_tag(f"tag_{i}", self.namespace, snapshot)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 100 tags in reasonable time (< 5 seconds)
        self.assertLess(creation_time, 5.0)
        
        # Verify all tags were created
        tags = self.asset_manager.list_tags(self.namespace, limit=200)
        self.assertEqual(len(tags), 100)


if __name__ == "__main__":
    unittest.main()
