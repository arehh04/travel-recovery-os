import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runSwarm, approveSwarm, rejectSwarm } from './swarm';
import { api } from './client';
import type { SwarmState, SwarmRunRequest } from './types';

vi.mock('./client', () => ({
  api: {
    post: vi.fn(),
  },
}));

describe('Swarm API Client', () => {
  const mockState: SwarmState = {
    disruption: {
      pnr: 'TEST-999',
      original_flight: 'BA117',
      disruption_type: 'CANCELLED',
      delay_minutes: 360,
      affected_passengers: ['Test Passenger'],
    },
    passenger_context: {},
    inventory_candidates: [
      {
        flight_number: 'BA102',
        departure_time: '2026-08-21T10:00:00Z',
        arrival_time: '2026-08-21T17:00:00Z',
        price_differential: 0.0,
        score: 0.95,
        carrier: 'BA',
      },
    ],
    selected_solution: {
      flight_number: 'BA102',
      departure_time: '2026-08-21T10:00:00Z',
      arrival_time: '2026-08-21T17:00:00Z',
      price_differential: 0.0,
      score: 0.95,
      carrier: 'BA',
    },
    human_consensus_status: 'PENDING',
    execution_receipt: null,
    agent_logs: ['Swarm initialized'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls /swarm/run with correct payload', async () => {
    const mockPost = vi.mocked(api.post).mockResolvedValue(mockState);
    const req: SwarmRunRequest = {
      pnr: 'TEST-999',
      original_flight: 'BA117',
      disruption_type: 'CANCELLED',
      delay_minutes: 360,
    };

    const result = await runSwarm(req);

    expect(mockPost).toHaveBeenCalledWith('/swarm/run', req);
    expect(result).toEqual(mockState);
  });

  it('calls /swarm/approve with state payload', async () => {
    const approvedState: SwarmState = {
      ...mockState,
      human_consensus_status: 'APPROVED',
      execution_receipt: { status: 'CONFIRMED', confirmation_code: 'CONF-123' },
    };
    const mockPost = vi.mocked(api.post).mockResolvedValue(approvedState);

    const result = await approveSwarm(mockState);

    expect(mockPost).toHaveBeenCalledWith('/swarm/approve', { state: mockState });
    expect(result.human_consensus_status).toBe('APPROVED');
    expect(result.execution_receipt).toBeTruthy();
  });

  it('calls /swarm/reject with reason', async () => {
    const rejectedState: SwarmState = {
      ...mockState,
      human_consensus_status: 'REJECTED',
    };
    const mockPost = vi.mocked(api.post).mockResolvedValue(rejectedState);

    const result = await rejectSwarm(mockState, 'Too expensive');

    expect(mockPost).toHaveBeenCalledWith('/swarm/reject', {
      state: mockState,
      reason: 'Too expensive',
    });
    expect(result.human_consensus_status).toBe('REJECTED');
  });
});
