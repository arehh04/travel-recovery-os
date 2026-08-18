/** Typed mission API client. */

import { api } from './client';
import type {
  MissionCreated,
  MissionRequest,
  MissionResult,
  MissionStatus,
  CancelResponse,
} from './types';

export const missionsApi = {
  create(request: MissionRequest, idempotencyKey?: string): Promise<MissionCreated> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    return api.post<MissionCreated>('/missions', request, headers);
  },

  getResult(missionId: string): Promise<MissionResult> {
    return api.get<MissionResult>(`/missions/${missionId}`);
  },

  getStatus(missionId: string): Promise<MissionStatus> {
    return api.get<MissionStatus>(`/missions/${missionId}/status`);
  },

  cancel(missionId: string): Promise<CancelResponse> {
    return api.post<CancelResponse>(`/missions/${missionId}/cancel`);
  },
};
