# Phase 10: Production Deployment, Cloud Infrastructure & CI/CD

## Overview

Phase 10 transforms TR-OS from a development prototype into a production-ready application with enterprise-grade deployment, security, and observability. This phase addresses all deployment blockers identified in Phase 9 and establishes a robust foundation for single-instance VPS deployment.

**Baseline:** 436 backend tests (Phase 9)  
**Final:** 549 backend tests (+113 new tests)  
**Frontend:** 25 tests (unchanged)  
**Total:** 574 tests

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         nginx (TLS)                          │
│  • HTTPS termination (Let's Encrypt)                        │
│  • HTTP → HTTPS redirect                                    │
│  • Connection limiting (20 conn/IP)                         │
│  • Security headers (HSTS, CSP, X-Frame-Options)           │
│  • SSE proxy (120s timeout, 3600s for events)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Application                        │
│  • Single worker (uvicorn --workers 1)                      │
│  • Request ID generation & logging                          │
│  • OpenAPI docs disabled in production                      │
│  • ThreadPoolExecutor (max 4 concurrent missions)          │
│  • SSE event streaming with Last-Event-ID replay           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    SQLite (WAL mode)                          │
│  • Persistence layer for missions, executions, events      │
│  • Connection-per-operation (thread-safe)                   │
│  • WAL mode for concurrent reads                            │
│  • Automatic migrations on startup                          │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Target

**Single VPS** with Docker Compose:
- **Rationale:** TR-OS is a single-tenant, mission-critical system with bounded concurrency (max 4 concurrent missions). A single VPS provides sufficient capacity while minimizing operational complexity.
- **Scaling limitation:** In-process state (SSE connections, cancellation tokens, execution manager) requires single-instance deployment. Horizontal scaling would require Redis/PostgreSQL and stateless design (out of scope).

## Infrastructure

### Docker Compose Stack

```yaml
services:
  api:
    image: tros-api:latest
    build: .
    environment:
      - TR_OS_ENVIRONMENT=production
      - TR_OS_AUTH_MODE=bearer
      - TR_OS_AUTH_SECRET=${TR_OS_AUTH_SECRET}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - TR_OS_ATLAS_AUTH_TOKEN=${TR_OS_ATLAS_AUTH_TOKEN}
    volumes:
      - ./data:/app/data  # SQLite persistence
    mem_limit: 512m
    cpus: 1.0
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:1.25.4-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl.conf:/etc/nginx/ssl.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
    depends_on:
      - api
```

### Resource Limits

- **Memory:** 512 MB (sufficient for 4 concurrent missions + SQLite)
- **CPU:** 1.0 core (single-worker constraint)
- **Disk:** 10 GB minimum (SQLite DB + logs)

## Environment Variables

### Required (Production)

| Variable | Prefix | Description | Example |
|----------|--------|-------------|---------|
| `TR_OS_ENVIRONMENT` | Yes | Environment mode | `production` |
| `TR_OS_AUTH_MODE` | Yes | Authentication mode | `bearer` |
| `TR_OS_AUTH_SECRET` | Yes | HMAC secret for bearer tokens | `your-secret-key` |
| `TR_OS_ATLAS_AUTH_TOKEN` | Yes | Atlas API authentication token | `atlas-token-here` |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key (non-prefixed) | `sk-...` |

### Optional (Production)

| Variable | Prefix | Default | Description |
|----------|--------|---------|-------------|
| `TR_OS_CORS_ORIGINS` | Yes | `http://localhost:5173,...` | Allowed CORS origins (comma-separated) |
| `TR_OS_DATABASE_URL` | Yes | `data/tros.db` | SQLite database path |
| `TR_OS_BUILD_VERSION` | Yes | `0.10.0` | Build version (injected by CI) |
| `TR_OS_COMMIT_SHA` | Yes | (git rev-parse) | Commit SHA (injected by CI) |
| `TR_OS_BUILD_TIME` | Yes | (build time) | ISO 8601 build timestamp |
| `TR_OS_WORKER_COUNT` | Yes | `1` | Worker count (must be 1 in production) |
| `TR_OS_LOG_LEVEL` | Yes | `INFO` | Logging level |
| `TR_OS_MAX_CONCURRENT_MISSIONS` | Yes | `10` | Max concurrent missions |
| `TR_OS_RATE_LIMIT_RPM` | Yes | `60` | Rate limit (requests per minute) |

### Development Only

| Variable | Prefix | Default | Description |
|----------|--------|---------|-------------|
| `TR_OS_AUTH_MODE` | Yes | `dev` | Dev mode (no auth required) |
| `TR_OS_CORS_ORIGINS` | Yes | `*` | Wildcard allowed in dev |

## Secret Management

### Strategy

1. **No hardcoded secrets:** All secrets loaded from environment variables
2. **No secrets in logs:** `SecretScrubberFilter` redacts API keys, bearer tokens, and auth headers
3. **No secrets in API responses:** Health, readiness, metrics endpoints expose only aggregate data
4. **No secrets in frontend:** Source maps hidden in production (`sourcemap: 'hidden'`)
5. **No secrets in repositories:** `result_json` stores sanitized `MissionResultResponse` only

### Validation (Production)

```python
# settings.py
@model_validator(mode="after")
def validate_production(self):
    if self.environment == Environment.PRODUCTION:
        # Reject empty or placeholder API keys
        if not self.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required in production")
        if self.deepseek_api_key.startswith("sk-your"):
            raise ValueError("DEEPSEEK_API_KEY must not be a placeholder")
        # Require Atlas token
        if not self.atlas_auth_token:
            raise ValueError("TR_OS_ATLAS_AUTH_TOKEN is required in production")
        # No wildcard CORS
        if "*" in self.cors_origins_list:
            raise ValueError("Production must not allow wildcard CORS")
```

### Secret Boundary Tests

13 tests verify no secrets leak through:
- Health/readiness/metrics responses
- SSE events
- Error responses
- Log output
- Repository `result_json`
- Frontend build output

## Database Schema & Migrations

### Schema (SQLite)

```sql
-- Executions (mission lifecycle)
CREATE TABLE IF NOT EXISTS executions (
  id TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  error TEXT
);

-- Missions (request details)
CREATE TABLE IF NOT EXISTS missions (
  mission_id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL,
  origin TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_date TEXT NOT NULL,
  status TEXT NOT NULL,
  result_json TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  idempotency_key TEXT UNIQUE
);

-- Events (SSE stream)
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  data_json TEXT NOT NULL,
  timestamp TEXT NOT NULL
);

-- Idempotency keys
CREATE TABLE IF NOT EXISTS idempotency_keys (
  key TEXT PRIMARY KEY,
  mission_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

### Migration Process

1. **Bootstrap:** `db.py:init_db()` creates tables on first startup (safe: `IF NOT EXISTS`)
2. **Migrations:** `migrations.py:MigrationRunner` applies numbered SQL files from `tros/api/migrations/`
3. **Tracking:** `migrations` table records applied migrations
4. **Safety:** Destructive operations (`DROP TABLE`, `TRUNCATE`) are blocked
5. **Automatic:** Pending migrations run on application startup

### Current Migrations

- `001_initial.sql`: Initial schema (executions, missions, events, idempotency_keys)

## Docker Configuration

### Dockerfile (Production)

```dockerfile
# Pinned base images for deterministic builds
FROM python:3.12.8-slim AS backend
FROM node:20.18-alpine AS frontend-builder

# Build args for versioning
ARG BUILD_VERSION=0.10.0
ARG COMMIT_SHA=unknown

# OCI labels
LABEL org.opencontainers.image.version="${BUILD_VERSION}"
LABEL org.opencontainers.image.revision="${COMMIT_SHA}"

# SQLite data directory
RUN mkdir -p /app/data && chown -R app:app /app/data

# Single worker in production
CMD ["uvicorn", "tros.api.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### .dockerignore

Excludes:
- `.git/`, `__pycache__/`, `*.pyc`
- `tests/`, `.env`, `.env.*`
- `demo/`, `*.md` (except README)
- `frontend/node_modules/`, `frontend/dist/`
- `.qoder/`, `.pytest_cache/`

### Resource Limits

```yaml
mem_limit: 512m
cpus: 1.0
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

## HTTPS & TLS (Let's Encrypt)

### nginx Configuration

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl;
    server_name your-domain.com;

    # TLS configuration (ssl.conf)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS with preload
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # CSP (no unsafe-inline for scripts)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;

    # Connection limiting
    limit_conn addr 20;

    # SSE proxy (extended timeout)
    location ~ ^/api/v1/missions/[^/]+/events$ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        chunked_transfer_encoding off;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api:8000;
        proxy_read_timeout 120s;
    }
}
```

### Let's Encrypt Setup

```bash
# scripts/init-letsencrypt.sh
# 1. Stop nginx
# 2. Run certbot standalone challenge
# 3. Start nginx
# 4. Setup auto-renewal cron
```

**Renewal:** Certbot auto-renewal cron runs twice daily, reloads nginx on success.

## SSE Production Behavior

### Last-Event-ID Support

Clients can resume from the last seen event ID on reconnection:

```http
GET /api/v1/missions/{mission_id}/events
Last-Event-ID: 42
```

The server replays events with `id > 42` from the event repository before streaming live events.

### Timeouts

- **Standard API:** 120s (`proxy_read_timeout`)
- **SSE events:** 3600s (1 hour, for long-running missions)
- **Heartbeat:** 15s (keep-alive comment)
- **Max connection:** 600s (10 minutes)

### Connection Limiting

- **Per IP:** 20 concurrent connections (`limit_conn addr 20`)
- **Rationale:** Prevents SSE connection exhaustion while allowing multiple tabs/clients

## PWA Hardening

### Source Maps

```typescript
// vite.config.ts
build: {
  sourcemap: 'hidden',  // Generate but don't expose
}
```

Source maps are generated for error tracking but not served to clients (prevents reverse engineering).

### Service Worker (v3)

```javascript
// sw.js
// Network-first with caching for API responses
async function networkFirst(request) {
  const response = await fetch(request);
  // Cache successful API responses (non-no-store)
  if (response.ok && !response.headers.get('Cache-Control')?.includes('no-store')) {
    const cache = await caches.open('tros-v3');
    cache.put(request, response.clone());
  }
  return response;
}
```

**Bug fix:** Previous version didn't cache API responses. Now caches successful responses before returning.

### Manifest

```json
{
  "name": "TR-OS",
  "categories": ["travel", "productivity"],
  "lang": "en",
  "scope": "/",
  "id": "/"
}
```

### Accessibility

Removed `user-scalable=no` from `index.html` (accessibility compliance).

## CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/ci.yml`

**Jobs:**

1. **lint:** Python `ruff check` + TypeScript `tsc --noEmit`
2. **test-backend:** `pytest tests/ -q` on Python 3.12
3. **test-frontend:** `cd frontend && npm test`
4. **build-frontend:** `cd frontend && npm run build`
5. **security-scan:** Grep for secret patterns in source
6. **docker-build:** `docker build -t tros-api .`
7. **smoke-test:** Start container, hit health endpoint

**Triggers:** Push to `main`, pull requests

**Secrets:** `DEEPSEEK_API_KEY`, `TR_OS_AUTH_SECRET` from GitHub secrets

### Deploy Workflow

**File:** `.github/workflows/deploy.yml`

**Trigger:** Push to `main` (after CI passes)

**Jobs:**
1. Build Docker image with commit SHA tag
2. Push to container registry
3. Deploy to VPS (SSH, docker-compose pull, docker-compose up -d)

## Observability & Metrics

### Metrics Endpoint

```json
GET /api/v1/metrics
{
  "version": "0.10.0",
  "commit": "abc1234",
  "timestamp": "2026-08-18T12:00:00Z",
  "missions_submitted": 42,
  "missions_completed": 40,
  "missions_failed": 2,
  "recovery_count": 3,
  "llm_errors": 1,
  "atlas_errors": 0,
  "request_count": 150,
  "rate_limit_events": 5,
  "auth_failures": 2,
  "repository_errors": 0,
  "duration": {
    "p50": 12000,
    "p95": 45000,
    "avg": 18000
  }
}
```

### Request Tracking

```python
# metrics.py
def record_request(self, method: str, path: str, status: int, duration_ms: float):
    self._counters["request_count"] += 1
    key = f"{method}:{path}"
    self._request_latencies[key].append(duration_ms)
```

Per-endpoint latency tracking with rolling window (last 100 requests).

### Structured Logging

```json
{
  "timestamp": "2026-08-18T12:00:00Z",
  "level": "INFO",
  "request_id": "req-abc123",
  "mission_id": "mission-xyz789",
  "logger": "tros.api.routes.missions",
  "message": "Mission submitted"
}
```

**RequestContextFilter:** Injects `request_id` and `mission_id` into all log records (thread-local context).

### Secret Scrubbing

`SecretScrubberFilter` redacts:
- API keys (`sk-...`)
- Bearer tokens (`Bearer eyJ...`)
- Auth headers (`Authorization: ...`)

## Backup & Recovery

### SQLite Backup

```bash
# Manual backup
sqlite3 data/tros.db ".backup 'backup-$(date +%Y%m%d).db'"

# Automated (cron)
0 2 * * * sqlite3 /app/data/tros.db ".backup '/backup/tros-$(date +\%Y\%m\%d).db'"
```

### Recovery

1. Stop application: `docker-compose stop api`
2. Restore backup: `cp backup.db data/tros.db`
3. Start application: `docker-compose start api`

**RPO:** 24 hours (daily backups)  
**RTO:** 15 minutes (restore + restart)

## Disaster Scenarios

### Backend Crash

- **Impact:** In-flight missions fail, SSE connections drop
- **Recovery:** Automatic restart by Docker, missions can be resubmitted (idempotency keys prevent duplicates)
- **Data loss:** None (SQLite persisted before crash)

### Database Unavailable

- **Impact:** Missions cannot be submitted (persistence required)
- **Recovery:** SQLite is file-based; check disk space, permissions, WAL lock
- **Mitigation:** `_persist_execution()` silently fails on DB errors (missions continue)

### Atlas API Unavailable

- **Impact:** Flight search fails, missions fail with `ATLAS_ERROR`
- **Recovery:** Automatic retry (3 attempts, exponential backoff)
- **Mitigation:** Recovery mechanism (Phase 9) attempts alternative routes

### LLM Unavailable

- **Impact:** Agent reasoning fails, missions fail with `LLM_ERROR`
- **Recovery:** Automatic retry (2 attempts)
- **Mitigation:** Graceful degradation (return partial results)

### Client Disconnect (SSE)

- **Impact:** Client misses events
- **Recovery:** Client reconnects with `Last-Event-ID`, server replays missed events
- **Data loss:** None (events persisted to SQLite)

## Scaling Limitations

### Single Worker Constraint

**Why:** In-process state (SSE connections, cancellation tokens, execution manager) cannot be shared across workers or instances.

**Impact:**
- Max 4 concurrent missions (ThreadPoolExecutor)
- Max ~100 concurrent SSE connections (file descriptor limit)
- No horizontal scaling without architectural changes

**Scaling path (out of scope):**
1. Move state to Redis (SSE pub/sub, cancellation tokens)
2. Move persistence to PostgreSQL (shared across instances)
3. Stateless execution manager (load balanced)

### SQLite Limitations

- **Write concurrency:** Single writer (WAL mode allows concurrent reads)
- **Max database size:** 281 TB (theoretical), 10 GB recommended
- **Backup:** File-level (no point-in-time recovery)

**When to migrate to PostgreSQL:**
- Write contention (frequent `database is locked` errors)
- Multi-instance deployment required
- Point-in-time recovery needed

## Deployment Procedure

### Prerequisites

1. VPS with Docker + Docker Compose installed
2. Domain name with DNS pointing to VPS
3. Let's Encrypt certificates (or self-signed for testing)
4. Environment variables configured (`.env` file)

### Step-by-Step

```bash
# 1. Clone repository
git clone https://github.com/your-org/tros.git
cd tros

# 2. Configure environment
cp .env.example .env
nano .env  # Set DEEPSEEK_API_KEY, TR_OS_AUTH_SECRET, TR_OS_ATLAS_AUTH_TOKEN

# 3. Initialize Let's Encrypt (first time only)
chmod +x scripts/init-letsencrypt.sh
./scripts/init-letsencrypt.sh your-domain.com

# 4. Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Verify
python scripts/smoke_test.py https://your-domain.com
```

### Rollback Procedure

```bash
# 1. Stop current version
docker-compose -f docker-compose.prod.yml down

# 2. Checkout previous version
git checkout v0.9.0  # or specific commit

# 3. Restore database backup (if schema changed)
cp backup-pre-upgrade.db data/tros.db

# 4. Rebuild and start
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Verify
python scripts/smoke_test.py https://your-domain.com
```

## Smoke Test

### Automated (CI/CD)

```bash
python scripts/smoke_test.py http://localhost:8000
```

**Checks:**
- Health endpoint returns 200 with version info
- Readiness endpoint returns 200
- Metrics endpoint returns aggregate data
- No secrets in any API response
- CORS configuration works
- API authentication works

### Manual (Post-Deployment)

```bash
# Health check
curl -i https://your-domain.com/api/v1/health

# Metrics
curl -i https://your-domain.com/api/v1/metrics

# Security headers
curl -I https://your-domain.com/ | grep -E "(X-Frame|X-Content|Strict)"
```

## Known Limitations

1. **Single instance:** Cannot scale horizontally (in-process state)
2. **Single worker:** Max 4 concurrent missions (ThreadPoolExecutor)
3. **SQLite:** Write contention under high load (single writer)
4. **No rate limiting per user:** IP-based only (no user-level quotas)
5. **No multi-tenancy:** Single-tenant design (one Atlas account)
6. **No audit log:** Mission history not persisted beyond SQLite
7. **No real-time monitoring:** Metrics exposed via HTTP only (no Prometheus/Grafana)
8. **No automated failover:** Single VPS (no HA/DR)

## Phase 10 Test Coverage

| Category | Tests |
|----------|-------|
| SQLite repositories | 22 |
| Migrations | 6 |
| Secret boundaries | 13 |
| Build info | 4 |
| Docker hardened | 14 |
| Production server | 10 |
| HTTPS security | 6 |
| PWA hardened | 10 |
| CI config | 6 |
| Observability | 7 |
| Stress (persistence) | 5 |
| Smoke test (Docker) | 10 |
| **Total new** | **113** |

## Files Created (Phase 10)

**Backend:**
- `tros/api/repositories_sqlite.py` — SQLite repository implementations
- `tros/api/db.py` — SQLite connection management
- `tros/api/migrations.py` — Migration runner
- `tros/api/migrations/001_initial.sql` — Initial schema
- `tros/api/build_info.py` — Build version metadata

**Infrastructure:**
- `.dockerignore` — Docker build exclusions
- `nginx/ssl.conf` — TLS configuration template
- `scripts/init-letsencrypt.sh` — Let's Encrypt setup
- `scripts/smoke_test.py` — Standalone smoke test
- `.github/workflows/ci.yml` — CI pipeline
- `.github/workflows/deploy.yml` — Deploy pipeline

**Tests:**
- `tests/test_repositories_sqlite.py` — SQLite repo tests
- `tests/test_migrations.py` — Migration tests
- `tests/test_secret_boundaries.py` — Secret leak prevention tests
- `tests/test_build_info.py` — Build info tests
- `tests/test_docker_hardened.py` — Docker hardening tests
- `tests/test_production_server.py` — Production config tests
- `tests/test_https_security.py` — HTTPS/security tests
- `tests/test_pwa_hardened.py` — PWA hardening tests
- `tests/test_ci_config.py` — CI config tests
- `tests/test_observability.py` — Observability tests
- `tests/test_stress_persistence.py` — SQLite stress tests
- `tests/test_smoke_docker.py` — Docker smoke tests

**Documentation:**
- `PHASE_10.md` — This file

## Files Modified (Phase 10)

- `tros/api/settings.py` — database_url, atlas_auth_token, worker_count, production validators
- `tros/api/app.py` — request ID middleware, request metrics, docs disabled in prod, lifespan DB init
- `tros/api/deps.py` — SQLite repository injection in production
- `tros/api/routes/events.py` — Last-Event-ID support
- `tros/api/routes/health.py` — build info in health/metrics
- `tros/api/metrics.py` — request-level tracking, latency percentiles
- `tros/api/structured_logging.py` — request context filter
- `tros/api/execution_manager.py` — persistence hooks
- `nginx.conf` — HTTPS redirect, connection limiting, SSE timeout, security headers
- `Dockerfile` — pinned base images, labels
- `docker-compose.prod.yml` — resource limits, logging, SQLite volume, version env vars
- `frontend/vite.config.ts` — hidden source maps, version define
- `frontend/public/sw.js` — fixed caching, v3
- `frontend/public/manifest.json` — PWA fields
- `frontend/index.html` — Apple meta tags, accessibility
- `frontend/src/App.tsx` — footer update
- `.env.example` — new variables
- `README.md` — Phase 10 section, deployment instructions

## Conclusion

Phase 10 establishes a production-ready foundation for TR-OS with enterprise-grade security, observability, and deployment automation. All deployment blockers from Phase 9 are resolved, and the system is ready for single-instance VPS deployment with HTTPS, persistence, and CI/CD.

**Next steps (future phases):**
- Horizontal scaling (Redis + PostgreSQL)
- Multi-tenancy support
- Real-time monitoring (Prometheus + Grafana)
- Automated failover (HA/DR)
- Audit logging and compliance
