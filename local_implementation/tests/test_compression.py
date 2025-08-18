#!/usr/bin/env python3
"""Tests for AIFS Compression Service."""

import unittest
import tempfile
import os
from pathlib import Path

# Import AIFS components
from aifs.compression import CompressionService


class TestCompressionService(unittest.TestCase):
    """Test compression functionality."""

    def setUp(self):
        """Set up test environment."""
        self.compression_service = CompressionService()

    def test_compression_service_initialization(self):
        """Test compression service initialization."""
        # Test default compression level
        service = CompressionService()
        self.assertEqual(service.compression_level, 1)
        
        # Test custom compression level
        service = CompressionService(compression_level=10)
        self.assertEqual(service.compression_level, 10)

    def test_invalid_compression_level(self):
        """Test invalid compression level handling."""
        # Test level too low
        with self.assertRaises(ValueError):
            CompressionService(compression_level=0)
        
        # Test level too high
        with self.assertRaises(ValueError):
            CompressionService(compression_level=23)

    def test_basic_compression(self):
        """Test basic compression and decompression."""
        # Test data
        test_data = b"This is a test string that should be compressed. " * 100
        
        # Compress
        compressed_data = self.compression_service.compress(test_data)
        self.assertIsInstance(compressed_data, bytes)
        self.assertNotEqual(compressed_data, test_data)
        
        # Decompress
        decompressed_data = self.compression_service.decompress(compressed_data)
        self.assertEqual(decompressed_data, test_data)

    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        # Create data that compresses well
        test_data = b"0" * 10000
        
        # Compress
        compressed_data = self.compression_service.compress(test_data)
        
        # Get compression info
        info = self.compression_service.get_compression_info(
            len(test_data), len(compressed_data)
        )
        
        self.assertIn("compression_ratio", info)
        self.assertIn("space_saved", info)
        self.assertIn("space_saved_percent", info)
        
        # Should have some compression
        self.assertLess(info["compression_ratio"], 1.0)
        self.assertGreater(info["space_saved"], 0)

    def test_stream_compression(self):
        """Test streaming compression."""
        # Test data
        test_data = b"Streaming compression test data. " * 1000
        
        # Compress in streaming fashion using simple method
        compressed_data = self.compression_service.compress_stream_simple(test_data)
        
        # Decompress
        decompressed_data = self.compression_service.decompress(compressed_data)
        
        # Verify data integrity
        self.assertEqual(test_data, decompressed_data)
        
        # Test that compression actually reduced size
        self.assertLess(len(compressed_data), len(test_data))
        
        # Test compression ratio
        ratio = self.compression_service.get_compression_ratio(len(test_data), len(compressed_data))
        self.assertLess(ratio, 1.0)
    
    def test_advanced_stream_compression(self):
        """Test advanced streaming compression with compressobj/decompressobj."""
        # Test data
        test_data = b"Advanced streaming compression test data. " * 1000
        
        # Compress using advanced streaming
        compressed_data = self.compression_service.compress_stream(test_data, chunk_size=1000)
        
        # Decompress using streaming decompression
        decompressed_data = self.compression_service.decompress_stream(compressed_data, chunk_size=1000)
        
        # Verify data integrity
        self.assertEqual(test_data, decompressed_data)
        
        # Test that compression actually reduced size
        self.assertLess(len(compressed_data), len(test_data))

    def test_compression_detection(self):
        """Test compression detection."""
        # Test uncompressed data
        uncompressed_data = b"This is uncompressed data"
        is_compressed = self.compression_service.is_compressed(uncompressed_data)
        self.assertFalse(is_compressed)
        
        # Test compressed data
        compressed_data = self.compression_service.compress(uncompressed_data)
        is_compressed = self.compression_service.is_compressed(compressed_data)
        self.assertTrue(is_compressed)

    def test_compression_levels(self):
        """Test available compression levels."""
        levels = self.compression_service.get_compression_levels()
        
        self.assertIsInstance(levels, list)
        self.assertEqual(len(levels), 22)  # zstd supports levels 1-22
        self.assertEqual(levels[0], 1)
        self.assertEqual(levels[-1], 22)

    def test_compression_level_change(self):
        """Test changing compression level."""
        # Start with level 1
        service = CompressionService(compression_level=1)
        self.assertEqual(service.compression_level, 1)
        
        # Change to level 10
        service.set_compression_level(10)
        self.assertEqual(service.compression_level, 10)
        
        # Test compression still works
        test_data = b"Test data for compression level change"
        compressed_data = service.compress(test_data)
        decompressed_data = service.decompress(compressed_data)
        self.assertEqual(decompressed_data, test_data)

    def test_compression_stats(self):
        """Test compression statistics."""
        stats = self.compression_service.get_compression_stats()
        
        self.assertIn("compression_level", stats)
        self.assertIn("algorithm", stats)
        self.assertIn("compressor_name", stats)
        self.assertIn("supports_streaming", stats)
        
        self.assertEqual(stats["algorithm"], "zstd")
        self.assertEqual(stats["compressor_name"], "Zstandard")
        self.assertTrue(stats["supports_streaming"])

    def test_empty_data_compression(self):
        """Test compression of empty data."""
        empty_data = b""
        
        # Compress empty data
        compressed_data = self.compression_service.compress(empty_data)
        self.assertIsInstance(compressed_data, bytes)
        
        # Decompress
        decompressed_data = self.compression_service.decompress(compressed_data)
        self.assertEqual(decompressed_data, empty_data)
        
        # Check compression info for empty data
        info = self.compression_service.get_compression_info(0, len(compressed_data))
        self.assertEqual(info["original_size"], 0)
        self.assertEqual(info["compression_ratio"], 0.0)

    def test_large_data_compression(self):
        """Test compression of large data."""
        # Create large test data
        large_data = b"Large data test. " * 10000
        
        # Compress
        compressed_data = self.compression_service.compress(large_data)
        
        # Verify compression worked
        self.assertLess(len(compressed_data), len(large_data))
        
        # Decompress and verify
        decompressed_data = self.compression_service.decompress(compressed_data)
        self.assertEqual(decompressed_data, large_data)

    def test_unicode_data_compression(self):
        """Test compression of Unicode data."""
        # Test Unicode string
        unicode_string = "Hello, 世界! 🌍 This is a test with Unicode characters."
        unicode_data = unicode_string.encode('utf-8')
        
        # Compress
        compressed_data = self.compression_service.compress(unicode_data)
        
        # Decompress
        decompressed_data = self.compression_service.decompress(compressed_data)
        
        # Verify
        self.assertEqual(decompressed_data, unicode_data)
        self.assertEqual(decompressed_data.decode('utf-8'), unicode_string)

    def test_compression_error_handling(self):
        """Test compression error handling."""
        # Test with None data (should raise error)
        with self.assertRaises(Exception):
            self.compression_service.compress(None)
        
        # Test with invalid compressed data (should raise error)
        invalid_compressed = b"invalid-compressed-data"
        with self.assertRaises(Exception):
            self.compression_service.decompress(invalid_compressed)


if __name__ == "__main__":
    unittest.main()
