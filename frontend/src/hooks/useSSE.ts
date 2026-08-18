/** SSE hook — subscribe to real-time mission events. */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { SSEEvent } from '../api/types';

export function useSSE(missionId: string | null) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (!missionId) return;

    const url = `/api/v1/missions/${missionId}/events`;
    const es = new EventSource(url);
    eventSourceRef.current = es;
    setConnected(true);
    setError(null);

    es.onmessage = (event) => {
      try {
        const data: SSEEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, data]);

        // Close on terminal event
        if (['mission.completed', 'mission.failed', 'mission.cancelled'].includes(data.type)) {
          es.close();
          setConnected(false);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setError('Connection lost');
      setConnected(false);
      es.close();
    };
  }, [missionId]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [connect]);

  return { events, connected, error, reconnect: connect };
}
