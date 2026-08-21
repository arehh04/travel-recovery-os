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

export interface GamificationStats {
  time_saved_minutes: number;
  money_saved: number;
  carbon_offset_kg: number;
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
  gamification?: GamificationStats;
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

export interface SwarmCandidateRoute {
  flight_number: string;
  departure_time: string;
  arrival_time: string;
  price_differential: number;
  score: number;
  carrier: string;
}

export interface SwarmDisruptionEvent {
  pnr: string;
  original_flight: string;
  disruption_type: string;
  delay_minutes: number;
  affected_passengers: string[];
}

export interface SwarmState {
  disruption: SwarmDisruptionEvent;
  passenger_context: Record<string, any>;
  inventory_candidates: SwarmCandidateRoute[];
  selected_solution: SwarmCandidateRoute | null;
  human_consensus_status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'AUTO_APPROVED' | 'EXECUTED';
  execution_receipt: Record<string, any> | null;
  agent_logs: string[];
}

export interface SwarmRunRequest {
  pnr: string;
  original_flight: string;
  disruption_type?: string;
  delay_minutes?: number;
  affected_passengers?: string[];
  passenger_context?: Record<string, any>;
  auto_execute?: boolean;
}

export interface SwarmApproveRequest {
  state: SwarmState;
}

export interface SwarmRejectRequest {
  state: SwarmState;
  reason?: string;
}

export interface LoyaltyAccount {
  id?: number;
  program_name: string;
  alliance: string;
  tier_status: string;
  member_number: string;
  points_balance: number;
}

export interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  phone: string;
  passport_number: string;
  nationality: string;
  seat_preference: string;
  meal_preference: string;
  max_layover_hours: number;
  preferred_alliance: string;
  updated_at?: string;
  loyalty_accounts: LoyaltyAccount[];
}

export interface RegulatoryClaim {
  id: string;
  mission_id: string;
  regulation: string;
  statutory_tier: string;
  amount: number;
  currency: string;
  status: string;
  claim_letter: string;
  created_at: string;
}

export interface MissionHistoryItem {
  mission_id: string;
  execution_id: string;
  status: string;
  phase: string;
  progress: number;
  started_at: string;
  completed_at?: string | null;
  has_result: boolean;
  recommended_flight?: string | null;
  carrier?: string | null;
  price?: number | null;
  currency: string;
  confidence: number;
}

export interface WeatherAssessment {
  airport: string;
  temperature_c: number;
  condition: string;
  wind_speed_knots: number;
  visibility_km: number;
  risk_score: number;
  flight_category: string;
}

export interface HotelVoucher {
  voucher_code: string;
  hotel_name: string;
  star_rating: number;
  distance_from_terminal_km: number;
  shuttle_logistics: string;
  nightly_rate_usd: number;
  rooms_booked: number;
  check_in_window: string;
  check_out_time: string;
  amenities: string[];
  airline_duty_of_care_covered: boolean;
  traveler_out_of_pocket_cost: number;
  meal_voucher_allowance_usd: number;
}

export interface TransportOption {
  voucher_code: string;
  mode: string;
  operator_service: string;
  departure_hub: string;
  arrival_hub: string;
  duration_minutes: number;
  unit_price_usd: number;
  total_price_usd: number;
  carbon_offset_kg: number;
  baggage_policy: string;
  seat_type: string;
  wifi_guaranteed: boolean;
}


