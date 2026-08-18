import { describe, it, expect } from 'vitest';
import type {
  FlightInfo,
  MissionResult,
  MissionStatus,
  MissionRequest,
  SSEEvent,
  ApiError,
} from './types';

describe('API types', () => {
  it('FlightInfo has required fields', () => {
    const flight: FlightInfo = {
      flight_number: 'MH70',
      carrier: 'Malaysia Airlines',
      departure: '202608200705',
      arrival: '202608201530',
      duration_minutes: 505,
      stops: 0,
      price: 450.5,
      currency: 'USD',
      score: 8.5,
    };
    expect(flight.flight_number).toBe('MH70');
    expect(flight.price).toBeGreaterThan(0);
  });

  it('MissionRequest has required fields', () => {
    const req: MissionRequest = {
      origin: 'KUL',
      destination: 'NRT',
      departure_date: '2026-08-20',
      traveler_count: 1,
      currency: 'USD',
      traveler_type: 'Business',
      disruption_type: 'FlightCancelled',
      budget_limit: 1000,
    };
    expect(req.origin).toBe('KUL');
    expect(req.traveler_count).toBeGreaterThanOrEqual(1);
  });

  it('MissionStatus has phase and progress', () => {
    const status: MissionStatus = {
      mission_id: 'm-1',
      execution_id: 'e-1',
      status: 'RUNNING',
      phase: 'PLANNING',
      progress: 0.25,
      started_at: '2026-08-20T07:00:00Z',
      elapsed_ms: 5000,
    };
    expect(status.progress).toBeGreaterThanOrEqual(0);
    expect(status.progress).toBeLessThanOrEqual(1);
  });

  it('ApiError has structured error info', () => {
    const err: ApiError = {
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid origin',
        retryable: false,
        request_id: 'req-1',
      },
    };
    expect(err.error.code).toBe('VALIDATION_ERROR');
    expect(err.error.retryable).toBe(false);
  });
});
