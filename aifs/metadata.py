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
        """Initialize the SQLite database."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create database connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if tables exist and have the correct schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assets'")
            if cursor.fetchone():
                # Check if the assets table has the correct schema
                cursor.execute("PRAGMA table_info(assets)")
                columns = {row[1] for row in cursor.fetchall()}
                if 'asset_id' not in columns:
                    # Drop existing tables and recreate them
                    cursor.execute("DROP TABLE IF EXISTS snapshot_assets")
                    cursor.execute("DROP TABLE IF EXISTS lineage")
                    cursor.execute("DROP TABLE IF EXISTS snapshots")
                    cursor.execute("DROP TABLE IF EXISTS namespaces")
                    cursor.execute("DROP TABLE IF EXISTS assets")
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    asset_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lineage (
                    child_id TEXT,
                    parent_id TEXT,
                    transform_name TEXT,
                    transform_digest TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (child_id) REFERENCES assets (asset_id),
                    FOREIGN KEY (parent_id) REFERENCES assets (asset_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    namespace TEXT NOT NULL,
                    merkle_root TEXT NOT NULL,
                    metadata TEXT,
                    signature TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS snapshot_assets (
                    snapshot_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (snapshot_id, asset_id),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id),
                    FOREIGN KEY (asset_id) REFERENCES assets (asset_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS namespaces (
                    namespace_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets (kind)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lineage_asset_id ON lineage (child_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lineage_parent_id ON lineage (parent_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_namespace ON snapshots (namespace)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_assets_snapshot ON snapshot_assets (snapshot_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot_assets_asset ON snapshot_assets (asset_id)')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Raise the exception instead of just printing a warning
            # This will make tests fail properly when there are database issues
            raise RuntimeError(f"Failed to initialize metadata database: {e}") from e
    
    def add_asset(self, asset_id: str, kind: str, size: int, metadata: Optional[Dict] = None) -> None:
        """Add asset metadata.
        
        Args:
            asset_id: Asset ID (SHA-256 hash)
            kind: Asset kind (blob, tensor, embed, artifact)
            size: Asset size in bytes
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            created_at = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO assets (asset_id, kind, size, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (asset_id, kind, size, metadata_json, created_at)
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get asset metadata.
        
        Args:
            asset_id: Asset ID (SHA-256 hash)
            
        Returns:
            Asset metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
                
            asset_id, kind, size, metadata_json, created_at = row
            
            return {
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "metadata": json.loads(metadata_json) if metadata_json else None,
                "created_at": created_at
            }
        finally:
            conn.close()
    
    def add_lineage(self, child_id: str, parent_id: str, transform_name: str, transform_digest: str) -> None:
        """Add lineage relationship.
        
        Args:
            child_id: Child asset ID
            parent_id: Parent asset ID
            transform_name: Name of transformation
            transform_digest: Digest of transformation
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            created_at = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO lineage (child_id, parent_id, transform_name, transform_digest, created_at) VALUES (?, ?, ?, ?, ?)",
                (child_id, parent_id, transform_name, transform_digest, created_at)
            )
            
            conn.commit()
        finally:
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
        
        try:
            cursor.execute("""
                SELECT a.*, l.transform_name, l.transform_digest
                FROM assets a
                JOIN lineage l ON a.asset_id = l.parent_id
                WHERE l.child_id = ?
                ORDER BY l.created_at DESC
            """, (asset_id,))
            
            parents = []
            for row in cursor.fetchall():
                asset_id, kind, size, metadata_json, created_at, transform_name, transform_digest = row
                
                parents.append({
                    "asset_id": asset_id,
                    "kind": kind,
                    "size": size,
                    "metadata": json.loads(metadata_json) if metadata_json else None,
                    "created_at": created_at,
                    "transform_name": transform_name,
                    "transform_digest": transform_digest
                })
            
            return parents
        finally:
            conn.close()
    
    def get_children(self, asset_id: str) -> List[Dict]:
        """Get child assets.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            List of child asset metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT a.*, l.transform_name, l.transform_digest
                FROM assets a
                JOIN lineage l ON a.asset_id = l.child_id
                WHERE l.parent_id = ?
                ORDER BY l.created_at DESC
            """, (asset_id,))
            
            children = []
            for row in cursor.fetchall():
                asset_id, kind, size, metadata_json, created_at, transform_name, transform_digest = row
                
                children.append({
                    "asset_id": asset_id,
                    "kind": kind,
                    "size": size,
                    "metadata": json.loads(metadata_json) if metadata_json else None,
                    "created_at": created_at,
                    "transform_name": transform_name,
                    "transform_digest": transform_digest
                })
            
            return children
        finally:
            conn.close()
    
    def add_snapshot(self, snapshot_id: str, namespace: str, merkle_root: str, metadata: Optional[Dict] = None, signature: Optional[str] = None) -> None:
        """Add snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            namespace: Namespace
            merkle_root: Merkle root hash
            metadata: Optional metadata dictionary
            signature: Optional Ed25519 signature
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            created_at = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO snapshots (snapshot_id, namespace, merkle_root, metadata, signature, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (snapshot_id, namespace, merkle_root, metadata_json, signature, created_at)
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
                
            snapshot_id, namespace, merkle_root, metadata_json, signature, created_at = row
            
            return {
                "snapshot_id": snapshot_id,
                "namespace": namespace,
                "merkle_root": merkle_root,
                "metadata": json.loads(metadata_json) if metadata_json else None,
                "signature": signature,
                "created_at": created_at
            }
        finally:
            conn.close()
    
    def add_asset_to_snapshot(self, snapshot_id: str, asset_id: str) -> None:
        """Add asset to snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            asset_id: Asset ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            created_at = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR IGNORE INTO snapshot_assets (snapshot_id, asset_id) VALUES (?, ?)",
                (snapshot_id, asset_id)
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def get_snapshot_assets(self, snapshot_id: str) -> List[Dict]:
        """Get assets in snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            List of asset metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT a.*
                FROM assets a
                JOIN snapshot_assets sa ON a.asset_id = sa.asset_id
                WHERE sa.snapshot_id = ?
                ORDER BY sa.created_at DESC
            """, (snapshot_id,))
            
            assets = []
            for row in cursor.fetchall():
                asset_id, kind, size, metadata_json, asset_created_at = row
                
                assets.append({
                    "asset_id": asset_id,
                    "kind": kind,
                    "size": size,
                    "metadata": json.loads(metadata_json) if metadata_json else None,
                    "created_at": asset_created_at
                })
            
            return assets
        finally:
            conn.close()
    
    def add_namespace(self, namespace_id: str, name: str, description: Optional[str] = None, metadata: Optional[Dict] = None) -> None:
        """Add namespace.
        
        Args:
            namespace_id: Namespace ID
            name: Namespace name
            description: Optional description
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            created_at = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO namespaces (namespace_id, name, description, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (namespace_id, name, description, metadata_json, created_at)
            )
            
            conn.commit()
        finally:
            conn.close()
    
    def get_namespace(self, namespace_id: str) -> Optional[Dict]:
        """Get namespace.
        
        Args:
            namespace_id: Namespace ID
            
        Returns:
            Namespace metadata dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM namespaces WHERE namespace_id = ?", (namespace_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
                
            namespace_id, name, description, metadata_json, created_at = row
            
            return {
                "namespace_id": namespace_id,
                "name": name,
                "description": description,
                "metadata": json.loads(metadata_json) if metadata_json else None,
                "created_at": created_at
            }
        finally:
            conn.close()
    
    def list_namespaces(self) -> List[Dict]:
        """List all namespaces.
        
        Returns:
            List of namespace metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM namespaces ORDER BY created_at DESC")
            
            namespaces = []
            for row in cursor.fetchall():
                namespace_id, name, description, metadata_json, created_at = row
                
                namespaces.append({
                    "namespace_id": namespace_id,
                    "name": name,
                    "description": description,
                    "metadata": json.loads(metadata_json) if metadata_json else None,
                    "created_at": created_at
                })
            
            return namespaces
        finally:
            conn.close()



