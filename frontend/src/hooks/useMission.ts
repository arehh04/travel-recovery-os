/** Mission state management hook — hardened with state machine (Phase 9). */

import { useState, useCallback, useRef, useEffect } from 'react';
import { missionsApi } from '../api/missions';
import type { MissionRequest, MissionResult, MissionStatus } from '../api/types';

type MissionState =
  | { phase: 'idle' }
  | { phase: 'submitting' }
  | { phase: 'queued'; missionId: string }
  | { phase: 'running'; missionId: string; status: MissionStatus }
  | { phase: 'cancelling'; missionId: string }
  | { phase: 'completed'; result: MissionResult }
  | { phase: 'error'; message: string };

// Valid state transitions
const VALID_TRANSITIONS: Record<string, string[]> = {
  idle: ['submitting', 'error'],
  submitting: ['queued', 'running', 'error'],
  queued: ['running', 'error'],
  running: ['completed', 'cancelling', 'error'],
  cancelling: ['completed', 'error'],
  completed: ['idle'],
  error: ['idle', 'submitting'],
};

function isValidTransition(from: string, to: string): boolean {
  return VALID_TRANSITIONS[from]?.includes(to) ?? false;
}

export function useMission() {
  const [state, setState] = useState<MissionState>({ phase: 'idle' });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const safeSetState = useCallback((newState: MissionState) => {
    setState((prev) => {
      if (!isValidTransition(prev.phase, newState.phase)) {
        console.warn(`Invalid state transition: ${prev.phase} -> ${newState.phase}`);
        return prev;
      }
      return newState;
    });
  }, []);

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
        safeSetState({ phase: 'running', missionId, status });

        if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(status.status)) {
          stopPolling();
          const result = await missionsApi.getResult(missionId);
          safeSetState({ phase: 'completed', result });
        }
      } catch (err: any) {
        // Keep polling on transient errors
      }
    }, 2000);
  }, [stopPolling, safeSetState]);

  const createMission = useCallback(async (request: MissionRequest) => {
    safeSetState({ phase: 'submitting' });
    try {
      const idempotencyKey = crypto.randomUUID();
      const created = await missionsApi.create(request, idempotencyKey);
      safeSetState({ phase: 'queued', missionId: created.mission_id });
      safeSetState({
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
      safeSetState({ phase: 'error', message: err.message || 'Failed to create mission' });
    }
  }, [pollStatus, safeSetState]);

  const cancelMission = useCallback(async () => {
    if (state.phase !== 'running') return;
    const missionId = state.missionId;
    safeSetState({ phase: 'cancelling', missionId });
    try {
      await missionsApi.cancel(missionId);
    } catch {
      // Revert to running on failure
      safeSetState({ phase: 'running', missionId, status: state.status });
    }
  }, [state, safeSetState]);

  const reset = useCallback(() => {
    stopPolling();
    safeSetState({ phase: 'idle' });
  }, [stopPolling, safeSetState]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { state, createMission, cancelMission, reset };
}
