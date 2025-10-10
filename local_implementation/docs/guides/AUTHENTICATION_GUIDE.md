# AIFS Authentication Guide

## 🔐 **Authentication System Overview**

AIFS implements a **Macaroon-based authorization system** with capability tokens that provide fine-grained access control.

### **Key Features:**
- ✅ **Capability-based**: Tokens specify exactly what operations are allowed
- ✅ **Namespace-restricted**: Tokens can be limited to specific namespaces
- ✅ **Time-limited**: Tokens have configurable expiration times
- ✅ **Method-specific**: Tokens can allow only specific operations
- ✅ **Secure**: Uses cryptographic signatures to prevent tampering

## 🚀 **Quick Start**

### **1. Check Authentication Status**
```bash
# This will fail with "Authorization token required"
grpcurl -plaintext localhost:50052 aifs.v1.AIFS/ListAssets
```

### **2. Create a Token**
```python
from aifs.auth import create_aifs_token

# Create a read-only token for the 'default' namespace
token = create_aifs_token(
    permissions=["get", "search"],
    namespace="default",
    expiry_hours=24
)
print(token)
```

### **3. Use Token in API Calls**
```bash
# Use the token in gRPC calls
grpcurl -plaintext \
  -H "authorization: Bearer <your-token>" \
  localhost:50052 aifs.v1.AIFS/ListAssets
```

## 📋 **Available Permissions**

| Permission | Description | Operations |
|------------|-------------|------------|
| `put` | Store assets | `PutAsset` |
| `get` | Retrieve assets | `GetAsset`, `ListAssets` |
| `search` | Vector search | `VectorSearch` |
| `snapshot` | Snapshot management | `CreateSnapshot`, `GetSnapshot`, `VerifySnapshot` |
| `branch` | Branch management | `CreateBranch`, `GetBranch`, `ListBranches`, `DeleteBranch` |
| `tag` | Tag management | `CreateTag`, `GetTag`, `ListTags`, `DeleteTag` |
| `admin` | Administrative operations | All operations |

## 🔧 **Token Types**

### **1. Full Access Token**
```python
from aifs.auth import create_aifs_token

# All permissions, no namespace restriction
token = create_aifs_token(
    permissions=["put", "get", "search", "snapshot", "branch", "tag", "admin"],
    namespace=None,
    expiry_hours=24
)
```

### **2. Read-Only Token**
```python
# Only read operations
token = create_aifs_token(
    permissions=["get", "search"],
    namespace="default",
    expiry_hours=12
)
```

### **3. Namespace-Specific Token**
```python
from aifs.auth import create_namespace_token

# Limited to specific namespace
token = create_namespace_token(
    namespace="my-namespace",
    methods=["put", "get", "search"],
    expiry_hours=8
)
```

### **4. Short-Lived Token**
```python
# Expires in 1 hour
token = create_aifs_token(
    permissions=["get"],
    namespace="default",
    expiry_hours=1
)
```

## 🌐 **Using Tokens with gRPC**

### **Method 1: Direct gRPC Calls**
```bash
# Create token
TOKEN=$(python -c "
from aifs.auth import create_aifs_token
import json
token = create_aifs_token(['get', 'search'], 'default', 1)
print(json.dumps(token))
")

# Use token
grpcurl -plaintext \
  -H "authorization: Bearer $TOKEN" \
  localhost:50052 aifs.v1.AIFS/ListAssets
```

### **Method 2: Using grpcurl with Base64 Encoding**
```bash
# Create and encode token
python -c "
from aifs.auth import create_aifs_token
import json
import base64
token = create_aifs_token(['get', 'search'], 'default', 1)
token_json = json.dumps(token)
token_b64 = base64.b64encode(token_json.encode()).decode()
print(f'Bearer {token_b64}')
"
```

### **Method 3: Using Python Client**
```python
import grpc
from aifs.proto import aifs_pb2, aifs_pb2_grpc
from aifs.auth import create_aifs_token

# Create token
token = create_aifs_token(["get", "search"], "default", 1)

# Create channel with authentication
channel = grpc.insecure_channel('localhost:50052')
metadata = [('authorization', f'Bearer {token}')]

# Create stub and make calls
stub = aifs_pb2_grpc.AIFSStub(channel)
response = stub.ListAssets(
    aifs_pb2.ListAssetsRequest(namespace="default"),
    metadata=metadata
)
```

## 🔒 **Security Features**

### **1. Token Validation**
- Tokens are cryptographically signed
- Tampering is detected and rejected
- Expired tokens are automatically rejected

### **2. Capability Restrictions**
- Tokens specify exactly what operations are allowed
- Namespace restrictions prevent cross-namespace access
- Method restrictions limit available operations

### **3. Time-based Expiration**
- Tokens have configurable expiration times
- Expired tokens are automatically rejected
- No way to extend expired tokens (must create new ones)

## 📊 **Token Structure**

AIFS tokens are JSON objects with the following structure:

```json
{
  "location": "aifs.local",
  "identifier": "aifs_token",
  "caveats": [
    ["first_party", "namespace = default"],
    ["first_party", "method = get"],
    ["first_party", "method = search"],
    ["first_party", "expires = 1760079573"]
  ],
  "signature": "3c6a861c287769a246f0cbc9e0187e7fd1e15df7423da6e7bd1424ad6c7ec3eb"
}
```

### **Fields:**
- **location**: Where the token was created
- **identifier**: Token type identifier
- **caveats**: List of restrictions (namespace, methods, expiry)
- **signature**: Cryptographic signature for validation

## 🛠️ **Practical Examples**

### **Example 1: Basic Asset Operations**
```python
from aifs.auth import create_aifs_token

# Create token for basic asset operations
token = create_aifs_token(
    permissions=["put", "get", "search"],
    namespace="default",
    expiry_hours=24
)

# Use with gRPC
import grpc
from aifs.proto import aifs_pb2, aifs_pb2_grpc

channel = grpc.insecure_channel('localhost:50052')
metadata = [('authorization', f'Bearer {token}')]
stub = aifs_pb2_grpc.AIFSStub(channel)

# List assets
response = stub.ListAssets(
    aifs_pb2.ListAssetsRequest(namespace="default"),
    metadata=metadata
)
```

### **Example 2: Snapshot Management**
```python
# Create token for snapshot operations
token = create_aifs_token(
    permissions=["get", "snapshot"],
    namespace="default",
    expiry_hours=12
)

# Create snapshot
response = stub.CreateSnapshot(
    aifs_pb2.CreateSnapshotRequest(
        namespace="default",
        description="My snapshot"
    ),
    metadata=[('authorization', f'Bearer {token}')]
)
```

### **Example 3: Admin Operations**
```python
# Create admin token
token = create_aifs_token(
    permissions=["admin"],
    namespace=None,  # No namespace restriction
    expiry_hours=1
)

# Admin operations
response = stub.ListNamespaces(
    aifs_pb2.ListNamespacesRequest(),
    metadata=[('authorization', f'Bearer {token}')]
)
```

## 🚨 **Error Handling**

### **Common Authentication Errors:**

1. **"Authorization token required"**
   - No token provided
   - Solution: Create and provide a token

2. **"Invalid token signature"**
   - Token has been tampered with
   - Solution: Create a new token

3. **"Token expired"**
   - Token has passed its expiration time
   - Solution: Create a new token

4. **"Insufficient permissions"**
   - Token doesn't have required permissions
   - Solution: Create token with required permissions

5. **"Namespace not allowed"**
   - Token is restricted to different namespace
   - Solution: Create token for correct namespace

## 🔧 **Troubleshooting**

### **1. Token Not Working**
```python
# Check token validity
from aifs.auth import verify_aifs_token

is_valid = verify_aifs_token(
    token_data=token,
    required_permissions={"get"},
    namespace="default"
)
print(f"Token valid: {is_valid}")
```

### **2. Permission Denied**
```python
# Check what permissions token has
from aifs.auth import get_macaroon_info

info = get_macaroon_info(token)
print(f"Token info: {info}")
```

### **3. Token Expired**
```python
# Create new token with longer expiry
token = create_aifs_token(
    permissions=["get", "search"],
    namespace="default",
    expiry_hours=24  # Longer expiry
)
```

## 📚 **Best Practices**

1. **Use minimal permissions**: Only grant necessary permissions
2. **Set appropriate expiry**: Don't create tokens that last too long
3. **Namespace isolation**: Use namespace-specific tokens when possible
4. **Rotate tokens regularly**: Create new tokens periodically
5. **Monitor token usage**: Keep track of token creation and usage

## 🆘 **Support**

For authentication issues:
1. Check token format and encoding
2. Verify permissions match required operations
3. Ensure namespace restrictions are correct
4. Check token expiration time
5. Verify server is running and accessible

## 📖 **Additional Resources**

- [API Reference](../api/API_REFERENCE.md)
- [CLI Usage Guide](CLI_USAGE.md)
- [Docker Usage Guide](../docker/DOCKER_USAGE.md)
- [Main Documentation](../../README.md)
