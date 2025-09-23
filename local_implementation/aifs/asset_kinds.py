"""
AIFS Asset Kinds Implementation

Implements the four asset kinds as specified in the AIFS architecture:
- Blob: Raw byte stream
- Tensor: Arrow2 encoding with nd-array.proto schema
- Embed: FlatBuffers encoding with embedding.fbs schema  
- Artifact: ZIP+MANIFEST encoding with artifact.proto schema
"""

import json
import zipfile
import io
import struct
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import blake3

# Import generated protobuf schemas
from .schemas.generated import nd_array_pb2, artifact_pb2

# Try to import FlatBuffers (optional dependency)
try:
    import flatbuffers
    from .schemas.generated import embedding_fbs
    FLATBUFFERS_AVAILABLE = True
except ImportError:
    FLATBUFFERS_AVAILABLE = False
    # Create a mock embedding_fbs module
    class MockEmbeddingFbs:
        class DistanceMetric:
            COSINE = 0
            EUCLIDEAN = 1
            DOT_PRODUCT = 2
            MANHATTAN = 3
            HAMMING = 4
        
        class EmbeddingModel:
            UNKNOWN = 0
            OPENAI_ADA_002 = 1
            OPENAI_3_SMALL = 2
            OPENAI_3_LARGE = 3
            SENTENCE_TRANSFORMERS = 4
            HUGGINGFACE = 5
            CUSTOM = 255
        
        class VectorMetadata:
            def __init__(self, *args, **kwargs):
                pass
        
        class Embedding:
            def __init__(self, *args, **kwargs):
                pass
        
        class EmbeddingRoot:
            def __init__(self, *args, **kwargs):
                pass
        
        @staticmethod
        def GetRootAs(data, offset=0):
            return MockEmbeddingFbs.EmbeddingRoot()
    
    embedding_fbs = MockEmbeddingFbs()
    print("Warning: FlatBuffers not available. Embed asset kind will be limited.")

# Try to import Arrow (optional dependency)
try:
    import pyarrow as pa
    import pyarrow.compute as pc
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False
    print("Warning: PyArrow not available. Tensor asset kind will be limited.")


class AssetKind(Enum):
    """Asset kinds as defined in AIFS architecture."""
    BLOB = "blob"
    TENSOR = "tensor"
    EMBED = "embed"
    ARTIFACT = "artifact"


@dataclass
class TensorData:
    """Tensor data structure for Arrow2 encoding."""
    data: np.ndarray
    dtype: str
    shape: Tuple[int, ...]
    strides: Optional[Tuple[int, ...]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_nullable: bool = False
    null_bitmap: Optional[np.ndarray] = None


@dataclass
class EmbeddingData:
    """Embedding data structure for FlatBuffers encoding."""
    vector: np.ndarray
    model: str
    dimension: int
    distance_metric: str = "cosine"
    model_version: Optional[str] = None
    framework: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    asset_id: Optional[str] = None
    chunk_index: Optional[int] = None
    confidence: Optional[float] = None


@dataclass
class ArtifactData:
    """Artifact data structure for ZIP+MANIFEST encoding."""
    files: List[Dict[str, Any]]  # List of file entries
    manifest: Dict[str, Any]     # Artifact manifest
    zip_data: bytes             # ZIP file data
    dependencies: Optional[List[Dict[str, Any]]] = None


class AssetKindEncoder:
    """Encoder for different asset kinds according to AIFS specification."""
    
    @staticmethod
    def encode_blob(data: bytes, metadata: Optional[Dict] = None) -> bytes:
        """Encode blob data (raw bytes)."""
        return data
    
    @staticmethod
    def decode_blob(data: bytes) -> bytes:
        """Decode blob data."""
        return data
    
    @staticmethod
    def encode_tensor(tensor_data: TensorData) -> bytes:
        """Encode tensor data using Arrow2 format with nd-array.proto schema."""
        if not ARROW_AVAILABLE:
            raise NotImplementedError("PyArrow required for tensor encoding")
        
        # Create NDArray protobuf message
        nd_array = nd_array_pb2.NDArray()
        
        # Set data type
        dtype_map = {
            'bool': nd_array_pb2.NDArray.DataType.BOOL,
            'int8': nd_array_pb2.NDArray.DataType.INT8,
            'uint8': nd_array_pb2.NDArray.DataType.UINT8,
            'int16': nd_array_pb2.NDArray.DataType.INT16,
            'uint16': nd_array_pb2.NDArray.DataType.UINT16,
            'int32': nd_array_pb2.NDArray.DataType.INT32,
            'uint32': nd_array_pb2.NDArray.DataType.UINT32,
            'int64': nd_array_pb2.NDArray.DataType.INT64,
            'uint64': nd_array_pb2.NDArray.DataType.UINT64,
            'float16': nd_array_pb2.NDArray.DataType.FLOAT16,
            'float32': nd_array_pb2.NDArray.DataType.FLOAT32,
            'float64': nd_array_pb2.NDArray.DataType.FLOAT64,
            'complex64': nd_array_pb2.NDArray.DataType.COMPLEX64,
            'complex128': nd_array_pb2.NDArray.DataType.COMPLEX128,
        }
        
        nd_array.dtype = dtype_map.get(tensor_data.dtype, nd_array_pb2.NDArray.DataType.UNKNOWN)
        
        # Set shape
        nd_array.shape.dimensions.extend(tensor_data.shape)
        
        # Set strides if provided
        if tensor_data.strides:
            nd_array.strides.strides.extend(tensor_data.strides)
        
        # Set data
        nd_array.data = tensor_data.data.tobytes()
        
        # Set metadata
        if tensor_data.metadata:
            nd_array.metadata.name = tensor_data.metadata.get('name', '')
            nd_array.metadata.description = tensor_data.metadata.get('description', '')
            nd_array.metadata.created_at = tensor_data.metadata.get('created_at', 0)
            nd_array.metadata.creator = tensor_data.metadata.get('creator', '')
            for key, value in tensor_data.metadata.get('attributes', {}).items():
                nd_array.metadata.attributes[key] = str(value)
        
        # Set Arrow2 specific fields
        nd_array.offset = 0
        nd_array.length = len(nd_array.data)
        nd_array.is_nullable = tensor_data.is_nullable
        
        if tensor_data.null_bitmap is not None:
            nd_array.null_bitmap.extend(tensor_data.null_bitmap.tolist())
        
        # Create Arrow schema
        if ARROW_AVAILABLE:
            arrow_schema = pa.schema([
                pa.field('data', pa.from_numpy_dtype(tensor_data.data.dtype)),
                pa.field('shape', pa.list_(pa.int64())),
                pa.field('strides', pa.list_(pa.int64())) if tensor_data.strides else None
            ])
            nd_array.arrow_schema = arrow_schema.to_json()
        
        return nd_array.SerializeToString()
    
    @staticmethod
    def decode_tensor(data: bytes) -> TensorData:
        """Decode tensor data from Arrow2 format."""
        nd_array = nd_array_pb2.NDArray()
        nd_array.ParseFromString(data)
        
        # Convert dtype back to numpy
        dtype_map = {
            nd_array_pb2.NDArray.DataType.BOOL: 'bool',
            nd_array_pb2.NDArray.DataType.INT8: 'int8',
            nd_array_pb2.NDArray.DataType.UINT8: 'uint8',
            nd_array_pb2.NDArray.DataType.INT16: 'int16',
            nd_array_pb2.NDArray.DataType.UINT16: 'uint16',
            nd_array_pb2.NDArray.DataType.INT32: 'int32',
            nd_array_pb2.NDArray.DataType.UINT32: 'uint32',
            nd_array_pb2.NDArray.DataType.INT64: 'int64',
            nd_array_pb2.NDArray.DataType.UINT64: 'uint64',
            nd_array_pb2.NDArray.DataType.FLOAT16: 'float16',
            nd_array_pb2.NDArray.DataType.FLOAT32: 'float32',
            nd_array_pb2.NDArray.DataType.FLOAT64: 'float64',
            nd_array_pb2.NDArray.DataType.COMPLEX64: 'complex64',
            nd_array_pb2.NDArray.DataType.COMPLEX128: 'complex128',
        }
        
        dtype = dtype_map.get(nd_array.dtype, 'float32')
        shape = tuple(nd_array.shape.dimensions)
        
        # Reconstruct numpy array
        data_array = np.frombuffer(nd_array.data, dtype=dtype).reshape(shape)
        
        # Reconstruct strides if available
        strides = tuple(nd_array.strides.strides) if nd_array.strides.strides else None
        
        # Reconstruct metadata
        metadata = {
            'name': nd_array.metadata.name,
            'description': nd_array.metadata.description,
            'created_at': nd_array.metadata.created_at,
            'creator': nd_array.metadata.creator,
            'attributes': dict(nd_array.metadata.attributes)
        }
        
        # Reconstruct null bitmap if available
        null_bitmap = np.array(nd_array.null_bitmap, dtype=bool) if nd_array.null_bitmap else None
        
        return TensorData(
            data=data_array,
            dtype=dtype,
            shape=shape,
            strides=strides,
            metadata=metadata,
            is_nullable=nd_array.is_nullable,
            null_bitmap=null_bitmap
        )
    
    @staticmethod
    def encode_embedding(embedding_data: EmbeddingData) -> bytes:
        """Encode embedding data using FlatBuffers format."""
        if not FLATBUFFERS_AVAILABLE:
            raise NotImplementedError("FlatBuffers required for embedding encoding")
        
        builder = flatbuffers.Builder(1024)
        
        # Model enum mapping
        model_map = {
            'openai_ada_002': embedding_fbs.EmbeddingModel.OPENAI_ADA_002,
            'openai_3_small': embedding_fbs.EmbeddingModel.OPENAI_3_SMALL,
            'openai_3_large': embedding_fbs.EmbeddingModel.OPENAI_3_LARGE,
            'sentence_transformers': embedding_fbs.EmbeddingModel.SENTENCE_TRANSFORMERS,
            'huggingface': embedding_fbs.EmbeddingModel.HUGGINGFACE,
        }
        
        # Distance metric enum mapping
        metric_map = {
            'cosine': embedding_fbs.DistanceMetric.COSINE,
            'euclidean': embedding_fbs.DistanceMetric.EUCLIDEAN,
            'dot_product': embedding_fbs.DistanceMetric.DOT_PRODUCT,
            'manhattan': embedding_fbs.DistanceMetric.MANHATTAN,
            'hamming': embedding_fbs.DistanceMetric.HAMMING,
        }
        
        # Create vector data
        vector_data = builder.CreateNumpyVector(embedding_data.vector.astype(np.float32))
        
        # Create metadata strings
        model_version = builder.CreateString(embedding_data.model_version or "")
        framework = builder.CreateString(embedding_data.framework or "")
        parameters = builder.CreateString(json.dumps(embedding_data.parameters or {}))
        
        # Create VectorMetadata
        embedding_fbs.VectorMetadataStart(builder)
        embedding_fbs.VectorMetadataAddModel(builder, model_map.get(embedding_data.model, embedding_fbs.EmbeddingModel.UNKNOWN))
        embedding_fbs.VectorMetadataAddDimension(builder, embedding_data.dimension)
        embedding_fbs.VectorMetadataAddDistanceMetric(builder, metric_map.get(embedding_data.distance_metric, embedding_fbs.DistanceMetric.COSINE))
        embedding_fbs.VectorMetadataAddCreatedAt(builder, int(embedding_data.created_at or 0))
        embedding_fbs.VectorMetadataAddModelVersion(builder, model_version)
        embedding_fbs.VectorMetadataAddFramework(builder, framework)
        embedding_fbs.VectorMetadataAddParameters(builder, parameters)
        metadata = embedding_fbs.VectorMetadataEnd(builder)
        
        # Create asset_id string
        asset_id = builder.CreateString(embedding_data.asset_id or "")
        
        # Create Embedding
        embedding_fbs.EmbeddingStart(builder)
        embedding_fbs.EmbeddingAddVector(builder, vector_data)
        embedding_fbs.EmbeddingAddMetadata(builder, metadata)
        embedding_fbs.EmbeddingAddAssetId(builder, asset_id)
        embedding_fbs.EmbeddingAddChunkIndex(builder, embedding_data.chunk_index or 0)
        embedding_fbs.EmbeddingAddConfidence(builder, embedding_data.confidence or 1.0)
        embedding = embedding_fbs.EmbeddingEnd(builder)
        
        # Create EmbeddingRoot
        embedding_fbs.EmbeddingRootStart(builder)
        embedding_fbs.EmbeddingRootAddSingle(builder, embedding)
        embedding_fbs.EmbeddingRootAddIsCollection(builder, False)
        root = embedding_fbs.EmbeddingRootEnd(builder)
        
        builder.Finish(root)
        return bytes(builder.Output())
    
    @staticmethod
    def decode_embedding(data: bytes) -> EmbeddingData:
        """Decode embedding data from FlatBuffers format."""
        if not FLATBUFFERS_AVAILABLE:
            raise NotImplementedError("FlatBuffers required for embedding decoding")
        
        root = embedding_fbs.EmbeddingRoot.GetRootAs(data, 0)
        embedding = root.Single()
        
        # Extract vector
        vector_data = embedding.VectorAsNumpy()
        
        # Extract metadata
        metadata = embedding.Metadata()
        
        # Model enum reverse mapping
        model_map = {
            embedding_fbs.EmbeddingModel.OPENAI_ADA_002: 'openai_ada_002',
            embedding_fbs.EmbeddingModel.OPENAI_3_SMALL: 'openai_3_small',
            embedding_fbs.EmbeddingModel.OPENAI_3_LARGE: 'openai_3_large',
            embedding_fbs.EmbeddingModel.SENTENCE_TRANSFORMERS: 'sentence_transformers',
            embedding_fbs.EmbeddingModel.HUGGINGFACE: 'huggingface',
        }
        
        # Distance metric enum reverse mapping
        metric_map = {
            embedding_fbs.DistanceMetric.COSINE: 'cosine',
            embedding_fbs.DistanceMetric.EUCLIDEAN: 'euclidean',
            embedding_fbs.DistanceMetric.DOT_PRODUCT: 'dot_product',
            embedding_fbs.DistanceMetric.MANHATTAN: 'manhattan',
            embedding_fbs.DistanceMetric.HAMMING: 'hamming',
        }
        
        return EmbeddingData(
            vector=vector_data,
            model=model_map.get(metadata.Model(), 'unknown'),
            dimension=metadata.Dimension(),
            distance_metric=metric_map.get(metadata.DistanceMetric(), 'cosine'),
            model_version=metadata.ModelVersion().decode() if metadata.ModelVersion() else None,
            framework=metadata.Framework().decode() if metadata.Framework() else None,
            parameters=json.loads(metadata.Parameters().decode()) if metadata.Parameters() else None,
            asset_id=embedding.AssetId().decode() if embedding.AssetId() else None,
            chunk_index=embedding.ChunkIndex(),
            confidence=embedding.Confidence()
        )
    
    @staticmethod
    def encode_artifact(artifact_data: ArtifactData) -> bytes:
        """Encode artifact data using ZIP+MANIFEST format."""
        # Create artifact manifest
        manifest = artifact_pb2.ArtifactManifest()
        manifest.name = artifact_data.manifest.get('name', '')
        manifest.version = artifact_data.manifest.get('version', '1.0.0')
        manifest.description = artifact_data.manifest.get('description', '')
        manifest.author = artifact_data.manifest.get('author', '')
        manifest.license = artifact_data.manifest.get('license', '')
        manifest.created_at = artifact_data.manifest.get('created_at', 0)
        manifest.modified_at = artifact_data.manifest.get('modified_at', 0)
        manifest.artifact_id = artifact_data.manifest.get('artifact_id', '')
        manifest.parent_artifact_id = artifact_data.manifest.get('parent_artifact_id', '')
        
        # Add tags
        for tag in artifact_data.manifest.get('tags', []):
            manifest.tags.append(tag)
        
        # Add lineage
        for lineage_item in artifact_data.manifest.get('lineage', []):
            manifest.lineage.append(lineage_item)
        
        # Add metadata
        for key, value in artifact_data.manifest.get('metadata', {}).items():
            manifest.metadata[key] = str(value)
        
        # Add file entries
        for file_info in artifact_data.files:
            file_entry = artifact_pb2.FileEntry()
            file_entry.path = file_info.get('path', '')
            file_entry.asset_id = file_info.get('asset_id', '')
            file_entry.size = file_info.get('size', 0)
            file_entry.mime_type = file_info.get('mime_type', 'application/octet-stream')
            file_entry.created_at = file_info.get('created_at', 0)
            file_entry.modified_at = file_info.get('modified_at', 0)
            file_entry.is_executable = file_info.get('is_executable', False)
            file_entry.checksum = file_info.get('checksum', '')
            
            # Add file metadata
            for key, value in file_info.get('metadata', {}).items():
                file_entry.metadata[key] = str(value)
            
            manifest.files.append(file_entry)
        
        # Add dependencies
        for dep_info in artifact_data.dependencies or []:
            dependency = artifact_pb2.Dependency()
            dependency.name = dep_info.get('name', '')
            dependency.version = dep_info.get('version', '')
            dependency.source = dep_info.get('source', '')
            dependency.asset_id = dep_info.get('asset_id', '')
            
            # Add dependency metadata
            for key, value in dep_info.get('metadata', {}).items():
                dependency.metadata[key] = str(value)
            
            manifest.dependencies.append(dependency)
        
        # Create artifact bundle
        bundle = artifact_pb2.ArtifactBundle()
        bundle.manifest.CopyFrom(manifest)
        bundle.zip_data = artifact_data.zip_data
        bundle.zip_checksum = blake3.blake3(artifact_data.zip_data).hexdigest()
        bundle.zip_size = len(artifact_data.zip_data)
        bundle.compression_method = 'deflate'  # Standard ZIP compression
        bundle.compression_level = 6  # Default compression level
        
        return bundle.SerializeToString()
    
    @staticmethod
    def decode_artifact(data: bytes) -> ArtifactData:
        """Decode artifact data from ZIP+MANIFEST format."""
        bundle = artifact_pb2.ArtifactBundle()
        bundle.ParseFromString(data)
        
        # Extract manifest
        manifest = bundle.manifest
        manifest_dict = {
            'name': manifest.name,
            'version': manifest.version,
            'description': manifest.description,
            'author': manifest.author,
            'license': manifest.license,
            'created_at': manifest.created_at,
            'modified_at': manifest.modified_at,
            'artifact_id': manifest.artifact_id,
            'parent_artifact_id': manifest.parent_artifact_id,
            'tags': list(manifest.tags),
            'lineage': list(manifest.lineage),
            'metadata': dict(manifest.metadata)
        }
        
        # Extract file entries
        files = []
        for file_entry in manifest.files:
            file_dict = {
                'path': file_entry.path,
                'asset_id': file_entry.asset_id,
                'size': file_entry.size,
                'mime_type': file_entry.mime_type,
                'created_at': file_entry.created_at,
                'modified_at': file_entry.modified_at,
                'is_executable': file_entry.is_executable,
                'checksum': file_entry.checksum,
                'metadata': dict(file_entry.metadata)
            }
            files.append(file_dict)
        
        # Extract dependencies
        dependencies = []
        for dep in manifest.dependencies:
            dep_dict = {
                'name': dep.name,
                'version': dep.version,
                'source': dep.source,
                'asset_id': dep.asset_id,
                'metadata': dict(dep.metadata)
            }
            dependencies.append(dep_dict)
        
        return ArtifactData(
            files=files,
            manifest=manifest_dict,
            zip_data=bundle.zip_data,
            dependencies=dependencies
        )


class AssetKindValidator:
    """Validator for different asset kinds."""
    
    @staticmethod
    def validate_blob(data: bytes, metadata: Optional[Dict] = None) -> bool:
        """Validate blob data."""
        return isinstance(data, bytes) and len(data) > 0
    
    @staticmethod
    def validate_tensor(data: bytes) -> bool:
        """Validate tensor data."""
        try:
            AssetKindEncoder.decode_tensor(data)
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_embedding(data: bytes) -> bool:
        """Validate embedding data."""
        try:
            AssetKindEncoder.decode_embedding(data)
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_artifact(data: bytes) -> bool:
        """Validate artifact data."""
        try:
            AssetKindEncoder.decode_artifact(data)
            return True
        except Exception:
            return False


def create_tensor_from_numpy(array: np.ndarray, 
                           name: str = "tensor",
                           description: str = "",
                           creator: str = "",
                           attributes: Optional[Dict[str, Any]] = None) -> bytes:
    """Convenience function to create tensor from numpy array."""
    tensor_data = TensorData(
        data=array,
        dtype=str(array.dtype),
        shape=array.shape,
        metadata={
            'name': name,
            'description': description,
            'creator': creator,
            'created_at': int(np.datetime64('now').astype('datetime64[s]').astype(int)),
            'attributes': attributes or {}
        }
    )
    return AssetKindEncoder.encode_tensor(tensor_data)


def create_embedding_from_vector(vector: np.ndarray,
                               model: str = "custom",
                               distance_metric: str = "cosine",
                               model_version: Optional[str] = None,
                               framework: Optional[str] = None,
                               parameters: Optional[Dict[str, Any]] = None) -> bytes:
    """Convenience function to create embedding from vector."""
    embedding_data = EmbeddingData(
        vector=vector,
        model=model,
        dimension=len(vector),
        distance_metric=distance_metric,
        model_version=model_version,
        framework=framework,
        parameters=parameters
    )
    return AssetKindEncoder.encode_embedding(embedding_data)


def create_artifact_from_files(files: List[Dict[str, Any]],
                             manifest: Dict[str, Any],
                             zip_data: bytes) -> bytes:
    """Convenience function to create artifact from files and manifest."""
    artifact_data = ArtifactData(
        files=files,
        manifest=manifest,
        zip_data=zip_data
    )
    return AssetKindEncoder.encode_artifact(artifact_data)
