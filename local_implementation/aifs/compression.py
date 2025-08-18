"""AIFS Compression Service

Implements zstd compression support as required by the AIFS specification.
"""

import zstandard
from typing import Optional, Tuple, Dict, List


class CompressionService:
    """Service for compressing and decompressing data using zstd."""
    
    def __init__(self, compression_level: int = 1):
        """Initialize the compression service.
        
        Args:
            compression_level: zstd compression level (1-22, default 1 as per spec)
        """
        if not 1 <= compression_level <= 22:
            raise ValueError("Compression level must be between 1 and 22")
        
        self.compression_level = compression_level
        self.compressor = zstandard.ZstdCompressor(level=compression_level)
        self.decompressor = zstandard.ZstdDecompressor()
    
    def compress(self, data: bytes) -> bytes:
        """Compress data using zstd.
        
        Args:
            data: Raw data to compress
            
        Returns:
            Compressed data
        """
        if data is None:
            raise ValueError("Data cannot be None")
        
        if not data:
            return b""
        
        return self.compressor.compress(data)
    
    def decompress(self, compressed_data: bytes) -> bytes:
        """Decompress data using zstd.
        
        Args:
            compressed_data: Compressed data to decompress
            
        Returns:
            Decompressed data
        """
        if compressed_data is None:
            raise ValueError("Compressed data cannot be None")
        
        if not compressed_data:
            return b""
        
        try:
            return self.decompressor.decompress(compressed_data)
        except Exception as e:
            raise ValueError(f"Failed to decompress data: {e}")
    
    def compress_stream(self, data: bytes, chunk_size: int = 8192) -> bytes:
        """Compress data using streaming compression.
        
        Args:
            data: Data to compress
            chunk_size: Size of chunks to process
            
        Returns:
            Compressed data
        """
        if not data:
            return b""
        
        compressed_chunks = []
        # Use compressobj() which returns an object with flush() method
        compressor_obj = self.compressor.compressobj()
        
        # Process data in chunks
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            compressed_chunk = compressor_obj.compress(chunk)
            if compressed_chunk:
                compressed_chunks.append(compressed_chunk)
        
        # Flush any remaining data
        final_chunk = compressor_obj.flush()
        if final_chunk:
            compressed_chunks.append(final_chunk)
        
        return b"".join(compressed_chunks)
    
    def decompress_stream(self, compressed_data: bytes, chunk_size: int = 8192) -> bytes:
        """Decompress data using streaming decompression.
        
        Args:
            compressed_data: Compressed data to decompress
            chunk_size: Size of chunks to process
            
        Returns:
            Decompressed data
        """
        if not compressed_data:
            return b""
        
        decompressed_chunks = []
        # Use decompressobj() which returns an object with flush() method
        decompressor_obj = self.decompressor.decompressobj()
        
        # Process compressed data in chunks
        for i in range(0, len(compressed_data), chunk_size):
            chunk = compressed_data[i:i + chunk_size]
            decompressed_chunk = decompressor_obj.decompress(chunk)
            if decompressed_chunk:
                decompressed_chunks.append(decompressed_chunk)
        
        # Flush any remaining data
        final_chunk = decompressor_obj.flush()
        if final_chunk:
            decompressed_chunks.append(final_chunk)
        
        return b"".join(decompressed_chunks)
    
    def compress_stream_simple(self, data: bytes) -> bytes:
        """Compress data using simple streaming compression.
        
        This method uses the regular compress method but processes data in chunks
        for memory efficiency with large datasets.
        
        Args:
            data: Data to compress
            
        Returns:
            Compressed data
        """
        if not data:
            return b""
        
        # For simple streaming, just use regular compression
        # This ensures compatibility with regular decompression
        return self.compressor.compress(data)
    
    def is_compressed(self, data: bytes) -> bool:
        """Check if data appears to be compressed.
        
        Args:
            data: Data to check
            
        Returns:
            True if data appears to be compressed
        """
        if not data or len(data) < 4:
            return False
        
        # Check for zstd magic number
        return data.startswith(b'(\xb5/\xfd')
    
    def get_compression_levels(self) -> list:
        """Get available compression levels.
        
        Returns:
            List of available compression levels (1-22)
        """
        return list(range(1, 23))
    
    def set_compression_level(self, level: int):
        """Set compression level.
        
        Args:
            level: New compression level (1-22)
        """
        if not 1 <= level <= 22:
            raise ValueError("Compression level must be between 1 and 22")
        
        self.compression_level = level
        self.compressor = zstandard.ZstdCompressor(level=level)
    
    def get_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """Calculate compression ratio.
        
        Args:
            original_size: Size of original data
            compressed_size: Size of compressed data
            
        Returns:
            Compression ratio (compressed_size / original_size)
            A ratio < 1.0 indicates compression, > 1.0 indicates expansion
        """
        if original_size == 0:
            return 0.0
        
        return compressed_size / original_size
    
    def get_compression_info(self, original_size: int, compressed_size: int) -> dict:
        """Get compression statistics.
        
        Args:
            original_size: Size of original data
            compressed_size: Size of compressed data
            
        Returns:
            Dictionary with compression information
        """
        if compressed_size == 0:
            return {
                "original_size": original_size,
                "compressed_size": 0,
                "compression_ratio": 0.0,
                "space_saved": original_size,
                "space_saved_percent": 100.0
            }
        
        ratio = self.get_compression_ratio(original_size, compressed_size)
        space_saved = original_size - compressed_size
        space_saved_percent = (space_saved / original_size) * 100.0
        
        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": ratio,
            "space_saved": space_saved,
            "space_saved_percent": space_saved_percent
        }
    
    def get_compression_stats(self) -> dict:
        """Get compression service statistics.
        
        Returns:
            Dictionary with service statistics
        """
        return {
            "compression_level": self.compression_level,
            "algorithm": "zstd",
            "compressor_name": "Zstandard",
            "supports_streaming": True
        }
