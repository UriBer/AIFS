#!/usr/bin/env python3
"""Explore AIFS gRPC API and show all available methods."""

import grpc
import json
from aifs.proto import aifs_pb2, aifs_pb2_grpc

def list_services():
    """List all available services."""
    print("🔍 AIFS gRPC Services:")
    print("=" * 50)
    
    services = [
        ("aifs.v1.AIFS", "Main AIFS service"),
        ("aifs.v1.Health", "Health check service"),
        ("aifs.v1.Introspect", "System introspection service"),
        ("aifs.v1.Admin", "Administrative operations"),
        ("aifs.v1.Metrics", "System metrics"),
        ("aifs.v1.Format", "Storage formatting"),
    ]
    
    for service_name, description in services:
        print(f"📡 {service_name}")
        print(f"   {description}")
        print()

def list_aifs_methods():
    """List all AIFS service methods."""
    print("🎯 AIFS Service Methods:")
    print("=" * 50)
    
    methods = [
        ("PutAsset", "Store an asset with streaming support"),
        ("GetAsset", "Retrieve an asset with optional data"),
        ("DeleteAsset", "Delete an asset (with force option)"),
        ("ListAssets", "List assets with pagination"),
        ("VectorSearch", "Search for similar assets using vectors"),
        ("CreateSnapshot", "Create a snapshot with Merkle tree"),
        ("GetSnapshot", "Retrieve snapshot metadata"),
        ("SubscribeEvents", "Real-time event streaming"),
        ("ListNamespaces", "List all namespaces"),
        ("GetNamespace", "Get namespace information"),
        ("VerifyAsset", "Verify asset integrity"),
        ("VerifySnapshot", "Verify snapshot integrity and signature"),
    ]
    
    for method_name, description in methods:
        print(f"🔧 {method_name}")
        print(f"   {description}")
        print()

def show_grpcurl_examples():
    """Show grpcurl command examples."""
    print("💻 grpcurl Command Examples:")
    print("=" * 50)
    
    examples = [
        ("List all services", "grpcurl -plaintext localhost:50051 list"),
        ("List AIFS methods", "grpcurl -plaintext localhost:50051 list aifs.v1.AIFS"),
        ("Describe AIFS service", "grpcurl -plaintext localhost:50051 describe aifs.v1.AIFS"),
        ("Health check", "grpcurl -plaintext localhost:50051 aifs.v1.Health/Check"),
        ("List assets", "grpcurl -plaintext -d '{\"limit\": 10}' localhost:50051 aifs.v1.AIFS/ListAssets"),
        ("Get asset", "grpcurl -plaintext -d '{\"asset_id\": \"your_asset_id\"}' localhost:50051 aifs.v1.AIFS/GetAsset"),
        ("List namespaces", "grpcurl -plaintext -d '{\"limit\": 10}' localhost:50051 aifs.v1.AIFS/ListNamespaces"),
    ]
    
    for description, command in examples:
        print(f"📝 {description}:")
        print(f"   {command}")
        print()

def show_proto_structure():
    """Show the proto file structure."""
    print("📋 Protocol Buffer Structure:")
    print("=" * 50)
    
    print("Services:")
    print("├── AIFS (Main service)")
    print("│   ├── PutAsset (stream PutAssetRequest) → PutAssetResponse")
    print("│   ├── GetAsset (GetAssetRequest) → GetAssetResponse")
    print("│   ├── DeleteAsset (DeleteAssetRequest) → DeleteAssetResponse")
    print("│   ├── ListAssets (ListAssetsRequest) → ListAssetsResponse")
    print("│   ├── VectorSearch (VectorSearchRequest) → VectorSearchResponse")
    print("│   ├── CreateSnapshot (CreateSnapshotRequest) → CreateSnapshotResponse")
    print("│   ├── GetSnapshot (GetSnapshotRequest) → GetSnapshotResponse")
    print("│   ├── SubscribeEvents (SubscribeEventsRequest) → stream SubscribeEventsResponse")
    print("│   ├── ListNamespaces (ListNamespacesRequest) → ListNamespacesResponse")
    print("│   ├── GetNamespace (GetNamespaceRequest) → GetNamespaceResponse")
    print("│   ├── VerifyAsset (VerifyAssetRequest) → VerifyAssetResponse")
    print("│   └── VerifySnapshot (VerifySnapshotRequest) → VerifySnapshotResponse")
    print("├── Health")
    print("│   └── Check (HealthCheckRequest) → HealthCheckResponse")
    print("├── Introspect")
    print("│   └── GetInfo (IntrospectRequest) → IntrospectResponse")
    print("├── Admin")
    print("│   ├── CreateNamespace (CreateNamespaceRequest) → CreateNamespaceResponse")
    print("│   ├── PruneSnapshot (PruneSnapshotRequest) → PruneSnapshotResponse")
    print("│   └── ManagePolicy (ManagePolicyRequest) → ManagePolicyResponse")
    print("├── Metrics")
    print("│   └── GetMetrics (MetricsRequest) → MetricsResponse")
    print("└── Format")
    print("    └── FormatStorage (FormatRequest) → FormatResponse")
    print()

def show_authentication_info():
    """Show authentication information."""
    print("🔐 Authentication Information:")
    print("=" * 50)
    print("The AIFS server uses token-based authentication.")
    print("Include the following header in your requests:")
    print()
    print("Authorization: Bearer <your_token>")
    print()
    print("Required permissions:")
    print("├── 'put' - For PutAsset")
    print("├── 'get' - For GetAsset, GetSnapshot, GetNamespace, VerifyAsset, VerifySnapshot")
    print("├── 'delete' - For DeleteAsset")
    print("├── 'list' - For ListAssets, ListNamespaces")
    print("├── 'search' - For VectorSearch")
    print("├── 'subscribe' - For SubscribeEvents")
    print("├── 'snapshot' - For CreateSnapshot")
    print("└── 'admin' - For Admin operations")
    print()

def main():
    """Main function."""
    print("🚀 AIFS gRPC API Explorer")
    print("=" * 50)
    print()
    
    list_services()
    list_aifs_methods()
    show_grpcurl_examples()
    show_proto_structure()
    show_authentication_info()
    
    print("🎉 Ready to explore your AIFS gRPC API!")
    print()
    print("Next steps:")
    print("1. Start the server: python start_server.py")
    print("2. Use grpcurl to explore: grpcurl -plaintext localhost:50051 list")
    print("3. Or use the web interface: python grpc_web_interface.py")
    print("4. Or use Postman/BloomRPC for a GUI experience")

if __name__ == "__main__":
    main()
