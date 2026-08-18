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
| | **Total** | **340** |

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
cp .env.example .env
# Fill in credentials
docker-compose up --build
```

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
# Backend tests
pytest

# Frontend tests
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
frontend/
  src/
    api/           # Typed API client
    components/    # React UI components
    hooks/         # State management hooks
    styles/        # Mobile-first CSS
  public/          # PWA manifest, service worker, icons
tests/             # Backend test suite
```

## License

Hackathon project — not for production use.
