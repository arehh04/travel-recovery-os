/** Health API client. */

import { api } from './client';
import type { HealthResponse } from './types';

export const healthApi = {
  check(): Promise<HealthResponse> {
    return api.get<HealthResponse>('/health');
  },

  readiness(): Promise<HealthResponse> {
    return api.get<HealthResponse>('/readiness');
  },
};
