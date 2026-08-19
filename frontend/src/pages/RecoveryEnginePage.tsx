/** Recovery Engine page — stitch attempts timeline with dynamic steps. */

import type { EngineStep } from '../types/app';

interface Props {
  attempt?: number;
  maxAttempts?: number;
  steps?: EngineStep[];
  assistantNote?: string;
}

const DEFAULT_STEPS: EngineStep[] = [
  { iconBg: 'bg-error-container text-error', iconText: '', icon: 'warning', filled: false, title: 'Recommendation Rejected', detail: '"Too many layovers" noted. Adjusting parameters.' },
  { iconBg: 'bg-secondary-container text-on-secondary-container', iconText: '', icon: 'check_circle', filled: true, title: 'Evidence Preserved', detail: 'Original disruption data retained for claims.' },
  { iconBg: 'bg-secondary-container text-on-secondary-container', iconText: '', icon: 'check_circle', filled: true, title: 'Searching Alternatives', detail: 'Scanning all global carrier alliances.' },
  { iconBg: 'border-2 border-secondary text-secondary bg-surface-container-lowest', iconText: '', icon: 'travel_explore', filled: false, title: 'New Candidate Found', detail: 'Finalizing booking details and verifying availability.', active: true },
];

export function RecoveryEnginePage({
  attempt = 2,
  maxAttempts = 2,
  steps = DEFAULT_STEPS,
  assistantNote = 'This is the final automated attempt based on your preferences. If this option is unsuitable, I will connect you with a live human agent to complete the rebooking.',
}: Props = {}) {
  return (
    <div className="w-full max-w-md mx-auto bg-surface min-h-screen relative overflow-hidden shadow-2xl flex flex-col">
      <main className="flex-1 px-container-margin py-stack-lg flex flex-col gap-stack-lg overflow-y-auto pb-32">
        {/* Header Section */}
        <div className="flex flex-col gap-unit">
          <span className="font-label-sm text-label-sm text-secondary tracking-widest uppercase font-bold">Attempt {attempt} of {maxAttempts}</span>
          <h1 className="font-headline-lg-mobile text-headline-lg-mobile text-primary">Generating Replacement</h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-2">
            Reviewing your feedback and calculating a new optimal route. Please stand by.
          </p>
        </div>

        {/* Recovery Timeline */}
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] relative">
          {steps.map((step, i) => (
            <div key={i} className={`recovery-step relative flex gap-gutter ${i < steps.length - 1 ? 'mb-stack-md' : ''} z-10`}>
              {i < steps.length - 1 && <div className="recovery-line"></div>}
              <div className={`flex-shrink-0 w-8 h-8 rounded-full ${step.iconBg} flex items-center justify-center z-10 border-2 border-surface-container-lowest ${step.active ? 'animate-pulse' : ''}`}>
                <span className={`material-symbols-outlined text-[18px] ${step.filled ? 'fill' : ''}`}>{step.icon}</span>
              </div>
              <div className="flex flex-col pt-1">
                <span className={`font-label-md text-label-md ${step.active ? 'text-secondary' : 'text-on-surface'}`}>{step.title}</span>
                <span className="font-body-md text-body-md text-on-surface-variant text-sm mt-1">{step.detail}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Skeleton Loader Card */}
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-stack-md shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)]">
          <div className="flex justify-between items-center mb-stack-sm">
            <div className="h-5 w-24 rounded skeleton"></div>
            <div className="h-6 w-16 rounded-full skeleton"></div>
          </div>
          <div className="flex gap-gutter items-center py-stack-sm border-b border-surface-variant mb-stack-sm">
            <div className="h-10 w-10 rounded-lg skeleton flex-shrink-0"></div>
            <div className="flex-1 flex flex-col gap-2">
              <div className="h-4 w-3/4 rounded skeleton"></div>
              <div className="h-3 w-1/2 rounded skeleton"></div>
            </div>
          </div>
          <div className="flex justify-between items-center">
            <div className="flex flex-col gap-2">
              <div className="h-4 w-20 rounded skeleton"></div>
              <div className="h-6 w-16 rounded skeleton"></div>
            </div>
            <div className="h-8 w-8 rounded-full skeleton"></div>
            <div className="flex flex-col gap-2 items-end">
              <div className="h-4 w-20 rounded skeleton"></div>
              <div className="h-6 w-16 rounded skeleton"></div>
            </div>
          </div>
          <div className="mt-stack-md flex gap-gutter">
            <div className="h-12 w-full rounded-lg skeleton opacity-70"></div>
          </div>
        </div>

        {/* Assistant Note */}
        <div className="bg-[#F0F9FF] rounded-xl p-stack-md border border-secondary/20 flex gap-gutter items-start">
          <span className="material-symbols-outlined text-secondary fill">robot_2</span>
          <p className="font-body-md text-body-md text-on-surface text-sm">
            {assistantNote}
          </p>
        </div>
      </main>
    </div>
  );
}
