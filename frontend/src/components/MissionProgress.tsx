/** Mission progress — stitch UI inspired Live Recovery screen.
 *
 * Adopts the navires_live_recovery design with animated radar ring,
 * timeline with check/active/pending states, and route badge.
 */

const PHASES = [
  { key: 'CONTEXT', label: 'Mission understood' },
  { key: 'PLANNING', label: 'Traveler constraints checked' },
  { key: 'FLIGHT_SEARCH', label: 'Searching live flights' },
  { key: 'BUDGET', label: 'Checking budget' },
  { key: 'CRITIC', label: 'Comparing alternatives' },
  { key: 'REFLECTION', label: 'Reviewing recommendation' },
  { key: 'VALIDATION', label: 'Final validation' },
  { key: 'SUMMARY', label: 'Summarizing results' },
  { key: 'COMPLETED', label: 'Complete' },
];

interface Props {
  status: string;
  phase: string;
  progress: number;
  elapsedMs: number;
  onCancel?: () => void;
  origin?: string;
  destination?: string;
  date?: string;
  offersFound?: number;
}

export function MissionProgress({
  status,
  phase,
  progress,
  elapsedMs,
  onCancel,
  origin,
  destination,
  date,
  offersFound,
}: Props) {
  const currentIdx = PHASES.findIndex((p) => p.key === phase);
  const isRunning = status === 'RUNNING';

  return (
    <div className="mission-progress" data-testid="mission-progress">
      {/* Route badge */}
      {origin && destination && (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <div className="route-badge">
            <span className="material-symbols-outlined">flight_takeoff</span>
            <span>
              {origin} <span className="material-symbols-outlined" style={{ fontSize: 16, verticalAlign: 'middle', padding: '0 4px' }}>arrow_right_alt</span> {destination}
              {date && `, ${date}`}
            </span>
          </div>
        </div>
      )}

      {/* Animated radar ring */}
      <div className="radar-ring">
        <svg className="radar-ring-track" viewBox="0 0 100 100">
          <circle cx="50" cy="50" fill="none" r="46" stroke="currentColor" strokeWidth="4" />
        </svg>
        {isRunning && (
          <svg
            className="radar-ring-active"
            viewBox="0 0 100 100"
            style={{ strokeDasharray: '100 200', strokeLinecap: 'round' }}
          >
            <circle cx="50" cy="50" fill="none" r="46" stroke="currentColor" strokeWidth="6" />
          </svg>
        )}
        <div className="radar-ring-icon">
          <span className="material-symbols-outlined">
            {isRunning ? 'radar' : 'check_circle'}
          </span>
        </div>
      </div>

      {/* Status text */}
      <div style={{ textAlign: 'center' }}>
        <h2>
          {isRunning ? 'Searching live flight options' : 'Mission complete'}
        </h2>
        {offersFound !== undefined && (
          <p style={{ fontSize: '0.875rem', color: 'var(--on-surface-variant)', marginTop: '4px' }}>
            {offersFound} live offers found
          </p>
        )}
      </div>

      {/* Progress bar (preserved for tests) */}
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${Math.round(progress * 100)}%` }}
          data-testid="progress-bar"
        />
      </div>
      <p className="progress-text">
        {Math.round(progress * 100)}% — {(elapsedMs / 1000).toFixed(1)}s
      </p>

      {/* Timeline */}
      <ul className="phase-list">
        {PHASES.map((p, idx) => {
          let icon = '○';
          let phaseClass = 'phase-pending';

          if (idx < currentIdx) {
            icon = '✓';
            phaseClass = 'phase-completed';
          } else if (idx === currentIdx) {
            icon = '●';
            phaseClass = 'phase-current';
          }

          return (
            <li
              key={p.key}
              className={`phase-item ${idx <= currentIdx ? 'active' : ''} ${phaseClass}`}
            >
              <span className={`phase-icon ${phaseClass === 'phase-completed' ? 'completed' : phaseClass === 'phase-current' ? 'current' : 'pending'}`}>
                {icon}
              </span>
              <span className={`phase-label ${phaseClass}`}>
                {p.label}
              </span>
            </li>
          );
        })}
      </ul>

      {/* Cancel button */}
      {isRunning && onCancel && (
        <button onClick={onCancel} className="btn-danger" data-testid="cancel-btn">
          Cancel Mission
        </button>
      )}

      {/* Bottom status indicator */}
      {isRunning && (
        <div className="status-indicator">
          <div className="status-indicator-inner">
            <span className="material-symbols-outlined">sync</span>
            <span className="status-indicator-text">Navires is evaluating your options...</span>
          </div>
        </div>
      )}
    </div>
  );
}
