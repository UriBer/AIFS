"""AIFS Client

Provides a Python client for the AIFS gRPC service.
"""

import os
from typing import Dict, List, Optional, Union, BinaryIO, Any, Iterator

import grpc
import numpy as np

# Import generated protobuf code
from .proto import aifs_pb2, aifs_pb2_grpc


class AIFSClient:
    """Client for the AIFS gRPC service."""
    
    def __init__(self, server_address: str = "localhost:50051"):
        """Initialize client.
        
        Args:
            server_address: Address of the AIFS server
        """
        self.channel = grpc.insecure_channel(server_address)
        self.stub = aifs_pb2_grpc.AIFSStub(self.channel)
    
    def put_asset(self, data: bytes, kind: str = "blob", 
                 embedding: Optional[np.ndarray] = None,
                 metadata: Optional[Dict[str, str]] = None,
                 parents: Optional[List[Dict]] = None,
                 chunk_size: int = 1024 * 1024) -> str:
        """Store an asset.
        
        Args:
            data: Asset data
            kind: Asset kind (blob, tensor, embed, artifact)
            embedding: Optional embedding vector
            metadata: Optional metadata dictionary
            parents: Optional list of parent assets with transform info
                     [{"asset_id": str, "transform_name": str, "transform_digest": str}]
            chunk_size: Size of chunks for streaming
            
        Returns:
            Asset ID (BLAKE3 hash)
        """
        # Map kind string to enum value
        kind_enum = getattr(aifs_pb2.AssetKind, kind.upper())
        
        # Create request generator
        def request_generator():
            # First request with metadata
            first_request = aifs_pb2.PutAssetRequest(kind=kind_enum)
            
            # Add metadata if provided
            if metadata:
                for key, value in metadata.items():
                    first_request.metadata[key] = str(value)
            
            # Add parents if provided
            if parents:
                for parent in parents:
                    parent_edge = aifs_pb2.ParentEdge(
                        parent_asset_id=parent["asset_id"],
                        transform_name=parent.get("transform_name", ""),
                        transform_digest=parent.get("transform_digest", "")
                    )
                    first_request.parents.append(parent_edge)
            
            # Add embedding if provided
            if embedding is not None:
                first_request.embedding = embedding.astype(np.float32).tobytes()
            
            # Add first chunk
            first_chunk = data[:chunk_size]
            chunk_proto = aifs_pb2.Chunk(data=first_chunk)
            first_request.chunks.append(chunk_proto)
            
            yield first_request
            
            # Stream remaining chunks
            for i in range(chunk_size, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                request = aifs_pb2.PutAssetRequest()
                chunk_proto = aifs_pb2.Chunk(data=chunk)
                request.chunks.append(chunk_proto)
                yield request
        
        # Call gRPC method
        response = self.stub.PutAsset(request_generator())
        
        return response.asset_id
    
    def get_asset(self, asset_id: str, include_data: bool = True) -> Optional[Dict]:
        """Retrieve an asset.
        
        Args:
            asset_id: Asset ID (BLAKE3 hash)
            include_data: Whether to include the actual data
            
        Returns:
            Asset dictionary or None if not found
        """
        # Create request
        request = aifs_pb2.GetAssetRequest(
            asset_id=asset_id,
            include_data=include_data
        )
        
        try:
            # Call gRPC method
            response = self.stub.GetAsset(request)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise
        
        # Convert response to dictionary
        asset = {
            "asset_id": response.metadata.asset_id,
            "kind": aifs_pb2.AssetKind.Name(response.metadata.kind).lower(),
            "size": response.metadata.size,
            "created_at": response.metadata.created_at,
            "metadata": dict(response.metadata.metadata),
            "parents": [],
            "children": list(response.children)
        }
        
        # Add parents
        for parent_edge in response.parents:
            asset["parents"].append({
                "asset_id": parent_edge.parent_asset_id,
                "transform_name": parent_edge.transform_name,
                "transform_digest": parent_edge.transform_digest
            })
        
        # Add data if included
        if include_data and response.data:
            asset["data"] = response.data
        
        return asset
    
    def vector_search(self, query_embedding: np.ndarray, k: int = 10, 
                     filter_metadata: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Search for similar assets.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of asset dictionaries with similarity scores
        """
        # Create request
        request = aifs_pb2.VectorSearchRequest(
            query_embedding=query_embedding.astype(np.float32).tobytes(),
            k=k
        )
        
        # Add filters if provided
        if filter_metadata:
            for key, value in filter_metadata.items():
                request.filter[key] = value
        
        # Call gRPC method
        response = self.stub.VectorSearch(request)
        
        # Convert response to list of dictionaries
        results = []
        for result in response.results:
            asset = {
                "asset_id": result.asset_id,
                "score": result.score,
                "kind": aifs_pb2.AssetKind.Name(result.metadata.kind).lower(),
                "size": result.metadata.size,
                "created_at": result.metadata.created_at,
                "metadata": dict(result.metadata.metadata)
            }
            results.append(asset)
        
        return results
    
    def create_snapshot(self, namespace: str, asset_ids: List[str], 
                       metadata: Optional[Dict[str, str]] = None) -> Dict:
        """Create a snapshot of assets.
        
        Args:
            namespace: Namespace for the snapshot
            asset_ids: List of asset IDs to include
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary with snapshot ID and merkle root
        """
        # Create request
        request = aifs_pb2.CreateSnapshotRequest(
            namespace=namespace,
            asset_ids=asset_ids
        )
        
        # Add metadata if provided
        if metadata:
            for key, value in metadata.items():
                request.metadata[key] = str(value)
        
        # Call gRPC method
        response = self.stub.CreateSnapshot(request)
        
        return {
            "snapshot_id": response.snapshot_id,
            "merkle_root": response.merkle_root
        }
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get snapshot.
        
        Args:
            snapshot_id: Snapshot ID
            
        Returns:
            Snapshot dictionary or None if not found
        """
        # Create request
        request = aifs_pb2.GetSnapshotRequest(
            snapshot_id=snapshot_id
        )
        
        try:
            # Call gRPC method
            response = self.stub.GetSnapshot(request)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise
        
        # Convert response to dictionary
        snapshot = {
            "snapshot_id": response.snapshot_id,
            "namespace": response.namespace,
            "merkle_root": response.merkle_root,
            "created_at": response.created_at,
            "metadata": dict(response.metadata),
            "asset_ids": list(response.asset_ids)
        }
        
        return snapshot
    
    def close(self):
        """Close the gRPC channel."""
        self.channel.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()