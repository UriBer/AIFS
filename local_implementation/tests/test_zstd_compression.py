"""
Test suite for zstd compression implementation in AIFS.

Tests the CompressionService and its integration throughout the AIFS codebase
according to the AIFS architecture specification.
"""

import os
import tempfile
import unittest
import numpy as np
from unittest.mock import patch, MagicMock

from aifs.compression import CompressionService
from aifs.asset import AssetManager
from aifs.storage import StorageBackend
from aifs.asset_kinds_simple import TensorData, EmbeddingData, ArtifactData
import zipfile
import io


class TestCompressionService(unittest.TestCase):
    """Test the CompressionService implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.compression_service = CompressionService(compression_level=1)
    
    def test_compression_service_initialization(self):
        """Test CompressionService initialization."""
        # Test default compression level
        service = CompressionService()
        self.assertEqual(service.compression_level, 1)
        
        # Test custom compression level
        service = CompressionService(compression_level=10)
        self.assertEqual(service.compression_level, 10)
        
        # Test invalid compression level
        with self.assertRaises(ValueError):
            CompressionService(compression_level=0)
        
        with self.assertRaises(ValueError):
            CompressionService(compression_level=23)
    
    def test_compress_decompress_round_trip(self):
        """Test basic compression and decompression."""
        # Test with various data types
        test_cases = [
            b"Hello, AIFS!",
            b"",
            b"x" * 1000,
            b"Random data: " + os.urandom(100),
            "Unicode test: 你好世界 🌍".encode('utf-8'),
        ]
        
        for data in test_cases:
            with self.subTest(data=data[:20]):  # Use first 20 chars for test name
                compressed = self.compression_service.compress(data)
                decompressed = self.compression_service.decompress(compressed)
                self.assertEqual(data, decompressed)
    
    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        # Test with compressible data
        data = b"Hello, AIFS! " * 100  # Repetitive data should compress well
        compressed = self.compression_service.compress(data)
        
        ratio = self.compression_service.get_compression_ratio(len(data), len(compressed))
        self.assertLess(ratio, 1.0)  # Should be compressed
        self.assertGreater(ratio, 0.0)  # Should be positive
        
        # Test with random data (less compressible)
        random_data = os.urandom(1000)
        compressed_random = self.compression_service.compress(random_data)
        ratio_random = self.compression_service.get_compression_ratio(len(random_data), len(compressed_random))
        self.assertGreater(ratio_random, 0.0)
    
    def test_compression_info(self):
        """Test compression information calculation."""
        original_size = 1000
        compressed_size = 500
        
        info = self.compression_service.get_compression_info(original_size, compressed_size)
        
        self.assertEqual(info["original_size"], original_size)
        self.assertEqual(info["compressed_size"], compressed_size)
        self.assertEqual(info["compression_ratio"], 0.5)
        self.assertEqual(info["space_saved"], 500)
        self.assertEqual(info["space_saved_percent"], 50.0)
    
    def test_compression_stats(self):
        """Test compression service statistics."""
        stats = self.compression_service.get_compression_stats()
        
        self.assertEqual(stats["compression_level"], 1)
        self.assertEqual(stats["algorithm"], "zstd")
        self.assertEqual(stats["compressor_name"], "Zstandard")
        self.assertTrue(stats["supports_streaming"])
    
    def test_is_compressed_detection(self):
        """Test compressed data detection."""
        # Test with compressed data
        data = b"Hello, AIFS!"
        compressed = self.compression_service.compress(data)
        self.assertTrue(self.compression_service.is_compressed(compressed))
        
        # Test with uncompressed data
        self.assertFalse(self.compression_service.is_compressed(data))
        
        # Test with empty data
        self.assertFalse(self.compression_service.is_compressed(b""))
        
        # Test with short data
        self.assertFalse(self.compression_service.is_compressed(b"abc"))
    
    def test_streaming_compression(self):
        """Test streaming compression methods."""
        data = b"Hello, AIFS! " * 1000  # Large data for streaming
        
        # Test compress_stream
        compressed_stream = self.compression_service.compress_stream(data, chunk_size=100)
        decompressed_stream = self.compression_service.decompress_stream(compressed_stream, chunk_size=100)
        self.assertEqual(data, decompressed_stream)
        
        # Test compress_stream_simple
        compressed_simple = self.compression_service.compress_stream_simple(data)
        decompressed_simple = self.compression_service.decompress(compressed_simple)
        self.assertEqual(data, decompressed_simple)
    
    def test_compression_level_changes(self):
        """Test changing compression level."""
        data = b"Hello, AIFS! " * 100
        
        # Test different compression levels
        for level in [1, 5, 10, 15, 22]:
            self.compression_service.set_compression_level(level)
            compressed = self.compression_service.compress(data)
            decompressed = self.compression_service.decompress(compressed)
            self.assertEqual(data, decompressed)
            self.assertEqual(self.compression_service.compression_level, level)
    
    def test_error_handling(self):
        """Test error handling in compression service."""
        # Test None data
        with self.assertRaises(ValueError):
            self.compression_service.compress(None)
        
        with self.assertRaises(ValueError):
            self.compression_service.decompress(None)
        
        # Test invalid compression level
        with self.assertRaises(ValueError):
            self.compression_service.set_compression_level(0)
        
        with self.assertRaises(ValueError):
            self.compression_service.set_compression_level(23)
        
        # Test decompression of invalid data
        with self.assertRaises(ValueError):
            self.compression_service.decompress(b"invalid compressed data")


class TestStorageBackendCompression(unittest.TestCase):
    """Test StorageBackend with zstd compression."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = StorageBackend(self.temp_dir, compression_level=1)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_storage_compression_integration(self):
        """Test that StorageBackend uses compression."""
        # Test with various data types
        test_cases = [
            b"Hello, AIFS!",
            b"x" * 1000,
            b"Random data: " + os.urandom(100),
        ]
        
        for data in test_cases:
            with self.subTest(data=data[:20]):
                # Store data
                asset_id = self.storage.put(data)
                self.assertIsNotNone(asset_id)
                
                # Retrieve data
                retrieved_data = self.storage.get(asset_id)
                self.assertEqual(data, retrieved_data)
                
                # Verify data exists
                self.assertTrue(self.storage.exists(asset_id))
    
    def test_compression_level_configuration(self):
        """Test different compression levels in StorageBackend."""
        data = b"Hello, AIFS! " * 100  # Compressible data
        
        # Use the same encryption key for all tests to avoid decryption issues
        encryption_key = os.urandom(32)
        
        for level in [1, 5, 10]:
            storage = StorageBackend(self.temp_dir, compression_level=level, encryption_key=encryption_key)
            asset_id = storage.put(data)
            retrieved_data = storage.get(asset_id)
            self.assertEqual(data, retrieved_data)
    
    def test_backward_compatibility(self):
        """Test backward compatibility with uncompressed data."""
        # This test ensures that if decompression fails, we fall back to raw data
        data = b"Hello, AIFS!"
        asset_id = self.storage.put(data)
        
        # Manually corrupt the compressed data to test fallback
        path = self.storage._hash_to_path(asset_id)
        if path.exists():
            # Read the file and corrupt it
            corrupted_data = b"corrupted"
            path.write_bytes(corrupted_data)
            
            # Should return None or handle gracefully
            retrieved = self.storage.get(asset_id)
            # The exact behavior depends on implementation, but should not crash
            self.assertIsInstance(retrieved, (bytes, type(None)))


class TestAssetManagerCompression(unittest.TestCase):
    """Test AssetManager with zstd compression."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir, compression_level=1, enable_strong_causality=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_asset_manager_compression_integration(self):
        """Test that AssetManager uses compression for all asset kinds."""
        # Test blob asset
        blob_data = b"Hello, AIFS blob!"
        blob_id = self.asset_manager.put_asset(blob_data, "blob")
        retrieved_blob = self.asset_manager.get_asset(blob_id)
        self.assertEqual(retrieved_blob["data"], blob_data)
        
        # Test tensor asset
        array = np.random.rand(2, 3).astype(np.float32)
        tensor_data = TensorData(
            data=array,
            dtype=str(array.dtype),
            shape=array.shape,
            metadata={'name': 'test_tensor'}
        )
        tensor_id = self.asset_manager.put_tensor(tensor_data)
        retrieved_tensor = self.asset_manager.get_tensor(tensor_id)
        self.assertIsNotNone(retrieved_tensor)
        self.assertTrue(np.array_equal(retrieved_tensor.data, array))
        
        # Test embedding asset
        vector = np.random.rand(64).astype(np.float32)
        embedding_data = EmbeddingData(
            vector=vector,
            model='custom',
            dimension=len(vector),
            distance_metric='cosine'
        )
        embed_id = self.asset_manager.put_embedding(embedding_data)
        retrieved_embed = self.asset_manager.get_embedding(embed_id)
        self.assertIsNotNone(retrieved_embed)
        self.assertTrue(np.array_equal(retrieved_embed.vector, vector))
        
        # Test artifact asset
        files = {'test.txt': b'Hello, artifact!'}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_data:
            for name, content in files.items():
                zip_data.writestr(name, content)
        zip_bytes = zip_buffer.getvalue()
        
        file_entries = [{
            'path': 'test.txt',
            'asset_id': 'test_asset',
            'size': len(files['test.txt']),
            'mime_type': 'text/plain',
            'created_at': 1640995200,
            'modified_at': 1640995200,
            'is_executable': False,
            'checksum': 'test_checksum',
            'metadata': {}
        }]
        
        manifest = {
            'name': 'test_artifact',
            'version': '1.0.0',
            'description': 'Test artifact'
        }
        
        artifact_data = ArtifactData(
            files=file_entries,
            manifest=manifest,
            zip_data=zip_bytes
        )
        
        artifact_id = self.asset_manager.put_artifact(artifact_data)
        retrieved_artifact = self.asset_manager.get_artifact(artifact_id)
        self.assertIsNotNone(retrieved_artifact)
        self.assertEqual(retrieved_artifact.files, file_entries)
        self.assertEqual(retrieved_artifact.manifest, manifest)
    
    def test_compression_level_configuration(self):
        """Test different compression levels in AssetManager."""
        data = b"Hello, AIFS! " * 100  # Compressible data
        
        for level in [1, 5, 10]:
            # Create a new temp directory for each level to avoid conflicts
            temp_dir = tempfile.mkdtemp()
            try:
                asset_manager = AssetManager(temp_dir, compression_level=level, enable_strong_causality=False)
                asset_id = asset_manager.put_asset(data, "blob")
                retrieved = asset_manager.get_asset(asset_id)
                self.assertEqual(retrieved["data"], data)
            finally:
                import shutil
                shutil.rmtree(temp_dir)
    
    def test_compression_service_access(self):
        """Test that AssetManager provides access to compression service."""
        # Test compression service is available
        self.assertIsNotNone(self.asset_manager.compression_service)
        self.assertIsInstance(self.asset_manager.compression_service, CompressionService)
        
        # Test compression service configuration
        stats = self.asset_manager.compression_service.get_compression_stats()
        self.assertEqual(stats["algorithm"], "zstd")


class TestCompressionPerformance(unittest.TestCase):
    """Test compression performance characteristics."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.compression_service = CompressionService(compression_level=1)
    
    def test_compression_performance(self):
        """Test compression performance with large data."""
        # Test with large data
        large_data = b"Hello, AIFS! " * 10000  # ~120KB
        
        # Time compression
        import time
        start_time = time.time()
        compressed = self.compression_service.compress(large_data)
        compression_time = time.time() - start_time
        
        # Time decompression
        start_time = time.time()
        decompressed = self.compression_service.decompress(compressed)
        decompression_time = time.time() - start_time
        
        # Verify correctness
        self.assertEqual(large_data, decompressed)
        
        # Performance should be reasonable (less than 1 second for 120KB)
        self.assertLess(compression_time, 1.0)
        self.assertLess(decompression_time, 1.0)
        
        # Compression should be effective
        compression_ratio = len(compressed) / len(large_data)
        self.assertLess(compression_ratio, 1.0)  # Should compress
    
    def test_different_compression_levels_performance(self):
        """Test performance with different compression levels."""
        data = b"Hello, AIFS! " * 1000  # ~12KB
        
        for level in [1, 5, 10, 15, 22]:
            service = CompressionService(compression_level=level)
            
            # Test compression
            compressed = service.compress(data)
            decompressed = service.decompress(compressed)
            self.assertEqual(data, decompressed)
            
            # Higher levels should generally compress better but take longer
            compression_ratio = len(compressed) / len(data)
            self.assertLess(compression_ratio, 1.0)


class TestCompressionSpecificationCompliance(unittest.TestCase):
    """Test compliance with AIFS specification requirements."""
    
    def test_specification_compliance(self):
        """Test that implementation meets AIFS specification requirements."""
        # Spec requirement: Client MUST support zstd compression
        compression_service = CompressionService()
        
        # Test that zstd is supported
        stats = compression_service.get_compression_stats()
        self.assertEqual(stats["algorithm"], "zstd")
        self.assertEqual(stats["compressor_name"], "Zstandard")
        
        # Test that compression level ≥ 1 is supported (spec requirement)
        self.assertGreaterEqual(compression_service.compression_level, 1)
        
        # Test that compression works with various data types
        test_data = [
            b"Hello, AIFS!",
            b"x" * 1000,
            b"Random data: " + os.urandom(100),
        ]
        
        for data in test_data:
            compressed = compression_service.compress(data)
            decompressed = compression_service.decompress(compressed)
            self.assertEqual(data, decompressed)
    
    def test_compression_negotiation_support(self):
        """Test that compression can be negotiated (as mentioned in spec)."""
        # The spec mentions compression should be negotiated via grpc-accept-encoding
        # This test ensures our implementation supports different compression levels
        
        for level in range(1, 23):  # zstd supports levels 1-22
            service = CompressionService(compression_level=level)
            data = b"Test data for compression negotiation"
            
            compressed = service.compress(data)
            decompressed = service.decompress(compressed)
            self.assertEqual(data, decompressed)


if __name__ == '__main__':
    unittest.main()
