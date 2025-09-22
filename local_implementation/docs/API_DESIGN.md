# AIFS Client App - API Design & Data Models

## 🔌 **API Architecture Overview**

### Base URL Structure
```
Production: https://api.aifs-client.com/v1
Development: http://localhost:8000/v1
```

### Authentication
- **API Key**: `Authorization: Bearer <api_key>`
- **Session**: `Cookie: session_id=<session_id>`

## 📊 **Data Models**

### Cloud Integration Models

#### CloudProvider
```typescript
interface CloudProvider {
  id: string;
  name: string;
  type: 'aws_s3' | 'gcs' | 'azure' | 'digitalocean' | 'minio';
  credentials: {
    access_key: string;
    secret_key: string;
    region?: string;
    endpoint?: string;
  };
  created_at: string;
  updated_at: string;
  status: 'active' | 'inactive' | 'error';
}
```

#### CloudBucket
```typescript
interface CloudBucket {
  name: string;
  provider_id: string;
  region: string;
  created_at: string;
  size: number;
  object_count: number;
  permissions: {
    read: boolean;
    write: boolean;
    delete: boolean;
  };
}
```

#### CloudOperation
```typescript
interface CloudOperation {
  id: string;
  type: 'copy' | 'move' | 'upload' | 'download' | 'delete' | 'sync';
  status: 'queued' | 'running' | 'completed' | 'failed';
  source?: {
    provider_id: string;
    bucket: string;
    key: string;
  };
  destination?: {
    provider_id: string;
    bucket: string;
    key: string;
  };
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  created_at: string;
  completed_at?: string;
  error?: string;
}
```

### 1. Asset Model
```python
class Asset(BaseModel):
    id: str
    name: str
    type: str  # file, folder, collection
    mime_type: str
    size: int
    content_hash: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]]
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str]
    parents: List[AssetRelationship]
    children: List[AssetRelationship]
    permissions: AssetPermissions

class AssetRelationship(BaseModel):
    id: str
    parent_id: str
    child_id: str
    relationship_type: str  # derived, transformed, contains
    transform_name: Optional[str]
    transform_digest: Optional[str]
    created_at: datetime
    metadata: Dict[str, Any]

class AssetPermissions(BaseModel):
    read: List[str]  # user_ids
    write: List[str]
    admin: List[str]
    public: bool
```

### 2. Search Models
```python
class SearchQuery(BaseModel):
    query: str
    filters: Optional[SearchFilters]
    sort: Optional[SearchSort]
    pagination: Optional[Pagination]
    include_embeddings: bool = False

class SearchFilters(BaseModel):
    asset_types: Optional[List[str]]
    mime_types: Optional[List[str]]
    tags: Optional[List[str]]
    date_range: Optional[DateRange]
    size_range: Optional[SizeRange]
    created_by: Optional[List[str]]
    has_embeddings: Optional[bool]

class SearchResult(BaseModel):
    asset: Asset
    relevance_score: float
    matched_fields: List[str]
    snippet: Optional[str]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    page: int
    per_page: int
    query_time: float
    suggestions: List[str]
```

### 3. RAG Models
```python
class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message]
    context_assets: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str
    settings: RAGSettings

class Message(BaseModel):
    id: str
    role: str  # user, assistant, system
    content: str
    sources: List[Source]
    created_at: datetime
    metadata: Dict[str, Any]

class Source(BaseModel):
    asset_id: str
    asset_name: str
    relevance_score: float
    snippet: str
    page_number: Optional[int]
    chunk_index: Optional[int]

class RAGSettings(BaseModel):
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.7
    max_tokens: int = 4000
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_context_chunks: int = 10
```

### 4. Lineage Models
```python
class LineageNode(BaseModel):
    asset: Asset
    level: int
    position: Tuple[int, int]
    connections: List[str]  # connected node IDs

class LineageGraph(BaseModel):
    nodes: List[LineageNode]
    edges: List[LineageEdge]
    layout: str  # force, hierarchical, circular
    metadata: Dict[str, Any]

class LineageEdge(BaseModel):
    source: str
    target: str
    relationship: AssetRelationship
    weight: float
    style: Dict[str, Any]
```

## 🛠️ **REST API Endpoints**

### 1. Asset Management

#### List Assets
```http
GET /assets
Query Parameters:
  - page: int = 1
  - per_page: int = 20
  - sort: str = "created_at"
  - order: str = "desc"
  - type: str (optional)
  - tags: List[str] (optional)
  - search: str (optional)

Response: 200 OK
{
  "assets": [Asset],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

#### Get Asset
```http
GET /assets/{asset_id}
Response: 200 OK
{
  "asset": Asset,
  "lineage": {
    "parents": [AssetRelationship],
    "children": [AssetRelationship]
  }
}
```

#### Upload Asset
```http
POST /assets
Content-Type: multipart/form-data

Form Data:
  - file: File
  - name: str (optional)
  - metadata: JSON (optional)
  - tags: List[str] (optional)
  - parents: List[str] (optional)
  - generate_embedding: bool = true

Response: 201 Created
{
  "asset": Asset,
  "upload_id": str,
  "processing_status": str
}
```

#### Update Asset
```http
PUT /assets/{asset_id}
Body: {
  "name": str (optional),
  "metadata": Dict (optional),
  "tags": List[str] (optional)
}

Response: 200 OK
{
  "asset": Asset
}
```

#### Delete Asset
```http
DELETE /assets/{asset_id}
Response: 204 No Content
```

#### Create Folder
```http
POST /assets/folders
Body: {
  "name": str,
  "parent_folder_id": str (optional),
  "tags": List[str] (optional),
  "metadata": Dict (optional)
}

Response: 201 Created
{
  "folder": Asset
}
```

#### Get Folder Contents
```http
GET /assets/folders/{folder_id}/contents
Query Parameters:
  - page: int = 1
  - per_page: int = 20
  - sort: str = "name"
  - order: str = "asc"
  - include_subfolders: bool = false

Response: 200 OK
{
  "contents": [Asset],
  "pagination": Pagination,
  "folder_info": {
    "id": str,
    "name": str,
    "total_items": int,
    "total_size": int
  }
}
```

#### Get Assets by Tags
```http
GET /assets/by-tags
Query Parameters:
  - tags: List[str] (comma-separated)
  - match_all: bool = false
  - page: int = 1
  - per_page: int = 20

Response: 200 OK
{
  "assets": [Asset],
  "pagination": Pagination,
  "matched_tags": [str]
}
```

#### Download Asset
```http
GET /assets/{asset_id}/download
Response: 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="asset_name"
```

### 2. Cloud Integration

#### Cloud Provider Management
```http
POST /cloud/providers
Body: {
  "name": str,
  "type": "aws_s3" | "gcs" | "azure" | "digitalocean" | "minio",
  "credentials": {
    "access_key": str,
    "secret_key": str,
    "region": str (optional),
    "endpoint": str (optional)
  }
}

Response: 201 Created
{
  "provider": CloudProvider
}
```

#### List Cloud Buckets
```http
GET /cloud/providers/{provider_id}/buckets
Response: 200 OK
{
  "buckets": [CloudBucket]
}
```

#### Cloud File Operations
```http
POST /cloud/operations/copy
Body: {
  "source": {
    "provider_id": str,
    "bucket": str,
    "key": str
  },
  "destination": {
    "provider_id": str,
    "bucket": str,
    "key": str
  }
}

Response: 202 Accepted
{
  "operation_id": str,
  "status": "queued"
}
```

#### Upload to Cloud
```http
POST /cloud/upload
Body: FormData with file
Query Parameters:
  - provider_id: str
  - bucket: str
  - key: str (optional)

Response: 200 OK
{
  "url": str,
  "bucket": str,
  "key": str,
  "size": int
}
```

#### Download from Cloud
```http
GET /cloud/download/{provider_id}/{bucket}/{key}
Response: 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="file_name"
```

#### Sync with AIFS
```http
POST /cloud/sync/aifs
Body: {
  "provider_id": str,
  "bucket": str,
  "prefix": str (optional),
  "aifs_folder": str (optional)
}

Response: 202 Accepted
{
  "sync_id": str,
  "status": "started"
}
```

### 3. Search & Discovery

#### Search Assets
```http
POST /search
Body: SearchQuery

Response: 200 OK
{
  "results": [SearchResult],
  "total": int,
  "page": int,
  "per_page": int,
  "query_time": float,
  "suggestions": [str],
  "facets": {
    "folders": [{"name": str, "count": int}],
    "tags": [{"name": str, "count": int}],
    "file_types": [{"type": str, "count": int}]
  }
}
```

#### Get Search Suggestions
```http
GET /search/suggestions?q={query}
Response: 200 OK
{
  "suggestions": [str],
  "categories": {
    "assets": [str],
    "tags": [str],
    "content": [str]
  }
}
```

#### Save Search Query
```http
POST /search/saved
Body: {
  "name": str,
  "query": SearchQuery,
  "is_public": bool = false
}

Response: 201 Created
{
  "saved_search": {
    "id": str,
    "name": str,
    "query": SearchQuery,
    "created_at": datetime
  }
}
```

### 3. Lineage Management

#### Get Asset Lineage
```http
GET /assets/{asset_id}/lineage
Query Parameters:
  - depth: int = 3
  - direction: str = "both"  # up, down, both
  - include_metadata: bool = false

Response: 200 OK
{
  "lineage": LineageGraph
}
```

#### Create Relationship
```http
POST /lineage/relationships
Body: {
  "parent_id": str,
  "child_id": str,
  "relationship_type": str,
  "transform_name": str (optional),
  "transform_digest": str (optional),
  "metadata": Dict (optional)
}

Response: 201 Created
{
  "relationship": AssetRelationship
}
```

#### Delete Relationship
```http
DELETE /lineage/relationships/{relationship_id}
Response: 204 No Content
```

### 4. RAG Operations

#### Create Conversation
```http
POST /rag/conversations
Body: {
  "title": str,
  "context_assets": List[str] (optional),
  "settings": RAGSettings (optional)
}

Response: 201 Created
{
  "conversation": Conversation
}
```

#### Send Message
```http
POST /rag/conversations/{conversation_id}/messages
Body: {
  "content": str,
  "context_assets": List[str] (optional)
}

Response: 200 OK
{
  "message": Message,
  "response": Message,
  "sources": [Source]
}
```

#### Get Conversation
```http
GET /rag/conversations/{conversation_id}
Response: 200 OK
{
  "conversation": Conversation
}
```

#### List Conversations
```http
GET /rag/conversations
Query Parameters:
  - page: int = 1
  - per_page: int = 20
  - search: str (optional)

Response: 200 OK
{
  "conversations": [Conversation],
  "pagination": Pagination
}
```

#### Process Document for RAG
```http
POST /rag/process
Body: {
  "asset_id": str,
  "chunk_size": int (optional),
  "chunk_overlap": int (optional),
  "force_reprocess": bool = false
}

Response: 200 OK
{
  "processing_id": str,
  "status": str,
  "chunks_created": int
}
```

### 5. File Operations

#### Batch Upload
```http
POST /assets/batch
Content-Type: multipart/form-data

Form Data:
  - files: List[File]
  - metadata: JSON (optional)
  - tags: List[str] (optional)
  - generate_embeddings: bool = true

Response: 200 OK
{
  "upload_id": str,
  "assets": [Asset],
  "processing_status": str
}
```

#### Get Upload Status
```http
GET /uploads/{upload_id}/status
Response: 200 OK
{
  "upload_id": str,
  "status": str,  # pending, processing, completed, failed
  "progress": float,  # 0.0 to 1.0
  "assets": [Asset],
  "errors": [str]
}
```

#### Export Assets
```http
POST /assets/export
Body: {
  "asset_ids": List[str],
  "format": str,  # zip, tar, individual
  "include_metadata": bool = true
}

Response: 200 OK
{
  "export_id": str,
  "download_url": str,
  "expires_at": datetime
}
```

## 🔄 **WebSocket Events**

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'authenticate',
    token: 'your_api_key'
  }));
};
```

### Event Types

#### Asset Events
```javascript
// Asset created
{
  "type": "asset_created",
  "data": {
    "asset": Asset,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}

// Asset updated
{
  "type": "asset_updated",
  "data": {
    "asset": Asset,
    "changes": ["name", "metadata"],
    "timestamp": "2024-01-15T10:35:00Z"
  }
}

// Asset deleted
{
  "type": "asset_deleted",
  "data": {
    "asset_id": "string",
    "timestamp": "2024-01-15T10:40:00Z"
  }
}
```

#### Upload Progress
```javascript
{
  "type": "upload_progress",
  "data": {
    "upload_id": "string",
    "progress": 0.75,
    "status": "processing",
    "current_file": "document.pdf",
    "files_processed": 3,
    "total_files": 5
  }
}
```

#### Search Results
```javascript
{
  "type": "search_results",
  "data": {
    "query_id": "string",
    "results": [SearchResult],
    "total": 100,
    "page": 1
  }
}
```

#### RAG Response
```javascript
{
  "type": "rag_response",
  "data": {
    "conversation_id": "string",
    "message_id": "string",
    "response": Message,
    "sources": [Source],
    "status": "completed"
  }
}
```

## 📊 **Error Handling**

### Error Response Format
```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Asset with ID 'abc123' not found",
    "details": {
      "asset_id": "abc123",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  }
}
```

### Error Codes
- `ASSET_NOT_FOUND`: Asset doesn't exist
- `ASSET_ACCESS_DENIED`: Insufficient permissions
- `INVALID_FILE_TYPE`: Unsupported file type
- `FILE_TOO_LARGE`: File exceeds size limit
- `UPLOAD_FAILED`: File upload failed
- `SEARCH_ERROR`: Search operation failed
- `RAG_ERROR`: RAG operation failed
- `AUTHENTICATION_FAILED`: Invalid API key
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `SERVER_ERROR`: Internal server error

## 🔒 **Security Considerations**

### Rate Limiting
- **Search**: 100 requests/minute
- **Upload**: 10 requests/minute
- **RAG**: 50 requests/minute
- **General**: 1000 requests/hour

### Input Validation
- File size limits: 100MB per file
- Supported file types: Whitelist approach
- SQL injection prevention: Parameterized queries
- XSS prevention: Input sanitization

### Data Privacy
- Sensitive data encryption
- Audit logging
- GDPR compliance
- Data retention policies

This comprehensive API design provides a robust foundation for building the AIFS client application with full RAG capabilities.
