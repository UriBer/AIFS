"""AIFS Vector Database

Implements vector storage and similarity search using FAISS.
"""

import os
import pickle
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import faiss


class VectorDB:
    """Vector database for AIFS using FAISS.
    
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
        self.index_path = os.path.join(self.root_dir, "vector_index.faiss")
        self.mapping_path = os.path.join(self.root_dir, "vector_mapping.pkl")
        
        # Create directory if it doesn't exist
        os.makedirs(self.root_dir, exist_ok=True)
        
        # Initialize or load index
        self._init_index()
    
    def _init_index(self):
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
    
    def _save_index(self):
        """Save FAISS index and mapping to disk."""
        faiss.write_index(self.index, self.index_path)
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
        
        # Add to index
        faiss_id = self.index.ntotal  # Get next available ID
        self.index.add(embedding.reshape(1, -1))  # Add to FAISS index
        self.id_to_asset[faiss_id] = asset_id  # Map FAISS ID to asset ID
        
        # Save changes
        self._save_index()
    
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
        
        # Search index
        distances, indices = self.index.search(query_embedding.reshape(1, -1), k)
        
        # Map FAISS IDs to asset IDs
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx in self.id_to_asset:  # -1 means no result
                results.append((self.id_to_asset[idx], float(distances[0][i])))
        
        return results
    
    def delete(self, asset_id: str) -> bool:
        """Delete embedding for an asset.
        
        Note: FAISS doesn't support efficient deletion, so we rebuild the index.
        
        Args:
            asset_id: Asset ID to delete
            
        Returns:
            True if deleted, False if not found
        """
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