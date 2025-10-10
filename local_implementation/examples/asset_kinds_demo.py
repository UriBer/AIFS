#!/usr/bin/env python3
"""
AIFS Asset Kinds Demo

Demonstrates the four asset kinds as specified in the AIFS architecture:
- Blob: Raw byte stream
- Tensor: Arrow2 encoding with nd-array.proto schema
- Embed: FlatBuffers encoding with embedding.fbs schema
- Artifact: ZIP+MANIFEST encoding with artifact.proto schema
"""

import numpy as np
import tempfile
import zipfile
import io
from pathlib import Path

# Import AIFS modules
from aifs.asset import AssetManager
from aifs.asset_kinds_simple import (
    SimpleAssetKindEncoder as AssetKindEncoder, SimpleAssetKindValidator as AssetKindValidator, 
    TensorData, EmbeddingData, ArtifactData,
    create_tensor_from_numpy, create_embedding_from_vector, create_artifact_from_files
)


def demo_blob_asset():
    """Demonstrate blob asset storage."""
    print("🔵 Blob Asset Demo")
    print("=" * 50)
    
    # Create some sample data
    blob_data = b"Hello, AIFS! This is a blob asset with raw byte data."
    
    # Validate blob data
    is_valid = AssetKindValidator.validate_blob(blob_data)
    print(f"✅ Blob data valid: {is_valid}")
    
    # Encode/decode blob (trivial for blobs)
    encoded = AssetKindEncoder.encode_blob(blob_data)
    decoded = AssetKindEncoder.decode_blob(encoded)
    print(f"✅ Blob encode/decode: {blob_data == decoded}")
    
    print()


def demo_tensor_asset():
    """Demonstrate tensor asset storage with Arrow2 encoding."""
    print("🔺 Tensor Asset Demo")
    print("=" * 50)
    
    try:
        # Create sample tensor data
        tensor_array = np.random.rand(3, 4, 5).astype(np.float32)
        print(f"📊 Created tensor: shape={tensor_array.shape}, dtype={tensor_array.dtype}")
        
        # Create tensor data structure
        tensor_data = TensorData(
            data=tensor_array,
            dtype=str(tensor_array.dtype),
            shape=tensor_array.shape,
            metadata={
                'name': 'demo_tensor',
                'description': 'Random 3D tensor for demonstration',
                'creator': 'aifs_demo',
                'created_at': 1640995200,
                'attributes': {
                    'purpose': 'demo',
                    'version': '1.0'
                }
            }
        )
        
        # Encode tensor
        encoded_data = AssetKindEncoder.encode_tensor(tensor_data)
        print(f"📦 Encoded tensor: {len(encoded_data)} bytes")
        
        # Validate encoded data
        is_valid = AssetKindValidator.validate_tensor(encoded_data)
        print(f"✅ Tensor data valid: {is_valid}")
        
        # Decode tensor
        decoded_tensor = AssetKindEncoder.decode_tensor(encoded_data)
        print(f"📊 Decoded tensor: shape={decoded_tensor.shape}, dtype={decoded_tensor.dtype}")
        print(f"✅ Tensor round-trip: {np.array_equal(tensor_array, decoded_tensor.data)}")
        
        # Test convenience function
        convenience_encoded = create_tensor_from_numpy(
            tensor_array, 
            name="convenience_tensor",
            description="Created with convenience function"
        )
        print(f"✅ Convenience function: {len(convenience_encoded)} bytes")
        
    except ImportError as e:
        print(f"⚠️  PyArrow not available: {e}")
        print("   Install with: pip install pyarrow")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


def demo_embedding_asset():
    """Demonstrate embedding asset storage with FlatBuffers encoding."""
    print("🔸 Embedding Asset Demo")
    print("=" * 50)
    
    try:
        # Create sample embedding data
        embedding_vector = np.random.rand(128).astype(np.float32)
        print(f"🧮 Created embedding: dimension={len(embedding_vector)}")
        
        # Create embedding data structure
        embedding_data = EmbeddingData(
            vector=embedding_vector,
            model="openai_ada_002",
            dimension=len(embedding_vector),
            distance_metric="cosine",
            model_version="2.0",
            framework="openai",
            parameters={
                "temperature": 0.7,
                "max_tokens": 1000
            },
            asset_id="demo_asset_123",
            chunk_index=0,
            confidence=0.95
        )
        
        # Encode embedding
        encoded_data = AssetKindEncoder.encode_embedding(embedding_data)
        print(f"📦 Encoded embedding: {len(encoded_data)} bytes")
        
        # Validate encoded data
        is_valid = AssetKindValidator.validate_embedding(encoded_data)
        print(f"✅ Embedding data valid: {is_valid}")
        
        # Decode embedding
        decoded_embedding = AssetKindEncoder.decode_embedding(encoded_data)
        print(f"🧮 Decoded embedding: dimension={decoded_embedding.dimension}, model={decoded_embedding.model}")
        print(f"✅ Embedding round-trip: {np.allclose(embedding_vector, decoded_embedding.vector)}")
        
        # Test convenience function
        convenience_encoded = create_embedding_from_vector(
            embedding_vector,
            model="custom",
            distance_metric="euclidean"
        )
        print(f"✅ Convenience function: {len(convenience_encoded)} bytes")
        
    except ImportError as e:
        print(f"⚠️  FlatBuffers not available: {e}")
        print("   Install with: pip install flatbuffers")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


def demo_artifact_asset():
    """Demonstrate artifact asset storage with ZIP+MANIFEST encoding."""
    print("📦 Artifact Asset Demo")
    print("=" * 50)
    
    try:
        # Create sample files for the artifact
        files_data = {
            "README.md": b"# Demo Artifact\n\nThis is a demo artifact with multiple files.",
            "config.json": b'{"version": "1.0", "debug": true}',
            "data.csv": b"name,value\nitem1,42\nitem2,84\n",
            "scripts/process.py": b"#!/usr/bin/env python3\nprint('Hello from artifact!')\n"
        }
        
        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path, file_data in files_data.items():
                zip_file.writestr(file_path, file_data)
        zip_data = zip_buffer.getvalue()
        
        print(f"📁 Created ZIP with {len(files_data)} files: {len(zip_data)} bytes")
        
        # Create file entries
        file_entries = []
        for file_path, file_data in files_data.items():
            file_entries.append({
                'path': file_path,
                'asset_id': f"asset_{hash(file_path)}",  # Mock asset ID
                'size': len(file_data),
                'mime_type': 'text/plain',
                'created_at': 1640995200,
                'modified_at': 1640995200,
                'is_executable': file_path.endswith('.py'),
                'checksum': f"blake3_{hash(file_data)}",  # Mock checksum
                'metadata': {
                    'encoding': 'utf-8',
                    'line_ending': 'unix'
                }
            })
        
        # Create artifact manifest
        manifest = {
            'name': 'demo_artifact',
            'version': '1.0.0',
            'description': 'Demo artifact for AIFS testing',
            'author': 'aifs_demo',
            'license': 'MIT',
            'tags': ['demo', 'test', 'aifs'],
            'created_at': 1640995200,
            'modified_at': 1640995200,
            'artifact_id': 'demo_artifact_123',
            'metadata': {
                'purpose': 'demonstration',
                'category': 'example'
            }
        }
        
        # Create artifact data
        artifact_data = ArtifactData(
            files=file_entries,
            manifest=manifest,
            zip_data=zip_data,
            dependencies=[
                {
                    'name': 'numpy',
                    'version': '>=1.20.0',
                    'source': 'pip',
                    'metadata': {'optional': False}
                }
            ]
        )
        
        # Encode artifact
        encoded_data = AssetKindEncoder.encode_artifact(artifact_data)
        print(f"📦 Encoded artifact: {len(encoded_data)} bytes")
        
        # Validate encoded data
        is_valid = AssetKindValidator.validate_artifact(encoded_data)
        print(f"✅ Artifact data valid: {is_valid}")
        
        # Decode artifact
        decoded_artifact = AssetKindEncoder.decode_artifact(encoded_data)
        print(f"📁 Decoded artifact: {len(decoded_artifact.files)} files, name={decoded_artifact.manifest['name']}")
        print(f"✅ Artifact round-trip: {len(decoded_artifact.zip_data) == len(zip_data)}")
        
        # Test convenience function
        convenience_encoded = create_artifact_from_files(
            file_entries, manifest, zip_data
        )
        print(f"✅ Convenience function: {len(convenience_encoded)} bytes")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


def demo_asset_manager_integration():
    """Demonstrate integration with AssetManager."""
    print("🏗️  AssetManager Integration Demo")
    print("=" * 50)
    
    try:
        # Create temporary directory for AIFS
        with tempfile.TemporaryDirectory() as temp_dir:
            asset_manager = AssetManager(temp_dir)
            
            # Test blob storage
            blob_data = b"Hello, AIFS blob!"
            blob_id = asset_manager.put_asset(blob_data, "blob")
            print(f"📦 Stored blob: {blob_id[:8]}...")
            
            # Test tensor storage
            if hasattr(asset_manager, 'put_tensor'):
                tensor_array = np.random.rand(2, 3).astype(np.float32)
                tensor_data = TensorData(
                    data=tensor_array,
                    dtype=str(tensor_array.dtype),
                    shape=tensor_array.shape,
                    metadata={'name': 'demo_tensor'}
                )
                tensor_id = asset_manager.put_tensor(tensor_data)
                print(f"🔺 Stored tensor: {tensor_id[:8]}...")
                
                # Retrieve tensor
                retrieved_tensor = asset_manager.get_tensor(tensor_id)
                if retrieved_tensor:
                    print(f"✅ Retrieved tensor: shape={retrieved_tensor.shape}")
            
            # Test embedding storage
            if hasattr(asset_manager, 'put_embedding'):
                embedding_vector = np.random.rand(64).astype(np.float32)
                embedding_data = EmbeddingData(
                    vector=embedding_vector,
                    model="custom",
                    dimension=len(embedding_vector)
                )
                embedding_id = asset_manager.put_embedding(embedding_data)
                print(f"🔸 Stored embedding: {embedding_id[:8]}...")
                
                # Retrieve embedding
                retrieved_embedding = asset_manager.get_embedding(embedding_id)
                if retrieved_embedding:
                    print(f"✅ Retrieved embedding: dimension={retrieved_embedding.dimension}")
            
            # List all assets
            assets = asset_manager.list_assets()
            print(f"📋 Total assets: {len(assets)}")
            for asset in assets:
                print(f"   - {asset['kind']}: {asset['asset_id'][:8]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()


def main():
    """Run all asset kind demonstrations."""
    print("🚀 AIFS Asset Kinds Demonstration")
    print("=" * 60)
    print()
    
    # Run individual demos
    demo_blob_asset()
    demo_tensor_asset()
    demo_embedding_asset()
    demo_artifact_asset()
    demo_asset_manager_integration()
    
    print("✅ Asset Kinds Demo Complete!")
    print()
    print("📚 Next Steps:")
    print("   1. Install missing dependencies: pip install pyarrow flatbuffers")
    print("   2. Run the AIFS server: aifs server --dev")
    print("   3. Test with the gRPC API explorer tools")
    print("   4. Check the docs/implementation/MISSING_FEATURES.md for implementation status")


if __name__ == "__main__":
    main()
