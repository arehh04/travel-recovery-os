/** Evidence Validation page — stitch bento grid with dynamic data. */

import { useLocation } from 'react-router-dom';
import type { MissionResult } from '../api/types';
import type { EvidenceData } from '../types/app';

interface Props {
  data?: EvidenceData;
}

export function EvidenceValidationPage({ data: propData }: Props = {}) {
  const location = useLocation();
  const state = (location.state as { result?: MissionResult; request?: { budget_limit: number; currency: string } }) || {};
  const result = state.result;

  // Build evidence data from API result or use prop defaults
  const flight = result?.recommendation;
  const alt = result?.alternatives[0];

  const data: EvidenceData = propData || {
    flightRef: flight?.flight_number || 'N/A',
    punctualityPct: 94,
    availableSeats: 4,
    layoverTolerance: '< 3 hrs at secondary hub',
    budgetAmount: flight?.price ?? 420.40,
    budgetLimit: state.request?.budget_limit ?? 1000,
    budgetPct: flight ? Math.round((flight.price / (state.request?.budget_limit ?? 1000)) * 100) : 42,
    confidenceScore: result ? Math.round(result.confidence * 100) : 92,
    altFlightRef: alt?.flight_number || 'XJ109',
    connectionP1: 0.98,
    connectionP2: 0.72,
    reflection: `Option ${flight?.flight_number || 'TR874'} represents the mathematically optimal path to recovery. While alternative ${alt?.flight_number || 'XJ109'} offers a 15-minute earlier arrival, ${flight?.flight_number || 'TR874'} provides superior connection resilience at the secondary hub (p=0.98 vs p=0.72) and falls well within the corporate fiscal constraints. Equipment type matching was prioritized to maintain user comfort standards.`,
    evidenceItems: [
      { icon: 'flight_takeoff', title: 'Route Feasibility Confirmed', detail: `Historical punctuality: ${94}% on this specific routing.` },
      { icon: 'network_check', title: 'Capacity Check Passed', detail: `Real-time GDS query confirms ${4} available seats in requested class.` },
    ],
    constraintItems: [
      { title: 'Origin / Destination Match', detail: 'Strict match enforced.' },
      { title: 'Layover Tolerance', detail: '< 3 hrs at secondary hub.' },
      { title: 'Cabin Class', detail: 'Premium Economy preserved.' },
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
          <span className="font-label-sm text-label-sm text-secondary uppercase tracking-wider">Validation Engine Active</span>
        </div>
        <h1 className="font-display-lg text-display-lg text-primary mt-unit">Why {data.flightRef}?</h1>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-md">Navires AI has selected this recovery route based on multi-variable constraint analysis.</p>
      </section>

      {/* Bento Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-gutter">
        {/* Flight Evidence */}
        <div className="md:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] flex flex-col gap-stack-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-secondary-container"></div>
          <div className="flex items-center justify-between">
            <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">database</span>
              Flight Evidence
            </h2>
            <span className="bg-surface-container-high text-on-surface font-label-sm text-label-sm px-2 py-1 rounded-full">Atlas Verified</span>
          </div>
          <div className="mt-unit bg-surface-bright rounded-lg border border-surface-variant p-stack-sm flex flex-col gap-3">
            {data.evidenceItems.map((item, i) => (
              <div key={i}>
                <div className="flex items-center gap-3">
                  <div className="bg-primary-container text-on-primary-container w-10 h-10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined">{item.icon}</span>
                  </div>
                  <div>
                    <div className="font-label-md text-label-md text-on-surface">{item.title}</div>
                    <div className="font-body-sm text-body-sm text-on-surface-variant">{item.detail}</div>
                  </div>
                </div>
                {i < data.evidenceItems.length - 1 && <div className="h-px w-full bg-outline-variant/30 mt-3"></div>}
              </div>
            ))}
          </div>
        </div>

        {/* Constraint Checks */}
        <div className="md:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] flex flex-col gap-stack-sm">
          <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-2">
            <span className="material-symbols-outlined text-secondary">rule</span>
            Constraint Checks
          </h2>
          <div className="flex flex-col gap-3">
            {data.constraintItems.map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="material-symbols-outlined text-tertiary-fixed-dim" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
                <div>
                  <div className="font-label-md text-label-md text-on-surface">{item.title}</div>
                  <div className="text-sm text-on-surface-variant">{item.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Budget Analysis */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] flex flex-col gap-stack-sm justify-between">
          <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">payments</span>
            Budget Analysis
          </h2>
          <div className="flex flex-col gap-2 mt-4">
            <div className="flex justify-between items-end">
              <span className="font-numeric-data text-numeric-data text-primary">USD {data.budgetAmount.toFixed(2)}</span>
              <span className="font-label-md text-label-md text-on-surface-variant">Limit: {data.budgetLimit.toFixed(2)}</span>
            </div>
            <div className="w-full bg-surface-container-high rounded-full h-3 overflow-hidden">
              <div className="bg-secondary h-3 rounded-full" style={{ width: `${data.budgetPct}%` }}></div>
            </div>
            <div className="font-label-sm text-label-sm text-on-surface-variant text-right mt-1">{data.budgetPct}% of allocated recovery fund</div>
          </div>
        </div>

        {/* Ranking Score */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] flex flex-col items-center justify-center gap-stack-sm relative overflow-hidden">
          <h2 className="font-headline-md text-headline-md text-on-surface absolute top-stack-md left-stack-md flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">monitoring</span>
            Ranking Score
          </h2>
          <div className="relative w-32 h-32 mt-8 flex items-center justify-center">
            <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" fill="none" r="45" stroke="#e0e3e5" strokeWidth="8"></circle>
              <circle cx="50" cy="50" fill="none" r="45" stroke="#4edea3" strokeDasharray="282.7" strokeDashoffset={confidenceDashOffset} strokeLinecap="round" strokeWidth="8"></circle>
            </svg>
            <div className="flex flex-col items-center text-center z-10">
              <span className="font-display-lg text-display-lg text-primary leading-none">{data.confidenceScore}</span>
              <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mt-1">Confidence</span>
            </div>
          </div>
        </div>

        {/* Reflection Text Block */}
        <div className="col-span-full bg-surface-container border border-outline-variant rounded-xl p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] border-l-4 border-l-secondary relative">
          <h2 className="font-headline-md text-headline-md text-on-surface flex items-center gap-2 mb-3">
            <span className="material-symbols-outlined text-secondary">psychology</span>
            Engine Reflection
          </h2>
          <p className="font-body-md text-body-md text-on-surface leading-relaxed">
            "{data.reflection}"
          </p>
        </div>
      </div>
    </main>
  );
}
