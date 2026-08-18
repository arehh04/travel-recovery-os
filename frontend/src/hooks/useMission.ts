/** Mission state management hook. */

import { useState, useCallback, useRef, useEffect } from 'react';
import { missionsApi } from '../api/missions';
import type { MissionRequest, MissionResult, MissionStatus } from '../api/types';

type MissionState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'running'; missionId: string; status: MissionStatus }
  | { phase: 'completed'; result: MissionResult }
  | { phase: 'error'; message: string };

export function useMission() {
  const [state, setState] = useState<MissionState>({ phase: 'idle' });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollStatus = useCallback((missionId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const status = await missionsApi.getStatus(missionId);
        setState({ phase: 'running', missionId, status });

        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status.status)) {
          stopPolling();
          const result = await missionsApi.getResult(missionId);
          setState({ phase: 'completed', result });
        }
      } catch (err: any) {
        // Keep polling on transient errors
      }
    }, 2000);
  }, [stopPolling]);

  const createMission = useCallback(async (request: MissionRequest) => {
    setState({ phase: 'submitting' });
    try {
      const idempotencyKey = crypto.randomUUID();
      const created = await missionsApi.create(request, idempotencyKey);
      setState({
        phase: 'running',
        missionId: created.mission_id,
        status: {
          mission_id: created.mission_id,
          execution_id: created.execution_id,
          status: created.status,
          phase: 'CONTEXT',
          progress: 0,
          started_at: new Date().toISOString(),
          elapsed_ms: 0,
        },
      });
      pollStatus(created.mission_id);
    } catch (err: any) {
      setState({ phase: 'error', message: err.message || 'Failed to create mission' });
    }
  }, [pollStatus]);

  const cancelMission = useCallback(async () => {
    if (state.phase !== 'running') return;
    try {
      await missionsApi.cancel(state.missionId);
    } catch {
      // ignore
    }
  }, [state]);

  const reset = useCallback(() => {
    stopPolling();
    setState({ phase: 'idle' });
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { state, createMission, cancelMission, reset };
}
