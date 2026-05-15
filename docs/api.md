# SmartRAG API Documentation

## Base URL

```
http://localhost:8000
```

## API Version

Current version: `v1`

Prefix: `/api/v1`

---

## Health Check

### GET /api/v1/health

Health check endpoint.

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

---

## Document Management

### POST /api/v1/documents/upload

Upload a document to the knowledge base.

**Request:**

- Content-Type: `multipart/form-data`
- Body: `file` - The document file

**Response:**

```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

### GET /api/v1/documents

List all documents.

**Query Parameters:**

- `page` (optional): Page number, default 1
- `page_size` (optional): Items per page, default 20

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

**Response:**

```json
{
  "message": "Document deleted successfully"
}
```

---

## Knowledge Base Management

### POST /api/v1/knowledge-bases

Create a new knowledge base.

**Request Body:**

```json
{
  "name": "My Knowledge Base",
  "description": "Optional description"
}
```

**Response:**

```json
{
  "id": "uuid",
  "name": "My Knowledge Base",
  "description": "Optional description",
  "document_count": 0,
  "chunk_count": 0,
  "created_at": "2026-01-01T00:00:00Z"
}
```

### GET /api/v1/knowledge-bases

List all knowledge bases.

**Response:**

```json
{
  "knowledge_bases": [
    {
      "id": "uuid",
      "name": "My Knowledge Base",
      "description": "Optional description",
      "document_count": 10,
      "chunk_count": 500,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/v1/knowledge-bases/{kb_id}

Get knowledge base details.

### DELETE /api/v1/knowledge-bases/{kb_id}

Delete a knowledge base and all its documents.

---

## Chat / Q&A

### POST /api/v1/chat

Send a chat message.

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

**Response (streaming):**

Server-Sent Events with `text/event-stream` content type.

```
data: {"token": "RAG"}
data: {"token": " stands"}
data: {"token": " for"}
data: [DONE]
```

### GET /api/v1/chat/history/{session_id}

Get chat history for a session.

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

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "success": false,
  "error_code": "DOCUMENT_NOT_FOUND",
  "error_message": "Document with ID xyz not found",
  "details": {}
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `DOCUMENT_NOT_FOUND` | Document does not exist |
| `KB_NOT_FOUND` | Knowledge base does not exist |
| `PARSE_ERROR` | Failed to parse document |
| `EMBEDDING_ERROR` | Failed to generate embeddings |
| `LLM_ERROR` | LLM service unavailable |
| `VALIDATION_ERROR` | Invalid request parameters |
