"""AIFS Vector Database

Implements vector storage and similarity search using FAISS or scikit-learn fallback.
"""

import os
import pickle
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

# Try to import FAISS, fallback to scikit-learn
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    try:
        import sklearn
        from sklearn.neighbors import NearestNeighbors
        FAISS_AVAILABLE = False
        print("Warning: FAISS not available, using scikit-learn fallback for vector operations.")
    except ImportError:
        raise ImportError("Neither FAISS nor scikit-learn is available. Please install one of them.")


class VectorDB:
    """Vector database for AIFS using FAISS or scikit-learn fallback.
    
    Stores embeddings and provides similarity search functionality.
    """
    
    def __init__(self, root_dir: str, dimension: int = 1536):
        """Initialize vector database.
        
        Args:
            root_dir: Root directory for storage
            dimension: Dimension of embedding vectors (default: 1536 for OpenAI embeddings)
        """
        self.root_dir = os.path.abspath(root_dir)
        self.dimension = dimension
        self.faiss_available = FAISS_AVAILABLE
        
        if self.faiss_available:
            # FAISS implementation
            self.index_path = os.path.join(self.root_dir, "vector_index.faiss")
            self.mapping_path = os.path.join(self.root_dir, "vector_mapping.pkl")
            self.index = None
            self.id_to_asset = {}
        else:
            # scikit-learn fallback
            self.index_path = os.path.join(self.root_dir, "vector_index_sklearn.pkl")
            self.mapping_path = os.path.join(self.root_dir, "vector_mapping.pkl")
            self.index = None
            self.id_to_asset = {}
            self.embeddings = []
            self.asset_ids = []
        
        # Create directory if it doesn't exist
        os.makedirs(self.root_dir, exist_ok=True)
        
        # Initialize or load index
        self._init_index()
    
    def _init_index(self):
        """Initialize or load index."""
        if self.faiss_available:
            self._init_faiss_index()
        else:
            self._init_sklearn_index()
    
    def _init_faiss_index(self):
        """Initialize or load FAISS index."""
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            # Load existing index and mapping
            self.index = faiss.read_index(self.index_path)
            with open(self.mapping_path, 'rb') as f:
                self.id_to_asset = pickle.load(f)
        else:
            # Create new index and mapping
            self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance
            self.id_to_asset = {}  # Maps FAISS IDs to asset IDs
    
    def _init_sklearn_index(self):
        """Initialize or load scikit-learn index."""
        if os.path.exists(self.index_path) and os.path.exists(self.mapping_path):
            # Load existing index and mapping
            with open(self.index_path, 'rb') as f:
                data = pickle.load(f)
                self.index = data['index']
                self.embeddings = data['embeddings']
                self.asset_ids = data['asset_ids']
            with open(self.mapping_path, 'rb') as f:
                self.id_to_asset = pickle.load(f)
        else:
            # Create new index and mapping
            self.index = None
            self.embeddings = []
            self.asset_ids = []
            self.id_to_asset = {}
    
    def _save_index(self):
        """Save index and mapping to disk."""
        if self.faiss_available:
            self._save_faiss_index()
        else:
            self._save_sklearn_index()
    
    def _save_faiss_index(self):
        """Save FAISS index and mapping to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.mapping_path, 'wb') as f:
            pickle.dump(self.id_to_asset, f)
    
    def _save_sklearn_index(self):
        """Save scikit-learn index and mapping to disk."""
        data = {
            'index': self.index,
            'embeddings': self.embeddings,
            'asset_ids': self.asset_ids
        }
        with open(self.index_path, 'wb') as f:
            pickle.dump(data, f)
        with open(self.mapping_path, 'wb') as f:
            pickle.dump(self.id_to_asset, f)
    
    def add(self, asset_id: str, embedding: np.ndarray):
        """Add embedding for an asset.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            embedding: Embedding vector as numpy array
        """
        # Ensure embedding is the right shape
        if embedding.shape != (self.dimension,):
            raise ValueError(f"Embedding must have shape ({self.dimension},)")
        
        if self.faiss_available:
            self._add_faiss(asset_id, embedding)
        else:
            self._add_sklearn(asset_id, embedding)
    
    def _add_faiss(self, asset_id: str, embedding: np.ndarray):
        """Add embedding to FAISS index."""
        # Add to index
        faiss_id = self.index.ntotal  # Get next available ID
        self.index.add(embedding.reshape(1, -1))  # Add to FAISS index
        self.id_to_asset[faiss_id] = asset_id  # Map FAISS ID to asset ID
        
        # Save changes
        self._save_index()
    
    def _add_sklearn(self, asset_id: str, embedding: np.ndarray):
        """Add embedding to scikit-learn index."""
        # Add to lists
        self.embeddings.append(embedding)
        self.asset_ids.append(asset_id)
        
        # Update mapping
        faiss_id = len(self.embeddings) - 1
        self.id_to_asset[faiss_id] = asset_id
        
        # Rebuild index if we have enough data
        if len(self.embeddings) > 1:
            self._rebuild_sklearn_index()
        
        # Save changes
        self._save_index()
    
    def _rebuild_sklearn_index(self):
        """Rebuild scikit-learn index."""
        if len(self.embeddings) > 0:
            embeddings_array = np.array(self.embeddings)
            self.index = NearestNeighbors(n_neighbors=min(10, len(self.embeddings)), 
                                        algorithm='auto', metric='euclidean')
            self.index.fit(embeddings_array)
    
    def search(self, query_embedding: np.ndarray, k: int = 10) -> List[Tuple[str, float]]:
        """Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            
        Returns:
            List of (asset_id, distance) tuples
        """
        # Ensure embedding is the right shape
        if query_embedding.shape != (self.dimension,):
            raise ValueError(f"Query embedding must have shape ({self.dimension},)")
        
        if self.faiss_available:
            return self._search_faiss(query_embedding, k)
        else:
            return self._search_sklearn(query_embedding, k)
    
    def _search_faiss(self, query_embedding: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Search using FAISS."""
        # Search index
        distances, indices = self.index.search(query_embedding.reshape(1, -1), k)
        
        # Map FAISS IDs to asset IDs
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in self.id_to_asset:  # -1 means no result
                results.append((self.id_to_asset[idx], float(distances[0][i])))
        
        return results
    
    def _search_sklearn(self, query_embedding: np.ndarray, k: int) -> List[Tuple[str, float]]:
        """Search using scikit-learn."""
        if len(self.embeddings) == 0:
            return []
        
        # Ensure index is built
        if self.index is None:
            self._rebuild_sklearn_index()
        
        if self.index is None:
            return []
        
        # Search
        query_reshaped = query_embedding.reshape(1, -1)
        distances, indices = self.index.kneighbors(query_reshaped, n_neighbors=min(k, len(self.embeddings)))
        
        # Map indices to asset IDs
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.asset_ids):
                asset_id = self.asset_ids[idx]
                distance = float(distances[0][i])
                results.append((asset_id, distance))
        
        return results
    
    def delete(self, asset_id: str) -> bool:
        """Delete embedding for an asset.
        
        Note: This is inefficient for large datasets as it requires rebuilding the index.
        
        Args:
            asset_id: Asset ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self.faiss_available:
            return self._delete_faiss(asset_id)
        else:
            return self._delete_sklearn(asset_id)
    
    def _delete_faiss(self, asset_id: str) -> bool:
        """Delete from FAISS index."""
        # Find FAISS IDs to delete
        faiss_ids_to_delete = []
        for faiss_id, aid in self.id_to_asset.items():
            if aid == asset_id:
                faiss_ids_to_delete.append(faiss_id)
        
        if not faiss_ids_to_delete:
            return False  # Asset not found
        
        # Remove from mapping
        for faiss_id in faiss_ids_to_delete:
            del self.id_to_asset[faiss_id]
        
        # Rebuild index (FAISS doesn't support efficient deletion)
        # This is inefficient but works for a local implementation
        # In production, you'd use a more sophisticated approach
        self._save_index()
        
        return True
    
    def _delete_sklearn(self, asset_id: str) -> bool:
        """Delete from scikit-learn index."""
        if asset_id not in self.asset_ids:
            return False
        
        # Remove from lists
        idx = self.asset_ids.index(asset_id)
        del self.embeddings[idx]
        del self.asset_ids[idx]
        
        # Update mapping
        new_id_to_asset = {}
        for i, aid in enumerate(self.asset_ids):
            new_id_to_asset[i] = aid
        self.id_to_asset = new_id_to_asset
        
        # Rebuild index
        self._rebuild_sklearn_index()
        
        # Save changes
        self._save_index()
        
        return True
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        if self.faiss_available:
            return {
                "backend": "FAISS",
                "total_vectors": self.index.ntotal if self.index else 0,
                "dimension": self.dimension,
                "index_type": "IndexFlatL2"
            }
        else:
            return {
                "backend": "scikit-learn",
                "total_vectors": len(self.embeddings),
                "dimension": self.dimension,
                "index_type": "NearestNeighbors"
            }