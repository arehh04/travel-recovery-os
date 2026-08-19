/** SSE hook — subscribe to real-time mission events (Phase 9 hardened). */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SSEEvent } from '../api/types';

const MAX_RECONNECT_ATTEMPTS = 3;
const HEARTBEAT_TIMEOUT_MS = 30000; // 30s without heartbeat → reconnect

export function useSSE(missionId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttempts = useRef(0);
  const heartbeatTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetHeartbeatTimer = useCallback(() => {
    if (heartbeatTimer.current) {
      clearTimeout(heartbeatTimer.current);
    }
    heartbeatTimer.current = setTimeout(() => {
      // No heartbeat received — trigger reconnect
      eventSourceRef.current?.close();
      setConnected(false);
      attemptReconnect();
    }, HEARTBEAT_TIMEOUT_MS);
  }, []);

  const attemptReconnect = useCallback(() => {
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
      setError('Max reconnect attempts reached');
      return;
    }
    reconnectAttempts.current += 1;
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current - 1), 8000);
    setTimeout(() => {
      if (missionId) connect(missionId);
    }, delay);
  }, [missionId]);

  const connect = useCallback((id: string) => {
    const url = `/api/v1/missions/${id}/events`;
    const es = new EventSource(url);
    eventSourceRef.current = es;
    setConnected(true);
    setError(null);
    resetHeartbeatTimer();

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);

        // Reset heartbeat on any event (heartbeat events count too)
        resetHeartbeatTimer();

        setEvents((prev) => [...prev, data]);

        // Close on terminal event
        if (['mission.completed', 'mission.failed', 'mission.cancelled'].includes(data.type)) {
          es.close();
          setConnected(false);
          if (heartbeatTimer.current) clearTimeout(heartbeatTimer.current);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      if (heartbeatTimer.current) clearTimeout(heartbeatTimer.current);
      attemptReconnect();
    };
  }, [resetHeartbeatTimer, attemptReconnect]);

  useEffect(() => {
    if (!missionId) return;
    reconnectAttempts.current = 0;
    connect(missionId);
    return () => {
      eventSourceRef.current?.close();
      if (heartbeatTimer.current) clearTimeout(heartbeatTimer.current);
    };
  }, [missionId, connect]);

  return { events, connected, error, reconnect: () => { reconnectAttempts.current = 0; if (missionId) connect(missionId); } };
}
