"""AIFS Compression Service

Implements zstd compression support as required by the AIFS specification.
"""

import zstandard as zstd
from typing import Optional, Tuple, Dict, List


class CompressionService:
    """Handles compression and decompression for AIFS.
    
    Implements zstd compression as required by the specification.
    """
    
    def __init__(self, compression_level: int = 1):
        """Initialize compression service.
        
        Args:
            compression_level: zstd compression level (1-22, default 1 as per spec)
        """
        if not 1 <= compression_level <= 22:
            raise ValueError("Compression level must be between 1 and 22")
        
        self.compression_level = compression_level
        self.compressor = zstd.ZstdCompressor(level=compression_level)
        self.decompressor = zstd.ZstdDecompressor()
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using zstd.
        
        Args:
            data: Raw data to compress
            
        Returns:
            Compressed data
        """
        return self.compressor.compress(data)
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress data using zstd.
        
        Args:
            compressed_data: Compressed data
            
        Returns:
            Decompressed data
        """
        return self.decompressor.decompress(compressed_data)
    
    def compress_stream(self, data: bytes, chunk_size: int = 1024 * 1024) -> bytes:
        """Compress data in streaming fashion.
        
        Args:
            data: Raw data to compress
            chunk_size: Size of chunks to process
            
        Returns:
            Compressed data
        """
        compressed_chunks = []
        
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            compressed_chunk = self.compress(chunk)
            compressed_chunks.append(compressed_chunk)
        
        return b''.join(compressed_chunks)
    
    def get_compression_info(self, original_size: int, compressed_size: int) -> Dict:
        """Get compression statistics.
        
        Args:
            original_size: Size of original data
            compressed_size: Size of compressed data
            
        Returns:
            Dictionary with compression statistics
        """
        if original_size == 0:
            return {
                "original_size": 0,
                "compressed_size": 0,
                "compression_ratio": 0.0,
                "space_saved": 0,
                "space_saved_percent": 0.0
            }
        
        compression_ratio = compressed_size / original_size
        space_saved = original_size - compressed_size
        space_saved_percent = (space_saved / original_size) * 100
        
        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio,
            "space_saved": space_saved,
            "space_saved_percent": space_saved_percent
        }
    
    def is_compressed(self, data: bytes) -> bool:
        """Check if data appears to be zstd compressed.
        
        Args:
            data: Data to check
            
        Returns:
            True if data appears to be zstd compressed
        """
        # zstd has a magic header
        if len(data) < 4:
            return False
        
        # Check for zstd magic number (0x28B52FFD)
        return data[:4] == b'\x28\xb5\x2f\xfd'
    
    def get_compression_levels(self) -> List[int]:
        """Get available compression levels.
        
        Returns:
            List of available compression levels
        """
        return list(range(1, 23))  # zstd supports levels 1-22
    
    def set_compression_level(self, level: int):
        """Set compression level.
        
        Args:
            level: New compression level (1-22)
        """
        if not 1 <= level <= 22:
            raise ValueError("Compression level must be between 1 and 22")
        
        self.compression_level = level
        self.compressor = zstd.ZstdCompressor(level=level)
    
    def get_compression_stats(self) -> Dict:
        """Get current compression configuration.
        
        Returns:
            Dictionary with compression configuration
        """
        return {
            "compression_level": self.compression_level,
            "algorithm": "zstd",
            "compressor_name": "Zstandard",
            "supports_streaming": True
        }
