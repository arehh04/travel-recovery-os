/** App-level types for dynamic page data. */

import type { FlightInfo, MissionResult, MissionStatus } from '../api/types';

/** Evidence card for the recovery plan page. */
export interface EvidenceCard {
  icon: string;
  title: string;
  detail: string;
  span?: boolean; // if true, spans full width in 2-col grid
}

/** Evidence validation page data. */
export interface EvidenceData {
  flightRef: string;
  punctualityPct: number;
  availableSeats: number;
  layoverTolerance: string;
  budgetAmount: number;
  budgetLimit: number;
  budgetPct: number;
  confidenceScore: number;
  altFlightRef: string;
  connectionP1: number;
  connectionP2: number;
  reflection: string;
  evidenceItems: { icon: string; title: string; detail: string }[];
  constraintItems: { title: string; detail: string }[];
}

/** History mission item. */
export interface HistoryMission {
  id: string;
  origin: string;
  destination: string;
  date: string;
  status: 'Recovered' | 'Completed' | 'Cancelled' | 'Failed';
  description: string;
  hasDetails: boolean;
}

/** Profile page data. */
export interface ProfileData {
  name: string;
  flyerStatus: string;
  avatarUrl?: string;
  preferences: string[];
  companionsCount: number;
  currency: string;
  appVersion: string;
  notificationsEnabled: boolean;
}

/** Recovery engine step. */
export interface EngineStep {
  iconBg: string;
  iconText: string;
  icon: string;
  filled: boolean;
  title: string;
  detail: string;
  active?: boolean;
}

/** Alternative flight card. */
export interface AlternativeFlight {
  flight: FlightInfo;
  badge: string;
  badgeStyle: 'tertiary' | 'secondary';
  score: number;
  origin: string;
  destination: string;
  depTime: string;
  arrTime: string;
  duration: string;
  stops: number;
  stopLocation?: string;
  isDirect: boolean;
  evidence: string;
  primaryAction: boolean;
}

/** Phase timeline steps for live recovery. */
export interface PhaseStep {
  label: string;
  state: 'completed' | 'current' | 'pending';
}

/** Mission context passed between pages via router state. */
export interface MissionContext {
  missionId?: string;
  request?: {
    origin: string;
    destination: string;
    departure_date: string;
    traveler_count: number;
    budget_limit: number;
    currency: string;
  };
  result?: MissionResult;
  status?: MissionStatus;
}
