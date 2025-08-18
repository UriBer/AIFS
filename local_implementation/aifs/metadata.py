"""AIFS Metadata Store

Implements metadata storage and lineage tracking using SQLite with signature support.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


class MetadataStore:
    """Metadata store for AIFS using SQLite.
    
    Stores asset metadata, lineage information, and Ed25519 signatures for snapshots.
    """
    
    def __init__(self, db_path: str):
        """Initialize metadata store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create assets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            size INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        )
        """)
        
        # Create lineage table for parent-child relationships
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lineage (
            child_id TEXT NOT NULL,
            parent_id TEXT NOT NULL,
            transform_name TEXT,
            transform_digest TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (child_id, parent_id),
            FOREIGN KEY (child_id) REFERENCES assets(asset_id),
            FOREIGN KEY (parent_id) REFERENCES assets(asset_id)
        )
        """)
        
        # Create snapshots table with signature support
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id TEXT PRIMARY KEY,
            namespace TEXT NOT NULL,
            merkle_root TEXT NOT NULL,
            created_at TEXT NOT NULL,
            signature TEXT NOT NULL,
            metadata TEXT
        )
        """)
        
        # Create snapshot_assets table for snapshot contents
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS snapshot_assets (
            snapshot_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, asset_id),
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id),
            FOREIGN KEY (asset_id) REFERENCES assets(asset_id)
        )
        """)
        
        # Create namespaces table for namespace management
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS namespaces (
            namespace_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT
        )
        """)
        
        conn.commit()
        conn.close()
    
    def add_asset(self, asset_id: str, kind: str, size: int, metadata: Optional[Dict] = None) -> None:
        """Add asset metadata.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            kind: Asset kind (blob, tensor, embed, artifact)
            size: Asset size in bytes
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_at = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT OR REPLACE INTO assets (asset_id, kind, size, created_at, metadata) VALUES (?, ?, ?, ?, ?)",
            (asset_id, kind, size, created_at, metadata_json)
        )
        
        conn.commit()
        conn.close()
    
    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get asset metadata.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            
        Returns:
            Asset metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        asset_id, kind, size, created_at, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        return {
            "asset_id": asset_id,
            "kind": kind,
            "size": size,
            "created_at": created_at,
            "metadata": metadata
        }
    
    def add_lineage(self, child_id: str, parent_id: str, transform_name: Optional[str] = None, 
                   transform_digest: Optional[str] = None) -> None:
        """Add lineage information.
        
        Args:
            child_id: Child asset ID
            parent_id: Parent asset ID
            transform_name: Optional name of the transformation
            transform_digest: Optional digest of the transformation (e.g., container hash)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_at = datetime.utcnow().isoformat()
        
        cursor.execute(
            "INSERT OR REPLACE INTO lineage (child_id, parent_id, transform_name, transform_digest, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (child_id, parent_id, transform_name, transform_digest, created_at)
        )
        
        conn.commit()
        conn.close()
    
    def get_parents(self, asset_id: str) -> List[Dict]:
        """Get parent assets.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            List of parent asset metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT a.*, l.transform_name, l.transform_digest
        FROM assets a
        JOIN lineage l ON a.asset_id = l.parent_id
        WHERE l.child_id = ?
        """, (asset_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        parents = []
        for row in rows:
            asset_id, kind, size, created_at, metadata_json, transform_name, transform_digest = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            parents.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": created_at,
                "metadata": metadata,
                "transform_name": transform_name,
                "transform_digest": transform_digest
            })
        
        return parents
    
    def get_children(self, asset_id: str) -> List[Dict]:
        """Get child assets.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            List of child asset metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT a.*, l.transform_name, l.transform_digest
        FROM assets a
        JOIN lineage l ON a.asset_id = l.child_id
        WHERE l.parent_id = ?
        """, (asset_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        children = []
        for row in rows:
            asset_id, kind, size, created_at, metadata_json, transform_name, transform_digest = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            children.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": created_at,
                "metadata": metadata,
                "transform_name": transform_name,
                "transform_digest": transform_digest
            })
        
        return children
    
    def create_snapshot(self, namespace: str, merkle_root: str, metadata: Optional[Dict] = None,
                       signature: str = None, created_at: str = None) -> str:
        """Create a new snapshot with Ed25519 signature.
        
        Args:
            namespace: Namespace for the snapshot
            merkle_root: Merkle root hash
            metadata: Optional metadata dictionary
            signature: Ed25519 signature of the snapshot
            created_at: ISO timestamp string
            
        Returns:
            Snapshot ID
        """
        import hashlib
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if created_at is None:
            created_at = datetime.utcnow().isoformat()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Generate snapshot ID from merkle root and timestamp
        snapshot_id_input = f"{merkle_root}:{created_at}"
        snapshot_id = hashlib.sha256(snapshot_id_input.encode()).hexdigest()[:32]  # 128-bit equivalent
        
        cursor.execute(
            "INSERT INTO snapshots (snapshot_id, namespace, merkle_root, created_at, signature, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_id, namespace, merkle_root, created_at, signature, metadata_json)
        )
        
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def add_asset_to_snapshot(self, snapshot_id: str, asset_id: str) -> None:
        """Add asset to snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            asset_id: Asset ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO snapshot_assets (snapshot_id, asset_id) VALUES (?, ?)",
            (snapshot_id, asset_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot metadata with signature.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        snapshot_id, namespace, merkle_root, created_at, signature, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        # Get assets in snapshot
        cursor.execute("""
        SELECT a.*
        FROM assets a
        JOIN snapshot_assets sa ON a.asset_id = sa.asset_id
        WHERE sa.snapshot_id = ?
        """, (snapshot_id,))
        
        asset_rows = cursor.fetchall()
        conn.close()
        
        assets = []
        for row in asset_rows:
            asset_id, kind, size, created_at, metadata_json = row
            asset_metadata = json.loads(metadata_json) if metadata_json else {}
            
            assets.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": created_at,
                "metadata": asset_metadata
            })
        
        return {
            "snapshot_id": snapshot_id,
            "namespace": namespace,
            "merkle_root": merkle_root,
            "created_at": created_at,
            "signature": signature,
            "metadata": metadata,
            "assets": assets
        }
    
    def create_namespace(self, name: str, metadata: Optional[Dict] = None) -> str:
        """Create a new namespace.
        
        Args:
            name: Namespace name
            metadata: Optional metadata dictionary
            
        Returns:
            Namespace ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_at = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Use name as ID for simplicity
        namespace_id = name
        
        cursor.execute(
            "INSERT OR REPLACE INTO namespaces (namespace_id, name, created_at, metadata) "
            "VALUES (?, ?, ?, ?)",
            (namespace_id, name, created_at, metadata_json)
        )
        
        conn.commit()
        conn.close()
        
        return namespace_id
    
    def get_namespace(self, namespace_id: str) -> Optional[Dict]:
        """Get namespace information.
        
        Args:
            namespace_id: Namespace ID
            
        Returns:
            Namespace dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM namespaces WHERE namespace_id = ?", (namespace_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        namespace_id, name, created_at, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}
        
        return {
            "namespace_id": namespace_id,
            "name": name,
            "created_at": created_at,
            "metadata": metadata
        }
    
    def list_namespaces(self) -> List[Dict]:
        """List all namespaces.
        
        Returns:
            List of namespace dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM namespaces ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        conn.close()
        
        namespaces = []
        for row in rows:
            namespace_id, name, created_at, metadata_json = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            namespaces.append({
                "namespace_id": namespace_id,
                "name": name,
                "created_at": created_at,
                "metadata": metadata
            })
        
        return namespaces