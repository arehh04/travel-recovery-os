/** History page — Enterprise Recovery Mission Ledger & Timeline. */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { HistoryMission } from '../types/app';
import type { MissionHistoryItem } from '../api/types';

interface Props {
  missions?: HistoryMission[];
}

const DEFAULT_MISSIONS: HistoryMission[] = [
  { id: 'mission-ba117-001', origin: 'LHR', destination: 'JFK', date: '21 Aug 2026', status: 'Recovered', description: 'Transatlantic weather cancellation. Multi-Agent Swarm rerouted via BA112 with EU261 €600 compensation.', hasDetails: true },
  { id: 'mission-sq321-002', origin: 'SIN', destination: 'LHR', date: '20 Aug 2026', status: 'Completed', description: 'Aircraft maintenance delay. Swarm assigned Crowne Plaza transit voucher & SQ306 flight rebooking.', hasDetails: true },
  { id: 'mission-aa204-003', origin: 'ORD', destination: 'LAX', date: '18 Aug 2026', status: 'Recovered', description: 'Blizzard ground-stop. Intermodal transfer arranged via Amtrak Midwest + United mainline flight.', hasDetails: true },
];

const STATUS_CONFIG: Record<string, { iconBg: string; icon: string; badgeBg: string; badgeIcon: string }> = {
  Recovered: { iconBg: 'bg-secondary-container text-on-secondary-container', icon: 'health_and_safety', badgeBg: 'bg-secondary-container text-on-secondary-container', badgeIcon: 'check_circle' },
  COMPLETED: { iconBg: 'bg-tertiary-container text-on-tertiary-container', icon: 'done_all', badgeBg: 'bg-tertiary-container text-on-tertiary-container', badgeIcon: 'done' },
  Completed: { iconBg: 'bg-tertiary-container text-on-tertiary-container', icon: 'done_all', badgeBg: 'bg-tertiary-container text-on-tertiary-container', badgeIcon: 'done' },
  RUNNING: { iconBg: 'bg-primary-container text-on-primary-container', icon: 'autorenew', badgeBg: 'bg-primary-container text-on-primary-container', badgeIcon: 'sync' },
  Cancelled: { iconBg: 'bg-surface-variant text-on-surface-variant', icon: 'cancel', badgeBg: 'bg-surface-variant text-on-surface-variant', badgeIcon: 'block' },
  CANCELLED: { iconBg: 'bg-surface-variant text-on-surface-variant', icon: 'cancel', badgeBg: 'bg-surface-variant text-on-surface-variant', badgeIcon: 'block' },
  Failed: { iconBg: 'bg-error-container text-error-container', icon: 'warning', badgeBg: 'bg-error-container text-error-container', badgeIcon: 'error' },
  FAILED: { iconBg: 'bg-error-container text-error-container', icon: 'warning', badgeBg: 'bg-error-container text-error-container', badgeIcon: 'error' },
};

export function HistoryPage({ missions: propMissions }: Props = {}) {
  const navigate = useNavigate();
  const [liveMissions, setLiveMissions] = useState<HistoryMission[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMissions();
  }, []);

  const loadMissions = async () => {
    try {
      setLoading(true);
      const data = await api.get<MissionHistoryItem[]>('/missions');
      if (data && data.length > 0) {
        const formatted: HistoryMission[] = data.map((item) => {
          const dateStr = new Date(item.started_at).toLocaleDateString('en-GB', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
          });
          const recDesc = item.recommended_flight
            ? `AI assigned flight ${item.recommended_flight} (${item.carrier || 'Mainline'}). Confidence: ${Math.round(item.confidence * 100)}%`
            : `Mission phase: ${item.phase || 'Initiated'}`;

          return {
            id: item.mission_id,
            origin: 'LHR',
            destination: 'JFK',
            date: dateStr,
            status: item.status === 'COMPLETED' ? 'Recovered' : item.status as any,
            description: recDesc,
            hasDetails: item.has_result,
          };
        });
        setLiveMissions(formatted);
      } else {
        setLiveMissions(DEFAULT_MISSIONS);
      }
    } catch (e) {
      console.warn('Using default mission history fallback:', e);
      setLiveMissions(DEFAULT_MISSIONS);
    } finally {
      setLoading(false);
    }
  };

  const missions = propMissions || liveMissions;

  const handleViewDetails = (mission: HistoryMission) => {
    navigate('/recovery/plan?mission_id=' + mission.id);
  };

  const handleStartNew = () => {
    navigate('/');
  };

  return (
    <main className="flex-grow px-container-margin py-stack-lg max-w-[1280px] mx-auto w-full pb-32">
      <header className="mb-stack-lg flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-secondary">history</span>
            <span className="font-label-sm text-secondary font-semibold uppercase tracking-wider">Enterprise Audit Trail</span>
          </div>
          <h1 className="font-headline-lg-mobile md:font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary">
            Mission History & Logs
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Chronological audit of autonomous travel recovery missions, decisions, and claims.
          </p>
        </div>
        <button
          onClick={handleStartNew}
          className="bg-primary-container text-on-primary hover:bg-primary-container/90 font-label-md text-label-md px-5 py-3 rounded-lg flex items-center gap-2 transition-all active:scale-95 shadow-sm"
        >
          <span className="material-symbols-outlined text-[20px]">add</span>
          New Recovery Mission
        </button>
      </header>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-10 h-10 border-4 border-secondary/30 border-t-secondary rounded-full animate-spin"></div>
          <p className="font-label-md text-on-surface-variant mt-4">Loading mission ledger...</p>
        </div>
      ) : missions.length === 0 ? (
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-12 flex flex-col items-center gap-4 text-center shadow-sm">
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant">luggage</span>
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface mb-1">No missions yet</h2>
            <p className="font-body-md text-body-md text-on-surface-variant mb-4">Start your first autonomous recovery mission.</p>
          </div>
          <button
            onClick={handleStartNew}
            className="bg-primary-container text-on-primary hover:bg-primary-container/90 font-label-md text-label-md px-5 py-3 rounded-lg flex items-center gap-2 transition-all"
          >
            <span className="material-symbols-outlined text-[20px]">flight_takeoff</span>
            Start Recovery
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-stack-md relative">
          {missions.map((mission) => {
            const config = STATUS_CONFIG[mission.status] || STATUS_CONFIG.Completed;
            return (
              <div
                key={mission.id}
                className="relative bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-6 flex flex-col md:flex-row gap-6 z-10 transition-all hover:shadow-md group"
              >
                {/* Icon */}
                <div className="hidden md:flex flex-col items-center justify-start min-w-[56px]">
                  <div className={`w-12 h-12 rounded-full ${config.iconBg} flex items-center justify-center group-hover:scale-110 transition-transform shadow-inner`}>
                    <span className="material-symbols-outlined">{config.icon}</span>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-grow space-y-2">
                  <div className="flex justify-between items-start flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                      <h2 className="font-headline-md text-primary flex items-center gap-2">
                        <span>{mission.origin}</span>
                        <span className="material-symbols-outlined text-[18px] text-on-surface-variant">arrow_forward</span>
                        <span>{mission.destination}</span>
                      </h2>
                      <span className="text-xs font-mono text-on-surface-variant bg-surface-container-high px-2 py-0.5 rounded">
                        {mission.id}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-label-sm flex items-center gap-1 font-semibold ${config.badgeBg}`}>
                        <span className="material-symbols-outlined text-[14px]">{config.badgeIcon}</span>
                        {mission.status}
                      </span>
                      <span className="text-xs font-label-md text-on-surface-variant">{mission.date}</span>
                    </div>
                  </div>

                  <p className="font-body-md text-on-surface-variant text-sm">{mission.description}</p>

                  <div className="pt-2 flex items-center gap-3">
                    <button
                      onClick={() => handleViewDetails(mission)}
                      className="text-xs font-label-md bg-secondary text-on-secondary px-3.5 py-1.5 rounded-lg flex items-center gap-1.5 hover:bg-secondary/90 transition-colors shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[16px]">visibility</span>
                      Inspect Recovery Plan
                    </button>
                    <button
                      onClick={() => navigate('/swarm')}
                      className="text-xs font-label-md text-on-surface-variant hover:text-primary px-2 py-1.5 flex items-center gap-1 transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">hub</span>
                      View Swarm Logs
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}
