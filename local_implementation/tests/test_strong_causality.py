#!/usr/bin/env python3
"""
Tests for AIFS Strong Causality implementation.

Tests the transaction system and strong causality guarantees as specified in the AIFS architecture.
Ensures that "Asset B SHALL NOT be visible until A is fully committed" when B lists A as a parent.
"""

import unittest
import tempfile
import time
import threading
from pathlib import Path

# Import AIFS modules
from aifs.asset import AssetManager
from aifs.transaction import TransactionManager, StrongCausalityManager, TransactionState
from aifs.metadata import MetadataStore


class TestTransactionManager(unittest.TestCase):
    """Test TransactionManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.transaction_manager = TransactionManager(str(Path(self.temp_dir) / "transactions.db"))
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_begin_transaction(self):
        """Test beginning a transaction."""
        transaction_id = self.transaction_manager.begin_transaction()
        
        self.assertIsNotNone(transaction_id)
        self.assertEqual(len(transaction_id), 36)  # UUID length
        self.assertEqual(self.transaction_manager.get_transaction_state(transaction_id), TransactionState.PENDING)
    
    def test_add_asset_to_transaction(self):
        """Test adding assets to a transaction."""
        transaction_id = self.transaction_manager.begin_transaction()
        asset_id = "test_asset_123"
        
        # Add asset to transaction
        success = self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
        self.assertTrue(success)
        
        # Check asset is in transaction
        self.assertEqual(self.transaction_manager.get_asset_transaction(asset_id), transaction_id)
    
    def test_add_dependency(self):
        """Test adding dependencies to a transaction."""
        transaction_id = self.transaction_manager.begin_transaction()
        parent_asset_id = "parent_asset_123"
        
        # Add dependency
        success = self.transaction_manager.add_dependency(transaction_id, parent_asset_id)
        self.assertTrue(success)
    
    def test_commit_transaction(self):
        """Test committing a transaction."""
        transaction_id = self.transaction_manager.begin_transaction()
        asset_id = "test_asset_123"
        
        # Add asset to transaction
        self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
        
        # Commit transaction
        success = self.transaction_manager.commit_transaction(transaction_id)
        self.assertTrue(success)
        
        # Check asset is visible
        self.assertTrue(self.transaction_manager.is_asset_visible(asset_id))
        
        # Check transaction state
        self.assertEqual(self.transaction_manager.get_transaction_state(transaction_id), TransactionState.COMMITTED)
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        transaction_id = self.transaction_manager.begin_transaction()
        asset_id = "test_asset_123"
        
        # Add asset to transaction
        self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
        
        # Rollback transaction
        success = self.transaction_manager.rollback_transaction(transaction_id)
        self.assertTrue(success)
        
        # Check asset is not visible
        self.assertFalse(self.transaction_manager.is_asset_visible(asset_id))
        
        # Check transaction state
        self.assertEqual(self.transaction_manager.get_transaction_state(transaction_id), TransactionState.ROLLED_BACK)
    
    def test_dependency_checking(self):
        """Test dependency checking before commit."""
        transaction_id = self.transaction_manager.begin_transaction()
        asset_id = "test_asset_123"
        parent_asset_id = "parent_asset_123"
        
        # Add asset and dependency
        self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
        self.transaction_manager.add_dependency(transaction_id, parent_asset_id)
        
        # Check dependencies (should fail - parent not committed)
        self.assertFalse(self.transaction_manager.check_dependencies_committed(transaction_id))
        
        # Commit parent first
        parent_transaction_id = self.transaction_manager.begin_transaction()
        self.transaction_manager.add_asset_to_transaction(parent_transaction_id, parent_asset_id)
        self.transaction_manager.commit_transaction(parent_transaction_id)
        
        # Now check dependencies (should pass)
        self.assertTrue(self.transaction_manager.check_dependencies_committed(transaction_id))
        
        # Now can commit the dependent transaction
        success = self.transaction_manager.commit_transaction(transaction_id)
        self.assertTrue(success)
    
    def test_transaction_context_manager(self):
        """Test transaction context manager."""
        asset_id = "test_asset_123"
        
        with self.transaction_manager.transaction() as transaction_id:
            self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
            # Transaction should auto-commit on exit
        
        # Check asset is visible
        self.assertTrue(self.transaction_manager.is_asset_visible(asset_id))
    
    def test_transaction_context_manager_rollback(self):
        """Test transaction context manager with rollback."""
        asset_id = "test_asset_123"
        
        try:
            with self.transaction_manager.transaction() as transaction_id:
                self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
                raise Exception("Test exception")
        except Exception:
            pass
        
        # Check asset is not visible (should be rolled back)
        self.assertFalse(self.transaction_manager.is_asset_visible(asset_id))


class TestStrongCausalityManager(unittest.TestCase):
    """Test StrongCausalityManager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.transaction_manager = TransactionManager(str(Path(self.temp_dir) / "transactions.db"))
        self.metadata_store = MetadataStore(str(Path(self.temp_dir) / "metadata.db"))
        self.causality_manager = StrongCausalityManager(self.transaction_manager, self.metadata_store)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_put_asset_with_causality(self):
        """Test putting an asset with strong causality."""
        asset_id = "test_asset_123"
        asset_data = {
            "kind": "blob",
            "size": 100,
            "metadata": {"name": "test"}
        }
        
        # Put asset with causality
        transaction_id = self.causality_manager.put_asset_with_causality(
            asset_id=asset_id,
            asset_data=asset_data
        )
        
        self.assertIsNotNone(transaction_id)
        
        # Asset should not be visible yet
        self.assertFalse(self.causality_manager.get_asset_with_causality(asset_id))
        
        # Commit transaction
        success = self.causality_manager.commit_asset(asset_id, transaction_id)
        self.assertTrue(success)
        
        # Now asset should be visible
        asset = self.causality_manager.get_asset_with_causality(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["asset_id"], asset_id)
    
    def test_put_asset_with_parents(self):
        """Test putting an asset with parent dependencies."""
        # First, create and commit a parent asset
        parent_asset_id = "parent_asset_123"
        parent_data = {
            "kind": "blob",
            "size": 50,
            "metadata": {"name": "parent"}
        }
        
        parent_transaction_id = self.causality_manager.put_asset_with_causality(
            asset_id=parent_asset_id,
            asset_data=parent_data
        )
        self.causality_manager.commit_asset(parent_asset_id, parent_transaction_id)
        
        # Now create a child asset that depends on the parent
        child_asset_id = "child_asset_123"
        child_data = {
            "kind": "blob",
            "size": 75,
            "metadata": {"name": "child"}
        }
        parents = [{"asset_id": parent_asset_id, "transform_name": "test_transform"}]
        
        child_transaction_id = self.causality_manager.put_asset_with_causality(
            asset_id=child_asset_id,
            asset_data=child_data,
            parents=parents
        )
        
        # Child should not be visible yet
        self.assertFalse(self.causality_manager.get_asset_with_causality(child_asset_id))
        
        # Commit child transaction
        success = self.causality_manager.commit_asset(child_asset_id, child_transaction_id)
        self.assertTrue(success)
        
        # Now child should be visible
        child_asset = self.causality_manager.get_asset_with_causality(child_asset_id)
        self.assertIsNotNone(child_asset)
        self.assertEqual(child_asset["asset_id"], child_asset_id)
    
    def test_dependency_waiting(self):
        """Test waiting for dependencies to be committed."""
        # Create parent transaction but don't commit yet
        parent_asset_id = "parent_asset_123"
        parent_data = {
            "kind": "blob",
            "size": 50,
            "metadata": {"name": "parent"}
        }
        
        parent_transaction_id = self.causality_manager.put_asset_with_causality(
            asset_id=parent_asset_id,
            asset_data=parent_data
        )
        
        # Create child that depends on parent
        child_asset_id = "child_asset_123"
        child_data = {
            "kind": "blob",
            "size": 75,
            "metadata": {"name": "child"}
        }
        parents = [{"asset_id": parent_asset_id, "transform_name": "test_transform"}]
        
        child_transaction_id = self.causality_manager.put_asset_with_causality(
            asset_id=child_asset_id,
            asset_data=child_data,
            parents=parents
        )
        
        # Try to commit child (should fail - parent not committed)
        success = self.causality_manager.commit_asset(child_asset_id, child_transaction_id)
        self.assertFalse(success)
        
        # Wait for dependencies (should timeout)
        success = self.causality_manager.wait_for_dependencies(child_transaction_id, timeout_seconds=0.1)
        self.assertFalse(success)
        
        # Commit parent
        self.causality_manager.commit_asset(parent_asset_id, parent_transaction_id)
        
        # Now wait for dependencies (should succeed)
        success = self.causality_manager.wait_for_dependencies(child_transaction_id, timeout_seconds=1.0)
        self.assertTrue(success)
        
        # Now can commit child
        success = self.causality_manager.commit_asset(child_asset_id, child_transaction_id)
        self.assertTrue(success)
    
    def test_get_visible_assets(self):
        """Test getting only visible assets."""
        # Create and commit some assets
        asset1_id = "asset_1"
        asset2_id = "asset_2"
        
        asset1_data = {"kind": "blob", "size": 100, "metadata": {"name": "asset1"}}
        asset2_data = {"kind": "blob", "size": 200, "metadata": {"name": "asset2"}}
        
        # Create transactions
        txn1 = self.causality_manager.put_asset_with_causality(asset1_id, asset1_data)
        txn2 = self.causality_manager.put_asset_with_causality(asset2_id, asset2_data)
        
        # Before commit - no visible assets
        visible_assets = self.causality_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 0)
        
        # Commit first asset
        self.causality_manager.commit_asset(asset1_id, txn1)
        
        # Now should see one visible asset
        visible_assets = self.causality_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 1)
        self.assertEqual(visible_assets[0]["asset_id"], asset1_id)
        
        # Commit second asset
        self.causality_manager.commit_asset(asset2_id, txn2)
        
        # Now should see both assets
        visible_assets = self.causality_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 2)


class TestAssetManagerStrongCausality(unittest.TestCase):
    """Test AssetManager integration with strong causality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir, enable_strong_causality=True)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_put_asset_with_transaction(self):
        """Test putting an asset with a transaction."""
        # Begin transaction
        transaction_id = self.asset_manager.begin_transaction()
        
        # Put asset in transaction
        data = b"Hello, AIFS!"
        asset_id = self.asset_manager.put_asset(data, transaction_id=transaction_id)
        
        # Asset should not be visible yet
        self.assertFalse(self.asset_manager.is_asset_visible(asset_id))
        self.assertIsNone(self.asset_manager.get_asset_with_causality(asset_id))
        
        # Commit transaction
        success = self.asset_manager.commit_transaction(transaction_id)
        self.assertTrue(success)
        
        # Now asset should be visible
        self.assertTrue(self.asset_manager.is_asset_visible(asset_id))
        asset = self.asset_manager.get_asset_with_causality(asset_id)
        self.assertIsNotNone(asset)
        self.assertEqual(asset["asset_id"], asset_id)
    
    def test_put_asset_with_parents_transaction(self):
        """Test putting an asset with parents in a transaction."""
        # Create and commit parent asset
        parent_data = b"Parent data"
        parent_asset_id = self.asset_manager.put_asset(parent_data)
        
        # Begin transaction for child
        transaction_id = self.asset_manager.begin_transaction()
        
        # Put child asset with parent dependency
        child_data = b"Child data"
        parents = [{"asset_id": parent_asset_id, "transform_name": "test_transform"}]
        child_asset_id = self.asset_manager.put_asset(
            child_data, 
            parents=parents, 
            transaction_id=transaction_id
        )
        
        # Child should not be visible yet
        self.assertFalse(self.asset_manager.is_asset_visible(child_asset_id))
        
        # Commit transaction
        success = self.asset_manager.commit_transaction(transaction_id)
        self.assertTrue(success)
        
        # Now child should be visible
        self.assertTrue(self.asset_manager.is_asset_visible(child_asset_id))
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        # Begin transaction
        transaction_id = self.asset_manager.begin_transaction()
        
        # Put asset in transaction
        data = b"Hello, AIFS!"
        asset_id = self.asset_manager.put_asset(data, transaction_id=transaction_id)
        
        # Rollback transaction
        success = self.asset_manager.rollback_transaction(transaction_id)
        self.assertTrue(success)
        
        # Asset should not be visible
        self.assertFalse(self.asset_manager.is_asset_visible(asset_id))
        self.assertIsNone(self.asset_manager.get_asset_with_causality(asset_id))
    
    def test_get_visible_assets(self):
        """Test getting only visible assets."""
        # Create some assets without transactions (immediately visible)
        data1 = b"Asset 1"
        data2 = b"Asset 2"
        
        asset1_id = self.asset_manager.put_asset(data1)
        asset2_id = self.asset_manager.put_asset(data2)
        
        # Get visible assets
        visible_assets = self.asset_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 2)
        
        # Create asset in transaction (not visible yet)
        transaction_id = self.asset_manager.begin_transaction()
        data3 = b"Asset 3"
        asset3_id = self.asset_manager.put_asset(data3, transaction_id=transaction_id)
        
        # Should still only see 2 assets
        visible_assets = self.asset_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 2)
        
        # Commit transaction
        self.asset_manager.commit_transaction(transaction_id)
        
        # Now should see 3 assets
        visible_assets = self.asset_manager.get_visible_assets()
        self.assertEqual(len(visible_assets), 3)
    
    def test_strong_causality_disabled(self):
        """Test behavior when strong causality is disabled."""
        # Create asset manager without strong causality
        asset_manager_no_causality = AssetManager(self.temp_dir, enable_strong_causality=False)
        
        # Put asset (should be immediately visible)
        data = b"Hello, AIFS!"
        asset_id = asset_manager_no_causality.put_asset(data)
        
        # Asset should be immediately visible
        self.assertTrue(asset_manager_no_causality.is_asset_visible(asset_id))
        asset = asset_manager_no_causality.get_asset_with_causality(asset_id)
        self.assertIsNotNone(asset)
    
    def test_concurrent_transactions(self):
        """Test concurrent transactions."""
        results = []
        errors = []
        
        def create_asset(asset_num):
            try:
                # Begin transaction
                transaction_id = self.asset_manager.begin_transaction()
                
                # Put asset
                data = f"Asset {asset_num}".encode()
                asset_id = self.asset_manager.put_asset(data, transaction_id=transaction_id)
                
                # Small delay
                time.sleep(0.01)
                
                # Commit transaction
                success = self.asset_manager.commit_transaction(transaction_id)
                results.append((asset_num, asset_id, success))
            except Exception as e:
                errors.append((asset_num, str(e)))
        
        # Create multiple concurrent transactions
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_asset, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 5)
        
        # All transactions should have succeeded
        for asset_num, asset_id, success in results:
            self.assertTrue(success)
            self.assertTrue(self.asset_manager.is_asset_visible(asset_id))


class TestStrongCausalityEdgeCases(unittest.TestCase):
    """Test edge cases for strong causality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir, enable_strong_causality=True)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_commit_nonexistent_transaction(self):
        """Test committing a non-existent transaction."""
        success = self.asset_manager.commit_transaction("nonexistent_transaction")
        self.assertFalse(success)
    
    def test_rollback_nonexistent_transaction(self):
        """Test rolling back a non-existent transaction."""
        success = self.asset_manager.rollback_transaction("nonexistent_transaction")
        self.assertFalse(success)
    
    def test_put_asset_with_nonexistent_transaction(self):
        """Test putting an asset with a non-existent transaction."""
        data = b"Hello, AIFS!"
        
        # This should raise an error or fail gracefully
        with self.assertRaises(Exception):
            self.asset_manager.put_asset(data, transaction_id="nonexistent_transaction")
    
    def test_dependency_cycle(self):
        """Test handling of dependency cycles."""
        # Create asset A that depends on asset B
        transaction_a = self.asset_manager.begin_transaction()
        data_a = b"Asset A"
        parents_a = [{"asset_id": "asset_b", "transform_name": "transform"}]
        asset_a_id = self.asset_manager.put_asset(data_a, parents=parents_a, transaction_id=transaction_a)
        
        # Create asset B that depends on asset A (cycle!)
        transaction_b = self.asset_manager.begin_transaction()
        data_b = b"Asset B"
        parents_b = [{"asset_id": asset_a_id, "transform_name": "transform"}]
        asset_b_id = self.asset_manager.put_asset(data_b, parents=parents_b, transaction_id=transaction_b)
        
        # Neither should be committable due to cycle
        success_a = self.asset_manager.commit_transaction(transaction_a)
        success_b = self.asset_manager.commit_transaction(transaction_b)
        
        # At least one should fail due to dependency cycle
        self.assertFalse(success_a or success_b)
    
    def test_large_transaction(self):
        """Test large transaction with many assets."""
        transaction_id = self.asset_manager.begin_transaction()
        
        # Create many assets in the same transaction
        asset_ids = []
        for i in range(100):
            data = f"Asset {i}".encode()
            asset_id = self.asset_manager.put_asset(data, transaction_id=transaction_id)
            asset_ids.append(asset_id)
        
        # None should be visible yet
        for asset_id in asset_ids:
            self.assertFalse(self.asset_manager.is_asset_visible(asset_id))
        
        # Commit transaction
        success = self.asset_manager.commit_transaction(transaction_id)
        self.assertTrue(success)
        
        # All should be visible now
        for asset_id in asset_ids:
            self.assertTrue(self.asset_manager.is_asset_visible(asset_id))


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
