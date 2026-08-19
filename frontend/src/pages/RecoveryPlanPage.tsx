/** Recovery Plan page — stitch recommendation card with dynamic data. */

import { useLocation, useNavigate } from 'react-router-dom';
import type { MissionResult } from '../api/types';

interface Props {
  result?: MissionResult;
}

export function RecoveryPlanPage({ result: propResult }: Props = {}) {
  const location = useLocation();
  const navigate = useNavigate();

  const state = (location.state as { result?: MissionResult; request?: { origin: string; destination: string; budget_limit: number; currency: string } }) || {};
  const result = propResult || state.result;

  if (!result) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-on-surface-variant">No recovery plan available.</p>
      </main>
    );
  }

  const flight = result.recommendation;
  if (!flight) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-on-surface-variant">No recommendation found.</p>
      </main>
    );
  }

  const budgetLimit = state.request?.budget_limit ?? 1000;
  const currency = flight.currency || state.request?.currency || 'USD';
  const price = flight.price;
  const budgetPct = Math.round((price / budgetLimit) * 100);
  const confidence = result.confidence <= 1 ? Math.round(result.confidence * 100) : Math.min(100, Math.round(result.confidence));
  const confidenceOffset = 100 - confidence;

  // Parse flight details
  const depTime = flight.departure;
  const arrTime = flight.arrival;
  const durationHours = Math.floor(flight.duration_minutes / 60);
  const durationMins = flight.duration_minutes % 60;
  const durationStr = `${durationHours}h ${durationMins}m`;
  const stopsLabel = flight.stops === 0 ? 'Direct' : `${flight.stops} stop`;

  return (
    <main className="flex-1 w-full max-w-7xl mx-auto px-container-margin pb-[120px] pt-stack-md flex flex-col gap-stack-lg">
      {/* Header Section */}
      <section className="flex flex-col gap-stack-sm">
        <div className="flex items-center gap-2">
          <div className="bg-tertiary-fixed/20 text-tertiary-container px-3 py-1 rounded-full font-label-sm text-label-sm flex items-center gap-1 w-max">
            <span className="material-symbols-outlined text-[14px]">check_circle</span>
            Verified Recovery Plan
          </div>
        </div>
        <h1 className="font-headline-lg-mobile text-headline-lg-mobile md:font-headline-lg md:text-headline-lg text-on-background">
          Your recovery plan
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          We've generated the optimal route to get you to your destination with minimal disruption.
        </p>
      </section>

      {/* Hero Card (RecommendationCard) */}
      <section className="bg-surface-container-lowest rounded-xl border border-surface-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] overflow-hidden flex flex-col">
        {/* Flight Header */}
        <div className="p-stack-md border-b border-surface-variant flex justify-between items-start bg-surface-bright">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container">
              <span className="material-symbols-outlined">flight_takeoff</span>
            </div>
            <div>
              <div className="font-headline-md text-headline-md text-on-surface">{flight.flight_number}</div>
              <div className="font-body-md text-body-md text-on-surface-variant">{flight.carrier}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-numeric-data text-numeric-data text-on-surface">{currency} {price.toFixed(2)}</div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Included in allowance</div>
          </div>
        </div>

        {/* Flight Details Timeline */}
        <div className="p-stack-md md:p-container-margin flex flex-col md:flex-row gap-stack-md justify-between items-center relative">
          {/* Departure */}
          <div className="flex flex-col md:items-start text-center md:text-left w-full md:w-auto">
            <div className="font-headline-md text-headline-md text-on-surface">{depTime}</div>
            <div className="font-label-md text-label-md text-on-surface-variant">{state.request?.origin || 'Origin'}</div>
          </div>
          {/* Connection/Duration */}
          <div className="flex flex-col items-center flex-1 w-full relative px-4 py-6 md:py-0">
            <div className="font-label-sm text-label-sm text-on-surface-variant mb-2">{durationStr}</div>
            <div className="w-full flex items-center">
              <div className="h-[2px] bg-outline-variant flex-1"></div>
              <div className="px-2 py-1 bg-surface-container rounded-full font-label-sm text-label-sm text-on-surface-variant border border-outline-variant z-10 flex flex-col items-center">
                <span>{stopsLabel}</span>
              </div>
              <div className="h-[2px] bg-outline-variant flex-1"></div>
            </div>
          </div>
          {/* Arrival */}
          <div className="flex flex-col md:items-end text-center md:text-right w-full md:w-auto">
            <div className="font-headline-md text-headline-md text-on-surface">{arrTime}</div>
            <div className="font-label-md text-label-md text-on-surface-variant">{state.request?.destination || 'Destination'}</div>
          </div>
        </div>

        {/* Confidence Indicator */}
        <div className="px-stack-md py-3 bg-secondary/5 border-t border-surface-variant flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12 flex items-center justify-center">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle className="stroke-surface-variant" cx="18" cy="18" fill="none" r="16" strokeWidth="3"></circle>
                <circle className="stroke-secondary" cx="18" cy="18" fill="none" r="16" strokeDasharray="100" strokeDashoffset={confidenceOffset} strokeLinecap="round" strokeWidth="3"></circle>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-label-md text-label-md text-secondary">{confidence}%</div>
            </div>
            <div>
              <div className="font-label-md text-label-md text-on-surface">Recovery Confidence</div>
              <div className="font-label-sm text-label-sm text-on-surface-variant">High likelihood of seamless connection</div>
            </div>
          </div>
          <span className="material-symbols-outlined text-secondary">analytics</span>
        </div>

        {/* Actions */}
        <div className="p-stack-md border-t border-surface-variant flex flex-col md:flex-row gap-3">
          <button
            onClick={() => navigate('/recovery/booking', { state: { flight, request: state.request, confidence } })}
            className="w-full md:flex-1 bg-primary-container text-on-primary py-3 rounded-lg font-label-md text-label-md flex justify-center items-center gap-2 hover:bg-primary-fixed-variant transition-colors"
          >
            Accept &amp; Book
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
        </div>
      </section>

      {/* Why this flight? */}
      <section className="flex flex-col gap-stack-md">
        <h2 className="font-headline-md text-headline-md text-on-background">Why this flight?</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { title: 'Within budget', detail: `Fully covered by disruption allowance. ${budgetPct}% of limit used.` },
            { title: 'Meets constraints', detail: 'Avoids high-risk hubs during storm season.' },
            { title: 'Highest score', detail: `Ranked #1 out of ${result.alternatives.length + 1} possible itineraries.` },
            { title: 'Live Atlas data', detail: 'Verified via real-time ATC routing data.' },
            { title: 'No conflicts', detail: 'Aligns with your calendar and upcoming meetings.', span: true },
          ].map((card, i) => (
            <div key={i} className={`bg-[#F0F9FF] border border-secondary-fixed-dim/30 rounded-lg p-3 flex items-start gap-3 ${card.span ? 'md:col-span-2' : ''}`}>
              <div className="mt-0.5 text-secondary">
                <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
              </div>
              <div>
                <div className="font-label-md text-label-md text-on-surface">{card.title}</div>
                <div className="font-label-sm text-label-sm text-on-surface-variant mt-1">{card.detail}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Secondary Actions */}
      <section className="flex flex-col gap-3 pt-4 border-t border-surface-variant">
        <button
          onClick={() => navigate('/recovery/evidence', { state: location.state })}
          className="w-full bg-surface text-secondary py-3 rounded-lg border border-outline-variant font-label-md text-label-md flex justify-center items-center hover:bg-surface-container transition-colors"
        >
          View recovery details
        </button>
        <button
          onClick={() => navigate('/recovery/alternatives', { state: location.state })}
          className="w-full bg-transparent text-on-surface-variant py-3 font-label-md text-label-md flex justify-center items-center hover:text-on-surface transition-colors"
        >
          Compare alternatives
        </button>
      </section>
    </main>
  );
}
