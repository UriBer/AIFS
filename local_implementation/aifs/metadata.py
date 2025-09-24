"""AIFS Metadata Store

Implements metadata storage and lineage tracking using SQLite with Ed25519 signature support.
Ensures snapshot root authenticity and integrity as specified in the AIFS architecture.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from .crypto import CryptoManager


class MetadataStore:
    """Metadata store for AIFS using SQLite.
    
    Stores asset metadata, lineage information, and Ed25519 signatures for snapshots.
    Integrates with CryptoManager for signature generation and verification.
    """
    
    def __init__(self, db_path: str, crypto_manager: Optional[CryptoManager] = None):
        """Initialize metadata store.
        
        Args:
            db_path: Path to SQLite database file
            crypto_manager: Optional crypto manager for signature operations
        """
        self.db_path = db_path
        self.crypto_manager = crypto_manager
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create database connection
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
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
            
            # Branches table - named pointers to snapshot roots with atomic updates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS branches (
                    branch_name TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    PRIMARY KEY (branch_name, namespace),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
                )
            ''')
            
            # Tags table - immutable labels for audit-grade provenance
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    tag_name TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    PRIMARY KEY (tag_name, namespace),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
                )
            ''')
            
            # Branch history table - track branch updates for audit trail
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS branch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_name TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    old_snapshot_id TEXT,
                    new_snapshot_id TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (old_snapshot_id) REFERENCES snapshots (snapshot_id),
                    FOREIGN KEY (new_snapshot_id) REFERENCES snapshots (snapshot_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets (kind)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lineage_asset_id ON lineage (child_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_lineage_parent_id ON lineage (parent_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_namespace ON snapshots (namespace)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_branches_namespace ON branches (namespace)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_namespace ON tags (namespace)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_branch_history_branch ON branch_history (branch_name, namespace)')
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
            asset_id: Asset ID (BLAKE3 hash)
            kind: Asset kind (blob, tensor, embed, artifact)
            size: Asset size in bytes
            metadata: Optional metadata dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        created_at = datetime.utcnow().isoformat()
        metadata_str = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT OR REPLACE INTO assets (asset_id, kind, size, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (asset_id, kind, size, metadata_str, created_at)
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
        
        asset_id, kind, size, metadata_str, created_at = row
        metadata = json.loads(metadata_str) if metadata_str else {}
        
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
            asset_id, kind, size, metadata_str, created_at, transform_name, transform_digest = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
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
            asset_id, kind, size, metadata_str, created_at, transform_name, transform_digest = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
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
                       signature: str = None, created_at: str = None, auto_sign: bool = True) -> str:
        """Create a new snapshot with Ed25519 signature.
        
        Creates a snapshot and automatically signs it if a crypto manager is available
        and auto_sign is True. This implements the AIFS specification requirement that
        snapshot roots MUST be signed with Ed25519.
        
        Args:
            namespace: Namespace for the snapshot
            merkle_root: Merkle root hash (BLAKE3)
            metadata: Optional metadata dictionary
            signature: Optional pre-computed Ed25519 signature
            created_at: ISO timestamp string
            auto_sign: Whether to automatically sign the snapshot if crypto manager is available
        
        Returns:
            Snapshot ID
        """
        import blake3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if created_at is None:
            created_at = datetime.utcnow().isoformat()
        
        metadata_str = json.dumps(metadata) if metadata else None
        
        # Generate snapshot ID from merkle root and timestamp
        snapshot_id_input = f"{merkle_root}:{created_at}"
        snapshot_id = blake3.blake3(snapshot_id_input.encode()).hexdigest()[:32]  # 128-bit equivalent
        
        # Auto-sign the snapshot if crypto manager is available and no signature provided
        if auto_sign and signature is None and self.crypto_manager is not None:
            # Register namespace key if not already registered
            self.crypto_manager.register_namespace_key(namespace, metadata)
            
            # Sign the snapshot
            signature_bytes, signature_hex = self.crypto_manager.sign_snapshot(
                merkle_root, created_at, namespace
            )
            signature = signature_hex
        
        cursor.execute(
            "INSERT INTO snapshots (snapshot_id, namespace, merkle_root, metadata, signature, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (snapshot_id, namespace, merkle_root, metadata_str, signature, created_at)
        )
        
        conn.commit()
        conn.close()
        
        return snapshot_id
    
    def verify_snapshot_signature(self, snapshot_id: str) -> bool:
        """Verify the Ed25519 signature of a snapshot.
        
        This method implements the AIFS specification requirement that Ed25519 signatures
        of snapshot roots MUST be verified before exposing a branch.
        
        Args:
            snapshot_id: Snapshot ID to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.crypto_manager:
            return False
        
        # Get snapshot data
        snapshot = self.get_snapshot(snapshot_id)
        if not snapshot:
            return False
        
        signature = snapshot.get('signature')
        if not signature:
            return False
        
        # Verify the signature using the namespace key
        # If namespace key is not registered, try with the current public key
        if self.crypto_manager.get_namespace_key(snapshot['namespace']):
            return self.crypto_manager.verify_snapshot_with_namespace_key(
                signature,
                snapshot['merkle_root'],
                snapshot['created_at'],
                snapshot['namespace']
            )
        else:
            # Fallback to current public key verification
            public_key = self.crypto_manager.get_public_key()
            return self.crypto_manager.verify_snapshot_signature(
                signature,
                snapshot['merkle_root'],
                snapshot['created_at'],
                snapshot['namespace'],
                public_key
            )
    
    def get_verified_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get a snapshot only if its signature is valid.
        
        This method ensures that snapshots are only returned if their Ed25519
        signatures are valid, implementing the AIFS specification requirement.
        
        Args:
            snapshot_id: Snapshot ID to retrieve
            
        Returns:
            Snapshot data if signature is valid, None otherwise
        """
        if not self.verify_snapshot_signature(snapshot_id):
            return None
        
        return self.get_snapshot(snapshot_id)
    
    def list_verified_snapshots(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """List snapshots with verified signatures only.
        
        Args:
            namespace: Optional namespace filter
            limit: Maximum number of snapshots to return
            
        Returns:
            List of snapshots with valid signatures
        """
        all_snapshots = self.list_snapshots(namespace, limit)
        verified_snapshots = []
        
        for snapshot in all_snapshots:
            if self.verify_snapshot_signature(snapshot['snapshot_id']):
                verified_snapshots.append(snapshot)
        
        return verified_snapshots
    
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
        
        snapshot_id, namespace, merkle_root, metadata_str, signature, created_at = row
        metadata = json.loads(metadata_str) if metadata_str else {}
        
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
            asset_id, kind, size, metadata_str, asset_created_at = row
            asset_metadata = json.loads(metadata_str) if metadata_str else {}
            
            assets.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": asset_created_at,
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
    
    def list_snapshots(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """List snapshots with optional namespace filter.
        
        Args:
            namespace: Optional namespace filter
            limit: Maximum number of snapshots to return
            
        Returns:
            List of snapshot dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if namespace:
            cursor.execute(
                "SELECT snapshot_id, namespace, merkle_root, metadata, signature, created_at "
                "FROM snapshots WHERE namespace = ? ORDER BY created_at DESC LIMIT ?",
                (namespace, limit)
            )
        else:
            cursor.execute(
                "SELECT snapshot_id, namespace, merkle_root, metadata, signature, created_at "
                "FROM snapshots ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        
        snapshots = []
        for row in cursor.fetchall():
            snapshot_id, namespace, merkle_root, metadata_str, signature, created_at = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            snapshots.append({
                "snapshot_id": snapshot_id,
                "namespace": namespace,
                "merkle_root": merkle_root,
                "created_at": created_at,
                "signature": signature,
                "metadata": metadata
            })
        
        conn.close()
        return snapshots
    
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
        metadata_str = json.dumps(metadata) if metadata else None
        
        # Use name as ID for simplicity
        namespace_id = name
        
        cursor.execute(
            "INSERT OR REPLACE INTO namespaces (namespace_id, name, created_at, metadata) "
            "VALUES (?, ?, ?, ?)",
            (namespace_id, name, created_at, metadata_str)
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
        
        namespace_id, name, description, metadata_str, created_at = row
        metadata = json.loads(metadata_str) if metadata_str else {}
        
        return {
            "namespace_id": namespace_id,
            "name": name,
            "description": description,
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
            namespace_id, name, description, metadata_str, created_at = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            namespaces.append({
                "namespace_id": namespace_id,
                "name": name,
                "description": description,
                "created_at": created_at,
                "metadata": metadata
            })
        
        return namespaces
    
    def list_assets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List assets.
        
        Args:
            limit: Maximum number of assets to return
            offset: Number of assets to skip
            
        Returns:
            List of asset metadata dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT asset_id, kind, size, created_at, metadata
            FROM assets 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        assets = []
        for row in rows:
            asset_id, kind, size, created_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            assets.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": created_at,
                "metadata": metadata
            })
        
        return assets
    
    # ============================================================================
    # Branch Management Methods
    # ============================================================================
    
    def create_branch(self, branch_name: str, namespace: str, snapshot_id: str, 
                     metadata: Optional[Dict] = None) -> bool:
        """Create or update a branch with atomic transaction.
        
        Branches are named pointers to snapshot roots. Creating or updating a branch
        MUST be an atomic metadata transaction according to the AIFS specification.
        
        Args:
            branch_name: Name of the branch
            namespace: Namespace for the branch
            snapshot_id: Snapshot ID to point to
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Check if snapshot exists and is verified
            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            if not self.verify_snapshot_signature(snapshot_id):
                raise ValueError(f"Snapshot {snapshot_id} signature verification failed")
            
            # Check if branch already exists
            cursor.execute("""
                SELECT snapshot_id FROM branches 
                WHERE branch_name = ? AND namespace = ?
            """, (branch_name, namespace))
            
            existing_branch = cursor.fetchone()
            old_snapshot_id = existing_branch[0] if existing_branch else None
            
            metadata_str = json.dumps(metadata) if metadata else None
            current_time = datetime.utcnow().isoformat()
            
            if existing_branch:
                # Update existing branch
                cursor.execute("""
                    UPDATE branches 
                    SET snapshot_id = ?, updated_at = ?, metadata = ?
                    WHERE branch_name = ? AND namespace = ?
                """, (snapshot_id, current_time, metadata_str, branch_name, namespace))
            else:
                # Create new branch
                cursor.execute("""
                    INSERT INTO branches (branch_name, namespace, snapshot_id, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (branch_name, namespace, snapshot_id, current_time, current_time, metadata_str))
            
            # Record in branch history for audit trail
            cursor.execute("""
                INSERT INTO branch_history (branch_name, namespace, old_snapshot_id, new_snapshot_id, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (branch_name, namespace, old_snapshot_id, snapshot_id, current_time, metadata_str))
            
            # Commit transaction
            cursor.execute("COMMIT")
            conn.close()
            return True
            
        except Exception as e:
            # Rollback on error
            cursor.execute("ROLLBACK")
            conn.close()
            print(f"Branch creation failed: {e}")
            return False
    
    def get_branch(self, branch_name: str, namespace: str) -> Optional[Dict]:
        """Get branch information.
        
        Args:
            branch_name: Name of the branch
            namespace: Namespace for the branch
            
        Returns:
            Branch dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT branch_name, namespace, snapshot_id, created_at, updated_at, metadata
            FROM branches 
            WHERE branch_name = ? AND namespace = ?
        """, (branch_name, namespace))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        branch_name, namespace, snapshot_id, created_at, updated_at, metadata_str = row
        metadata = json.loads(metadata_str) if metadata_str else {}
        
        return {
            "branch_name": branch_name,
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "metadata": metadata
        }
    
    def list_branches(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """List branches.
        
        Args:
            namespace: Optional namespace filter
            limit: Maximum number of branches to return
            
        Returns:
            List of branch dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if namespace:
            cursor.execute("""
                SELECT branch_name, namespace, snapshot_id, created_at, updated_at, metadata
                FROM branches 
                WHERE namespace = ?
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (namespace, limit))
        else:
            cursor.execute("""
                SELECT branch_name, namespace, snapshot_id, created_at, updated_at, metadata
                FROM branches 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        branches = []
        for row in rows:
            branch_name, namespace, snapshot_id, created_at, updated_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            branches.append({
                "branch_name": branch_name,
                "namespace": namespace,
                "snapshot_id": snapshot_id,
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": metadata
            })
        
        return branches
    
    def get_branch_history(self, branch_name: str, namespace: str, limit: int = 50) -> List[Dict]:
        """Get branch update history for audit trail.
        
        Args:
            branch_name: Name of the branch
            namespace: Namespace for the branch
            limit: Maximum number of history entries to return
            
        Returns:
            List of branch history dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, old_snapshot_id, new_snapshot_id, updated_at, metadata
            FROM branch_history 
            WHERE branch_name = ? AND namespace = ?
            ORDER BY updated_at DESC 
            LIMIT ?
        """, (branch_name, namespace, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            id, old_snapshot_id, new_snapshot_id, updated_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            history.append({
                "id": id,
                "branch_name": branch_name,
                "namespace": namespace,
                "old_snapshot_id": old_snapshot_id,
                "new_snapshot_id": new_snapshot_id,
                "updated_at": updated_at,
                "metadata": metadata
            })
        
        return history
    
    def delete_branch(self, branch_name: str, namespace: str) -> bool:
        """Delete a branch.
        
        Args:
            branch_name: Name of the branch
            namespace: Namespace for the branch
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM branches 
                WHERE branch_name = ? AND namespace = ?
            """, (branch_name, namespace))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.close()
            print(f"Branch deletion failed: {e}")
            return False
    
    # ============================================================================
    # Tag Management Methods
    # ============================================================================
    
    def create_tag(self, tag_name: str, namespace: str, snapshot_id: str, 
                  metadata: Optional[Dict] = None) -> bool:
        """Create an immutable tag for audit-grade provenance.
        
        Tags are immutable labels that SHOULD be used for audit-grade provenance
        (e.g., "dataset v1.2 regulatory-export") according to the AIFS specification.
        
        Args:
            tag_name: Name of the tag
            namespace: Namespace for the tag
            snapshot_id: Snapshot ID to tag
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if tag already exists (tags are immutable)
            cursor.execute("""
                SELECT tag_name FROM tags 
                WHERE tag_name = ? AND namespace = ?
            """, (tag_name, namespace))
            
            if cursor.fetchone():
                raise ValueError(f"Tag {tag_name} already exists in namespace {namespace} (tags are immutable)")
            
            # Check if snapshot exists and is verified
            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
            
            if not self.verify_snapshot_signature(snapshot_id):
                raise ValueError(f"Snapshot {snapshot_id} signature verification failed")
            
            metadata_str = json.dumps(metadata) if metadata else None
            current_time = datetime.utcnow().isoformat()
            
            # Create tag
            cursor.execute("""
                INSERT INTO tags (tag_name, namespace, snapshot_id, created_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (tag_name, namespace, snapshot_id, current_time, metadata_str))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            conn.close()
            print(f"Tag creation failed: {e}")
            return False
    
    def get_tag(self, tag_name: str, namespace: str) -> Optional[Dict]:
        """Get tag information.
        
        Args:
            tag_name: Name of the tag
            namespace: Namespace for the tag
            
        Returns:
            Tag dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tag_name, namespace, snapshot_id, created_at, metadata
            FROM tags 
            WHERE tag_name = ? AND namespace = ?
        """, (tag_name, namespace))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        tag_name, namespace, snapshot_id, created_at, metadata_str = row
        metadata = json.loads(metadata_str) if metadata_str else {}
        
        return {
            "tag_name": tag_name,
            "namespace": namespace,
            "snapshot_id": snapshot_id,
            "created_at": created_at,
            "metadata": metadata
        }
    
    def list_tags(self, namespace: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """List tags.
        
        Args:
            namespace: Optional namespace filter
            limit: Maximum number of tags to return
            
        Returns:
            List of tag dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if namespace:
            cursor.execute("""
                SELECT tag_name, namespace, snapshot_id, created_at, metadata
                FROM tags 
                WHERE namespace = ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (namespace, limit))
        else:
            cursor.execute("""
                SELECT tag_name, namespace, snapshot_id, created_at, metadata
                FROM tags 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tags = []
        for row in rows:
            tag_name, namespace, snapshot_id, created_at, metadata_str = row
            metadata = json.loads(metadata_str) if metadata_str else {}
            
            tags.append({
                "tag_name": tag_name,
                "namespace": namespace,
                "snapshot_id": snapshot_id,
                "created_at": created_at,
                "metadata": metadata
            })
        
        return tags
    
    def delete_tag(self, tag_name: str, namespace: str) -> bool:
        """Delete a tag.
        
        Note: While tags are immutable, deletion may be needed for cleanup.
        This should be used with caution as it breaks audit-grade provenance.
        
        Args:
            tag_name: Name of the tag
            namespace: Namespace for the tag
            
        Returns:
            True if successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM tags 
                WHERE tag_name = ? AND namespace = ?
            """, (tag_name, namespace))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except Exception as e:
            conn.close()
            print(f"Tag deletion failed: {e}")
            return False