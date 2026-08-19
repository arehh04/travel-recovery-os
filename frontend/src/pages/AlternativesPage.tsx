/** Alternatives page — flight comparison with selection + navigation. */

import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { MissionResult, FlightInfo } from '../api/types';

interface Props {
  alternatives?: FlightInfo[];
  recommendation?: FlightInfo;
}

/** Normalize score to 0-100 range regardless of input format (0-1, 0-100, or >100). */
function normalizeScore(score: number): number {
  if (score <= 0) return 0;
  if (score <= 1) return Math.round(score * 100);
  return Math.min(100, Math.round(score));
}

export function AlternativesPage({ alternatives: propAlts, recommendation: propRec }: Props = {}) {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as { result?: MissionResult; request?: { origin: string; destination: string; budget_limit: number; currency: string } }) || {};
  const result = state.result;

  const rec = propRec || result?.recommendation;
  const alts = propAlts || result?.alternatives || [];

  // Build option cards from API data
  const options = [
    ...(rec ? [{
      flight: rec,
      badge: 'Best Overall',
      badgeStyle: 'tertiary' as const,
      score: normalizeScore(rec.score),
      isDirect: rec.stops === 0,
      depTime: rec.departure,
      arrTime: rec.arrival,
      origin: state.request?.origin || '',
      destination: state.request?.destination || '',
      duration: `${Math.floor(rec.duration_minutes / 60)}h ${rec.duration_minutes % 60}m`,
      stops: rec.stops,
      evidence: 'Highest historical on-time performance for this route. Arrives with ample buffer time for your connecting itinerary.',
    }] : []),
    ...alts.map((alt) => ({
      flight: alt,
      badge: alt.price < (rec?.price ?? Infinity) ? 'Cheapest' : 'Alternative',
      badgeStyle: 'secondary' as const,
      score: normalizeScore(alt.score),
      isDirect: alt.stops === 0,
      depTime: alt.departure,
      arrTime: alt.arrival,
      origin: state.request?.origin || '',
      destination: state.request?.destination || '',
      duration: `${Math.floor(alt.duration_minutes / 60)}h ${alt.duration_minutes % 60}m`,
      stops: alt.stops,
      evidence: 'Most cost-effective routing available today. Requires a brief layover, but maintains a solid reliability score.',
    })),
  ];

  const [selectedIdx, setSelectedIdx] = useState(0);

  // Accept selected alternative — navigate to plan page with it as the recommendation
  const handleAccept = (idx: number) => {
    const selected = options[idx];
    if (!selected) return;
    const newResult: MissionResult = result
      ? { ...result, recommendation: selected.flight, alternatives: options.filter((_, i) => i !== idx).map((o) => o.flight) }
      : {
          mission_id: '', execution_id: '', status: 'COMPLETED',
          recommendation: selected.flight,
          alternatives: options.filter((_, i) => i !== idx).map((o) => o.flight),
          budget: {}, confidence: selected.score / 100,
          recovery: { occurred: false, attempts: 0, reason: '', recovered: false },
          conflicts: { count: 0, has_critical: false },
          execution_metadata: { mission_id: '', execution_id: '', request_id: '', status: 'COMPLETED', duration_ms: 0 },
        };
    navigate('/recovery/plan', { state: { result: newResult, request: state.request } });
  };

  // View evidence details for a specific alternative
  const handleViewDetails = (idx: number) => {
    const selected = options[idx];
    if (!selected || !result) return;
    navigate('/recovery/evidence', { state: { result: { ...result, recommendation: selected.flight } as MissionResult, request: state.request } });
  };

  if (options.length === 0) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-on-surface-variant">No alternatives available.</p>
      </main>
    );
  }

  return (
    <main className="flex-grow px-container-margin py-stack-lg max-w-7xl mx-auto w-full pb-32">
      {/* Brand Header Section */}
      <div className="mb-stack-lg flex flex-col items-center text-center">
        <img src="/Navires-logo.png" alt="Navires Logo" className="w-32 h-auto mb-stack-md object-contain" />
        <h2 className="font-headline-lg-mobile text-headline-lg-mobile text-primary">Alternative Flights</h2>
        <p className="font-body-md text-on-surface-variant mt-unit text-center">We found recovering options for your disrupted journey. Tap one to select, then accept to proceed.</p>
      </div>

      {/* Options Container */}
      <div className="flex flex-col gap-stack-lg">
        {options.map((opt, i) => (
          <article
            key={i}
            onClick={() => setSelectedIdx(i)}
            className={`bg-surface-container-lowest rounded-xl border-2 shadow-[0_-4px_20px_-2px_rgba(15,23,42,0.08)] overflow-hidden flex flex-col relative cursor-pointer transition-all ${
              selectedIdx === i
                ? 'border-secondary ring-2 ring-secondary/20'
                : 'border-outline-variant hover:border-secondary/30'
            }`}
          >
            {/* Selected checkmark */}
            {selectedIdx === i && (
              <div className="absolute top-4 right-4 z-10 w-6 h-6 rounded-full bg-secondary flex items-center justify-center shadow-md">
                <span className="material-symbols-outlined text-[14px] text-on-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
              </div>
            )}

            {/* Card Header / Badges */}
            <div className="p-stack-md pb-0 flex justify-between items-start">
              <div className="flex gap-unit flex-wrap">
                <span className={`inline-flex items-center px-3 py-1 rounded-full font-label-sm text-label-sm ${
                  opt.badgeStyle === 'tertiary'
                    ? 'bg-tertiary-fixed text-on-tertiary-fixed'
                    : 'bg-secondary-fixed text-on-secondary-fixed'
                }`}>
                  <span className="material-symbols-outlined text-[14px] mr-1">
                    {opt.badgeStyle === 'tertiary' ? 'verified' : 'sell'}
                  </span>
                  {opt.badge}
                </span>
              </div>
              <div className={`flex flex-col items-end ${selectedIdx === i ? 'mr-8' : ''}`}>
                <span className="font-numeric-data text-numeric-data text-secondary">{opt.score}%</span>
                <span className="font-label-sm text-label-sm text-on-surface-variant">Deterministic Score</span>
              </div>
            </div>

            {/* Flight Details */}
            <div className="p-stack-md flex flex-col gap-stack-md">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-stack-sm">
                  <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-primary font-label-md text-label-md">
                    {opt.flight.flight_number.slice(0, 2)}
                  </div>
                  <div>
                    <h3 className="font-headline-md text-headline-md text-primary">{opt.flight.flight_number}</h3>
                    <p className="font-body-md text-on-surface-variant">{opt.flight.carrier}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-headline-md text-headline-md text-primary">{opt.flight.currency} {opt.flight.price}</p>
                  <p className="font-label-sm text-label-sm text-on-surface-variant">Economy</p>
                </div>
              </div>

              {/* Routing Timeline */}
              <div className="flex items-center justify-between mt-stack-sm relative">
                <div className={`absolute left-1/2 top-1/2 -translate-y-1/2 -translate-x-1/2 w-full max-w-[120px] ${opt.isDirect ? 'h-px bg-outline-variant' : 'border-t border-dashed border-outline-variant'} z-0`}></div>
                <div className="absolute left-1/2 top-1/2 -translate-y-1/2 -translate-x-1/2 z-10 bg-surface-container-lowest px-2 text-outline flex flex-col items-center">
                  {opt.isDirect ? (
                    <span className="material-symbols-outlined text-[16px] transform rotate-90">flight</span>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[16px]">sync</span>
                      <span className="text-xs">{opt.stops} Stop</span>
                    </>
                  )}
                </div>
                <div className="flex flex-col z-10 bg-surface-container-lowest pr-2">
                  <span className="font-headline-md text-headline-md text-primary">{opt.depTime}</span>
                  <span className="font-body-md text-on-surface-variant">{opt.origin}</span>
                </div>
                <div className="flex flex-col items-end z-10 bg-surface-container-lowest pl-2">
                  <span className="font-headline-md text-headline-md text-primary">{opt.arrTime}</span>
                  <span className="font-body-md text-on-surface-variant">{opt.destination}</span>
                </div>
              </div>
              <div className="flex justify-center">
                <span className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[14px]">schedule</span>
                  {opt.duration}
                  {opt.isDirect ? ' Direct' : ''}
                </span>
              </div>
            </div>

            {/* Evidence Card */}
            <div className="bg-surface p-stack-md border-t border-outline-variant">
              <h4 className="font-label-md text-label-md text-secondary flex items-center gap-1 mb-stack-sm">
                <span className="material-symbols-outlined text-[16px]">info</span> Why this option?
              </h4>
              <p className="font-body-md text-on-surface-variant text-sm">{opt.evidence}</p>
            </div>

            {/* Action Area */}
            <div className="p-stack-md pt-0 bg-surface flex gap-3">
              <button
                onClick={(e) => { e.stopPropagation(); handleAccept(i); }}
                className={`flex-1 py-3 rounded-lg font-label-md text-label-md transition-transform hover:scale-[0.98] active:scale-95 flex justify-center items-center gap-2 ${
                  selectedIdx === i
                    ? 'bg-secondary text-on-secondary'
                    : 'bg-surface-container text-primary border border-outline-variant hover:bg-surface-container-high'
                }`}
              >
                {selectedIdx === i ? 'Accept Alternative' : 'Select'}
                {selectedIdx === i && <span className="material-symbols-outlined">arrow_forward</span>}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleViewDetails(i); }}
                className="px-4 py-3 rounded-lg font-label-md text-label-md text-on-surface-variant border border-outline-variant hover:bg-surface-container-low transition-colors flex justify-center items-center gap-1"
              >
                <span className="material-symbols-outlined text-[18px]">description</span>
                Details
              </button>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
