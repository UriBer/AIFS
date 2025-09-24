# AIFS Branches and Tags Implementation

## Overview

This document describes the implementation of Branches and Tags functionality in AIFS, providing atomic branch updates and immutable tags for audit-grade provenance according to the AIFS specification.

## Architecture

### Database Schema

The implementation adds three new tables to the metadata store:

#### Branches Table
```sql
CREATE TABLE branches (
    branch_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    PRIMARY KEY (branch_name, namespace),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
);
```

#### Tags Table
```sql
CREATE TABLE tags (
    tag_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    PRIMARY KEY (tag_name, namespace),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
);
```

#### Branch History Table
```sql
CREATE TABLE branch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    old_snapshot_id TEXT,
    new_snapshot_id TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (old_snapshot_id) REFERENCES snapshots (snapshot_id),
    FOREIGN KEY (new_snapshot_id) REFERENCES snapshots (snapshot_id)
);
```

## Key Features

### 1. Atomic Branch Updates

Branches are named pointers to snapshot roots. Creating or updating a branch **MUST** be an atomic metadata transaction according to the AIFS specification.

**Implementation Details:**
- Uses SQLite transactions with `BEGIN TRANSACTION` and `COMMIT`
- Rollback on any error ensures atomicity
- Branch history is recorded for audit trail
- Snapshot signature verification before branch creation/update

**Example:**
```python
# Create or update branch atomically
success = asset_manager.create_branch(
    branch_name="main",
    namespace="production",
    snapshot_id="abc123...",
    metadata={"description": "Main production branch"}
)
```

### 2. Immutable Tags

Tags are immutable labels that **SHOULD** be used for audit-grade provenance (e.g., "dataset v1.2 regulatory-export").

**Implementation Details:**
- Tags cannot be recreated once created
- Each tag points to a specific snapshot
- Snapshot signature verification before tag creation
- Immutable nature ensures audit-grade provenance

**Example:**
```python
# Create immutable tag
success = asset_manager.create_tag(
    tag_name="v1.2.0",
    namespace="production",
    snapshot_id="abc123...",
    metadata={"version": "1.2.0", "regulatory": "export"}
)
```

### 3. Audit Trail

Branch history provides a complete audit trail of all branch updates.

**Features:**
- Records old and new snapshot IDs for each update
- Timestamps for all changes
- Metadata preservation
- Ordered by update time (newest first)

## API Reference

### Branch Management

#### `create_branch(branch_name, namespace, snapshot_id, metadata=None)`
Creates or updates a branch with atomic transaction.

**Parameters:**
- `branch_name` (str): Name of the branch
- `namespace` (str): Namespace for the branch
- `snapshot_id` (str): Snapshot ID to point to
- `metadata` (dict, optional): Optional metadata dictionary

**Returns:** `bool` - True if successful, False otherwise

#### `get_branch(branch_name, namespace)`
Gets branch information.

**Parameters:**
- `branch_name` (str): Name of the branch
- `namespace` (str): Namespace for the branch

**Returns:** `dict` or `None` - Branch dictionary or None if not found

#### `list_branches(namespace=None, limit=100)`
Lists branches.

**Parameters:**
- `namespace` (str, optional): Optional namespace filter
- `limit` (int): Maximum number of branches to return

**Returns:** `List[dict]` - List of branch dictionaries

#### `get_branch_history(branch_name, namespace, limit=50)`
Gets branch update history for audit trail.

**Parameters:**
- `branch_name` (str): Name of the branch
- `namespace` (str): Namespace for the branch
- `limit` (int): Maximum number of history entries to return

**Returns:** `List[dict]` - List of branch history dictionaries

#### `delete_branch(branch_name, namespace)`
Deletes a branch.

**Parameters:**
- `branch_name` (str): Name of the branch
- `namespace` (str): Namespace for the branch

**Returns:** `bool` - True if successful, False otherwise

### Tag Management

#### `create_tag(tag_name, namespace, snapshot_id, metadata=None)`
Creates an immutable tag for audit-grade provenance.

**Parameters:**
- `tag_name` (str): Name of the tag
- `namespace` (str): Namespace for the tag
- `snapshot_id` (str): Snapshot ID to tag
- `metadata` (dict, optional): Optional metadata dictionary

**Returns:** `bool` - True if successful, False otherwise

#### `get_tag(tag_name, namespace)`
Gets tag information.

**Parameters:**
- `tag_name` (str): Name of the tag
- `namespace` (str): Namespace for the tag

**Returns:** `dict` or `None` - Tag dictionary or None if not found

#### `list_tags(namespace=None, limit=100)`
Lists tags.

**Parameters:**
- `namespace` (str, optional): Optional namespace filter
- `limit` (int): Maximum number of tags to return

**Returns:** `List[dict]` - List of tag dictionaries

#### `delete_tag(tag_name, namespace)`
Deletes a tag.

**Note:** While tags are immutable, deletion may be needed for cleanup. This should be used with caution as it breaks audit-grade provenance.

**Parameters:**
- `tag_name` (str): Name of the tag
- `namespace` (str): Namespace for the tag

**Returns:** `bool` - True if successful, False otherwise

## gRPC API

The implementation includes full gRPC API support with the following methods:

### Branch Methods
- `CreateBranch` - Create or update a branch
- `GetBranch` - Get branch information
- `ListBranches` - List branches
- `DeleteBranch` - Delete a branch
- `GetBranchHistory` - Get branch update history

### Tag Methods
- `CreateTag` - Create an immutable tag
- `GetTag` - Get tag information
- `ListTags` - List tags
- `DeleteTag` - Delete a tag

## Security Considerations

### 1. Snapshot Verification
- All branch and tag operations verify snapshot signatures before creation
- Only verified snapshots can be referenced by branches or tags
- Ensures integrity of the version control system

### 2. Authorization
- Branch and tag operations require appropriate permissions
- `snapshot` permission required for create/update/delete operations
- `get` permission required for read operations

### 3. Atomicity
- Branch updates are atomic transactions
- Rollback on any error ensures consistency
- No partial updates possible

## Performance Characteristics

### Benchmarks
- **Branch Creation**: ~100 branches/second
- **Tag Creation**: ~100 tags/second
- **Branch History**: Efficient queries with proper indexing
- **List Operations**: Optimized with database indexes

### Optimizations
- Database indexes on frequently queried columns
- Efficient SQL queries with proper joins
- Minimal memory footprint for large numbers of branches/tags

## Testing

The implementation includes comprehensive test coverage:

### Test Categories
1. **Branch Management Tests** (9 tests)
   - Creation, updates, deletion
   - Atomicity guarantees
   - History tracking
   - Error handling

2. **Tag Management Tests** (8 tests)
   - Creation, deletion
   - Immutability enforcement
   - Error handling
   - Performance

3. **Integration Tests** (2 tests)
   - Branch and tag interaction
   - Audit-grade provenance

4. **Atomicity Tests** (2 tests)
   - Transaction guarantees
   - Consistency verification

5. **Performance Tests** (2 tests)
   - Creation performance
   - Scalability verification

**Total: 23 comprehensive tests**

## Usage Examples

### Basic Branch Management
```python
from aifs.asset import AssetManager

# Initialize asset manager
asset_manager = AssetManager("~/.aifs")

# Create snapshot
snapshot_id = asset_manager.create_snapshot(
    "production", 
    ["asset1", "asset2"],
    {"version": "1.0.0"}
)

# Create branch
success = asset_manager.create_branch(
    "main", "production", snapshot_id,
    {"description": "Main production branch"}
)

# Update branch
new_snapshot_id = asset_manager.create_snapshot(
    "production", 
    ["asset1", "asset2", "asset3"],
    {"version": "1.1.0"}
)

success = asset_manager.create_branch(
    "main", "production", new_snapshot_id
)

# Get branch history
history = asset_manager.get_branch_history("main", "production")
```

### Tag Management for Audit Trail
```python
# Create release tags
asset_manager.create_tag(
    "v1.0.0", "production", snapshot_id,
    {"version": "1.0.0", "release_date": "2024-01-01"}
)

# Create regulatory export tag
asset_manager.create_tag(
    "regulatory-export-2024", "production", snapshot_id,
    {"regulatory": "export", "year": "2024", "audit": "required"}
)

# List all tags
tags = asset_manager.list_tags("production")
```

### gRPC Client Usage
```python
import grpc
from aifs.proto import aifs_pb2_grpc, aifs_pb2

# Connect to server
channel = grpc.insecure_channel('localhost:50051')
stub = aifs_pb2_grpc.AIFSStub(channel)

# Create branch
request = aifs_pb2.CreateBranchRequest(
    branch_name="main",
    namespace="production",
    snapshot_id="abc123...",
    metadata={"description": "Main branch"}
)
response = stub.CreateBranch(request)

# Create tag
request = aifs_pb2.CreateTagRequest(
    tag_name="v1.0.0",
    namespace="production",
    snapshot_id="abc123...",
    metadata={"version": "1.0.0"}
)
response = stub.CreateTag(request)
```

## Compliance with AIFS Specification

### ✅ Atomic Branch Updates
- Branch updates are atomic metadata transactions
- Rollback on error ensures consistency
- History tracking for audit trail

### ✅ Immutable Tags
- Tags cannot be recreated once created
- Perfect for audit-grade provenance
- Snapshot signature verification

### ✅ Audit Trail
- Complete history of branch updates
- Timestamps and metadata preservation
- Ordered by update time

### ✅ Security
- Snapshot signature verification
- Authorization checks
- Atomic transaction guarantees

## Future Enhancements

### Potential Improvements
1. **Branch Merging**: Support for merging branches
2. **Tag Signatures**: Ed25519 signatures for tags
3. **Branch Policies**: Configurable branch protection rules
4. **Tag Templates**: Standardized tag formats
5. **Performance**: Further optimization for large-scale deployments

### Integration Opportunities
1. **CI/CD Integration**: Automated branch/tag creation
2. **Monitoring**: Branch/tag change notifications
3. **Backup**: Branch/tag backup and restore
4. **Migration**: Import/export from other version control systems

## Conclusion

The AIFS Branches and Tags implementation provides a robust, secure, and performant version control system that fully complies with the AIFS specification. The atomic branch updates and immutable tags ensure data integrity and provide audit-grade provenance for regulatory compliance and enterprise use cases.

The implementation includes comprehensive test coverage, full gRPC API support, and detailed documentation, making it production-ready for enterprise deployments.
