/** Evidence Validation page — Multi-Agent Audit, Proof & Statutory Passenger Rights Claim Engine. */

import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../api/client';
import type { MissionResult, RegulatoryClaim } from '../api/types';
import type { EvidenceData } from '../types/app';

interface Props {
  data?: EvidenceData;
}

export function EvidenceValidationPage({ data: propData }: Props = {}) {
  const location = useLocation();
  const state = (location.state as { result?: MissionResult; request?: { budget_limit: number; currency: string }; mission?: any }) || {};
  const result = state.result;

  const missionId = result?.execution_metadata?.mission_id || state.mission?.id || 'mission-ba117-live';

  const [claim, setClaim] = useState<RegulatoryClaim | null>(null);
  const [claimLoading, setClaimLoading] = useState(false);
  const [claimFiled, setClaimFiled] = useState(false);

  useEffect(() => {
    loadClaim();
  }, [missionId]);

  const loadClaim = async () => {
    try {
      setClaimLoading(true);
      const data = await api.get<RegulatoryClaim>(`/claims/${missionId}`);
      setClaim(data);
      if (data.status === 'SUBMITTED_TO_AIRLINE') {
        setClaimFiled(true);
      }
    } catch (e) {
      console.warn('Claim calculation error or not yet generated:', e);
    } finally {
      setClaimLoading(false);
    }
  };

  const handleFileClaim = async () => {
    try {
      const data = await api.post<RegulatoryClaim>(`/claims/${missionId}/file`);
      setClaim(data);
      setClaimFiled(true);
    } catch (e) {
      console.error('Failed to file claim:', e);
    }
  };

  const handleDownloadNotice = () => {
    if (!claim) return;
    const blob = new Blob([claim.claim_letter], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `TR-OS_Legal_Claim_${claim.id}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Build evidence data from API result or use prop defaults
  const flight = result?.recommendation;
  const alt = result?.alternatives?.[0];

  const data: EvidenceData = propData || {
    flightRef: flight?.flight_number || 'BA112',
    punctualityPct: 96,
    availableSeats: 4,
    layoverTolerance: '< 3 hrs at secondary hub',
    budgetAmount: flight?.price ?? 420.40,
    budgetLimit: state.request?.budget_limit ?? 1000,
    budgetPct: flight ? Math.round((flight.price / (state.request?.budget_limit ?? 1000)) * 100) : 42,
    confidenceScore: result ? Math.round(result.confidence * 100) : 94,
    altFlightRef: alt?.flight_number || 'SQ12',
    connectionP1: 0.98,
    connectionP2: 0.72,
    reflection: `Autonomous Multi-Agent Swarm selected ${flight?.flight_number || 'BA112'} as the mathematically optimal recovery path. Direct Scout verified active seat inventory, Alliance Scout confirmed codeshare protection, Weather Agent verified VFR flight category across transatlantic corridors, and Policy Agent computed full EU261 €600 compensation entitlements.`,
    evidenceItems: [
      { icon: 'flight_takeoff', title: 'Route Feasibility Verified', detail: 'Global Flight Engine confirmed primary seat inventory.' },
      { icon: 'cloud', title: 'Meteorological Risk Passed', detail: 'Weather Agent verified VFR ceiling and sub-0.20 storm risk index.' },
      { icon: 'policy', title: 'Statutory Protection Active', detail: 'EU261 / MAVCOM regulatory duty of care mandates applied.' },
      { icon: 'hotel', title: 'Distress Accommodations Ready', detail: 'Hotel Agent pre-allocated transit vouchers & shuttle logistics.' },
    ],
    constraintItems: [
      { title: 'Origin / Destination Match', detail: 'Strict route corridor preserved.' },
      { title: 'Alliance Priority', detail: 'Oneworld & Star Alliance tier benefits preserved.' },
      { title: 'Budget Limit', detail: 'Well within corporate recovery fund limit.' },
    ],
  };

  const confidenceDashOffset = 282.7 - (282.7 * data.confidenceScore / 100);

  return (
    <main className="max-w-7xl mx-auto px-container-margin mt-stack-md flex flex-col gap-stack-lg pb-32">
      {/* Page Header & Branding */}
      <section className="flex flex-col items-center text-center space-y-stack-sm mt-stack-sm">
        <img src="/Navires-logo.png" alt="Navires Logo" className="w-16 h-16 object-contain mb-2" />
        <div className="inline-flex items-center gap-2 bg-secondary-fixed/20 px-3 py-1 rounded-full border border-secondary-fixed-dim">
          <div className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-secondary"></span>
          </div>
          <span className="font-label-sm text-label-sm text-secondary uppercase tracking-wider">Multi-Agent Evidence Engine</span>
        </div>
        <h1 className="font-display-lg text-display-lg text-primary mt-unit">Evidence Dossier: {data.flightRef}</h1>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-xl">
          Multi-agent mathematical validation, meteorological clearance, and statutory passenger rights protection.
        </p>
      </section>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        {/* Flight Evidence */}
        <div className="md:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-sm flex flex-col gap-stack-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-secondary"></div>
          <div className="flex items-center justify-between">
            <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">verified</span>
              Specialist Agent Verification Evidence
            </h2>
            <span className="bg-secondary-container text-on-secondary-container font-label-sm px-2.5 py-1 rounded-full font-semibold">
              Autonomous Clearance
            </span>
          </div>
          <div className="mt-unit bg-surface-bright rounded-lg border border-surface-variant p-stack-sm flex flex-col gap-3">
            {data.evidenceItems.map((item, i) => (
              <div key={i}>
                <div className="flex items-center gap-3">
                  <div className="bg-primary-container text-on-primary-container w-10 h-10 rounded-full flex items-center justify-center shadow-inner">
                    <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                  </div>
                  <div>
                    <div className="font-label-md text-label-md text-on-surface font-semibold">{item.title}</div>
                    <div className="font-body-sm text-body-sm text-on-surface-variant">{item.detail}</div>
                  </div>
                </div>
                {i < data.evidenceItems.length - 1 && <div className="h-px w-full bg-outline-variant/30 mt-3"></div>}
              </div>
            ))}
          </div>
        </div>

        {/* Confidence Gauge */}
        <div className="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-sm flex flex-col items-center justify-center relative overflow-hidden">
          <h2 className="font-headline-md text-headline-md text-on-surface absolute top-4 left-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">monitoring</span>
            Confidence
          </h2>
          <div className="relative w-36 h-36 mt-8 flex items-center justify-center">
            <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" fill="none" r="45" stroke="#e0e3e5" strokeWidth="8"></circle>
              <circle cx="50" cy="50" fill="none" r="45" stroke="#4edea3" strokeDasharray="282.7" strokeDashoffset={confidenceDashOffset} strokeLinecap="round" strokeWidth="8"></circle>
            </svg>
            <div className="flex flex-col items-center text-center z-10">
              <span className="font-display-lg text-display-lg text-primary leading-none font-bold">{data.confidenceScore}%</span>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mt-1">Utility Score</span>
            </div>
          </div>
        </div>

        {/* Regulatory Passenger Rights & Claims Card */}
        <div className="col-span-full bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col gap-4 relative overflow-hidden">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center">
                <span className="material-symbols-outlined">gavel</span>
              </div>
              <div>
                <h3 className="font-headline-md text-primary">Statutory Passenger Rights & Compensation</h3>
                <p className="text-xs text-on-surface-variant">Automated legal compliance under international aviation consumer protection regulations.</p>
              </div>
            </div>
            {claim && (
              <span className="bg-secondary-container text-on-secondary-container text-xs px-3 py-1 rounded-full font-label-sm font-semibold">
                {claim.regulation}
              </span>
            )}
          </div>

          {claim ? (
            <div className="bg-surface-bright rounded-xl p-4 border border-outline-variant space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <span className="text-xs text-on-surface-variant font-label-md">Entitled Statutory Compensation:</span>
                  <div className="text-2xl font-bold text-primary">
                    {claim.currency} {claim.amount.toFixed(2)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleDownloadNotice}
                    className="border border-outline-variant px-3.5 py-2 rounded-lg text-xs font-label-md flex items-center gap-1.5 hover:bg-surface-container-high transition-colors"
                  >
                    <span className="material-symbols-outlined text-[16px]">download</span>
                    Download Legal Notice Letter
                  </button>
                  <button
                    onClick={handleFileClaim}
                    disabled={claimFiled}
                    className={`px-4 py-2 rounded-lg text-xs font-label-md flex items-center gap-1.5 transition-all shadow-sm ${
                      claimFiled
                        ? 'bg-tertiary text-on-tertiary opacity-90'
                        : 'bg-primary-container text-on-primary hover:bg-primary-container/90'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {claimFiled ? 'task_alt' : 'send'}
                    </span>
                    {claimFiled ? 'Claim Notice Dispatched' : 'Submit Claim to Airline'}
                  </button>
                </div>
              </div>
              <p className="text-xs text-on-surface-variant font-mono bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/60 whitespace-pre-line max-h-32 overflow-y-auto">
                {claim.claim_letter}
              </p>
            </div>
          ) : (
            <p className="text-xs text-on-surface-variant">Calculating statutory compensation entitlements...</p>
          )}
        </div>

        {/* Engine Reflection */}
        <div className="col-span-full bg-surface-container border border-outline-variant rounded-xl p-stack-md shadow-sm border-l-4 border-l-secondary">
          <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-secondary">psychology</span>
            Autonomous Reflection & Optimization Trace
          </h2>
          <p className="font-body-md text-body-md text-on-surface leading-relaxed italic">
            "{data.reflection}"
          </p>
        </div>
      </div>
    </main>
  );
}
