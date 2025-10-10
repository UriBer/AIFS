#!/usr/bin/env python3
"""Test AIFS authentication."""

import sys
import os
import json
import base64
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aifs.auth import create_aifs_token

def main():
    print("🔐 Testing AIFS Authentication")
    print("=" * 40)
    
    # Create a simple read-only token
    token = create_aifs_token(
        permissions=["get", "search"],
        namespace="default",
        expiry_hours=1
    )
    
    print(f"Token: {token}")
    
    # Encode token for HTTP header
    token_json = json.dumps(token)
    token_b64 = base64.b64encode(token_json.encode()).decode()
    
    print(f"\nBase64 Encoded Token:")
    print(f"Bearer {token_b64}")
    
    print(f"\ngRPC Command:")
    print(f"grpcurl -plaintext \\")
    print(f"  -H 'authorization: Bearer {token_b64}' \\")
    print(f"  localhost:50052 aifs.v1.AIFS/ListAssets \\")
    print(f"  -d '{{\"namespace\": \"default\"}}'")

if __name__ == "__main__":
    main()