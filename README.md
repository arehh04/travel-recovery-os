# TR-OS: Travel Recovery Operating System

AI-powered travel disruption recovery system that uses multi-agent orchestration to find optimal rebooking solutions when flights are cancelled or disrupted.

## Architecture

```
PWA (React + TypeScript + Vite)
    │
FastAPI REST API (Python)
    │
ExecutionManager (async background)
    │
MissionService (service boundary)
    │
SupervisorAgent (orchestration)
    │
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Context  │ Planning │  Flight  │  Budget  │  Critic  │  Summary │
│  Agent   │  Agent   │  Search  │  Agent   │  Agent   │  Agent   │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
    │              │
DeepSeek LLM    Atlas Flight CLI
```

## Phases

| Phase | Description | Tests |
|-------|-------------|-------|
| 1 | Context Agent — parse disruption, extract entities | 26 |
| 2 | Planning Agent — generate recovery strategy | 22 |
| 3 | Flight Search — Atlas CLI integration | 31 |
| 4 | Budget Agent — cost analysis and constraints | 29 |
| 5 | Critic Agent — validation and ranking | 30 |
| 6 | Summary + Recovery — final output and error recovery | 50 |
| 7 | Production Hardening — execution context, logging, health | 68 |
| 8 | API + PWA — FastAPI, React PWA, Docker deployment | 84 |
| 9 | Production Hardening — config, auth, rate limiting, SSE, metrics, security | 121 |
| 10 | Production Deployment — SQLite, HTTPS, CI/CD, observability | 88 |
| | **Total** | **549** |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- DeepSeek API key
- Atlas Flight Booking CLI authorized

### Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend
cd frontend && npm install && cd ..

# Copy environment config
cp .env.example .env
# Edit .env with your DEEPSEEK_API_KEY

# Start backend API
uvicorn tros.api.app:app --reload --port 8000

# Start frontend dev server (separate terminal)
cd frontend && npm run dev
```

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

### Docker

```bash
# Development
cp .env.example .env
# Fill in credentials
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up --build
```

## Production Deployment

See [PHASE_10.md](PHASE_10.md) for complete deployment documentation.

### Quick Deploy

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Set DEEPSEEK_API_KEY, TR_OS_AUTH_SECRET, TR_OS_ATLAS_AUTH_TOKEN

# 2. Initialize Let's Encrypt (first time)
./scripts/init-letsencrypt.sh your-domain.com

# 3. Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# 4. Verify
python scripts/smoke_test.py https://your-domain.com
```

### Production Checklist

- [ ] Set `TR_OS_ENVIRONMENT=production`
- [ ] Set `TR_OS_AUTH_MODE=bearer` and `TR_OS_AUTH_SECRET`
- [ ] Set `DEEPSEEK_API_KEY` (non-placeholder)
- [ ] Set `TR_OS_ATLAS_AUTH_TOKEN`
- [ ] Configure `TR_OS_CORS_ORIGINS` (no wildcards)
- [ ] Initialize Let's Encrypt certificates
- [ ] Verify HTTPS redirect works
- [ ] Run smoke test
- [ ] Setup automated backups

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TR_OS_ENVIRONMENT` | `development` | Environment: development, testing, production |
| `TR_OS_API_PORT` | `8000` | API port |
| `TR_OS_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CORS origins (comma-separated) |
| `TR_OS_AUTH_MODE` | `dev` | Auth mode: dev or bearer |
| `TR_OS_AUTH_SECRET` | (empty) | HMAC secret for bearer tokens |
| `TR_OS_MAX_WORKERS` | `4` | Thread pool workers |
| `TR_OS_MAX_CONCURRENT_MISSIONS` | `10` | Max concurrent missions |
| `TR_OS_SSE_HEARTBEAT_SEC` | `15` | SSE heartbeat interval |
| `TR_OS_IDEMPOTENCY_TTL_SEC` | `3600` | Idempotency key TTL |
| `TR_OS_RATE_LIMIT_RPM` | `60` | Rate limit (requests/min) |
| `TR_OS_DATABASE_URL` | `data/tros.db` | SQLite database path |
| `TR_OS_BUILD_VERSION` | `0.10.0` | Build version (injected by CI) |
| `TR_OS_COMMIT_SHA` | (git) | Commit SHA (injected by CI) |
| `TR_OS_BUILD_TIME` | (build) | ISO 8601 build timestamp |
| `TR_OS_WORKER_COUNT` | `1` | Worker count (must be 1 in production) |
| `TR_OS_ATLAS_AUTH_TOKEN` | (empty) | Atlas API authentication token |
| `DEEPSEEK_API_KEY` | (required) | DeepSeek API key |

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/missions` | Create recovery mission (202) |
| `GET` | `/api/v1/missions/:id` | Get mission result |
| `GET` | `/api/v1/missions/:id/status` | Poll mission progress |
| `POST` | `/api/v1/missions/:id/cancel` | Cancel running mission |
| `GET` | `/api/v1/missions/:id/events` | SSE event stream |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/readiness` | Readiness probe |
| `GET` | `/api/v1/metrics` | Aggregate metrics |

### Example

```bash
# Create a mission
curl -X POST http://localhost:8000/api/v1/missions \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "origin": "KUL",
    "destination": "NRT",
    "departure_date": "2026-08-20",
    "traveler_count": 1,
    "currency": "USD",
    "traveler_type": "Business",
    "disruption_type": "FlightCancelled",
    "budget_limit": 1000
  }'

# Poll status
curl http://localhost:8000/api/v1/missions/{id}/status

# Get result
curl http://localhost:8000/api/v1/missions/{id}
```

## Testing

```bash
# Backend tests (549 tests)
pytest

# Frontend tests (25 tests)
cd frontend && npm test

# All tests
pytest && cd frontend && npm test
```

## Project Structure

```
tros/
  agents/          # Phase 1-5 agents (context, planning, flight, budget, critic)
  execution/       # Phase 7 execution framework
  service/         # Phase 7 mission service boundary
  recovery/        # Phase 6 recovery engine
  api/             # Phase 8 FastAPI API layer
    migrations/    # Phase 10 database migrations
    repositories_sqlite.py  # Phase 10 SQLite persistence
    db.py          # Phase 10 connection management
    build_info.py  # Phase 10 version metadata
frontend/
  src/
    api/           # Typed API client
    components/    # React UI components
    hooks/         # State management hooks
    styles/        # Mobile-first CSS
  public/          # PWA manifest, service worker, icons
scripts/
  smoke_test.py    # Phase 10 deployment smoke test
  init-letsencrypt.sh  # Phase 10 TLS setup
.github/workflows/  # Phase 10 CI/CD pipelines
nginx/             # Phase 10 TLS configuration
tests/             # Backend test suite (549 tests)
```

## License

Hackathon project — not for production use.
