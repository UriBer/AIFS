"""AIFS Embedding Utilities

Provides simple text embedding functionality for vector search.
"""

import hashlib
import numpy as np
from typing import Union, List


class SimpleTextEmbedder:
    """Simple text embedder that converts text to fixed-dimensional vectors.
    
    This is a basic implementation for demonstration purposes.
    In production, you would use a proper embedding model like OpenAI's text-embedding-ada-002,
    sentence-transformers, or similar.
    """
    
    def __init__(self, dimension: int = 128):
        """Initialize the embedder.
        
        Args:
            dimension: Output vector dimension
        """
        self.dimension = dimension
    
    def embed_text(self, text: str) -> np.ndarray:
        """Convert text to embedding vector.
        
        Args:
            text: Input text string
            
        Returns:
            Embedding vector as numpy array
        """
        # Convert text to bytes and hash it
        text_bytes = text.encode('utf-8')
        
        # Create a deterministic vector from the text
        # This is a simple approach - in production use proper embedding models
        vector = np.zeros(self.dimension, dtype=np.float32)
        
        # Use multiple hash functions to fill the vector
        for i in range(0, self.dimension, 64):  # Process in 64-byte chunks
            # Create different hash variants
            hash_input = text_bytes + str(i).encode('utf-8')
            hash_value = hashlib.sha256(hash_input).digest()
            
            # Convert hash bytes to float values
            for j, byte_val in enumerate(hash_value):
                if i + j < self.dimension:
                    # Convert byte to float in [-1, 1] range
                    vector[i + j] = (byte_val / 128.0) - 1.0
        
        # Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector
    
    def embed_file(self, file_path: str) -> np.ndarray:
        """Embed the contents of a file.
        
        Args:
            file_path: Path to the file to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.embed_text(content)
        except UnicodeDecodeError:
            # Try binary mode for non-text files
            with open(file_path, 'rb') as f:
                content = f.read()
            # Convert binary content to text representation
            text_repr = str(content[:1000])  # First 1000 bytes as string
            return self.embed_text(text_repr)
    
    def embed_binary(self, data: bytes) -> np.ndarray:
        """Embed binary data.
        
        Args:
            data: Binary data to embed
            
        Returns:
            Embedding vector as numpy array
        """
        # Convert binary data to text representation
        text_repr = str(data[:1000])  # First 1000 bytes as string
        return self.embed_text(text_repr)


def get_embedder(dimension: int = 128) -> SimpleTextEmbedder:
    """Get a text embedder instance.
    
    Args:
        dimension: Output vector dimension
        
    Returns:
        SimpleTextEmbedder instance
    """
    return SimpleTextEmbedder(dimension)


def embed_text(text: str, dimension: int = 128) -> np.ndarray:
    """Quick function to embed text.
    
    Args:
        text: Input text string
        dimension: Output vector dimension
        
    Returns:
        Embedding vector as numpy array
    """
    embedder = SimpleTextEmbedder(dimension)
    return embedder.embed_text(text)


def embed_file(file_path: str, dimension: int = 128) -> np.ndarray:
    """Quick function to embed a file.
    
    Args:
        file_path: Path to the file to embed
        dimension: Output vector dimension
        
    Returns:
        Embedding vector as numpy array
    """
    embedder = SimpleTextEmbedder(dimension)
    return embedder.embed_file(file_path)
