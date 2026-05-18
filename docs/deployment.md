# SmartRAG Deployment Documentation

## Prerequisites

| Requirement | Minimum Version | Recommended |
|-------------|----------------|-------------|
| Python | 3.11 | 3.11+ |
| PostgreSQL | 15 | 15+ |
| Redis | 7 | 7+ |
| Docker | 20.x | Latest |
| Docker Compose | 2.x | Latest |
| Git | Any recent | Latest |

---

## Docker Deployment (Recommended)

### Overview

Docker Compose starts four services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `app` | Built from Dockerfile | 8000 | FastAPI application |
| `db` | postgres:15-alpine | 5432 | PostgreSQL database |
| `redis` | redis:7-alpine | 6379 | Redis cache and sessions |
| `nginx` | nginx:alpine | 80 | Reverse proxy and rate limiting |

### Quick Start

```bash
# 1. Clone and navigate to project
git clone https://github.com/gaosanliukoushui/smart_rag.git
cd smart_rag

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys and secrets

# 3. Generate a secure JWT secret
python -c "import secrets; print(secrets.token_hex(32))"
# Add the output to JWT_SECRET_KEY in .env

# 4. Start all services
cd docker
docker-compose up -d

# 5. Verify health
curl http://localhost:8000/health
```

### Docker Compose File Structure

```yaml
services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/smartrag
      - REDIS_URL=redis://redis:6379/0
      - CHROMA_PERSIST_DIR=/app/data/chroma
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-changeme-in-production}
    volumes:
      - ../data:/app/data
      - ../.env:/app/.env:ro
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=smartrag
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      app:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Service Details

#### App Service

- Runs uvicorn with 4 workers
- Health check: `GET /health`
- Data persisted to `./data/` on host
- Reads `.env` from host at runtime

#### PostgreSQL Service

- Default credentials: `postgres / postgres`
- Database name: `smartrag`
- Data persisted to Docker volume `postgres_data`
- Health check: `pg_isready -U postgres`

#### Redis Service

- Default port: 6379
- AOF persistence enabled (`--appendonly yes`)
- Data persisted to Docker volume `redis_data`
- Health check: `redis-cli ping`

#### Nginx Service

- Listens on port 80
- Rate limiting zones:
  - API: 10 requests/second
  - Auth: 5 requests/second (stricter)
- WebSocket support for SSE streaming
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)

### Common Docker Commands

```bash
# View logs
docker-compose logs -f app

# Restart a service
docker-compose restart app

# Rebuild after code changes
docker-compose up -d --build

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Scale app service (for high load)
docker-compose up -d --scale app=3
```

---

## Manual Deployment

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration. See the Environment Variables Reference below.

### 3. Set Up Database

```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE smartrag;"

# The application uses SQLAlchemy's create_all() on startup,
# so tables are created automatically on first run.
# For production, consider using Alembic migrations:
pip install alembic
alembic init alembic
```

### 4. Create Data Directories

```bash
mkdir -p data/uploads data/chroma
```

### 5. Run the Application

```bash
# Development (single worker, reload enabled)
uvicorn app.main:app --reload --port 8000

# Production (multiple workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With systemd (example unit file)
# Save as /etc/systemd/system/smartrag.service
```

```ini
[Unit]
Description=SmartRAG API Server
After=network.target postgresql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/smartrag
Environment="PATH=/opt/smartrag/.venv/bin"
ExecStart=/opt/smartrag/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable smartrag
sudo systemctl start smartrag
```

---

## Environment Variables Reference

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | SmartRAG | Application name |
| `DEBUG` | true | Debug mode |
| `API_V1_PREFIX` | /api/v1 | API version prefix |
| `ENVIRONMENT` | development | Runtime environment |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | console | Log output format |

### Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | (required) | Secret key for JWT signing. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime in days |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://postgres:postgres@localhost:5432/smartrag | PostgreSQL connection string |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection string |

### Vector Database

| Variable | Default | Description |
|----------|---------|-------------|
| `VECTOR_DB_TYPE` | chroma | Vector database type |
| `CHROMA_PERSIST_DIR` | ./data/chroma | ChromaDB persistence directory |

### LLM Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | deepseek | LLM provider: deepseek / qwen / openai / ollama |

#### DeepSeek

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | (required) | DeepSeek API key |
| `DEEPSEEK_MODEL` | deepseek-chat | Model name |
| `DEEPSEEK_BASE_URL` | https://api.deepseek.com | API base URL |

#### Qwen

| Variable | Default | Description |
|----------|---------|-------------|
| `QWEN_API_KEY` | (required) | Qwen API key |
| `QWEN_MODEL` | qwen-plus | Model name |
| `QWEN_BASE_URL` | https://dashscope.aliyuncs.com/compatible-mode/v1 | API base URL |

#### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `OPENAI_MODEL` | gpt-4o | Model name |

#### Ollama (Local)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama server URL |
| `OLLAMA_MODEL` | llama3.2 | Model name |
| `OLLAMA_NUM_CTX` | 4096 | Context window size |
| `OLLAMA_TEMPERATURE` | 0.7 | Generation temperature |
| `OLLAMA_TIMEOUT` | 120 | Request timeout in seconds |

### Embedding

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | BAAI/bge-m3 | HuggingFace model name |
| `EMBEDDING_DEVICE` | cpu | Device: cpu / cuda |
| `EMBEDDING_DIM` | 1024 | Embedding dimension |

### Reranker

| Variable | Default | Description |
|----------|---------|-------------|
| `RERANKER_MODEL` | BAAI/bge-reranker-v2-m3 | HuggingFace model name |

### File Upload

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | ./data/uploads | Directory for uploaded files |
| `MAX_UPLOAD_SIZE` | 104857600 | Max upload size in bytes (100MB) |

### Chunk Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | 500 | Target chunk size in tokens |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |

---

## Frontend Deployment

### Development

```bash
cd frontend
npm install
npm run dev
```

The frontend development server runs on `http://localhost:5173` (Vite default) and proxies API requests to `http://localhost:8000`.

### Production Build

```bash
cd frontend
npm install
npm run build
```

The build output is placed in `frontend/dist/`. The FastAPI backend serves this directory as static files at the root `/`.

To build and deploy together:

```bash
cd frontend && npm run build && cd ..
cd docker && docker-compose up -d --build
```

---

## Production Considerations

### Security

- **Change all default passwords** in production (PostgreSQL, Redis)
- **Generate a strong `JWT_SECRET_KEY`** - never use the default placeholder
- **Set `DEBUG=false`** in production
- **Restrict CORS origins** - change `allow_origins=["*"]` in `app/main.py` to specific domains
- **Use HTTPS** - deploy behind a TLS-terminating reverse proxy (Nginx with SSL certs)

### Database

- **Connection pooling**: Configure `pool_size` and `max_overflow` in the DATABASE_URL:

```
postgresql://user:pass@host:5432/smartrag?pool_size=20&max_overflow=10
```

- **Backups**: Set up `pg_dump` cron jobs for regular PostgreSQL backups
- **Monitoring**: Add `pg_stat_statements` extension for query performance monitoring

### Redis

- **Persistence**: AOF is enabled in Docker Compose (`--appendonly yes`)
- **Memory**: Set `maxmemory` directive in `redis.conf` to prevent OOM
- **Sentinel/Cluster**: For high availability, deploy Redis Sentinel or Redis Cluster

### Nginx

- **SSL/TLS**: Add a TLS termination block to `nginx.conf` for HTTPS
- **Static file caching**: Add cache headers for frontend assets
- **Request body size**: Already set to 100MB (`client_max_body_size 100M`)
- **Upstream scaling**: Add multiple `server` entries in `upstream app_backend` for load balancing

### Logging

- **Structured logging**: The app uses JSON structured logging in production
- **Log aggregation**: Configure log drivers in Docker Compose (e.g., `logging: driver: "json-file"`)
- **Log rotation**: Add logrotate configuration:

```bash
# /etc/logrotate.d/smartrag
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    compress
    missingok
    delaycompress
}
```

### Monitoring

- **Metrics**: Prometheus-format metrics available at `GET /metrics`
- **Health checks**: Docker health checks verify `/health` endpoint
- **Systemd**: If running without Docker, use `systemctl status smartrag` for service status
