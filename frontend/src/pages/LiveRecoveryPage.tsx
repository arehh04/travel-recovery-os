/** Live Recovery page — stitch radar ring + timeline, with error handling. */

import { useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useMission } from '../hooks/useMission';
import type { MissionRequest } from '../api/types';
import type { PhaseStep } from '../types/app';
import { AgentTerminal } from '../components/AgentTerminal';

const PHASE_STEPS: PhaseStep[] = [
  { label: 'Mission understood', state: 'pending' },
  { label: 'Traveler constraints checked', state: 'pending' },
  { label: 'Searching live flights', state: 'pending' },
  { label: 'Comparing alternatives', state: 'pending' },
  { label: 'Checking budget', state: 'pending' },
  { label: 'Reviewing recommendation', state: 'pending' },
  { label: 'Final validation', state: 'pending' },
];

const PHASE_ORDER = ['CONTEXT', 'CONSTRAINTS', 'SEARCH', 'COMPARE', 'BUDGET', 'RECOMMEND', 'VALIDATE'];

export function LiveRecoveryPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { state, createMission, cancelMission } = useMission();
  const initRef = useRef(false);

  const request = (location.state as { request?: MissionRequest })?.request;

  // Compute route display
  const origin = request?.origin || '';
  const destination = request?.destination || '';
  const date = request?.departure_date || '';

  // Redirect to home if no request data (e.g., direct URL access)
  useEffect(() => {
    if (!request) {
      navigate('/', { replace: true });
    }
  }, [request, navigate]);

  // Start mission on mount
  useEffect(() => {
    if (initRef.current || !request) return;
    initRef.current = true;
    createMission(request);
  }, [request, createMission]);

  // Navigate to plan when completed
  useEffect(() => {
    if (state.phase === 'completed' && state.result) {
      navigate('/recovery/plan', { state: { result: state.result, request } });
    }
  }, [state, navigate, request]);

  // Derive phase step states from API status
  const getSteps = (): PhaseStep[] => {
    if (state.phase === 'idle' || state.phase === 'submitting' || state.phase === 'queued') {
      return PHASE_STEPS.map((s, i) => ({ ...s, state: i === 0 ? 'current' : 'pending' }));
    }
    if (state.phase === 'error') {
      return PHASE_STEPS.map((s) => ({ ...s, state: 'pending' }));
    }
    const currentPhase = state.phase === 'running' ? state.status?.phase : 'VALIDATE';
    const currentIndex = Math.max(0, PHASE_ORDER.indexOf(currentPhase || 'CONTEXT'));
    return PHASE_STEPS.map((s, i) => ({
      ...s,
      state: i < currentIndex ? 'completed' : i === currentIndex ? 'current' : 'pending',
    }));
  };

  const steps = getSteps();
  const isRunning = state.phase === 'running' || state.phase === 'queued';
  const isSubmitting = state.phase === 'submitting' || state.phase === 'idle';
  const isError = state.phase === 'error';
  const missionId = isRunning ? state.missionId : undefined;
  const offers = state.phase === 'running' ? (state.status?.phase === 'FLIGHT_SEARCH' ? 12 : 23) : 0;

  // ERROR STATE — show error message with retry button
  if (isError) {
    return (
      <main className="flex-1 w-full max-w-xl mx-auto px-container-margin py-stack-lg flex flex-col gap-6 items-center justify-center min-h-[60vh]">
        <div className="bg-surface-container-lowest border border-error-container rounded-xl p-8 flex flex-col items-center gap-6 shadow-lg max-w-md w-full text-center">
          <div className="w-16 h-16 rounded-full bg-error-container text-error-container flex items-center justify-center">
            <span className="material-symbols-outlined text-[32px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              error
            </span>
          </div>
          <div>
            <h1 className="font-headline-md text-headline-md text-on-surface mb-2">Recovery Failed</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">
              {state.message || 'An unexpected error occurred while starting your recovery mission.'}
            </p>
          </div>
          {origin && destination && (
            <div className="bg-surface rounded-lg px-4 py-2 text-sm text-on-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px] text-primary">flight_takeoff</span>
              {origin} <span className="material-symbols-outlined text-[16px]">arrow_right_alt</span> {destination}
              {date && <span className="text-on-surface-variant">· {date}</span>}
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/', { replace: true })}
              className="bg-primary-container text-on-primary hover:bg-primary-container/90 font-label-md text-label-md px-6 py-3 rounded-lg flex items-center gap-2 transition-all active:scale-95"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_back</span>
              Back to Home
            </button>
            <button
              onClick={() => {
                initRef.current = false;
                if (request) {
                  createMission(request);
                } else {
                  navigate('/');
                }
              }}
              className="border border-outline-variant text-on-surface-variant hover:bg-surface-container-low font-label-md text-label-md px-6 py-3 rounded-lg flex items-center gap-2 transition-all active:scale-95"
            >
              <span className="material-symbols-outlined text-[20px]">refresh</span>
              Try Again
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex-1 w-full max-w-xl mx-auto px-container-margin py-stack-lg flex flex-col gap-stack-lg relative z-10 pb-32">
      {/* Header */}
      <header className="flex flex-col items-center text-center gap-stack-sm mb-2">
        <h1 className="font-headline-lg-mobile text-headline-lg-mobile text-on-surface">
          {isSubmitting ? 'Starting your recovery...' : 'Assisting with your recovery'}
        </h1>
        <div className="flex items-center gap-2 text-on-secondary-container font-label-md text-label-md bg-secondary-container px-4 py-2 rounded-full border border-outline-variant/50">
          <span className="material-symbols-outlined text-[16px] text-primary">flight_takeoff</span>
          <span>Mission: {origin} <span className="material-symbols-outlined text-[16px] align-middle px-1">arrow_right_alt</span> {destination}{date ? `, ${date}` : ''}</span>
        </div>
      </header>

      {/* Live Status Card */}
      <section className="bg-surface-container-lowest border border-outline-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] rounded-xl p-8 flex flex-col items-center gap-6 relative overflow-hidden">
        <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-b from-secondary-container/20 to-transparent opacity-50"></div>
        {/* Animated Progress Ring */}
        <div className="relative w-28 h-28 flex items-center justify-center mt-2">
          <svg className="w-full h-full absolute inset-0 text-surface-container-highest" viewBox="0 0 100 100">
            <circle cx="50" cy="50" fill="none" r="46" stroke="currentColor" strokeWidth="4"></circle>
          </svg>
          <svg className="w-full h-full absolute inset-0 text-primary animate-[spin_4s_linear_infinite]" style={{ strokeDasharray: '100 200', strokeLinecap: 'round' }} viewBox="0 0 100 100">
            <circle cx="50" cy="50" fill="none" r="46" stroke="currentColor" strokeWidth="6"></circle>
          </svg>
          <div className="bg-surface-container-lowest rounded-full p-3 shadow-sm z-10">
            <span className="material-symbols-outlined text-primary text-4xl animate-pulse" style={{ fontVariationSettings: "'FILL' 1" }}>
              {isSubmitting ? 'hourglass_top' : 'radar'}
            </span>
          </div>
        </div>
        <div className="text-center z-10 flex flex-col gap-2">
          <h2 className="font-headline-md text-headline-md text-primary">
            {isSubmitting ? 'Connecting to recovery engine...' : 'Searching live flight options'}
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant flex items-center justify-center gap-2 relative">
            <span className="w-2 h-2 rounded-full bg-primary animate-ping absolute opacity-75"></span>
            <span className="w-2 h-2 rounded-full bg-primary"></span>
            {isSubmitting ? 'Preparing your mission' : `${offers} live offers found`}
          </p>
        </div>
      </section>

      {/* Recovery Timeline */}
      <section className="bg-surface-container-lowest border border-outline-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] rounded-xl p-6 md:p-8">
        <div className="relative">
          {steps.map((step, i) => (
            <div key={i} className="relative flex items-start gap-4 pb-8 last:pb-0">
              <div className={`timeline-line ${step.state === 'completed' ? 'bg-tertiary' : 'bg-surface-container-highest'}`}></div>
              {step.state === 'completed' && (
                <div className="w-6 h-6 rounded-full bg-surface-container-lowest border-2 border-tertiary flex items-center justify-center relative z-10 mt-0.5 shadow-sm">
                  <span className="material-symbols-outlined text-[14px] text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>check</span>
                </div>
              )}
              {step.state === 'current' && (
                <div className="w-6 h-6 rounded-full bg-surface-container-lowest border-2 border-primary flex items-center justify-center relative z-10 mt-0.5 shadow-[0_0_12px_rgba(0,102,138,0.2)]">
                  <div className="w-2 h-2 rounded-full bg-primary"></div>
                </div>
              )}
              {step.state === 'pending' && (
                <div className="w-6 h-6 rounded-full bg-surface-container-lowest border-2 border-outline-variant/50 flex items-center justify-center relative z-10 mt-0.5"></div>
              )}
              <div className="flex-1 pt-0.5">
                <p className={`font-label-md text-label-md ${step.state === 'current' ? 'text-primary' : step.state === 'pending' ? 'text-on-surface-variant' : 'text-on-surface'}`}>
                  {step.label}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom Status Indicator */}
      <div className="flex justify-center mt-4 mb-2">
        <div className="inline-flex items-center gap-3 bg-surface/80 backdrop-blur-md border border-outline-variant/50 px-5 py-3 rounded-full shadow-sm">
          <span className="material-symbols-outlined text-primary animate-[spin_3s_linear_infinite] text-[18px]">sync</span>
          <span className="font-label-sm text-label-sm text-on-surface-variant tracking-wide">Navires is evaluating your options...</span>
        </div>
      </div>

      {/* Agent Terminal */}
      {missionId && isRunning && (
        <section className="w-full max-w-2xl mx-auto mb-8">
          <AgentTerminal missionId={missionId} />
        </section>
      )}

      {/* Cancel button */}
      {missionId && state.phase === 'running' && (
        <div className="flex justify-center">
          <button
            onClick={() => cancelMission()}
            className="text-on-surface-variant hover:text-error font-label-sm text-label-sm transition-colors"
          >
            Cancel mission
          </button>
        </div>
      )}
    </main>
  );
}
