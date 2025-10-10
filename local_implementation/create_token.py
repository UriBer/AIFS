#!/usr/bin/env python3
"""Create AIFS authentication tokens."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aifs.auth import create_aifs_token, create_namespace_token

def main():
    print("🔐 AIFS Authentication Token Generator")
    print("=" * 50)
    
    # Create different types of tokens
    print("\n1. Full Access Token (all permissions):")
    full_token = create_aifs_token(
        permissions=["put", "get", "search", "snapshot", "branch", "tag", "admin"],
        namespace=None,  # No namespace restriction
        expiry_hours=24
    )
    print(f"Token: {full_token}")
    
    print("\n2. Read-Only Token:")
    read_token = create_aifs_token(
        permissions=["get", "search"],
        namespace="default",
        expiry_hours=12
    )
    print(f"Token: {read_token}")
    
    print("\n3. Namespace-Specific Token:")
    ns_token = create_namespace_token(
        namespace="my-namespace",
        methods=["put", "get", "search"],
        expiry_hours=8
    )
    print(f"Token: {ns_token}")
    
    print("\n4. Admin Token (all permissions, no expiry):")
    admin_token = create_aifs_token(
        permissions=["put", "get", "search", "snapshot", "branch", "tag", "admin"],
        namespace=None,
        expiry_hours=8760  # 1 year
    )
    print(f"Token: {admin_token}")
    
    print("\n" + "=" * 50)
    print("✅ Tokens created successfully!")
    print("\nUsage examples:")
    print("grpcurl -plaintext -H 'authorization: Bearer <token>' localhost:50052 aifs.v1.AIFS/ListAssets")

if __name__ == "__main__":
    main()
