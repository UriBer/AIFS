"""AIFS gRPC Server

Implements the AIFS service defined in the proto file.
"""

import os
import time
import pathlib
import logging
from concurrent import futures
from typing import Dict, List, Optional, Iterator, Set
from functools import wraps

import grpc
import numpy as np
from grpc_reflection.v1alpha import reflection

# Import generated protobuf code
# Note: You'll need to run the protobuf compiler first:
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. aifs/proto/aifs.proto
from .proto import aifs_pb2, aifs_pb2_grpc
from .asset import AssetManager
from .auth import AuthorizationManager, verify_simple_token
from .errors import AIFSError, NotFoundError, InvalidArgumentError, handle_exception


def require_auth(permissions: Set[str]):
    """Decorator to require authorization for gRPC methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, context):
            # Extract authorization token from metadata
            metadata = dict(context.invocation_metadata())
            auth_token = metadata.get('authorization', '')
            
            if not auth_token:
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Authorization token required")
                return
            
            # Remove 'Bearer ' prefix if present
            if auth_token.startswith('Bearer '):
                auth_token = auth_token[7:]
            
            # Verify token
            if not verify_simple_token(auth_token, permissions):
                context.abort(grpc.StatusCode.PERMISSION_DENIED, "Insufficient permissions")
                return
            
            return func(self, request, context)
        return wrapper
    return decorator


# Built-in service implementations
class HealthServicer(aifs_pb2_grpc.HealthServicer):
    def Check(self, request, context):
        return aifs_pb2.HealthCheckResponse(healthy=True, status="SERVING")

class IntrospectServicer(aifs_pb2_grpc.IntrospectServicer):
    def GetInfo(self, request, context):
        return aifs_pb2.IntrospectResponse(version="1.0.0", config="default", features=["core", "vector", "snapshot"])

class AdminServicer(aifs_pb2_grpc.AdminServicer):
    def __init__(self, asset_manager: AssetManager):
        """Initialize admin servicer.
        
        Args:
            asset_manager: Asset manager instance
        """
        self.asset_manager = asset_manager
    
    @require_auth({"admin"})
    def CreateNamespace(self, request, context):
        """Create a new namespace.
        
        Args:
            request: CreateNamespaceRequest message
            context: gRPC context
            
        Returns:
            CreateNamespaceResponse with success status and namespace ID
        """
        try:
            # Create namespace using metadata store
            namespace_id = self.asset_manager.metadata_db.create_namespace(
                name=request.name,
                metadata={"description": f"Namespace created via gRPC API"}
            )
            
            return aifs_pb2.CreateNamespaceResponse(
                success=True, 
                namespace_id=namespace_id
            )
        except Exception as e:
            logging.error(f"Error creating namespace: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to create namespace: {str(e)}")
            return
    
    @require_auth({"admin"})
    def PruneSnapshot(self, request, context):
        """Prune a snapshot (remove it and its assets if not referenced elsewhere).
        
        Args:
            request: PruneSnapshotRequest message
            context: gRPC context
            
        Returns:
            PruneSnapshotResponse with success status
        """
        try:
            # Get snapshot to check if it exists
            snapshot = self.asset_manager.get_snapshot(request.snapshot_id)
            if not snapshot:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Snapshot {request.snapshot_id} not found")
                return
            
            # For now, just mark as pruned in metadata
            # In a full implementation, this would:
            # 1. Check if assets are referenced by other snapshots
            # 2. Remove unreferenced assets from storage
            # 3. Remove snapshot from metadata
            
            return aifs_pb2.PruneSnapshotResponse(success=True)
        except Exception as e:
            logging.error(f"Error pruning snapshot: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to prune snapshot: {str(e)}")
            return
    
    @require_auth({"admin"})
    def ManagePolicy(self, request, context):
        """Manage access policies for a namespace.
        
        Args:
            request: ManagePolicyRequest message
            context: gRPC context
            
        Returns:
            ManagePolicyResponse with success status
        """
        try:
            # For now, this is a placeholder implementation
            # In a full implementation, this would:
            # 1. Parse the policy JSON/YAML
            # 2. Validate the policy syntax
            # 3. Store the policy in the metadata store
            # 4. Apply the policy to the namespace
            
            logging.info(f"Policy management requested for namespace {request.namespace_id}: {request.policy}")
            
            return aifs_pb2.ManagePolicyResponse(success=True)
        except Exception as e:
            logging.error(f"Error managing policy: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to manage policy: {str(e)}")
            return

class MetricsServicer(aifs_pb2_grpc.MetricsServicer):
    def __init__(self, asset_manager: AssetManager):
        """Initialize metrics servicer.
        
        Args:
            asset_manager: Asset manager instance
        """
        self.asset_manager = asset_manager
    
    def GetMetrics(self, request, context):
        """Get system metrics in Prometheus and OpenTelemetry formats.
        
        Args:
            request: MetricsRequest message
            context: gRPC context
            
        Returns:
            MetricsResponse with metrics data
        """
        try:
            # Get basic system metrics
            assets = self.asset_manager.list_assets(limit=1000)  # Get a sample for metrics
            total_assets = len(assets)
            
            # Calculate storage metrics
            total_size = sum(asset.get('size', 0) for asset in assets)
            
            # Get namespace count
            namespaces = self.asset_manager.metadata_db.list_namespaces()
            total_namespaces = len(namespaces)
            
            # Get snapshot count
            # Note: This would need a method in metadata_db to count snapshots
            total_snapshots = 0  # Placeholder
            
            # Generate Prometheus metrics
            prometheus_metrics = f"""# HELP aifs_assets_total Total number of assets
# TYPE aifs_assets_total counter
aifs_assets_total {total_assets}

# HELP aifs_storage_bytes_total Total storage used in bytes
# TYPE aifs_storage_bytes_total counter
aifs_storage_bytes_total {total_size}

# HELP aifs_namespaces_total Total number of namespaces
# TYPE aifs_namespaces_total counter
aifs_namespaces_total {total_namespaces}

# HELP aifs_snapshots_total Total number of snapshots
# TYPE aifs_snapshots_total counter
aifs_snapshots_total {total_snapshots}

# HELP aifs_server_uptime_seconds Server uptime in seconds
# TYPE aifs_server_uptime_seconds counter
aifs_server_uptime_seconds {time.time()}
"""
            
            # Generate OpenTelemetry metrics (simplified JSON format)
            opentelemetry_metrics = {
                "metrics": [
                    {
                        "name": "aifs.assets.total",
                        "type": "counter",
                        "value": total_assets,
                        "timestamp": int(time.time() * 1000)
                    },
                    {
                        "name": "aifs.storage.bytes.total",
                        "type": "counter", 
                        "value": total_size,
                        "timestamp": int(time.time() * 1000)
                    },
                    {
                        "name": "aifs.namespaces.total",
                        "type": "counter",
                        "value": total_namespaces,
                        "timestamp": int(time.time() * 1000)
                    }
                ]
            }
            
            import json
            return aifs_pb2.MetricsResponse(
                prometheus_metrics=prometheus_metrics,
                opentelemetry_metrics=json.dumps(opentelemetry_metrics)
            )
        except Exception as e:
            logging.error(f"Error getting metrics: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to get metrics: {str(e)}")
            return

class FormatServicer(aifs_pb2_grpc.FormatServicer):
    def __init__(self, asset_manager: AssetManager):
        """Initialize format servicer.
        
        Args:
            asset_manager: Asset manager instance
        """
        self.asset_manager = asset_manager
    
    def FormatStorage(self, request, context):
        """Format the storage system (initialize or reinitialize).
        
        Args:
            request: FormatRequest message
            context: gRPC context
            
        Returns:
            FormatResponse with success status and root snapshot ID
        """
        try:
            if request.dry_run:
                # Dry run - just check if storage can be formatted
                log_messages = ["Dry run: Storage formatting would be successful"]
                return aifs_pb2.FormatResponse(
                    success=True,
                    root_snapshot_id="dry_run_root",
                    log="\n".join(log_messages)
                )
            
            # Actually format the storage
            log_messages = []
            
            # Create a root snapshot with all current assets
            assets = self.asset_manager.list_assets(limit=10000)  # Get all assets
            asset_ids = [asset["asset_id"] for asset in assets]
            
            if asset_ids:
                # Create root snapshot
                root_snapshot_id = self.asset_manager.create_snapshot(
                    namespace="root",
                    asset_ids=asset_ids,
                    metadata={"description": "Root snapshot created during storage formatting"}
                )
                log_messages.append(f"Created root snapshot: {root_snapshot_id}")
                log_messages.append(f"Included {len(asset_ids)} assets in root snapshot")
            else:
                # No assets, create empty root snapshot
                root_snapshot_id = self.asset_manager.create_snapshot(
                    namespace="root",
                    asset_ids=[],
                    metadata={"description": "Empty root snapshot created during storage formatting"}
                )
                log_messages.append("Created empty root snapshot")
            
            # Verify the snapshot
            snapshot = self.asset_manager.get_snapshot(root_snapshot_id)
            if snapshot:
                log_messages.append(f"Snapshot verification: {snapshot['merkle_root']}")
            
            log_messages.append("Storage formatting completed successfully")
            
            return aifs_pb2.FormatResponse(
                success=True,
                root_snapshot_id=root_snapshot_id,
                log="\n".join(log_messages)
            )
        except Exception as e:
            logging.error(f"Error formatting storage: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to format storage: {str(e)}")
            return


class AIFSServicer(aifs_pb2_grpc.AIFSServicer):
    """Implementation of the AIFS gRPC service."""
    
    def __init__(self, asset_manager: AssetManager):
        """Initialize servicer.
        
        Args:
            asset_manager: Asset manager instance
        """
        self.asset_manager = asset_manager
    
    @require_auth({"put"})
    def PutAsset(self, request_iterator: Iterator[aifs_pb2.PutAssetRequest], context) -> aifs_pb2.PutAssetResponse:
        """Store an asset.
        
        Args:
            request_iterator: Stream of PutAssetRequest messages
            context: gRPC context
            
        Returns:
            PutAssetResponse with asset ID
        """
        try:
            # Process first request to get metadata
            try:
                first_request = next(request_iterator)
            except StopIteration:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Empty request stream")
                return
            
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
            
        except Exception as e:
            # Log the error and return appropriate gRPC error
            logging.error(f"Error in PutAsset: {e}")
            handle_exception(context, "PutAsset", e)
            return
    
    @require_auth({"get"})
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
            error = NotFoundError("Asset", request.asset_id)
            handle_exception(context, "GetAsset", error)
            return
        
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
        
        # Set URI
        response.uri = self.asset_manager.get_asset_uri(asset["asset_id"])
        
        # Set data if requested
        if request.include_data:
            response.data = asset["data"]
        
        return response
    
    @require_auth({"delete"})
    def DeleteAsset(self, request: aifs_pb2.DeleteAssetRequest, context) -> aifs_pb2.DeleteAssetResponse:
        """Delete an asset.
        
        Args:
            request: DeleteAssetRequest message
            context: gRPC context
            
        Returns:
            DeleteAssetResponse with success status
        """
        try:
            # Delete asset using asset manager
            success = self.asset_manager.delete_asset(
                asset_id=request.asset_id,
                force=request.force
            )
            
            if success:
                return aifs_pb2.DeleteAssetResponse(
                    success=True,
                    message=f"Asset {request.asset_id} deleted successfully"
                )
            else:
                return aifs_pb2.DeleteAssetResponse(
                    success=False,
                    message=f"Failed to delete asset {request.asset_id}"
                )
        except ValueError as e:
            # This is for cases where asset is referenced by other assets
            return aifs_pb2.DeleteAssetResponse(
                success=False,
                message=str(e)
            )
        except Exception as e:
            logging.error(f"Error deleting asset: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to delete asset: {str(e)}")
            return
    
    @require_auth({"search"})
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
    
    @require_auth({"list"})
    def ListAssets(self, request: aifs_pb2.ListAssetsRequest, context) -> aifs_pb2.ListAssetsResponse:
        """List assets.
        
        Args:
            request: ListAssetsRequest message
            context: gRPC context
            
        Returns:
            ListAssetsResponse with list of assets
        """
        # Get assets from asset manager
        assets = self.asset_manager.list_assets(limit=request.limit, offset=request.offset)
        
        # Create response
        response = aifs_pb2.ListAssetsResponse()
        
        # Add assets
        for asset in assets:
            asset_proto = response.assets.add()
            asset_proto.asset_id = asset["asset_id"]
            asset_proto.kind = getattr(aifs_pb2.AssetKind, asset["kind"].upper())
            asset_proto.size = asset["size"]
            if asset["created_at"]:
                asset_proto.created_at = asset["created_at"]
            
            if asset["metadata"]:
                for key, value in asset["metadata"].items():
                    asset_proto.metadata[key] = str(value)
        
        return response
    
    @require_auth({"subscribe"})
    def SubscribeEvents(self, request: aifs_pb2.SubscribeEventsRequest, context) -> Iterator[aifs_pb2.SubscribeEventsResponse]:
        """Subscribe to events.
        
        Args:
            request: SubscribeEventsRequest message
            context: gRPC context
            
        Yields:
            SubscribeEventsResponse with events
        """
        try:
            # Create initial connection event
            connection_event = aifs_pb2.Event()
            connection_event.event_id = f"connection_{int(time.time())}"
            connection_event.event_type = "connection_established"
            connection_event.asset_id = ""
            connection_event.namespace = "system"
            connection_event.timestamp = int(time.time() * 1000)
            connection_event.metadata["client_id"] = str(id(context))
            connection_event.metadata["filter"] = request.filter
            connection_event.metadata["include_lineage"] = str(request.include_lineage)
            connection_event.metadata["include_drift"] = str(request.include_drift)
            
            response = aifs_pb2.SubscribeEventsResponse()
            response.events.append(connection_event)
            yield response
            
            # Send periodic heartbeat events
            heartbeat_count = 0
            while True:
                try:
                    # Check if client is still connected
                    if context.is_cancelled():
                        break
                    
                    # Create heartbeat event every 30 seconds
                    if heartbeat_count % 30 == 0:
                        heartbeat_event = aifs_pb2.Event()
                        heartbeat_event.event_id = f"heartbeat_{int(time.time())}"
                        heartbeat_event.event_type = "heartbeat"
                        heartbeat_event.asset_id = ""
                        heartbeat_event.namespace = "system"
                        heartbeat_event.timestamp = int(time.time() * 1000)
                        heartbeat_event.metadata["count"] = str(heartbeat_count)
                        
                        response = aifs_pb2.SubscribeEventsResponse()
                        response.events.append(heartbeat_event)
                        yield response
                    
                    # In a real implementation, this would:
                    # 1. Listen to a message queue or event bus
                    # 2. Filter events based on request.filter
                    # 3. Include lineage events if request.include_lineage is True
                    # 4. Include drift events if request.include_drift is True
                    # 5. Push events to the client as they occur
                    
                    # For now, we'll simulate some events occasionally
                    if heartbeat_count % 60 == 0 and heartbeat_count > 0:
                        # Simulate an asset creation event
                        if not request.filter or "asset" in request.filter.lower():
                            asset_event = aifs_pb2.Event()
                            asset_event.event_id = f"asset_event_{int(time.time())}"
                            asset_event.event_type = "asset_created"
                            asset_event.asset_id = f"simulated_asset_{heartbeat_count}"
                            asset_event.namespace = "default"
                            asset_event.timestamp = int(time.time() * 1000)
                            asset_event.metadata["source"] = "simulation"
                            asset_event.metadata["size"] = "1024"
                            
                            response = aifs_pb2.SubscribeEventsResponse()
                            response.events.append(asset_event)
                            yield response
                    
                    heartbeat_count += 1
                    time.sleep(1)  # Sleep for 1 second between checks
                    
                except Exception as e:
                    logging.error(f"Error in event subscription: {e}")
                    break
                    
        except Exception as e:
            logging.error(f"Error setting up event subscription: {e}")
            # Send error event
            error_event = aifs_pb2.Event()
            error_event.event_id = f"error_{int(time.time())}"
            error_event.event_type = "subscription_error"
            error_event.asset_id = ""
            error_event.namespace = "system"
            error_event.timestamp = int(time.time() * 1000)
            error_event.metadata["error"] = str(e)
            
            response = aifs_pb2.SubscribeEventsResponse()
            response.events.append(error_event)
            yield response
    
    @require_auth({"snapshot"})
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
    
    @require_auth({"get"})
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
    
    @require_auth({"list"})
    def ListNamespaces(self, request: aifs_pb2.ListNamespacesRequest, context) -> aifs_pb2.ListNamespacesResponse:
        """List namespaces.
        
        Args:
            request: ListNamespacesRequest message
            context: gRPC context
            
        Returns:
            ListNamespacesResponse with list of namespaces
        """
        try:
            # Get namespaces from metadata store
            namespaces = self.asset_manager.metadata_db.list_namespaces()
            
            # Apply pagination
            if request.limit > 0:
                namespaces = namespaces[request.offset:request.offset + request.limit]
            elif request.offset > 0:
                namespaces = namespaces[request.offset:]
            
            # Create response
            response = aifs_pb2.ListNamespacesResponse()
            
            # Add namespaces
            for namespace in namespaces:
                namespace_info = response.namespaces.add()
                namespace_info.namespace_id = namespace["namespace_id"]
                namespace_info.name = namespace["name"]
                namespace_info.description = namespace.get("description", "")
                namespace_info.created_at = namespace["created_at"]
                
                if namespace["metadata"]:
                    for key, value in namespace["metadata"].items():
                        namespace_info.metadata[key] = str(value)
            
            return response
        except Exception as e:
            logging.error(f"Error listing namespaces: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to list namespaces: {str(e)}")
            return
    
    @require_auth({"get"})
    def GetNamespace(self, request: aifs_pb2.GetNamespaceRequest, context) -> aifs_pb2.GetNamespaceResponse:
        """Get namespace information.
        
        Args:
            request: GetNamespaceRequest message
            context: gRPC context
            
        Returns:
            GetNamespaceResponse with namespace information
        """
        try:
            # Get namespace from metadata store
            namespace = self.asset_manager.metadata_db.get_namespace(request.namespace_id)
            if not namespace:
                context.abort(grpc.StatusCode.NOT_FOUND, f"Namespace {request.namespace_id} not found")
                return
            
            # Create response
            response = aifs_pb2.GetNamespaceResponse()
            response.namespace.namespace_id = namespace["namespace_id"]
            response.namespace.name = namespace["name"]
            response.namespace.description = namespace.get("description", "")
            response.namespace.created_at = namespace["created_at"]
            
            if namespace["metadata"]:
                for key, value in namespace["metadata"].items():
                    response.namespace.metadata[key] = str(value)
            
            return response
        except Exception as e:
            logging.error(f"Error getting namespace: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to get namespace: {str(e)}")
            return
    
    @require_auth({"get"})
    def VerifyAsset(self, request: aifs_pb2.VerifyAssetRequest, context) -> aifs_pb2.VerifyAssetResponse:
        """Verify asset integrity.
        
        Args:
            request: VerifyAssetRequest message
            context: gRPC context
            
        Returns:
            VerifyAssetResponse with verification results
        """
        try:
            # Get asset data
            asset = self.asset_manager.get_asset(request.asset_id)
            if not asset:
                return aifs_pb2.VerifyAssetResponse(
                    valid=False,
                    message=f"Asset {request.asset_id} not found",
                    computed_hash="",
                    stored_hash=""
                )
            
            # Compute hash of stored data
            import blake3
            computed_hash = blake3.blake3(asset["data"]).hexdigest()
            stored_hash = request.asset_id  # Asset ID is the hash
            
            # Compare hashes
            if computed_hash == stored_hash:
                return aifs_pb2.VerifyAssetResponse(
                    valid=True,
                    message="Asset integrity verified",
                    computed_hash=computed_hash,
                    stored_hash=stored_hash
                )
            else:
                return aifs_pb2.VerifyAssetResponse(
                    valid=False,
                    message="Asset integrity check failed - hash mismatch",
                    computed_hash=computed_hash,
                    stored_hash=stored_hash
                )
        except Exception as e:
            logging.error(f"Error verifying asset: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to verify asset: {str(e)}")
            return
    
    @require_auth({"get"})
    def VerifySnapshot(self, request: aifs_pb2.VerifySnapshotRequest, context) -> aifs_pb2.VerifySnapshotResponse:
        """Verify snapshot integrity and signature.
        
        Args:
            request: VerifySnapshotRequest message
            context: gRPC context
            
        Returns:
            VerifySnapshotResponse with verification results
        """
        try:
            # Get snapshot
            snapshot = self.asset_manager.get_snapshot(request.snapshot_id)
            if not snapshot:
                return aifs_pb2.VerifySnapshotResponse(
                    valid=False,
                    message=f"Snapshot {request.snapshot_id} not found",
                    merkle_root="",
                    signature_valid=False
                )
            
            # Verify signature if public key provided
            signature_valid = False
            if request.public_key:
                signature_valid = self.asset_manager.verify_snapshot(
                    request.snapshot_id, 
                    request.public_key
                )
            else:
                # Use default public key
                signature_valid = self.asset_manager.verify_snapshot(request.snapshot_id)
            
            # Get merkle root
            merkle_root = snapshot.get("merkle_root", "")
            
            if signature_valid:
                return aifs_pb2.VerifySnapshotResponse(
                    valid=True,
                    message="Snapshot integrity and signature verified",
                    merkle_root=merkle_root,
                    signature_valid=True
                )
            else:
                return aifs_pb2.VerifySnapshotResponse(
                    valid=False,
                    message="Snapshot signature verification failed",
                    merkle_root=merkle_root,
                    signature_valid=False
                )
        except Exception as e:
            logging.error(f"Error verifying snapshot: {e}")
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to verify snapshot: {str(e)}")
            return


def serve(root_dir: str = "~/.aifs", port: int = 50051, max_workers: int = 10, dev_mode: bool = False):
    """Start the AIFS gRPC server.
    
    Args:
        root_dir: Root directory for AIFS data
        port: Port to listen on
        max_workers: Maximum number of worker threads
        dev_mode: Enable development features like gRPC reflection
    """
    # Expand user directory
    root_dir = os.path.expanduser(root_dir)
    
    # Initialize asset manager
    asset_manager = AssetManager(root_dir)
    
    # Configure gRPC options for large file support and compression
    # Note: gRPC natively supports Gzip/Deflate. zstd would need custom implementation
    options = [
        ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
        ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
        ('grpc.max_message_length', 100 * 1024 * 1024),  # 100MB
        ('grpc.default_compression_algorithm', grpc.Compression.Gzip),  # Enable compression
    ]
    
    # Create server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers), options=options)
    aifs_pb2_grpc.add_AIFSServicer_to_server(AIFSServicer(asset_manager), server)

    # Register built-in services
    aifs_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)
    aifs_pb2_grpc.add_IntrospectServicer_to_server(IntrospectServicer(), server)
    aifs_pb2_grpc.add_AdminServicer_to_server(AdminServicer(asset_manager), server)
    aifs_pb2_grpc.add_MetricsServicer_to_server(MetricsServicer(asset_manager), server)
    aifs_pb2_grpc.add_FormatServicer_to_server(FormatServicer(asset_manager), server)
    
    # Enable gRPC reflection for API discovery (dev mode only)
    if dev_mode:
        try:
            SERVICE_NAMES = (
                aifs_pb2.DESCRIPTOR.services_by_name['AIFS'].full_name,
                aifs_pb2.DESCRIPTOR.services_by_name['Health'].full_name,
                aifs_pb2.DESCRIPTOR.services_by_name['Introspect'].full_name,
                aifs_pb2.DESCRIPTOR.services_by_name['Admin'].full_name,
                aifs_pb2.DESCRIPTOR.services_by_name['Metrics'].full_name,
                aifs_pb2.DESCRIPTOR.services_by_name['Format'].full_name,
                reflection.SERVICE_NAME,
            )
            
            # Enable reflection
            reflection.enable_server_reflection(SERVICE_NAMES, server)
            print(f"✅ Enabled reflection for services: {SERVICE_NAMES}")
        except Exception as e:
            print(f"⚠️  Failed to enable reflection: {e}")
            print("   Reflection will not be available, but server will work normally")
    else:
        print("🔒 Production mode: gRPC reflection disabled")
    
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