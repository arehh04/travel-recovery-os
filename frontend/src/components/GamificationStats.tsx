import type { GamificationStats as Stats } from '../api/types';

interface GamificationStatsProps {
  stats: Stats;
}

export function GamificationStats({ stats }: GamificationStatsProps) {
  if (!stats) return null;

  return (
    <section className="bg-surface-container-lowest border border-outline-variant shadow-lg rounded-xl p-6 md:p-8 relative overflow-hidden mt-8 w-full max-w-4xl mx-auto">
      {/* Decorative background element */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4 pointer-events-none"></div>
      
      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
        <div className="flex-1 text-center md:text-left">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-2 flex items-center justify-center md:justify-start gap-2">
            <span className="material-symbols-outlined text-primary text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              workspace_premium
            </span>
            Impact Summary
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-sm">
            Here's what you saved by letting TR-OS negotiate your recovery instead of waiting in line at the airport.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          {/* Time Saved Card */}
          <div className="flex-1 sm:w-48 bg-secondary-container/30 border border-secondary-container rounded-xl p-5 flex flex-col items-center justify-center gap-2">
            <span className="material-symbols-outlined text-secondary text-[32px]">schedule</span>
            <div className="text-center">
              <div className="font-display-md text-display-md text-on-surface tracking-tight">
                {Math.floor(stats.time_saved_minutes / 60)}<span className="text-2xl">h</span> {stats.time_saved_minutes % 60}<span className="text-2xl">m</span>
              </div>
              <div className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mt-1">Time Saved</div>
            </div>
          </div>

          {/* Money Saved Card */}
          <div className="flex-1 sm:w-48 bg-primary-container/30 border border-primary-container rounded-xl p-5 flex flex-col items-center justify-center gap-2">
            <span className="material-symbols-outlined text-primary text-[32px]">savings</span>
            <div className="text-center">
              <div className="font-display-md text-display-md text-on-surface tracking-tight">
                <span className="text-2xl">$</span>{stats.money_saved.toFixed(2)}
              </div>
              <div className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mt-1">Money Saved</div>
            </div>
          </div>

          {/* Carbon Card (Optional stretch) */}
          <div className="flex-1 sm:w-48 bg-tertiary-container/30 border border-tertiary-container rounded-xl p-5 flex flex-col items-center justify-center gap-2">
            <span className="material-symbols-outlined text-tertiary text-[32px]">eco</span>
            <div className="text-center">
              <div className="font-display-md text-display-md text-on-surface tracking-tight">
                {stats.carbon_offset_kg.toFixed(1)}<span className="text-2xl">kg</span>
              </div>
              <div className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mt-1">CO₂ Offset</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
