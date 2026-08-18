/** API response types — mirrors the Python API schemas. */

export interface FlightInfo {
  flight_number: string;
  carrier: string;
  departure: string;
  arrival: string;
  duration_minutes: number;
  stops: number;
  price: number;
  currency: string;
  score: number;
}

export interface RecoveryInfo {
  occurred: boolean;
  attempts: number;
  reason: string;
  recovered: boolean;
}

export interface ConflictInfo {
  count: number;
  has_critical: boolean;
}

export interface ExecutionMetadata {
  mission_id: string;
  execution_id: string;
  request_id: string;
  status: string;
  duration_ms: number;
}

export interface MissionResult {
  mission_id: string;
  execution_id: string;
  status: string;
  recommendation: FlightInfo | null;
  alternatives: FlightInfo[];
  budget: Record<string, unknown>;
  confidence: number;
  recovery: RecoveryInfo;
  conflicts: ConflictInfo;
  execution_metadata: ExecutionMetadata;
}

export interface MissionCreated {
  mission_id: string;
  execution_id: string;
  status: string;
}

export interface MissionStatus {
  mission_id: string;
  execution_id: string;
  status: string;
  phase: string;
  progress: number;
  started_at: string;
  elapsed_ms: number;
}

export interface CancelResponse {
  mission_id: string;
  status: string;
  message: string;
}

export interface HealthCheck {
  name: string;
  status: string;
  message: string;
}

export interface HealthResponse {
  status: string;
  checks: HealthCheck[];
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    request_id: string;
  };
}

export interface MissionRequest {
  origin: string;
  destination: string;
  departure_date: string;
  traveler_count: number;
  currency: string;
  traveler_type: string;
  disruption_type: string;
  budget_limit: number;
}

export interface SSEEvent {
  type: string;
  mission_id: string;
  timestamp?: string;
  [key: string]: unknown;
}
