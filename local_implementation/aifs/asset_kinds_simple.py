"""
Simplified AIFS Asset Kinds Implementation

A working implementation of the four asset kinds without complex dependencies.
This provides the core functionality as specified in the AIFS architecture.
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


class SimpleAssetKindEncoder:
    """Simplified encoder for different asset kinds."""
    
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
        """Encode tensor data using simplified format."""
        # Create a simple binary format for tensors
        # Format: [dtype_len][dtype][shape_len][shape][data_len][data][metadata_len][metadata]
        
        dtype_bytes = tensor_data.dtype.encode('utf-8')
        shape_bytes = struct.pack(f'{len(tensor_data.shape)}q', *tensor_data.shape)
        data_bytes = tensor_data.data.tobytes()
        metadata_bytes = json.dumps(tensor_data.metadata or {}).encode('utf-8')
        
        # Pack the data
        result = struct.pack('I', len(dtype_bytes))  # dtype length
        result += dtype_bytes
        result += struct.pack('I', len(tensor_data.shape))  # shape length
        result += shape_bytes
        result += struct.pack('I', len(data_bytes))  # data length
        result += data_bytes
        result += struct.pack('I', len(metadata_bytes))  # metadata length
        result += metadata_bytes
        
        return result
    
    @staticmethod
    def decode_tensor(data: bytes) -> TensorData:
        """Decode tensor data from simplified format."""
        offset = 0
        
        # Read dtype
        dtype_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        dtype = data[offset:offset+dtype_len].decode('utf-8')
        offset += dtype_len
        
        # Read shape
        shape_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        shape = struct.unpack(f'{shape_len}q', data[offset:offset+shape_len*8])
        offset += shape_len * 8
        
        # Read data
        data_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        data_bytes = data[offset:offset+data_len]
        offset += data_len
        
        # Read metadata
        metadata_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        metadata_bytes = data[offset:offset+metadata_len]
        metadata = json.loads(metadata_bytes.decode('utf-8'))
        
        # Reconstruct numpy array
        data_array = np.frombuffer(data_bytes, dtype=dtype).reshape(shape)
        
        return TensorData(
            data=data_array,
            dtype=dtype,
            shape=shape,
            metadata=metadata
        )
    
    @staticmethod
    def encode_embedding(embedding_data: EmbeddingData) -> bytes:
        """Encode embedding data using simplified format."""
        # Create a simple binary format for embeddings
        # Format: [model_len][model][dimension][distance_metric_len][distance_metric][vector_len][vector][metadata_len][metadata]
        
        model_bytes = embedding_data.model.encode('utf-8')
        distance_metric_bytes = embedding_data.distance_metric.encode('utf-8')
        vector_bytes = embedding_data.vector.astype(np.float32).tobytes()
        
        metadata = {
            'model_version': embedding_data.model_version,
            'framework': embedding_data.framework,
            'parameters': embedding_data.parameters,
            'asset_id': embedding_data.asset_id,
            'chunk_index': embedding_data.chunk_index,
            'confidence': embedding_data.confidence
        }
        metadata_bytes = json.dumps(metadata).encode('utf-8')
        
        # Pack the data
        result = struct.pack('I', len(model_bytes))  # model length
        result += model_bytes
        result += struct.pack('I', embedding_data.dimension)  # dimension
        result += struct.pack('I', len(distance_metric_bytes))  # distance metric length
        result += distance_metric_bytes
        result += struct.pack('I', len(vector_bytes))  # vector length
        result += vector_bytes
        result += struct.pack('I', len(metadata_bytes))  # metadata length
        result += metadata_bytes
        
        return result
    
    @staticmethod
    def decode_embedding(data: bytes) -> EmbeddingData:
        """Decode embedding data from simplified format."""
        offset = 0
        
        # Read model
        model_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        model = data[offset:offset+model_len].decode('utf-8')
        offset += model_len
        
        # Read dimension
        dimension = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        
        # Read distance metric
        distance_metric_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        distance_metric = data[offset:offset+distance_metric_len].decode('utf-8')
        offset += distance_metric_len
        
        # Read vector
        vector_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        vector_bytes = data[offset:offset+vector_len]
        offset += vector_len
        
        # Read metadata
        metadata_len = struct.unpack('I', data[offset:offset+4])[0]
        offset += 4
        metadata_bytes = data[offset:offset+metadata_len]
        metadata = json.loads(metadata_bytes.decode('utf-8'))
        
        # Reconstruct vector
        vector = np.frombuffer(vector_bytes, dtype=np.float32)
        
        return EmbeddingData(
            vector=vector,
            model=model,
            dimension=dimension,
            distance_metric=distance_metric,
            model_version=metadata.get('model_version'),
            framework=metadata.get('framework'),
            parameters=metadata.get('parameters'),
            asset_id=metadata.get('asset_id'),
            chunk_index=metadata.get('chunk_index'),
            confidence=metadata.get('confidence')
        )
    
    @staticmethod
    def encode_artifact(artifact_data: ArtifactData) -> bytes:
        """Encode artifact data using ZIP+MANIFEST format."""
        # Create a simple JSON-based format for artifacts
        artifact_dict = {
            'manifest': artifact_data.manifest,
            'files': artifact_data.files,
            'dependencies': artifact_data.dependencies or [],
            'zip_data': artifact_data.zip_data.hex(),  # Convert to hex string
            'zip_checksum': blake3.blake3(artifact_data.zip_data).hexdigest(),
            'zip_size': len(artifact_data.zip_data)
        }
        
        return json.dumps(artifact_dict).encode('utf-8')
    
    @staticmethod
    def decode_artifact(data: bytes) -> ArtifactData:
        """Decode artifact data from ZIP+MANIFEST format."""
        artifact_dict = json.loads(data.decode('utf-8'))
        
        return ArtifactData(
            files=artifact_dict['files'],
            manifest=artifact_dict['manifest'],
            zip_data=bytes.fromhex(artifact_dict['zip_data']),
            dependencies=artifact_dict.get('dependencies')
        )


class SimpleAssetKindValidator:
    """Simplified validator for different asset kinds."""
    
    @staticmethod
    def validate_blob(data: bytes, metadata: Optional[Dict] = None) -> bool:
        """Validate blob data."""
        return isinstance(data, bytes)  # Empty blobs are valid
    
    @staticmethod
    def validate_tensor(data: bytes) -> bool:
        """Validate tensor data."""
        try:
            SimpleAssetKindEncoder.decode_tensor(data)
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_embedding(data: bytes) -> bool:
        """Validate embedding data."""
        try:
            SimpleAssetKindEncoder.decode_embedding(data)
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_artifact(data: bytes) -> bool:
        """Validate artifact data."""
        try:
            SimpleAssetKindEncoder.decode_artifact(data)
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
    return SimpleAssetKindEncoder.encode_tensor(tensor_data)


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
    return SimpleAssetKindEncoder.encode_embedding(embedding_data)


def create_artifact_from_files(files: List[Dict[str, Any]],
                             manifest: Dict[str, Any],
                             zip_data: bytes) -> bytes:
    """Convenience function to create artifact from files and manifest."""
    artifact_data = ArtifactData(
        files=files,
        manifest=manifest,
        zip_data=zip_data
    )
    return SimpleAssetKindEncoder.encode_artifact(artifact_data)
