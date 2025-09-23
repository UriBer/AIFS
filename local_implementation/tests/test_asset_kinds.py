#!/usr/bin/env python3
"""
Comprehensive tests for AIFS Asset Kinds implementation.

Tests all four asset kinds: Blob, Tensor, Embed, and Artifact
according to the AIFS architecture specification.
"""

import unittest
import tempfile
import numpy as np
import zipfile
import io
import json
from pathlib import Path

# Import AIFS modules
from aifs.asset import AssetManager
from aifs.asset_kinds_simple import (
    SimpleAssetKindEncoder, SimpleAssetKindValidator,
    TensorData, EmbeddingData, ArtifactData,
    create_tensor_from_numpy, create_embedding_from_vector, create_artifact_from_files
)


class TestBlobAsset(unittest.TestCase):
    """Test Blob asset kind implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.test_data = b"Hello, AIFS! This is a test blob asset."
        self.empty_data = b""
        self.large_data = b"x" * 1024 * 1024  # 1MB of data
    
    def test_blob_encoding(self):
        """Test blob encoding and decoding."""
        # Test normal blob
        encoded = SimpleAssetKindEncoder.encode_blob(self.test_data)
        decoded = SimpleAssetKindEncoder.decode_blob(encoded)
        self.assertEqual(self.test_data, decoded)
        
        # Test empty blob
        encoded_empty = SimpleAssetKindEncoder.encode_blob(self.empty_data)
        decoded_empty = SimpleAssetKindEncoder.decode_blob(encoded_empty)
        self.assertEqual(self.empty_data, decoded_empty)
        
        # Test large blob
        encoded_large = SimpleAssetKindEncoder.encode_blob(self.large_data)
        decoded_large = SimpleAssetKindEncoder.decode_blob(encoded_large)
        self.assertEqual(self.large_data, decoded_large)
    
    def test_blob_validation(self):
        """Test blob validation."""
        # Valid blobs
        self.assertTrue(SimpleAssetKindValidator.validate_blob(self.test_data))
        self.assertTrue(SimpleAssetKindValidator.validate_blob(self.empty_data))
        self.assertTrue(SimpleAssetKindValidator.validate_blob(self.large_data))
        
        # Invalid inputs
        self.assertFalse(SimpleAssetKindValidator.validate_blob(None))
        self.assertFalse(SimpleAssetKindValidator.validate_blob("not bytes"))
    
    def test_blob_round_trip(self):
        """Test complete blob round-trip."""
        original = self.test_data
        encoded = SimpleAssetKindEncoder.encode_blob(original)
        decoded = SimpleAssetKindEncoder.decode_blob(encoded)
        self.assertEqual(original, decoded)


class TestTensorAsset(unittest.TestCase):
    """Test Tensor asset kind implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.test_array_2d = np.random.rand(3, 4).astype(np.float32)
        self.test_array_3d = np.random.rand(2, 3, 4).astype(np.float64)
        self.test_array_1d = np.array([1, 2, 3, 4, 5], dtype=np.int32)
        self.test_array_empty = np.array([])
        
        self.tensor_metadata = {
            'name': 'test_tensor',
            'description': 'Test tensor for unit testing',
            'creator': 'test_suite',
            'created_at': 1640995200,
            'attributes': {
                'purpose': 'testing',
                'version': '1.0'
            }
        }
    
    def test_tensor_encoding_decoding(self):
        """Test tensor encoding and decoding."""
        # Test 2D tensor
        tensor_data = TensorData(
            data=self.test_array_2d,
            dtype=str(self.test_array_2d.dtype),
            shape=self.test_array_2d.shape,
            metadata=self.tensor_metadata
        )
        
        encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
        decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
        
        self.assertEqual(decoded.dtype, tensor_data.dtype)
        self.assertEqual(decoded.shape, tensor_data.shape)
        np.testing.assert_array_equal(decoded.data, tensor_data.data)
        self.assertEqual(decoded.metadata, tensor_data.metadata)
    
    def test_tensor_different_dtypes(self):
        """Test tensor with different data types."""
        dtypes = ['int8', 'int16', 'int32', 'int64', 'float16', 'float32', 'float64']
        
        for dtype in dtypes:
            with self.subTest(dtype=dtype):
                array = np.random.rand(2, 3).astype(dtype)
                tensor_data = TensorData(
                    data=array,
                    dtype=dtype,
                    shape=array.shape,
                    metadata={'name': f'test_{dtype}'}
                )
                
                encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
                decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
                
                self.assertEqual(decoded.dtype, dtype)
                np.testing.assert_array_equal(decoded.data, array)
    
    def test_tensor_different_shapes(self):
        """Test tensor with different shapes."""
        shapes = [(1,), (2,), (3, 4), (2, 3, 4), (1, 2, 3, 4)]
        
        for shape in shapes:
            with self.subTest(shape=shape):
                array = np.random.rand(*shape).astype(np.float32)
                tensor_data = TensorData(
                    data=array,
                    dtype='float32',
                    shape=shape,
                    metadata={'name': f'test_shape_{shape}'}
                )
                
                encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
                decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
                
                self.assertEqual(decoded.shape, shape)
                np.testing.assert_array_equal(decoded.data, array)
    
    def test_tensor_validation(self):
        """Test tensor validation."""
        # Valid tensor
        tensor_data = TensorData(
            data=self.test_array_2d,
            dtype=str(self.test_array_2d.dtype),
            shape=self.test_array_2d.shape
        )
        encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
        self.assertTrue(SimpleAssetKindValidator.validate_tensor(encoded))
        
        # Invalid data
        self.assertFalse(SimpleAssetKindValidator.validate_tensor(b"invalid"))
        self.assertFalse(SimpleAssetKindValidator.validate_tensor(b""))
    
    def test_tensor_convenience_function(self):
        """Test tensor convenience function."""
        array = np.random.rand(2, 3).astype(np.float32)
        encoded = create_tensor_from_numpy(
            array,
            name="convenience_test",
            description="Test convenience function"
        )
        
        decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
        np.testing.assert_array_equal(decoded.data, array)
        self.assertEqual(decoded.metadata['name'], "convenience_test")


class TestEmbeddingAsset(unittest.TestCase):
    """Test Embedding asset kind implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.test_vector_128 = np.random.rand(128).astype(np.float32)
        self.test_vector_512 = np.random.rand(512).astype(np.float32)
        self.test_vector_1024 = np.random.rand(1024).astype(np.float32)
        
        self.embedding_metadata = {
            'model': 'openai_ada_002',
            'dimension': 128,
            'distance_metric': 'cosine',
            'model_version': '2.0',
            'framework': 'openai',
            'parameters': {'temperature': 0.7, 'max_tokens': 1000},
            'confidence': 0.95
        }
    
    def test_embedding_encoding_decoding(self):
        """Test embedding encoding and decoding."""
        embedding_data = EmbeddingData(
            vector=self.test_vector_128,
            model='openai_ada_002',
            dimension=len(self.test_vector_128),
            distance_metric='cosine',
            model_version='2.0',
            framework='openai',
            parameters={'temperature': 0.7},
            confidence=0.95
        )
        
        encoded = SimpleAssetKindEncoder.encode_embedding(embedding_data)
        decoded = SimpleAssetKindEncoder.decode_embedding(encoded)
        
        self.assertEqual(decoded.model, embedding_data.model)
        self.assertEqual(decoded.dimension, embedding_data.dimension)
        self.assertEqual(decoded.distance_metric, embedding_data.distance_metric)
        self.assertEqual(decoded.model_version, embedding_data.model_version)
        self.assertEqual(decoded.framework, embedding_data.framework)
        self.assertEqual(decoded.confidence, embedding_data.confidence)
        np.testing.assert_array_almost_equal(decoded.vector, embedding_data.vector)
    
    def test_embedding_different_models(self):
        """Test embedding with different models."""
        models = ['openai_ada_002', 'openai_3_small', 'openai_3_large', 'sentence_transformers', 'custom']
        
        for model in models:
            with self.subTest(model=model):
                vector = np.random.rand(64).astype(np.float32)
                embedding_data = EmbeddingData(
                    vector=vector,
                    model=model,
                    dimension=len(vector),
                    distance_metric='cosine'
                )
                
                encoded = SimpleAssetKindEncoder.encode_embedding(embedding_data)
                decoded = SimpleAssetKindEncoder.decode_embedding(encoded)
                
                self.assertEqual(decoded.model, model)
                np.testing.assert_array_almost_equal(decoded.vector, vector)
    
    def test_embedding_different_metrics(self):
        """Test embedding with different distance metrics."""
        metrics = ['cosine', 'euclidean', 'dot_product', 'manhattan', 'hamming']
        
        for metric in metrics:
            with self.subTest(metric=metric):
                vector = np.random.rand(32).astype(np.float32)
                embedding_data = EmbeddingData(
                    vector=vector,
                    model='custom',
                    dimension=len(vector),
                    distance_metric=metric
                )
                
                encoded = SimpleAssetKindEncoder.encode_embedding(embedding_data)
                decoded = SimpleAssetKindEncoder.decode_embedding(encoded)
                
                self.assertEqual(decoded.distance_metric, metric)
    
    def test_embedding_validation(self):
        """Test embedding validation."""
        # Valid embedding
        embedding_data = EmbeddingData(
            vector=self.test_vector_128,
            model='custom',
            dimension=len(self.test_vector_128)
        )
        encoded = SimpleAssetKindEncoder.encode_embedding(embedding_data)
        self.assertTrue(SimpleAssetKindValidator.validate_embedding(encoded))
        
        # Invalid data
        self.assertFalse(SimpleAssetKindValidator.validate_embedding(b"invalid"))
        self.assertFalse(SimpleAssetKindValidator.validate_embedding(b""))
    
    def test_embedding_convenience_function(self):
        """Test embedding convenience function."""
        vector = np.random.rand(64).astype(np.float32)
        encoded = create_embedding_from_vector(
            vector,
            model="custom",
            distance_metric="euclidean"
        )
        
        decoded = SimpleAssetKindEncoder.decode_embedding(encoded)
        np.testing.assert_array_almost_equal(decoded.vector, vector)
        self.assertEqual(decoded.model, "custom")
        self.assertEqual(decoded.distance_metric, "euclidean")


class TestArtifactAsset(unittest.TestCase):
    """Test Artifact asset kind implementation."""
    
    def setUp(self):
        """Set up test data."""
        self.test_files = {
            "README.md": b"# Test Artifact\n\nThis is a test artifact.",
            "config.json": b'{"version": "1.0", "debug": true}',
            "data.csv": b"name,value\nitem1,42\nitem2,84\n",
            "scripts/process.py": b"#!/usr/bin/env python3\nprint('Hello!')\n"
        }
        
        self.test_manifest = {
            'name': 'test_artifact',
            'version': '1.0.0',
            'description': 'Test artifact for unit testing',
            'author': 'test_suite',
            'license': 'MIT',
            'tags': ['test', 'demo'],
            'created_at': 1640995200,
            'modified_at': 1640995200,
            'artifact_id': 'test_artifact_123',
            'metadata': {
                'purpose': 'testing',
                'category': 'example'
            }
        }
        
        self.test_dependencies = [
            {
                'name': 'numpy',
                'version': '>=1.20.0',
                'source': 'pip',
                'metadata': {'optional': False}
            },
            {
                'name': 'pandas',
                'version': '>=1.3.0',
                'source': 'pip',
                'metadata': {'optional': True}
            }
        ]
    
    def create_zip_data(self, files):
        """Create ZIP data from files dictionary."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, file_data in files.items():
                zip_file.writestr(file_path, file_data)
        return zip_buffer.getvalue()
    
    def test_artifact_encoding_decoding(self):
        """Test artifact encoding and decoding."""
        zip_data = self.create_zip_data(self.test_files)
        
        file_entries = []
        for file_path, file_data in self.test_files.items():
            file_entries.append({
                'path': file_path,
                'asset_id': f"asset_{hash(file_path)}",
                'size': len(file_data),
                'mime_type': 'text/plain',
                'created_at': 1640995200,
                'modified_at': 1640995200,
                'is_executable': file_path.endswith('.py'),
                'checksum': f"blake3_{hash(file_data)}",
                'metadata': {'encoding': 'utf-8'}
            })
        
        artifact_data = ArtifactData(
            files=file_entries,
            manifest=self.test_manifest,
            zip_data=zip_data,
            dependencies=self.test_dependencies
        )
        
        encoded = SimpleAssetKindEncoder.encode_artifact(artifact_data)
        decoded = SimpleAssetKindEncoder.decode_artifact(encoded)
        
        self.assertEqual(len(decoded.files), len(artifact_data.files))
        self.assertEqual(decoded.manifest['name'], artifact_data.manifest['name'])
        self.assertEqual(len(decoded.zip_data), len(artifact_data.zip_data))
        self.assertEqual(len(decoded.dependencies), len(artifact_data.dependencies))
    
    def test_artifact_zip_validation(self):
        """Test artifact ZIP data validation."""
        zip_data = self.create_zip_data(self.test_files)
        
        # Verify ZIP can be read
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            file_list = zip_file.namelist()
            self.assertEqual(set(file_list), set(self.test_files.keys()))
            
            # Verify file contents
            for file_path, expected_data in self.test_files.items():
                actual_data = zip_file.read(file_path)
                self.assertEqual(actual_data, expected_data)
    
    def test_artifact_validation(self):
        """Test artifact validation."""
        zip_data = self.create_zip_data(self.test_files)
        
        file_entries = [{
            'path': 'test.txt',
            'asset_id': 'test_asset',
            'size': 10,
            'mime_type': 'text/plain',
            'created_at': 1640995200,
            'modified_at': 1640995200,
            'is_executable': False,
            'checksum': 'test_checksum',
            'metadata': {}
        }]
        
        artifact_data = ArtifactData(
            files=file_entries,
            manifest=self.test_manifest,
            zip_data=zip_data
        )
        
        encoded = SimpleAssetKindEncoder.encode_artifact(artifact_data)
        self.assertTrue(SimpleAssetKindValidator.validate_artifact(encoded))
        
        # Invalid data
        self.assertFalse(SimpleAssetKindValidator.validate_artifact(b"invalid"))
        self.assertFalse(SimpleAssetKindValidator.validate_artifact(b""))
    
    def test_artifact_convenience_function(self):
        """Test artifact convenience function."""
        zip_data = self.create_zip_data(self.test_files)
        
        file_entries = [{
            'path': 'test.txt',
            'asset_id': 'test_asset',
            'size': 10,
            'mime_type': 'text/plain',
            'created_at': 1640995200,
            'modified_at': 1640995200,
            'is_executable': False,
            'checksum': 'test_checksum',
            'metadata': {}
        }]
        
        encoded = create_artifact_from_files(file_entries, self.test_manifest, zip_data)
        decoded = SimpleAssetKindEncoder.decode_artifact(encoded)
        
        self.assertEqual(len(decoded.files), len(file_entries))
        self.assertEqual(decoded.manifest['name'], self.test_manifest['name'])


class TestAssetManagerIntegration(unittest.TestCase):
    """Test AssetManager integration with asset kinds."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.asset_manager = AssetManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_blob_asset_manager_integration(self):
        """Test blob integration with AssetManager."""
        blob_data = b"Hello, AIFS blob!"
        asset_id = self.asset_manager.put_asset(blob_data, "blob")
        
        self.assertIsNotNone(asset_id)
        self.assertEqual(len(asset_id), 64)  # BLAKE3 hash length
        
        # Retrieve asset
        retrieved = self.asset_manager.get_asset(asset_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['kind'], 'blob')
        self.assertEqual(retrieved['data'], blob_data)
    
    def test_tensor_asset_manager_integration(self):
        """Test tensor integration with AssetManager."""
        array = np.random.rand(2, 3).astype(np.float32)
        tensor_data = TensorData(
            data=array,
            dtype=str(array.dtype),
            shape=array.shape,
            metadata={'name': 'test_tensor'}
        )
        
        asset_id = self.asset_manager.put_tensor(tensor_data)
        self.assertIsNotNone(asset_id)
        
        # Retrieve tensor
        retrieved = self.asset_manager.get_tensor(asset_id)
        self.assertIsNotNone(retrieved)
        np.testing.assert_array_equal(retrieved.data, array)
        self.assertEqual(retrieved.metadata['name'], 'test_tensor')
    
    def test_embedding_asset_manager_integration(self):
        """Test embedding integration with AssetManager."""
        vector = np.random.rand(64).astype(np.float32)
        embedding_data = EmbeddingData(
            vector=vector,
            model='custom',
            dimension=len(vector),
            distance_metric='cosine'
        )
        
        asset_id = self.asset_manager.put_embedding(embedding_data)
        self.assertIsNotNone(asset_id)
        
        # Retrieve embedding
        retrieved = self.asset_manager.get_embedding(asset_id)
        self.assertIsNotNone(retrieved)
        np.testing.assert_array_almost_equal(retrieved.vector, vector)
        self.assertEqual(retrieved.model, 'custom')
    
    def test_artifact_asset_manager_integration(self):
        """Test artifact integration with AssetManager."""
        files = {'test.txt': b'Hello, artifact!'}
        zip_data = self.create_zip_data(files)
        
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
            zip_data=zip_data
        )
        
        asset_id = self.asset_manager.put_artifact(artifact_data)
        self.assertIsNotNone(asset_id)
        
        # Retrieve artifact
        retrieved = self.asset_manager.get_artifact(asset_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.manifest['name'], 'test_artifact')
        self.assertEqual(len(retrieved.files), 1)
    
    def create_zip_data(self, files):
        """Create ZIP data from files dictionary."""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, file_data in files.items():
                zip_file.writestr(file_path, file_data)
        return zip_buffer.getvalue()
    
    def test_asset_validation_in_asset_manager(self):
        """Test asset validation in AssetManager."""
        # Valid blob
        valid_blob = b"valid blob data"
        asset_id = self.asset_manager.put_asset(valid_blob, "blob")
        self.assertIsNotNone(asset_id)
        
        # Invalid tensor data
        with self.assertRaises(ValueError):
            self.asset_manager.put_asset(b"invalid tensor", "tensor")
        
        # Invalid embedding data
        with self.assertRaises(ValueError):
            self.asset_manager.put_asset(b"invalid embedding", "embed")
        
        # Invalid artifact data
        with self.assertRaises(ValueError):
            self.asset_manager.put_asset(b"invalid artifact", "artifact")


class TestAssetKindEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_empty_data_handling(self):
        """Test handling of empty data."""
        # Empty blob
        empty_blob = b""
        encoded = SimpleAssetKindEncoder.encode_blob(empty_blob)
        decoded = SimpleAssetKindEncoder.decode_blob(encoded)
        self.assertEqual(decoded, empty_blob)
        
        # Empty tensor
        empty_array = np.array([])
        tensor_data = TensorData(
            data=empty_array,
            dtype='float32',
            shape=empty_array.shape
        )
        encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
        decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
        self.assertEqual(decoded.shape, (0,))
    
    def test_large_data_handling(self):
        """Test handling of large data."""
        # Large blob (1MB)
        large_blob = b"x" * (1024 * 1024)
        encoded = SimpleAssetKindEncoder.encode_blob(large_blob)
        decoded = SimpleAssetKindEncoder.decode_blob(encoded)
        self.assertEqual(decoded, large_blob)
        
        # Large tensor (1000x1000)
        large_array = np.random.rand(1000, 1000).astype(np.float32)
        tensor_data = TensorData(
            data=large_array,
            dtype='float32',
            shape=large_array.shape
        )
        encoded = SimpleAssetKindEncoder.encode_tensor(tensor_data)
        decoded = SimpleAssetKindEncoder.decode_tensor(encoded)
        np.testing.assert_array_equal(decoded.data, large_array)
    
    def test_unicode_handling(self):
        """Test handling of Unicode data."""
        unicode_blob = "Hello, 世界! 🌍".encode('utf-8')
        encoded = SimpleAssetKindEncoder.encode_blob(unicode_blob)
        decoded = SimpleAssetKindEncoder.decode_blob(encoded)
        self.assertEqual(decoded, unicode_blob)
    
    def test_corrupted_data_handling(self):
        """Test handling of corrupted data."""
        # Corrupted tensor data
        with self.assertRaises(Exception):
            SimpleAssetKindEncoder.decode_tensor(b"corrupted tensor data")
        
        # Corrupted embedding data
        with self.assertRaises(Exception):
            SimpleAssetKindEncoder.decode_embedding(b"corrupted embedding data")
        
        # Corrupted artifact data
        with self.assertRaises(Exception):
            SimpleAssetKindEncoder.decode_artifact(b"corrupted artifact data")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
