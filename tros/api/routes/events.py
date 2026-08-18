"""SSE events endpoint — real-time mission progress (Phase 8).

Uses Server-Sent Events to stream mission lifecycle events.
Clients subscribe to GET /api/v1/missions/:mission_id/events
and receive events as they occur.

Event types:
- mission.started
- mission.phase_changed
- mission.recovery.started
- mission.recovery.completed
- mission.completed
- mission.failed
- mission.cancelled
- mission.cancelling
"""

from __future__ import annotations

import asyncio
import json
import queue

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from tros.api.auth import AuthContext, require_auth
from tros.api.deps import get_execution_manager
from tros.api.execution_manager import ExecutionManager

router = APIRouter(prefix="/api/v1/missions", tags=["events"])


async def _event_generator(mission_id: str, manager: ExecutionManager):
    """Async generator that yields SSE events from the mission queue."""
    execution = manager.get_execution(mission_id)
    if not execution:
        # Send error event and stop
        yield f"data: {json.dumps({'type': 'error', 'message': 'Mission not found'})}\n\n"
        return

    # Send initial status
    yield f"data: {json.dumps({'type': 'connected', 'mission_id': mission_id, 'status': execution.status})}\n\n"

    # Stream events until terminal state or timeout
    max_wait = 300  # 5 minutes max
    waited = 0
    while waited < max_wait:
        try:
            event = execution.events.get_nowait()
            yield f"data: {json.dumps(event)}\n\n"

            # Stop after terminal event
            if event.get("type") in ("mission.completed", "mission.failed", "mission.cancelled"):
                return
        except queue.Empty:
            # No event yet, wait a bit
            await asyncio.sleep(0.5)
            waited += 0.5

            # Check if mission is already terminal
            if execution.status in ("COMPLETED", "FAILED", "CANCELLED"):
                # Send final status event
                yield f"data: {json.dumps({'type': 'mission.completed', 'mission_id': mission_id, 'status': execution.status})}\n\n"
                return

    # Timeout
    yield f"data: {json.dumps({'type': 'timeout', 'message': 'SSE stream timeout'})}\n\n"


@router.get("/{mission_id}/events")
async def mission_events(
    mission_id: str,
    auth: AuthContext = Depends(require_auth),
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Subscribe to real-time mission progress events via SSE."""
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
        _event_generator(mission_id, manager),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
