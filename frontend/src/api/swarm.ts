/** API client for TR-OS Multi-Agent Swarm endpoints. */

import { api } from './client';
import type {
  SwarmApproveRequest,
  SwarmRejectRequest,
  SwarmRunRequest,
  SwarmState,
} from './types';

/**
 * Execute the multi-agent swarm against a disruption event.
 */
export async function runSwarm(request: SwarmRunRequest): Promise<SwarmState> {
  return api.post<SwarmState>('/swarm/run', request);
}

/**
 * Approve the current pending swarm solution and trigger immediate execution/rebooking.
 */
export async function approveSwarm(state: SwarmState): Promise<SwarmState> {
  const req: SwarmApproveRequest = { state };
  return api.post<SwarmState>('/swarm/approve', req);
}

/**
 * Reject the current pending swarm solution with an optional reason.
 */
export async function rejectSwarm(state: SwarmState, reason: string = 'Declined by passenger'): Promise<SwarmState> {
  const req: SwarmRejectRequest = { state, reason };
  return api.post<SwarmState>('/swarm/reject', req);
}
