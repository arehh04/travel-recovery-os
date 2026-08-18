# Phase 8: API + Mobile-First PWA + Deployment Readiness

## Overview

Phase 8 transforms the TR-OS multi-agent mission engine from a production-ready Python core into a **complete HTTP-accessible application** with a mobile-first Progressive Web App frontend, real-time progress updates via SSE, and Docker-based deployment.

### Architecture Decision

**FastAPI (Python)** chosen over Node.js+Fastify because:
- Entire engine is Python (MissionService, SupervisorAgent, RecoveryEngine)
- MissionService already has a clean service boundary
- Native Pydantic integration — no serialization overhead
- Single deployment unit, single language
- Async support for SSE, automatic OpenAPI docs

### System Architecture

```
PWA (React + TypeScript + Vite)
    │ HTTPS
FastAPI API Service (Python)
    │
ExecutionManager (threading.ThreadPoolExecutor)
    │
MissionService (Phase 7)
    │
SupervisorAgent (Phase 1–6)
    │
DeepSeek LLM + Atlas CLI
```

---

## What Was Built

### Backend: API Layer (`tros/api/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app factory, CORS, security headers, lifespan |
| `config.py` | Environment-driven API configuration |
| `deps.py` | FastAPI dependencies (get_service, get_auth_context) |
| `models.py` | Pydantic request/response schemas |
| `errors.py` | Error handler: MissionError → HTTP status codes |
| `auth.py` | AuthContext dataclass, dev-mode provider |
| `execution_manager.py` | Background execution with ThreadPoolExecutor |
| `routes/missions.py` | POST/GET /missions, status, cancel |
| `routes/health.py` | GET /health, GET /readiness |
| `routes/events.py` | GET /missions/:id/events (SSE) |

### Frontend: React + TypeScript + Vite PWA (`frontend/`)

| Directory | Files | Purpose |
|-----------|-------|---------|
| `src/api/` | 4 files | Typed API client (client, missions, health, types) |
| `src/hooks/` | 2 files | useMission (state + polling), useSSE (events) |
| `src/components/` | 6 files | MissionForm, MissionProgress, FlightCard, MissionResult, ErrorDisplay, OfflineBanner |
| `src/styles/` | 1 file | Mobile-first CSS with CSS variables |
| `public/` | 4 files | manifest.json, sw.js, SVG icons |

### Deployment

| File | Purpose |
|------|---------|
| `.env.example` | Environment variable template |
| `Dockerfile` | Multi-stage build (Node frontend + Python runtime) |
| `docker-compose.yml` | Single-service deployment |

---

## API Endpoints

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/api/v1/missions` | Create mission | 202 Accepted |
| `GET` | `/api/v1/missions/:id` | Get mission result | 200 OK |
| `GET` | `/api/v1/missions/:id/status` | Get mission status | 200 OK |
| `POST` | `/api/v1/missions/:id/cancel` | Cancel mission | 200 OK |
| `GET` | `/api/v1/missions/:id/events` | SSE event stream | text/event-stream |
| `GET` | `/api/v1/health` | Health check | 200 OK |
| `GET` | `/api/v1/readiness` | Readiness probe | 200 OK |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid origin: must be 3-letter IATA code",
    "retryable": false,
    "request_id": "req-abc123"
  }
}
```

### Error Mapping

| MissionError | HTTP Status |
|---|---|
| ValidationError | 400 |
| ConstraintViolationError | 422 |
| CancellationError | 499 |
| AtlasError / AtlasTimeoutError | 502 |
| LLMError / LLMTimeoutError | 503 |
| Mission not found | 404 |
| Idempotency conflict | 409 |
| InternalMissionError | 500 |

---

## Execution Manager

Background execution using `concurrent.futures.ThreadPoolExecutor`:

- **submit()** — starts mission in background thread, returns immediately with mission_id
- **get_status()** — returns current phase, progress (0–1), elapsed time
- **cancel()** — signals CancellationToken, graceful shutdown
- **get_result()** — returns sanitized MissionResult when completed
- **Idempotency** — `Idempotency-Key` header with payload hash conflict detection

### SSE Events

Real-time progress via Server-Sent Events:
- `mission.started` — mission accepted and queued
- `mission.phase_changed` — phase transition (CONTEXT → PLANNING → ... → COMPLETED)
- `mission.recovery.started` — recovery engine activated
- `mission.completed` — mission finished successfully
- `mission.failed` — mission failed
- `mission.cancelled` — mission cancelled

---

## Frontend PWA

### Mobile-First UX

- **Mission form**: origin, destination, date, travelers, currency
- **Progress view**: phase-based progress with ✓/●/○ indicators, progress bar, elapsed time
- **Result view**: flight card (number, route, price, stops, duration, confidence), alternatives, budget, conflicts
- **Error display**: structured error with retry button
- **Offline banner**: automatic online/offline detection

### PWA Features

- `manifest.json` — installable app with icons and theme
- Service worker — cache-first for static assets, network-first for API
- Offline detection — show shell but indicate backend required
- Large touch targets (min 44px)

### State Machine

```
idle → submitting → running → completed
                         ↓
                       error → idle (retry)
```

Polling-based status updates every 2 seconds during `running` state.

---

## Security

1. CORS configured from environment (not allow-all)
2. Security headers: X-Content-Type-Options, X-Frame-Options, X-Request-Id
3. AuthContext boundary — API never trusts raw client user_id
4. Dev-mode auth via X-Dev-User-Id header; production-replaceable with JWT/OAuth
5. No secrets in API responses or frontend
6. Structured error responses — no stack traces leaked
7. Request ID echo for debugging
8. Idempotency prevents duplicate mission execution

---

## Key Constraints Preserved

1. PWA never talks to Atlas directly
2. API calls MissionService only
3. SupervisorAgent controls orchestration
4. ToolExecutor remains security boundary
5. Ranking remains deterministic
6. Evidence remains Atlas-derived
7. Recovery remains bounded (max 2)
8. MissionResult remains sanitized
9. No secrets in API responses or frontend
10. No infinite background jobs

---

## Testing

### Backend API Tests (`tests/test_api.py`) — 59 tests

| Category | Tests |
|----------|-------|
| App config | 4 |
| Health endpoints | 6 |
| Mission validation | 9 |
| Mission status | 3 |
| Mission result | 3 |
| Cancellation | 3 |
| Idempotency | 3 |
| Error format | 3 |
| CORS & security | 3 |
| Auth boundary | 4 |
| Execution manager | 9 |
| Error mapping | 6 |
| Security regression | 3 |

### Frontend Tests (6 test files) — 25 tests

| File | Tests |
|------|-------|
| MissionForm | 5 |
| MissionProgress | 5 |
| FlightCard | 6 |
| ErrorDisplay | 3 |
| OfflineBanner | 2 |
| API types | 4 |

### Total Test Count

- **Phase 1–6**: 188 tests
- **Phase 7**: 68 tests
- **Phase 8 backend**: 59 tests
- **Phase 8 frontend**: 25 tests
- **Grand total**: 340 tests

---

## Running

### Development

```bash
# Backend
uvicorn tros.api.app:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

Frontend dev server at http://localhost:5173 proxies `/api` to backend at http://localhost:8000.

### Docker

```bash
cp .env.example .env
# Fill in DEEPSEEK_API_KEY and ATLAS_AUTH_TOKEN
docker-compose up --build
```

API available at http://localhost:8000 with OpenAPI docs at http://localhost:8000/docs.

---

## Files Added in Phase 8

```
tros/api/
  __init__.py
  app.py
  auth.py
  config.py
  deps.py
  errors.py
  execution_manager.py
  models.py
  routes/
    __init__.py
    events.py
    health.py
    missions.py

frontend/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  public/
    manifest.json
    sw.js
    icons/
      icon-192.svg
      icon-512.svg
  src/
    main.tsx
    App.tsx
    vite-env.d.ts
    api/
      client.ts
      health.ts
      missions.ts
      types.ts
      types.test.ts
    components/
      MissionForm.tsx
      MissionForm.test.tsx
      MissionProgress.tsx
      MissionProgress.test.tsx
      FlightCard.tsx
      FlightCard.test.tsx
      MissionResult.tsx
      ErrorDisplay.tsx
      ErrorDisplay.test.tsx
      OfflineBanner.tsx
      OfflineBanner.test.tsx
    hooks/
      useMission.ts
      useSSE.ts
    styles/
      app.css
    test/
      setup.ts

.env.example
Dockerfile
docker-compose.yml
tests/test_api.py
```
