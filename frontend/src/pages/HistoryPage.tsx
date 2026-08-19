/** History page — stitch mission timeline with dynamic data. */

import type { HistoryMission } from '../types/app';

interface Props {
  missions?: HistoryMission[];
}

const DEFAULT_MISSIONS: HistoryMission[] = [
  { id: '1', origin: 'KUL', destination: 'NRT', date: '20 Aug 2026', status: 'Recovered', description: 'Original flight MH70 disrupted. AI rerouted via SQ12.', hasDetails: true },
  { id: '2', origin: 'KUL', destination: 'SIN', date: '18 Aug 2026', status: 'Completed', description: 'Mission completed smoothly without automated interventions.', hasDetails: false },
  { id: '3', origin: 'BKK', destination: 'HKG', date: '10 Aug 2026', status: 'Cancelled', description: '', hasDetails: false },
  { id: '4', origin: 'LHR', destination: 'JFK', date: '05 Aug 2026', status: 'Failed', description: 'Severe weather disruption. Alternative routing not accepted by user within time window.', hasDetails: false },
];

const STATUS_CONFIG: Record<HistoryMission['status'], { iconBg: string; icon: string; badgeBg: string; badgeIcon: string }> = {
  Recovered: { iconBg: 'bg-secondary-container text-on-secondary-container', icon: 'health_and_safety', badgeBg: 'bg-secondary-container text-on-secondary-container', badgeIcon: 'check_circle' },
  Completed: { iconBg: 'bg-tertiary-container text-on-tertiary-container', icon: 'done_all', badgeBg: 'bg-tertiary-container text-on-tertiary-container', badgeIcon: 'done' },
  Cancelled: { iconBg: 'bg-surface-variant text-on-surface-variant', icon: 'cancel', badgeBg: 'bg-surface-variant text-on-surface-variant', badgeIcon: 'block' },
  Failed: { iconBg: 'bg-error-container text-error-container', icon: 'warning', badgeBg: 'bg-error-container text-error-container', badgeIcon: 'error' },
};

export function HistoryPage({ missions = DEFAULT_MISSIONS }: Props = {}) {
  return (
    <main className="flex-grow px-container-margin py-stack-lg max-w-[1280px] mx-auto w-full pb-32">
      <header className="mb-stack-lg">
        <h1 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary mb-2">Mission History</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">Review your past travels and recovery operations.</p>
      </header>

      {/* Timeline / List Container */}
      <div className="flex flex-col gap-stack-md relative">
        {/* Timeline Line (Desktop only) */}
        <div className="hidden md:block absolute left-8 top-8 bottom-8 w-[2px] bg-outline-variant z-0"></div>

        {missions.map((mission) => {
          const config = STATUS_CONFIG[mission.status];
          return (
            <div
              key={mission.id}
              className={`relative bg-surface-container-lowest rounded-xl border border-outline-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] p-stack-md flex flex-col md:flex-row gap-stack-md z-10 transition-all hover:shadow-lg group ${mission.status === 'Cancelled' ? 'opacity-75' : ''}`}
            >
              {/* Icon */}
              <div className="hidden md:flex flex-col items-center justify-start min-w-[64px]">
                <div className={`w-12 h-12 rounded-full ${config.iconBg} flex items-center justify-center mb-2 group-hover:scale-110 transition-transform`}>
                  <span className="material-symbols-outlined">{config.icon}</span>
                </div>
              </div>

              {/* Content */}
              <div className="flex-grow">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-3">
                    <h2 className="font-headline-md text-headline-md text-primary">
                      {mission.origin} <span className="text-outline-variant mx-1">→</span> {mission.destination}
                    </h2>
                  </div>
                  <span className={`${config.badgeBg} px-3 py-1 rounded-full font-label-sm text-label-sm uppercase tracking-wider flex items-center gap-1`}>
                    <span className="material-symbols-outlined text-[14px]">{config.badgeIcon}</span>
                    {mission.status}
                  </span>
                </div>
                <div className="font-body-md text-body-md text-on-surface-variant mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-[18px]">calendar_today</span>
                  {mission.date}
                </div>
                {mission.description && (
                  <div className="bg-surface-bright rounded-lg p-3 border border-outline-variant/50 text-sm flex flex-col gap-2">
                    <div className="flex items-start gap-2">
                      <span className="material-symbols-outlined text-outline text-[16px] mt-0.5">
                        {mission.status === 'Failed' ? 'report' : mission.status === 'Recovered' ? 'flight_takeoff' : 'info'}
                      </span>
                      <span className="font-body-md text-body-md text-on-surface-variant">{mission.description}</span>
                    </div>
                    {mission.hasDetails && (
                      <button className="text-secondary font-label-md text-label-md flex items-center gap-1 hover:underline w-fit">
                        View Recovery Details <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </main>
  );
}
