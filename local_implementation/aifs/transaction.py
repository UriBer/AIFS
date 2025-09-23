"""
AIFS Transaction System for Strong Causality

Implements atomic transactions and strong causality guarantees as specified in the AIFS architecture.
Ensures that "Asset B SHALL NOT be visible until A is fully committed" when B lists A as a parent.
"""

import sqlite3
import threading
import time
import uuid
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager


class TransactionState(Enum):
    """Transaction state enumeration."""
    PENDING = "pending"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Transaction:
    """Transaction data structure."""
    transaction_id: str
    state: TransactionState
    created_at: float
    assets: Set[str]  # Assets in this transaction
    dependencies: Set[str]  # Parent assets this transaction depends on
    metadata: Dict[str, Any]


class TransactionManager:
    """Manages transactions and ensures strong causality."""
    
    def __init__(self, db_path: str):
        """Initialize transaction manager.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._active_transactions: Dict[str, Transaction] = {}
        self._asset_transactions: Dict[str, str] = {}  # asset_id -> transaction_id
        self._init_db()
    
    def _init_db(self):
        """Initialize transaction tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                created_at REAL NOT NULL,
                committed_at REAL,
                metadata TEXT
            )
        ''')
        
        # Create transaction_assets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_assets (
                transaction_id TEXT,
                asset_id TEXT,
                PRIMARY KEY (transaction_id, asset_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
            )
        ''')
        
        # Create transaction_dependencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_dependencies (
                transaction_id TEXT,
                parent_asset_id TEXT,
                PRIMARY KEY (transaction_id, parent_asset_id),
                FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
            )
        ''')
        
        # Create asset_visibility table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_visibility (
                asset_id TEXT PRIMARY KEY,
                visible BOOLEAN NOT NULL DEFAULT FALSE,
                transaction_id TEXT,
                committed_at REAL,
                FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def begin_transaction(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Begin a new transaction.
        
        Args:
            metadata: Optional transaction metadata
            
        Returns:
            Transaction ID
        """
        with self._lock:
            transaction_id = str(uuid.uuid4())
            transaction = Transaction(
                transaction_id=transaction_id,
                state=TransactionState.PENDING,
                created_at=time.time(),
                assets=set(),
                dependencies=set(),
                metadata=metadata or {}
            )
            
            self._active_transactions[transaction_id] = transaction
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transactions (transaction_id, state, created_at, metadata) VALUES (?, ?, ?, ?)",
                (transaction_id, transaction.state.value, transaction.created_at, 
                 str(transaction.metadata))
            )
            conn.commit()
            conn.close()
            
            return transaction_id
    
    def add_asset_to_transaction(self, transaction_id: str, asset_id: str) -> bool:
        """Add an asset to a transaction.
        
        Args:
            transaction_id: Transaction ID
            asset_id: Asset ID
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if transaction_id not in self._active_transactions:
                return False
            
            transaction = self._active_transactions[transaction_id]
            if transaction.state != TransactionState.PENDING:
                return False
            
            transaction.assets.add(asset_id)
            self._asset_transactions[asset_id] = transaction_id
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO transaction_assets (transaction_id, asset_id) VALUES (?, ?)",
                (transaction_id, asset_id)
            )
            conn.commit()
            conn.close()
            
            return True
    
    def add_dependency(self, transaction_id: str, parent_asset_id: str) -> bool:
        """Add a dependency to a transaction.
        
        Args:
            transaction_id: Transaction ID
            parent_asset_id: Parent asset ID
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if transaction_id not in self._active_transactions:
                return False
            
            transaction = self._active_transactions[transaction_id]
            if transaction.state != TransactionState.PENDING:
                return False
            
            transaction.dependencies.add(parent_asset_id)
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO transaction_dependencies (transaction_id, parent_asset_id) VALUES (?, ?)",
                (transaction_id, parent_asset_id)
            )
            conn.commit()
            conn.close()
            
            return True
    
    def check_dependencies_committed(self, transaction_id: str) -> bool:
        """Check if all dependencies are committed.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if all dependencies are committed, False otherwise
        """
        with self._lock:
            if transaction_id not in self._active_transactions:
                return False
            
            transaction = self._active_transactions[transaction_id]
            
            # If no dependencies, return True
            if not transaction.dependencies:
                return True
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for parent_asset_id in transaction.dependencies:
                cursor.execute(
                    "SELECT visible FROM asset_visibility WHERE asset_id = ?",
                    (parent_asset_id,)
                )
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    conn.close()
                    return False
            
            conn.close()
            return True
    
    def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a transaction and make assets visible.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if transaction_id not in self._active_transactions:
                return False
            
            transaction = self._active_transactions[transaction_id]
            
            # Check if all dependencies are committed
            if not self.check_dependencies_committed(transaction_id):
                return False
            
            # Update transaction state
            transaction.state = TransactionState.COMMITTING
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Update transaction state
                cursor.execute(
                    "UPDATE transactions SET state = ?, committed_at = ? WHERE transaction_id = ?",
                    (TransactionState.COMMITTING.value, time.time(), transaction_id)
                )
                
                # Make all assets visible
                for asset_id in transaction.assets:
                    cursor.execute(
                        "INSERT OR REPLACE INTO asset_visibility (asset_id, visible, transaction_id, committed_at) "
                        "VALUES (?, ?, ?, ?)",
                        (asset_id, True, transaction_id, time.time())
                    )
                
                # Update transaction state to committed
                cursor.execute(
                    "UPDATE transactions SET state = ? WHERE transaction_id = ?",
                    (TransactionState.COMMITTED.value, transaction_id)
                )
                
                conn.commit()
                
                # Update in-memory state
                transaction.state = TransactionState.COMMITTED
                
                # Clean up
                for asset_id in transaction.assets:
                    if asset_id in self._asset_transactions:
                        del self._asset_transactions[asset_id]
                
                del self._active_transactions[transaction_id]
                
                return True
                
            except Exception as e:
                conn.rollback()
                transaction.state = TransactionState.FAILED
                return False
            finally:
                conn.close()
    
    def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback a transaction.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            if transaction_id not in self._active_transactions:
                return False
            
            transaction = self._active_transactions[transaction_id]
            transaction.state = TransactionState.ROLLING_BACK
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Update transaction state
                cursor.execute(
                    "UPDATE transactions SET state = ? WHERE transaction_id = ?",
                    (TransactionState.ROLLED_BACK.value, transaction_id)
                )
                
                # Remove asset visibility
                for asset_id in transaction.assets:
                    cursor.execute(
                        "DELETE FROM asset_visibility WHERE asset_id = ?",
                        (asset_id,)
                    )
                
                conn.commit()
                
                # Update in-memory state
                transaction.state = TransactionState.ROLLED_BACK
                
                # Clean up
                for asset_id in transaction.assets:
                    if asset_id in self._asset_transactions:
                        del self._asset_transactions[asset_id]
                
                del self._active_transactions[transaction_id]
                
                return True
                
            except Exception as e:
                conn.rollback()
                transaction.state = TransactionState.FAILED
                return False
            finally:
                conn.close()
    
    def is_asset_visible(self, asset_id: str) -> bool:
        """Check if an asset is visible.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            True if asset is visible, False otherwise
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT visible FROM asset_visibility WHERE asset_id = ?",
                (asset_id,)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            return result is not None and result[0]
    
    def get_asset_transaction(self, asset_id: str) -> Optional[str]:
        """Get the transaction ID for an asset.
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Transaction ID if asset is in a transaction, None otherwise
        """
        with self._lock:
            return self._asset_transactions.get(asset_id)
    
    def get_transaction_state(self, transaction_id: str) -> Optional[TransactionState]:
        """Get the state of a transaction.
        
        Args:
            transaction_id: Transaction ID
            
        Returns:
            Transaction state or None if not found
        """
        with self._lock:
            if transaction_id in self._active_transactions:
                return self._active_transactions[transaction_id].state
            
            # Check database for committed/rolled back transactions
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT state FROM transactions WHERE transaction_id = ?",
                (transaction_id,)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return TransactionState(result[0])
            
            return None
    
    def get_pending_transactions(self) -> List[str]:
        """Get list of pending transaction IDs.
        
        Returns:
            List of pending transaction IDs
        """
        with self._lock:
            return [tid for tid, txn in self._active_transactions.items() 
                   if txn.state == TransactionState.PENDING]
    
    def cleanup_old_transactions(self, max_age_seconds: float = 3600) -> int:
        """Clean up old completed transactions.
        
        Args:
            max_age_seconds: Maximum age of transactions to keep
            
        Returns:
            Number of transactions cleaned up
        """
        with self._lock:
            cutoff_time = time.time() - max_age_seconds
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Find old completed transactions
            cursor.execute(
                "SELECT transaction_id FROM transactions WHERE state IN (?, ?) AND created_at < ?",
                (TransactionState.COMMITTED.value, TransactionState.ROLLED_BACK.value, cutoff_time)
            )
            old_transactions = [row[0] for row in cursor.fetchall()]
            
            if old_transactions:
                # Delete transaction data
                placeholders = ','.join('?' * len(old_transactions))
                cursor.execute(f"DELETE FROM transactions WHERE transaction_id IN ({placeholders})", old_transactions)
                cursor.execute(f"DELETE FROM transaction_assets WHERE transaction_id IN ({placeholders})", old_transactions)
                cursor.execute(f"DELETE FROM transaction_dependencies WHERE transaction_id IN ({placeholders})", old_transactions)
                
                conn.commit()
            
            conn.close()
            
            return len(old_transactions)
    
    @contextmanager
    def transaction(self, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for transactions.
        
        Args:
            metadata: Optional transaction metadata
            
        Yields:
            Transaction ID
        """
        transaction_id = self.begin_transaction(metadata)
        try:
            yield transaction_id
            self.commit_transaction(transaction_id)
        except Exception:
            self.rollback_transaction(transaction_id)
            raise


class StrongCausalityManager:
    """Manages strong causality guarantees for asset lineage."""
    
    def __init__(self, transaction_manager: TransactionManager, metadata_store):
        """Initialize strong causality manager.
        
        Args:
            transaction_manager: Transaction manager instance
            metadata_store: Metadata store instance
        """
        self.transaction_manager = transaction_manager
        self.metadata_store = metadata_store
    
    def put_asset_with_causality(self, asset_id: str, asset_data: Dict[str, Any], 
                                parents: Optional[List[Dict]] = None,
                                transaction_id: Optional[str] = None) -> str:
        """Put an asset with strong causality guarantees.
        
        Args:
            asset_id: Asset ID
            asset_data: Asset data
            parents: List of parent assets
            transaction_id: Optional transaction ID
            
        Returns:
            Transaction ID
        """
        if transaction_id is None:
            transaction_id = self.transaction_manager.begin_transaction()
        
        # Add asset to transaction
        self.transaction_manager.add_asset_to_transaction(transaction_id, asset_id)
        
        # Add dependencies
        if parents:
            for parent in parents:
                parent_id = parent["asset_id"]
                self.transaction_manager.add_dependency(transaction_id, parent_id)
        
        # Store asset metadata (but not visible yet)
        self.metadata_store.add_asset(
            asset_id=asset_id,
            kind=asset_data.get("kind", "blob"),
            size=asset_data.get("size", 0),
            metadata=asset_data.get("metadata")
        )
        
        # Add lineage information
        if parents:
            for parent in parents:
                self.metadata_store.add_lineage(
                    child_id=asset_id,
                    parent_id=parent["asset_id"],
                    transform_name=parent.get("transform_name"),
                    transform_digest=parent.get("transform_digest")
                )
        
        return transaction_id
    
    def commit_asset(self, asset_id: str, transaction_id: str) -> bool:
        """Commit an asset and make it visible.
        
        Args:
            asset_id: Asset ID
            transaction_id: Transaction ID
            
        Returns:
            True if successful, False otherwise
        """
        return self.transaction_manager.commit_transaction(transaction_id)
    
    def get_visible_assets(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get only visible assets.
        
        Args:
            limit: Maximum number of assets to return
            offset: Number of assets to skip
            
        Returns:
            List of visible asset metadata
        """
        # Get visible asset IDs from transaction database
        txn_conn = sqlite3.connect(self.transaction_manager.db_path)
        txn_cursor = txn_conn.cursor()
        
        # Check if asset_visibility table exists
        txn_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='asset_visibility'")
        if not txn_cursor.fetchone():
            # Table doesn't exist, return empty list
            txn_conn.close()
            return []
        
        # Get visible asset IDs
        txn_cursor.execute('''
            SELECT asset_id FROM asset_visibility 
            WHERE visible = TRUE 
            ORDER BY committed_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        visible_asset_ids = [row[0] for row in txn_cursor.fetchall()]
        txn_conn.close()
        
        if not visible_asset_ids:
            return []
        
        # Get asset metadata from metadata database
        metadata_conn = sqlite3.connect(self.metadata_store.db_path)
        metadata_cursor = metadata_conn.cursor()
        
        # Create placeholders for the IN clause
        placeholders = ','.join('?' * len(visible_asset_ids))
        metadata_cursor.execute(f'''
            SELECT asset_id, kind, size, metadata, created_at
            FROM assets 
            WHERE asset_id IN ({placeholders})
            ORDER BY created_at DESC
        ''', visible_asset_ids)
        
        assets = []
        for row in metadata_cursor.fetchall():
            asset_id, kind, size, metadata_str, created_at = row
            metadata = eval(metadata_str) if metadata_str else {}
            
            assets.append({
                "asset_id": asset_id,
                "kind": kind,
                "size": size,
                "created_at": created_at,
                "metadata": metadata
            })
        
        metadata_conn.close()
        return assets
    
    def get_asset_with_causality(self, asset_id: str) -> Optional[Dict]:
        """Get an asset only if it's visible (strong causality).
        
        Args:
            asset_id: Asset ID
            
        Returns:
            Asset metadata if visible, None otherwise
        """
        if not self.transaction_manager.is_asset_visible(asset_id):
            return None
        
        return self.metadata_store.get_asset(asset_id)
    
    def wait_for_dependencies(self, transaction_id: str, timeout_seconds: float = 30.0) -> bool:
        """Wait for all dependencies to be committed.
        
        Args:
            transaction_id: Transaction ID
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if all dependencies committed, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            if self.transaction_manager.check_dependencies_committed(transaction_id):
                return True
            time.sleep(0.1)
        
        return False
