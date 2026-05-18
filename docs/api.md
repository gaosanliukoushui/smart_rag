# SmartRAG API Documentation

## Base URL

```
http://localhost:8000
```

## API Version

Current version: `v1`

Prefix: `/api/v1`

## Authentication

All protected endpoints require a JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Token responses include both access and refresh tokens:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## Health & Monitoring

### GET /health

Root-level health check for load balancers and orchestrators.

**Response:**

```json
{
  "status": "healthy"
}
```

### GET /api/v1/health

**Response:**

```json
{
  "status": "healthy",
  "service": "SmartRAG"
}
```

### GET /api/v1/health/ready

Readiness check endpoint.

**Response:**

```json
{
  "status": "ready"
}
```

### GET /metrics

Prometheus-format metrics endpoint.

**Response:** `text/plain`

```
# HELP smartrag_http_requests_total Total HTTP requests
# TYPE smartrag_http_requests_total counter
smartrag_http_requests_total 1234
smartrag_http_requests_total{status="200"} 1100
smartrag_http_requests_total{status="500"} 5

# HELP smartrag_http_request_duration_ms_avg Average HTTP request duration in ms
# TYPE smartrag_http_request_duration_ms_avg gauge
smartrag_http_request_duration_ms_avg 45.32

# HELP smartrag_http_request_duration_ms_p95 P95 HTTP request duration in ms
# TYPE smartrag_http_request_duration_ms_p95 gauge
smartrag_http_request_duration_ms_p95 120.5

# HELP smartrag_tokens_total Total tokens processed
# TYPE smartrag_tokens_total counter
smartrag_tokens_total 50000

# HELP smartrag_errors_total Total errors
# TYPE smartrag_errors_total counter
smartrag_errors_total 5
```

### GET /metrics/summary

Metrics in JSON format for programmatic consumption.

**Response:**

```json
{
  "requests": {
    "total": 1234,
    "by_status": { "200": 1100, "500": 5 }
  },
  "duration_ms": {
    "avg": 45.32,
    "max": 300.0,
    "p95": 120.5
  },
  "tokens_total": 50000,
  "errors_total": 5
}
```

### POST /metrics/reset

Reset all in-memory metrics. Use with caution in production.

**Response:**

```json
{
  "status": "reset"
}
```

---

## Authentication (`/api/v1/auth`)

### POST /api/v1/auth/register

Register a new user account. Rate limited to 5 requests per hour per IP.

**Request Body:**

```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response** `201 Created`:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "avatar_url": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### POST /api/v1/auth/login

Authenticate and return JWT tokens. Rate limited to 10 requests per minute per IP.

**Request Body:**

```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### POST /api/v1/auth/refresh

Refresh access token using a valid refresh token.

**Query Parameters:**

- `refresh_token` (required): The refresh token string

**Response:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET /api/v1/auth/me

Get current authenticated user info.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "is_superuser": false,
  "avatar_url": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

---

## Users (`/api/v1/users`)

### GET /api/v1/users

List all users. Admin only.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Query Parameters:**

- `skip` (optional): Offset for pagination, default 0
- `limit` (optional): Number of results, default 50, max 200
- `search` (optional): Search by username or email

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "is_active": true,
    "is_superuser": false,
    "avatar_url": null,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
]
```

### GET /api/v1/users/me

Get current user's own profile.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** Same as `UserResponse` above.

### GET /api/v1/users/{user_id}

Get user by ID. Admin only.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Response:** `UserResponse` object.

### PUT /api/v1/users/{user_id}

Update user profile. Users can update their own profile; admins can update any user.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "full_name": "Jane Doe",
  "avatar_url": "https://example.com/avatar.jpg"
}
```

**Response:** Updated `UserResponse` object.

### DELETE /api/v1/users/{user_id}

Delete (soft delete by deactivating) a user. Admin only.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Response:** `204 No Content`

---

## Roles (`/api/v1/roles`)

### GET /api/v1/roles

List all roles.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "admin",
    "description": "Administrator",
    "is_system": true,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
]
```

### POST /api/v1/roles

Create a new custom role. Admin only.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Request Body:**

```json
{
  "name": "editor",
  "description": "Can edit documents"
}
```

**Response** `201 Created`: `RoleResponse` object.

### GET /api/v1/roles/{role_id}

Get role with its permissions.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "admin",
  "description": "Administrator",
  "is_system": true,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "permissions": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "resource": "documents",
      "action": "write",
      "description": "Can create and edit documents"
    }
  ]
}
```

### PUT /api/v1/roles/{role_id}

Update a custom role. Admin only. System roles cannot be modified.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Request Body:**

```json
{
  "name": "senior_editor",
  "description": "Can edit and delete documents"
}
```

**Response:** Updated `RoleResponse` object.

### GET /api/v1/roles/{role_id}/permissions

Get all permissions assigned to a role.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** Array of `PermissionResponse` objects.

### PUT /api/v1/roles/{role_id}/permissions

Update permissions for a role. Admin only. System role permissions cannot be modified.

**Headers:** `Authorization: Bearer <access_token>` (admin required)

**Request Body:**

```json
{
  "permission_ids": [
    "660e8400-e29b-41d4-a716-446655440001",
    "660e8400-e29b-41d4-a716-446655440002"
  ]
}
```

**Response:** `RoleWithPermissions` object.

### GET /api/v1/roles/permissions/all

List all available permissions in the system.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "resource": "documents",
    "action": "read",
    "description": "Can view documents"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440002",
    "resource": "documents",
    "action": "write",
    "description": "Can create and edit documents"
  }
]
```

---

## Tenants (`/api/v1/tenants`)

### POST /api/v1/tenants

Create a new tenant. Any authenticated user can create a tenant and is automatically assigned the admin role.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "name": "My Company",
  "slug": "my-company",
  "description": "Company knowledge base"
}
```

**Response** `201 Created`:

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "name": "My Company",
  "slug": "my-company",
  "description": "Company knowledge base",
  "is_active": true,
  "settings": null,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### GET /api/v1/tenants/{tenant_id}

Get tenant details. User must belong to the tenant or be a superuser.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `TenantResponse` object.

### GET /api/v1/tenants/{tenant_id}/users

List all users belonging to a tenant.

**Headers:** `Authorization: Bearer <access_token>` (tenant member or superuser)

**Response:**

```json
[
  {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "770e8400-e29b-41d4-a716-446655440000",
    "role_id": "550e8400-e29b-41d4-a716-446655440001",
    "role_name": "admin"
  }
]
```

### POST /api/v1/tenants/{tenant_id}/users/{user_id}/roles

Assign a role to a user within a tenant. Tenant admin or superuser only.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "role_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

**Response:**

```json
{
  "message": "Role assigned"
}
```

### DELETE /api/v1/tenants/{tenant_id}/users/{user_id}/roles/{role_id}

Remove a role from a user within a tenant. Tenant admin or superuser only.

**Headers:** `Authorization: Bearer <access_token>`

**Response:** `204 No Content`

---

## Knowledge Bases (`/api/v1/knowledge-bases`)

### POST /api/v1/knowledge-bases

Create a new knowledge base.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "name": "My Knowledge Base",
  "description": "Optional description",
  "tenant_id": "optional-tenant-uuid"
}
```

**Response** `201 Created`:

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440000",
  "name": "My Knowledge Base",
  "description": "Optional description",
  "document_count": 0,
  "chunk_count": 0,
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### GET /api/v1/knowledge-bases

List knowledge bases accessible to the current user.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "knowledge_bases": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440000",
      "name": "My Knowledge Base",
      "description": "Optional description",
      "document_count": 10,
      "chunk_count": 500,
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/v1/knowledge-bases/{kb_id}

Get knowledge base details.

**Headers:** `Authorization: Bearer <access_token>`

### PUT /api/v1/knowledge-bases/{kb_id}

Update knowledge base.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

### DELETE /api/v1/knowledge-bases/{kb_id}

Delete a knowledge base and all its documents.

**Headers:** `Authorization: Bearer <access_token>`

### POST /api/v1/knowledge-bases/{kb_id}/reload

Reload all documents in a knowledge base.

**Headers:** `Authorization: Bearer <access_token>`

---

## Documents (`/api/v1/documents`)

### POST /api/v1/documents/upload

Upload and parse a document. Supports PDF, Markdown, Word, and TXT files.

**Headers:**
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

**Form Fields:**

- `file` (required): The document file
- `knowledge_base_id` (required): Target knowledge base UUID
- `chunk_size` (optional): Override default chunk size
- `chunk_overlap` (optional): Override default chunk overlap

**Response** `201 Created`:

```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

### GET /api/v1/documents

List documents with pagination.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**

- `page` (optional): Page number, default 1
- `page_size` (optional): Items per page, default 20
- `knowledge_base_id` (optional): Filter by knowledge base

**Response:**

```json
{
  "documents": [
    {
      "id": "uuid",
      "title": "Document Title",
      "file_type": "pdf",
      "file_size": 1024000,
      "status": "completed",
      "chunk_count": 50,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 100
}
```

### GET /api/v1/documents/{document_id}

Get document details.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "id": "uuid",
  "title": "Document Title",
  "file_type": "pdf",
  "file_size": 1024000,
  "status": "completed",
  "chunk_count": 50,
  "created_at": "2026-01-01T00:00:00Z",
  "metadata": {}
}
```

### DELETE /api/v1/documents/{document_id}

Delete a document.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "message": "Document deleted successfully"
}
```

### GET /api/v1/documents/{document_id}/preview

Preview document content.

**Headers:** `Authorization: Bearer <access_token>`

### POST /api/v1/documents/{document_id}/reparse

Reparse a document.

**Headers:** `Authorization: Bearer <access_token>`

### GET /api/v1/documents/{document_id}/version

Get document version information.

**Headers:** `Authorization: Bearer <access_token>`

---

## Chat (`/api/v1/chat`)

### POST /api/v1/chat

Send a chat message with RAG-powered answer generation.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "message": "What is RAG?",
  "knowledge_base_id": "uuid",
  "session_id": "optional-session-uuid",
  "stream": true
}
```

**Response (non-streaming):**

```json
{
  "session_id": "uuid",
  "answer": "RAG stands for Retrieval-Augmented Generation...",
  "sources": [
    {
      "text": "RAG is a technique...",
      "score": 0.95
    }
  ],
  "tokens_used": 1500
}
```

**Response (streaming):** Server-Sent Events (`text/event-stream`)

```
data: {"token": "RAG"}
data: {"token": " stands"}
data: {"token": " for"}
data: [DONE]
```

### POST /api/v1/chat/stream

SSE streaming chat endpoint.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** Same as `/api/v1/chat`

### GET /api/v1/chat/history/{session_id}

Get chat history for a session.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "session_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "What is RAG?",
      "created_at": "2026-01-01T00:00:00Z"
    },
    {
      "role": "assistant",
      "content": "RAG stands for...",
      "created_at": "2026-01-01T00:00:01Z"
    }
  ],
  "created_at": "2026-01-01T00:00:00Z"
}
```

### POST /api/v1/chat/session

Create a new chat session.

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**

```json
{
  "knowledge_base_id": "uuid"
}
```

---

## Sessions (`/api/v1/chat/sessions`)

### GET /api/v1/chat/sessions

List all chat sessions, optionally filtered by knowledge base.

**Headers:** `Authorization: Bearer <access_token>`

**Query Parameters:**

- `knowledge_base_id` (optional): Filter sessions by knowledge base

**Response:**

```json
[
  {
    "session_id": "uuid",
    "knowledge_base_id": "uuid",
    "message_count": 10,
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

### DELETE /api/v1/chat/sessions/{session_id}

Delete a chat session and its history.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "message": "Session uuid deleted",
  "session_id": "uuid"
}
```

### DELETE /api/v1/chat/sessions/{session_id}/history

Clear all messages from a session but keep the session.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**

```json
{
  "message": "History cleared for session uuid",
  "session_id": "uuid"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource does not exist |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

### Common Error Codes

| Code | Description |
|------|-------------|
| `DOCUMENT_NOT_FOUND` | Document does not exist |
| `KB_NOT_FOUND` | Knowledge base does not exist |
| `PARSE_ERROR` | Failed to parse document |
| `EMBEDDING_ERROR` | Failed to generate embeddings |
| `LLM_ERROR` | LLM service unavailable |
| `VALIDATION_ERROR` | Invalid request parameters |
| `AUTH_CREDENTIALS_INVALID` | Invalid username or password |
| `USER_ALREADY_EXISTS` | User with this email/username already exists |
| `ROLE_NOT_FOUND` | Role does not exist |
| `TENANT_NOT_FOUND` | Tenant does not exist |
| `ACCESS_DENIED` | Insufficient permissions |
