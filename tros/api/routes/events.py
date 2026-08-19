"""SSE events endpoint — hardened real-time mission progress (Phase 9/10).

Uses Server-Sent Events to stream mission lifecycle events with:
- Heartbeat events to keep connections alive
- Monotonically increasing event IDs
- Proper event: field with type names
- Client disconnect detection and cleanup
- Bounded connection lifetime
- Sanitized event payloads (no secrets)
- Last-Event-ID replay for reconnection (Phase 10)

Event types:
- mission.queued
- mission.running
- mission.phase
- mission.progress
- mission.completed
- mission.failed
- mission.cancelled
- heartbeat
"""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from tros.api.auth import AuthContext, require_auth
from tros.api.deps import get_execution_manager
from tros.api.execution_manager import ExecutionManager
from tros.api.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/missions", tags=["events"])

# Terminal SSE event types
_TERMINAL_EVENTS = frozenset({"mission.completed", "mission.failed", "mission.cancelled"})

# Event ID counter (monotonically increasing across all streams)
_event_counter = 0


def _next_event_id() -> str:
    global _event_counter
    _event_counter += 1
    return str(_event_counter)


def _sanitize_event(event: dict) -> dict:
    """Remove sensitive fields from event data before streaming."""
    sanitized = {}
    for key, value in event.items():
        # Skip sensitive fields
        if key.lower() in ("prompt", "raw_llm", "api_key", "secret", "token", "stack_trace"):
            continue
        sanitized[key] = value
    return sanitized


def _format_sse(event_type: str, data: dict, event_id: str | None = None) -> str:
    """Format a server-sent event string."""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


async def _event_generator(
    mission_id: str,
    manager: ExecutionManager,
    request: Request,
    last_event_id: int = 0,
):
    """Async generator that yields SSE events with heartbeats and disconnect detection."""
    settings = get_settings()
    heartbeat_interval = settings.sse_heartbeat_sec
    max_connection_sec = settings.sse_max_connection_sec
    poll_interval = 0.5

    execution = manager.get_execution(mission_id)
    if not execution:
        yield _format_sse("error", {"type": "error", "message": "Mission not found"}, _next_event_id())
        return

    # Send initial connection event
    yield _format_sse(
        "connected",
        {"type": "connected", "mission_id": mission_id, "status": execution.status},
        _next_event_id(),
    )

    # Replay missed events from repository (Phase 10)
    if last_event_id > 0 and manager._event_repo:
        try:
            missed_events = manager._event_repo.get_events(mission_id, after_id=last_event_id)
            for evt in missed_events:
                sanitized = _sanitize_event(evt)
                evt_type = evt.get("event_type", evt.get("type", "mission.progress"))
                yield _format_sse(evt_type, sanitized, _next_event_id())
        except Exception:
            logger.debug("Failed to replay events for %s", mission_id)

    start_time = time.time()
    last_heartbeat = start_time

    while True:
        now = time.time()

        # --- Bounded connection lifetime ---
        if now - start_time > max_connection_sec:
            yield _format_sse(
                "timeout",
                {"type": "timeout", "message": "SSE connection lifetime exceeded"},
                _next_event_id(),
            )
            return

        # --- Client disconnect detection ---
        if await request.is_disconnected():
            logger.debug("SSE client disconnected for mission %s", mission_id)
            return

        # --- Heartbeat ---
        if now - last_heartbeat >= heartbeat_interval:
            yield _format_sse(
                "heartbeat",
                {"type": "heartbeat", "timestamp": time.time()},
                _next_event_id(),
            )
            last_heartbeat = now

        # --- Drain event queue ---
        try:
            event = execution.events.get_nowait()
            sanitized = _sanitize_event(event)
            event_type = event.get("type", "mission.progress")
            yield _format_sse(event_type, sanitized, _next_event_id())

            # Terminal event — close stream
            if event_type in _TERMINAL_EVENTS:
                return
        except queue.Empty:
            pass

        # --- Check if mission already terminal ---
        if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
            terminal_type = f"mission.{execution.status.lower()}"
            yield _format_sse(
                terminal_type,
                {"type": terminal_type, "mission_id": mission_id, "status": execution.status},
                _next_event_id(),
            )
            return

        # Small sleep before next poll
        await asyncio.sleep(poll_interval)


@router.get("/{mission_id}/events")
async def mission_events(
    mission_id: str,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Subscribe to real-time mission progress events via SSE.

    Features:
    - Heartbeat every 15s (configurable)
    - Monotonically increasing event IDs
    - Auto-disconnect after 10 minutes
    - Client disconnect detection
    - Sanitized payloads (no secrets)
    - Last-Event-ID replay for reconnection (Phase 10)
    """
    # Parse Last-Event-ID for reconnection replay (Phase 10)
    last_event_id = 0
    last_id_header = request.headers.get("Last-Event-ID", "")
    if last_id_header:
        try:
            last_event_id = int(last_id_header)
        except (ValueError, TypeError):
            pass

    execution = manager.get_execution(mission_id)
    if not execution:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "MISSION_NOT_FOUND",
                    "message": f"Mission {mission_id} not found",
                    "retryable": False,
                },
            },
        )

    return StreamingResponse(
        _event_generator(mission_id, manager, request, last_event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
