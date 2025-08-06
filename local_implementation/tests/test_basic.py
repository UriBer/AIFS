#!/usr/bin/env python3
"""Basic tests for AIFS local implementation."""

import os
import tempfile
import unittest
import numpy as np
from pathlib import Path

# Import AIFS components
from aifs.storage import ContentAddressedStorage
from aifs.vector_db import VectorDB
from aifs.metadata import MetadataStore
from aifs.asset import AssetManager


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of AIFS components."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "storage"
        self.vector_db_path = Path(self.temp_dir.name) / "vector_db"
        self.metadata_path = Path(self.temp_dir.name) / "metadata.db"
        
        # Initialize components
        self.storage = ContentAddressedStorage(self.storage_path)
        self.vector_db = VectorDB(self.vector_db_path)
        self.metadata = MetadataStore(self.metadata_path)
        self.asset_manager = AssetManager(
            self.storage, self.vector_db, self.metadata
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_storage(self):
        """Test content-addressed storage."""
        # Store data
        data = b"Hello, AIFS!"
        digest = self.storage.put(data)
        
        # Check if data exists
        self.assertTrue(self.storage.exists(digest))
        
        # Retrieve data
        retrieved_data = self.storage.get(digest)
        self.assertEqual(data, retrieved_data)
        
        # Delete data
        self.storage.delete(digest)
        self.assertFalse(self.storage.exists(digest))

    def test_vector_db(self):
        """Test vector database."""
        # Add embeddings
        ids = ["id1", "id2", "id3"]
        embeddings = np.random.rand(3, 4).astype(np.float32)  # 3 vectors of dimension 4
        
        for i, (id_, embedding) in enumerate(zip(ids, embeddings)):
            self.vector_db.add(id_, embedding)
        
        # Search
        query = np.random.rand(4).astype(np.float32)
        results = self.vector_db.search(query, k=2)
        
        # Check results
        self.assertEqual(len(results), 2)
        self.assertIn(results[0]["id"], ids)
        self.assertIn(results[1]["id"], ids)
        
        # Delete
        self.vector_db.delete(ids[0])
        results = self.vector_db.search(query, k=3)
        self.assertEqual(len(results), 2)  # Only 2 left
        self.assertNotIn(ids[0], [r["id"] for r in results])

    def test_metadata(self):
        """Test metadata store."""
        # Add asset
        asset_id = "test_asset"
        kind = "blob"
        size = 100
        metadata = {"content_type": "text/plain", "description": "Test asset"}
        
        self.metadata.add_asset(asset_id, kind, size, metadata)
        
        # Get asset
        asset = self.metadata.get_asset(asset_id)
        self.assertEqual(asset["asset_id"], asset_id)
        self.assertEqual(asset["kind"], kind)
        self.assertEqual(asset["size"], size)
        self.assertEqual(asset["metadata"], metadata)
        
        # Add lineage
        parent_id = "parent_asset"
        transform_name = "test_transform"
        transform_digest = "test_digest"
        
        self.metadata.add_lineage(asset_id, parent_id, transform_name, transform_digest)
        
        # Get lineage
        lineage = self.metadata.get_lineage(asset_id)
        self.assertEqual(len(lineage), 1)
        self.assertEqual(lineage[0]["parent_id"], parent_id)
        self.assertEqual(lineage[0]["transform_name"], transform_name)
        self.assertEqual(lineage[0]["transform_digest"], transform_digest)
        
        # Create snapshot
        snapshot_id = "test_snapshot"
        namespace = "default"
        asset_ids = [asset_id, parent_id]
        merkle_root = "test_merkle_root"
        snapshot_metadata = {"description": "Test snapshot"}
        
        self.metadata.create_snapshot(
            snapshot_id, namespace, asset_ids, merkle_root, snapshot_metadata
        )
        
        # Get snapshot
        snapshot = self.metadata.get_snapshot(snapshot_id)
        self.assertEqual(snapshot["snapshot_id"], snapshot_id)
        self.assertEqual(snapshot["namespace"], namespace)
        self.assertEqual(snapshot["merkle_root"], merkle_root)
        self.assertEqual(snapshot["metadata"], snapshot_metadata)
        
        # Get snapshot assets
        snapshot_assets = self.metadata.get_snapshot_assets(snapshot_id)
        self.assertEqual(set(snapshot_assets), set(asset_ids))

    def test_asset_manager(self):
        """Test asset manager."""
        # Put asset
        data = b"Hello, Asset Manager!"
        kind = "blob"
        metadata = {"content_type": "text/plain", "description": "Test asset"}
        
        asset_id = self.asset_manager.put_asset(data, kind, metadata)
        
        # Get asset
        asset = self.asset_manager.get_asset(asset_id)
        self.assertEqual(asset["data"], data)
        self.assertEqual(asset["kind"], kind)
        self.assertEqual(asset["metadata"], metadata)
        
        # Put asset with embedding
        data2 = b"Another asset with embedding"
        embedding = np.random.rand(4).astype(np.float32)
        
        asset_id2 = self.asset_manager.put_asset(
            data2, kind, metadata, embedding=embedding
        )
        
        # Vector search
        query = np.random.rand(4).astype(np.float32)
        results = self.asset_manager.vector_search(query, k=1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["asset_id"], asset_id2)
        
        # Put asset with lineage
        data3 = b"Asset with lineage"
        parents = [{
            "asset_id": asset_id,
            "transform_name": "test_transform",
            "transform_digest": "test_digest"
        }]
        
        asset_id3 = self.asset_manager.put_asset(
            data3, kind, metadata, parents=parents
        )
        
        # Get asset with lineage
        asset3 = self.asset_manager.get_asset(asset_id3)
        self.assertEqual(len(asset3["parents"]), 1)
        self.assertEqual(asset3["parents"][0]["asset_id"], asset_id)
        
        # Create snapshot
        asset_ids = [asset_id, asset_id2, asset_id3]
        snapshot_metadata = {"description": "Test snapshot"}
        
        snapshot = self.asset_manager.create_snapshot(
            "default", asset_ids, snapshot_metadata
        )
        
        # Get snapshot
        retrieved_snapshot = self.asset_manager.get_snapshot(snapshot["snapshot_id"])
        self.assertEqual(retrieved_snapshot["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(set(retrieved_snapshot["asset_ids"]), set(asset_ids))


if __name__ == "__main__":
    unittest.main()