/** Swarm Operations Dashboard — Visual Decentralized Multi-Agent Recovery Hub. */

import { useState } from 'react';
import { runSwarm, approveSwarm, rejectSwarm } from '../api/swarm';
import type { SwarmCandidateRoute, SwarmDisruptionEvent, SwarmState } from '../api/types';

interface PresetScenario {
  label: string;
  badge: string;
  disruption: SwarmDisruptionEvent;
}

const PRESET_SCENARIOS: PresetScenario[] = [
  {
    label: 'BA117 Cancellation (LHR → JFK)',
    badge: 'Flagship Transatlantic',
    disruption: {
      pnr: 'LON-9824X',
      original_flight: 'BA117',
      disruption_type: 'CANCELLED',
      delay_minutes: 360,
      affected_passengers: ['Dr. Samantha Vance', 'Marcus Vance'],
    },
  },
  {
    label: 'AA204 Snowstorm Ground Stop (ORD → LAX)',
    badge: 'Weather Disruption',
    disruption: {
      pnr: 'ORD-5512W',
      original_flight: 'AA204',
      disruption_type: 'DELAY_MISSED_CONN',
      delay_minutes: 420,
      affected_passengers: ['Elena Rostova'],
    },
  },
  {
    label: 'SQ321 Mechanical Outage (SIN → LHR)',
    badge: 'Long-haul Re-route',
    disruption: {
      pnr: 'SIN-1109K',
      original_flight: 'SQ321',
      disruption_type: 'MECHANICAL_AOG',
      delay_minutes: 480,
      affected_passengers: ['David Chen', 'Sarah Chen'],
    },
  },
];

interface AgentCardInfo {
  name: string;
  role: string;
  icon: string;
  color: string;
  description: string;
}

const SWARM_AGENTS: AgentCardInfo[] = [
  {
    name: 'Direct Scout',
    role: 'Primary Carrier Inventory',
    icon: 'flight_takeoff',
    color: 'border-blue-500/30 bg-blue-500/5 text-blue-600',
    description: 'Scans non-stop flights and next available departures on operating carrier.',
  },
  {
    name: 'Alliance Scout',
    role: 'Oneworld / SkyTeam / Star',
    icon: 'hub',
    color: 'border-purple-500/30 bg-purple-500/5 text-purple-600',
    description: 'Interrogates codeshare & cross-alliance bilateral inventory availability.',
  },
  {
    name: 'Intermodal Scout',
    role: 'High-Speed Rail & Multi-Modal',
    icon: 'train',
    color: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-600',
    description: 'Evaluates high-speed ground segments and alternate airport hubs.',
  },
  {
    name: 'Critic Ranker',
    role: 'Multi-Objective Utility Ranking',
    icon: 'balance',
    color: 'border-amber-500/30 bg-amber-500/5 text-amber-600',
    description: 'Scores candidates on arrival variance, delta price, layover risk, and comfort.',
  },
  {
    name: 'Consensus Arbiter',
    role: 'Human-in-the-Loop Policy',
    icon: 'how_to_reg',
    color: 'border-cyan-500/30 bg-cyan-500/5 text-cyan-600',
    description: 'Enforces traveler policy guardrails and triggers escalation if diff > threshold.',
  },
  {
    name: 'Execution Worker',
    role: 'GDS & Ticketing Engine',
    icon: 'task_alt',
    color: 'border-rose-500/30 bg-rose-500/5 text-rose-600',
    description: 'Issues electronic ticket confirmation, seat assignment, and digital pass.',
  },
];

export function SwarmDashboardPage() {
  const [selectedPreset, setSelectedPreset] = useState<PresetScenario>(PRESET_SCENARIOS[0]);
  const [customPnr, setCustomPnr] = useState(PRESET_SCENARIOS[0].disruption.pnr);
  const [customFlight, setCustomFlight] = useState(PRESET_SCENARIOS[0].disruption.original_flight);
  const [passengers, setPassengers] = useState(PRESET_SCENARIOS[0].disruption.affected_passengers.join(', '));
  const [delayMinutes, setDelayMinutes] = useState(PRESET_SCENARIOS[0].disruption.delay_minutes);

  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [swarmState, setSwarmState] = useState<SwarmState | null>(null);

  const handleSelectPreset = (preset: PresetScenario) => {
    setSelectedPreset(preset);
    setCustomPnr(preset.disruption.pnr);
    setCustomFlight(preset.disruption.original_flight);
    setPassengers(preset.disruption.affected_passengers.join(', '));
    setDelayMinutes(preset.disruption.delay_minutes);
    setError(null);
  };

  const handleRunSwarm = async () => {
    setLoading(true);
    setError(null);
    try {
      const passengerList = passengers
        .split(',')
        .map((p) => p.trim())
        .filter(Boolean);

      const result = await runSwarm({
        pnr: customPnr || 'PNR-AUTO',
        original_flight: customFlight || 'FL-100',
        disruption_type: selectedPreset.disruption.disruption_type,
        delay_minutes: Number(delayMinutes) || 180,
        affected_passengers: passengerList.length > 0 ? passengerList : ['Traveler 1'],
        auto_execute: false,
      });

      setSwarmState(result);
    } catch (err: any) {
      setError(err?.message || 'Failed to dispatch agent swarm.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!swarmState) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await approveSwarm(swarmState);
      setSwarmState(updated);
    } catch (err: any) {
      setError(err?.message || 'Approval failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!swarmState) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await rejectSwarm(swarmState, 'Traveler requested alternate routing');
      setSwarmState(updated);
    } catch (err: any) {
      setError(err?.message || 'Rejection failed.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 py-8 pb-32 flex flex-col gap-8 animate-fadeIn">
      {/* Header Banner */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-72 h-72 bg-gradient-to-br from-secondary/10 to-primary/5 rounded-full blur-3xl -z-0 pointer-events-none" />
        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container text-xs font-semibold uppercase tracking-wider mb-3">
            <span className="material-symbols-outlined text-[16px] animate-spin">cyclone</span>
            Decentralized Swarm Mesh
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-primary tracking-tight">
            Autonomous Travel Recovery Swarm
          </h1>
          <p className="text-on-surface-variant text-sm sm:text-base mt-2 leading-relaxed">
            Parallel AI scouts continuously fan-out across airline alliances, codeshares, and intermodal routes.
            State reducers aggregate candidates using <code className="bg-surface-container px-1.5 py-0.5 rounded text-xs text-primary font-mono">operator.add</code> with multi-attribute critic consensus.
          </p>
        </div>

        <div className="relative z-10 flex flex-col items-start md:items-end gap-2 bg-surface-container/60 p-4 rounded-xl border border-outline-variant/60">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping" />
            <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Swarm Mesh Active</span>
          </div>
          <span className="text-xs text-on-surface-variant">FastAPI Worker Daemon: Single-Tenant VPS</span>
          <span className="text-xs font-mono text-primary font-semibold">Max Concurrency: 4 Missions</span>
        </div>
      </div>

      {/* Disruption Trigger Controls */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-outline-variant pb-4">
          <div>
            <h2 className="text-lg font-bold text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">flash_on</span>
              Disruption Event Simulator
            </h2>
            <p className="text-xs text-on-surface-variant mt-0.5">Select a real-world scenario or customize parameters to dispatch the swarm</p>
          </div>
          <button
            onClick={handleRunSwarm}
            disabled={loading || actionLoading}
            className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-primary text-on-primary font-semibold text-sm shadow-md hover:bg-primary/90 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">refresh</span>
                Scouts Searching...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">rocket_launch</span>
                Deploy Swarm Mesh
              </>
            )}
          </button>
        </div>

        {/* Preset scenario selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PRESET_SCENARIOS.map((preset) => {
            const isSelected = selectedPreset.label === preset.label;
            return (
              <button
                key={preset.label}
                type="button"
                onClick={() => handleSelectPreset(preset)}
                className={`p-3.5 rounded-xl text-left border transition-all flex flex-col gap-1.5 ${
                  isSelected
                    ? 'border-secondary bg-secondary-container/30 ring-1 ring-secondary shadow-sm'
                    : 'border-outline-variant hover:border-outline bg-surface-container-lowest'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant">
                    {preset.badge}
                  </span>
                  {isSelected && <span className="material-symbols-outlined text-secondary text-[18px]">check_circle</span>}
                </div>
                <div className="font-semibold text-xs text-primary">{preset.label}</div>
                <div className="text-[11px] text-on-surface-variant font-mono">PNR: {preset.disruption.pnr}</div>
              </button>
            );
          })}
        </div>

        {/* Custom parameters */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">PNR Identifier</label>
            <input
              type="text"
              value={customPnr}
              onChange={(e) => setCustomPnr(e.target.value)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-outline-variant bg-surface focus:outline-none focus:ring-2 focus:ring-secondary"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Disrupted Flight</label>
            <input
              type="text"
              value={customFlight}
              onChange={(e) => setCustomFlight(e.target.value)}
              className="w-full text-xs font-mono px-3 py-2 rounded-lg border border-outline-variant bg-surface focus:outline-none focus:ring-2 focus:ring-secondary"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Delay (Minutes)</label>
            <input
              type="number"
              value={delayMinutes}
              onChange={(e) => setDelayMinutes(Number(e.target.value))}
              className="w-full text-xs px-3 py-2 rounded-lg border border-outline-variant bg-surface focus:outline-none focus:ring-2 focus:ring-secondary"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-on-surface-variant mb-1">Affected Passenger(s)</label>
            <input
              type="text"
              value={passengers}
              onChange={(e) => setPassengers(e.target.value)}
              className="w-full text-xs px-3 py-2 rounded-lg border border-outline-variant bg-surface focus:outline-none focus:ring-2 focus:ring-secondary"
            />
          </div>
        </div>

        {error && (
          <div className="p-3 bg-error-container text-error rounded-xl text-xs flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            {error}
          </div>
        )}
      </div>

      {/* Swarm Agents Fleet Visualizer */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-primary flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">groups</span>
            Decentralized Swarm Agent Fleet
          </h2>
          <span className="text-xs text-on-surface-variant font-mono">6 Specialized Workers</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {SWARM_AGENTS.map((agent) => (
            <div
              key={agent.name}
              className={`p-4 rounded-xl border ${agent.color} flex flex-col gap-2 shadow-sm transition-all hover:shadow-md`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px]">{agent.icon}</span>
                  <span className="font-bold text-xs text-primary">{agent.name}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface/80 border border-outline-variant font-mono">
                  {loading ? 'RUNNING' : swarmState ? 'SYNCED' : 'IDLE'}
                </span>
              </div>
              <div className="text-[11px] font-semibold text-secondary">{agent.role}</div>
              <p className="text-xs text-on-surface-variant leading-relaxed">{agent.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Swarm Result & State Reduction View */}
      {swarmState && (
        <div className="flex flex-col gap-6 animate-fadeIn">
          {/* Consensus Decision / Execution Banner */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 ${
                swarmState.human_consensus_status === 'APPROVED' || swarmState.human_consensus_status === 'AUTO_APPROVED'
                  ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/30'
                  : swarmState.human_consensus_status === 'REJECTED'
                  ? 'bg-rose-500/10 text-rose-600 border border-rose-500/30'
                  : 'bg-amber-500/10 text-amber-600 border border-amber-500/30 animate-pulse'
              }`}>
                <span className="material-symbols-outlined text-[28px]">
                  {swarmState.human_consensus_status === 'APPROVED' || swarmState.human_consensus_status === 'AUTO_APPROVED'
                    ? 'verified'
                    : swarmState.human_consensus_status === 'REJECTED'
                    ? 'cancel'
                    : 'gavel'}
                </span>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-primary">Consensus Status:</h3>
                  <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${
                    swarmState.human_consensus_status === 'APPROVED' || swarmState.human_consensus_status === 'AUTO_APPROVED'
                      ? 'bg-emerald-100 text-emerald-800'
                      : swarmState.human_consensus_status === 'REJECTED'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-amber-100 text-amber-800'
                  }`}>
                    {swarmState.human_consensus_status}
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant mt-1">
                  {swarmState.human_consensus_status === 'PENDING'
                    ? 'Recommended route identified by Critic Ranker requires traveler consensus approval before ticketing.'
                    : swarmState.human_consensus_status === 'APPROVED'
                    ? 'Traveler approved recovery plan. Rebooking ticket issued successfully.'
                    : 'Candidate option rejected. Swarm stands ready for secondary refinement.'}
                </p>
              </div>
            </div>

            {/* Action Buttons for Pending State */}
            {swarmState.human_consensus_status === 'PENDING' && (
              <div className="flex items-center gap-3">
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="px-4 py-2 rounded-xl border border-outline-variant text-on-surface text-xs font-semibold hover:bg-surface-container transition-all active:scale-95"
                >
                  Decline
                </button>
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="px-5 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold shadow hover:bg-emerald-700 transition-all active:scale-95 flex items-center gap-1.5"
                >
                  {actionLoading ? (
                    <>
                      <span className="material-symbols-outlined text-[16px] animate-spin">refresh</span>
                      Issuing Ticket...
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">check</span>
                      Approve & Rebook
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Execution Receipt if available */}
          {swarmState.execution_receipt && (
            <div className="bg-emerald-500/5 border border-emerald-500/30 rounded-2xl p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-emerald-600 text-[32px]">confirmation_number</span>
                <div>
                  <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider">Electronic Ticket Issued</div>
                  <div className="text-base font-bold text-primary">
                    Ref: {swarmState.execution_receipt.confirmation_code || 'TROS-CONF-9842'}
                  </div>
                  <div className="text-xs text-on-surface-variant">
                    Flight {swarmState.selected_solution?.flight_number} ({swarmState.selected_solution?.carrier}) • Status: {swarmState.execution_receipt.status}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs font-mono px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 font-semibold">
                  CONFIRMED & TICKETED
                </span>
              </div>
            </div>
          )}

          {/* Aggregated Candidate Routes (State Reduction) */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-outline-variant pb-3">
              <div>
                <h3 className="text-base font-bold text-primary flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary">table_rows</span>
                  Candidate Routes (operator.add Aggregated)
                </h3>
                <p className="text-xs text-on-surface-variant">
                  Decentralized discoveries merged into central blackboard state
                </p>
              </div>
              <span className="text-xs font-mono text-secondary font-semibold">
                {swarmState.inventory_candidates.length} Viable Options Found
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-outline-variant text-on-surface-variant">
                    <th className="py-2.5 px-3 font-semibold">Rank</th>
                    <th className="py-2.5 px-3 font-semibold">Flight / Route</th>
                    <th className="py-2.5 px-3 font-semibold">Carrier</th>
                    <th className="py-2.5 px-3 font-semibold">Departure</th>
                    <th className="py-2.5 px-3 font-semibold">Arrival</th>
                    <th className="py-2.5 px-3 font-semibold">Price Delta</th>
                    <th className="py-2.5 px-3 font-semibold">Composite Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/60">
                  {swarmState.inventory_candidates.map((cand: SwarmCandidateRoute, index: number) => {
                    const isSelected =
                      swarmState.selected_solution &&
                      cand.flight_number === swarmState.selected_solution.flight_number;
                    const diffStr =
                      cand.price_differential > 0
                        ? `+$${cand.price_differential.toFixed(2)}`
                        : cand.price_differential < 0
                        ? `-$${Math.abs(cand.price_differential).toFixed(2)}`
                        : '$0.00';

                    return (
                      <tr
                        key={`${cand.flight_number}-${index}`}
                        className={`transition-colors ${
                          isSelected ? 'bg-secondary-container/20 font-medium' : 'hover:bg-surface-container/40'
                        }`}
                      >
                        <td className="py-3 px-3">
                          {isSelected ? (
                            <span className="px-2 py-0.5 rounded bg-secondary text-on-secondary font-bold text-[10px]">
                              TOP #1
                            </span>
                          ) : (
                            <span className="text-on-surface-variant font-mono">#{index + 1}</span>
                          )}
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-primary">{cand.flight_number}</td>
                        <td className="py-3 px-3">{cand.carrier}</td>
                        <td className="py-3 px-3 font-mono text-[11px]">{cand.departure_time}</td>
                        <td className="py-3 px-3 font-mono text-[11px]">{cand.arrival_time}</td>
                        <td className="py-3 px-3 font-mono font-semibold">
                          <span
                            className={
                              cand.price_differential > 0
                                ? 'text-amber-600'
                                : cand.price_differential < 0
                                ? 'text-emerald-600'
                                : 'text-on-surface'
                            }
                          >
                            {diffStr}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-emerald-700">
                          {cand.score.toFixed(3)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Chronological Swarm Audit Log */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-2xl p-6 shadow-sm flex flex-col gap-3">
            <h3 className="text-sm font-bold text-primary flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary text-[18px]">terminal</span>
              Swarm Audit Log Trace
            </h3>
            <div className="bg-slate-950 text-slate-200 font-mono text-[11px] p-4 rounded-xl max-h-60 overflow-y-auto space-y-1.5 shadow-inner">
              {swarmState.agent_logs.map((log: string, idx: number) => (
                <div key={idx} className="leading-relaxed flex items-start gap-2">
                  <span className="text-slate-500 select-none">[{idx + 1}]</span>
                  <span className={log.includes('Scout') ? 'text-cyan-400' : log.includes('Critic') ? 'text-amber-400' : log.includes('Consensus') ? 'text-purple-400' : 'text-slate-300'}>
                    {log}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
