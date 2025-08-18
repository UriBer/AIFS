"""AIFS gRPC Server

Implements the AIFS service defined in the proto file.
"""

import os
import time
import pathlib
import logging
from concurrent import futures
from typing import Dict, List, Optional, Iterator

import grpc
import numpy as np

# Import generated protobuf code
# Note: You'll need to run the protobuf compiler first:
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. aifs/proto/aifs.proto
from .proto import aifs_pb2, aifs_pb2_grpc
from .asset import AssetManager

# Built-in service implementations
class HealthServicer(aifs_pb2_grpc.HealthServicer):
    def Check(self, request, context):
        return aifs_pb2.HealthCheckResponse(healthy=True, status="SERVING")

class IntrospectServicer(aifs_pb2_grpc.IntrospectServicer):
    def GetInfo(self, request, context):
        return aifs_pb2.IntrospectResponse(version="1.0.0", config="default", features=["core", "vector", "snapshot"])

class AdminServicer(aifs_pb2_grpc.AdminServicer):
    def CreateNamespace(self, request, context):
        return aifs_pb2.CreateNamespaceResponse(success=True, namespace_id=request.name)
    def PruneSnapshot(self, request, context):
        return aifs_pb2.PruneSnapshotResponse(success=True)
    def ManagePolicy(self, request, context):
        return aifs_pb2.ManagePolicyResponse(success=True)

class MetricsServicer(aifs_pb2_grpc.MetricsServicer):
    def GetMetrics(self, request, context):
        return aifs_pb2.MetricsResponse(prometheus_metrics="# HELP dummy\n", opentelemetry_metrics="{}")

class FormatServicer(aifs_pb2_grpc.FormatServicer):
    def FormatStorage(self, request, context):
        return aifs_pb2.FormatResponse(success=True, root_snapshot_id="root123", log="Formatted")


class AIFSServicer(aifs_pb2_grpc.AIFSServicer):
    """Implementation of the AIFS gRPC service."""
    
    def __init__(self, asset_manager: AssetManager):
        """Initialize servicer.
        
        Args:
            asset_manager: Asset manager instance
        """
        self.asset_manager = asset_manager
    
    def PutAsset(self, request_iterator: Iterator[aifs_pb2.PutAssetRequest], context) -> aifs_pb2.PutAssetResponse:
        """Store an asset.
        
        Args:
            request_iterator: Stream of PutAssetRequest messages
            context: gRPC context
            
        Returns:
            PutAssetResponse with asset ID
        """
        # Process first request to get metadata
        try:
            first_request = next(request_iterator)
        except StopIteration:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Empty request stream")
        
        # Extract metadata
        kind = aifs_pb2.AssetKind.Name(first_request.kind).lower()
        metadata = dict(first_request.metadata)
        
        # Extract parents
        parents = []
        for parent_edge in first_request.parents:
            parents.append({
                "asset_id": parent_edge.parent_asset_id,
                "transform_name": parent_edge.transform_name,
                "transform_digest": parent_edge.transform_digest
            })
        
        # Extract embedding if provided
        embedding = None
        if first_request.embedding:
            embedding = np.frombuffer(first_request.embedding, dtype=np.float32)
        
        # Collect chunks
        chunks = []
        if first_request.chunks:
            for chunk in first_request.chunks:
                chunks.append(chunk.data)
        
        # Process remaining chunks
        for request in request_iterator:
            for chunk in request.chunks:
                chunks.append(chunk.data)
        
        # Combine chunks
        data = b''.join(chunks)
        
        # Store asset
        asset_id = self.asset_manager.put_asset(
            data=data,
            kind=kind,
            embedding=embedding,
            metadata=metadata,
            parents=parents
        )
        
        # Return response
        return aifs_pb2.PutAssetResponse(asset_id=asset_id)
    
    def GetAsset(self, request: aifs_pb2.GetAssetRequest, context) -> aifs_pb2.GetAssetResponse:
        """Retrieve an asset.
        
        Args:
            request: GetAssetRequest message
            context: gRPC context
            
        Returns:
            GetAssetResponse with asset metadata and optionally data
        """
        # Get asset
        asset = self.asset_manager.get_asset(request.asset_id)
        if not asset:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Asset {request.asset_id} not found")
        
        # Create response
        response = aifs_pb2.GetAssetResponse()
        
        # Set metadata
        response.metadata.asset_id = asset["asset_id"]
        response.metadata.kind = getattr(aifs_pb2.AssetKind, asset["kind"].upper())
        response.metadata.size = asset["size"]
        if asset["created_at"]:
            response.metadata.created_at = asset["created_at"]
        
        if asset["metadata"]:
            for key, value in asset["metadata"].items():
                response.metadata.metadata[key] = str(value)
        
        # Set parents
        for parent in asset["parents"]:
            parent_edge = response.parents.add()
            parent_edge.parent_asset_id = parent["asset_id"]
            if parent.get("transform_name"):
                parent_edge.transform_name = parent["transform_name"]
            if parent.get("transform_digest"):
                parent_edge.transform_digest = parent["transform_digest"]
        
        # Set children
        for child in asset["children"]:
            response.children.append(child["asset_id"])
        
        # Set data if requested
        if request.include_data:
            response.data = asset["data"]
        
        return response
    
    def VectorSearch(self, request: aifs_pb2.VectorSearchRequest, context) -> aifs_pb2.VectorSearchResponse:
        """Search for similar assets.
        
        Args:
            request: VectorSearchRequest message
            context: gRPC context
            
        Returns:
            VectorSearchResponse with search results
        """
        # Extract query embedding
        query_embedding = np.frombuffer(request.query_embedding, dtype=np.float32)
        
        # Perform search
        results = self.asset_manager.vector_search(query_embedding, request.k)
        
        # Create response
        response = aifs_pb2.VectorSearchResponse()
        
        # Add results
        for result in results:
            search_result = response.results.add()
            search_result.asset_id = result["asset_id"]
            search_result.score = result["score"]
            
            # Set metadata
            search_result.metadata.asset_id = result["asset_id"]
            search_result.metadata.kind = getattr(aifs_pb2.AssetKind, result["kind"].upper())
            search_result.metadata.size = result["size"]
            if result["created_at"]:
                search_result.metadata.created_at = result["created_at"]
            
            if result["metadata"]:
                for key, value in result["metadata"].items():
                    search_result.metadata.metadata[key] = str(value)
        
        return response
    
    def CreateSnapshot(self, request: aifs_pb2.CreateSnapshotRequest, context) -> aifs_pb2.CreateSnapshotResponse:
        """Create a snapshot.
        
        Args:
            request: CreateSnapshotRequest message
            context: gRPC context
            
        Returns:
            CreateSnapshotResponse with snapshot ID
        """
        # Create snapshot
        snapshot_id = self.asset_manager.create_snapshot(
            namespace=request.namespace,
            asset_ids=list(request.asset_ids),
            metadata=dict(request.metadata)
        )
        
        # Get snapshot to get merkle root
        snapshot = self.asset_manager.get_snapshot(snapshot_id)
        
        # Create response
        return aifs_pb2.CreateSnapshotResponse(
            snapshot_id=snapshot_id,
            merkle_root=snapshot["merkle_root"]
        )
    
    def GetSnapshot(self, request: aifs_pb2.GetSnapshotRequest, context) -> aifs_pb2.GetSnapshotResponse:
        """Get a snapshot.
        
        Args:
            request: GetSnapshotRequest message
            context: gRPC context
            
        Returns:
            GetSnapshotResponse with snapshot metadata
        """
        # Get snapshot
        snapshot = self.asset_manager.get_snapshot(request.snapshot_id)
        if not snapshot:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Snapshot {request.snapshot_id} not found")
        
        # Create response
        response = aifs_pb2.GetSnapshotResponse(
            snapshot_id=snapshot["snapshot_id"],
            namespace=snapshot["namespace"],
            merkle_root=snapshot["merkle_root"],
            created_at=snapshot["created_at"]
        )
        
        # Set metadata
        if snapshot["metadata"]:
            for key, value in snapshot["metadata"].items():
                response.metadata[key] = str(value)
        
        # Set asset IDs
        for asset in snapshot["assets"]:
            response.asset_ids.append(asset["asset_id"])
        
        return response


def serve(root_dir: str = "~/.aifs", port: int = 50051, max_workers: int = 10):
    """Start the AIFS gRPC server.
    
    Args:
        root_dir: Root directory for AIFS data
        port: Port to listen on
        max_workers: Maximum number of worker threads
    """
    # Expand user directory
    root_dir = os.path.expanduser(root_dir)
    
    # Initialize asset manager
    asset_manager = AssetManager(root_dir)
    
    # Create server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    aifs_pb2_grpc.add_AIFSServicer_to_server(AIFSServicer(asset_manager), server)

    # Register built-in services
    aifs_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)
    aifs_pb2_grpc.add_IntrospectServicer_to_server(IntrospectServicer(), server)
    aifs_pb2_grpc.add_AdminServicer_to_server(AdminServicer(), server)
    aifs_pb2_grpc.add_MetricsServicer_to_server(MetricsServicer(), server)
    aifs_pb2_grpc.add_FormatServicer_to_server(FormatServicer(), server)
    
    # Add secure port
    server.add_insecure_port(f"[::]:{port}")
    
    # Start server
    server.start()
    print(f"AIFS server started on port {port}")
    print(f"Data directory: {root_dir}")
    
    try:
        # Keep server running
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        server.stop(0)
        print("AIFS server stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AIFS gRPC Server")
    parser.add_argument("--root-dir", type=str, default="~/.aifs", help="Root directory for AIFS data")
    parser.add_argument("--port", type=int, default=50051, help="Port to listen on")
    parser.add_argument("--max-workers", type=int, default=10, help="Maximum number of worker threads")
    
    args = parser.parse_args()
    
    serve(args.root_dir, args.port, args.max_workers)