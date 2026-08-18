/** Mission progress — phase-based progress display. */

const PHASES = [
  { key: 'CONTEXT', label: 'Context' },
  { key: 'PLANNING', label: 'Planning' },
  { key: 'FLIGHT_SEARCH', label: 'Flight Search' },
  { key: 'BUDGET', label: 'Budget' },
  { key: 'CRITIC', label: 'Review' },
  { key: 'REFLECTION', label: 'Reflection' },
  { key: 'VALIDATION', label: 'Validation' },
  { key: 'SUMMARY', label: 'Summary' },
  { key: 'COMPLETED', label: 'Complete' },
];

interface Props {
  status: string;
  phase: string;
  progress: number;
  elapsedMs: number;
  onCancel?: () => void;
}

export function MissionProgress({ status, phase, progress, elapsedMs, onCancel }: Props) {
  const currentIdx = PHASES.findIndex((p) => p.key === phase);

  return (
    <div className="mission-progress" data-testid="mission-progress">
      <h2>Mission Progress</h2>

      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${Math.round(progress * 100)}%` }}
          data-testid="progress-bar"
        />
      </div>
      <p className="progress-text">{Math.round(progress * 100)}% — {(elapsedMs / 1000).toFixed(1)}s</p>

      <ul className="phase-list">
        {PHASES.map((p, idx) => {
          let icon = '○';
          if (idx < currentIdx) icon = '✓';
          else if (idx === currentIdx) icon = '●';

          return (
            <li key={p.key} className={`phase-item ${idx <= currentIdx ? 'active' : ''}`}>
              <span className="phase-icon">{icon}</span>
              <span>{p.label}</span>
            </li>
          );
        })}
      </ul>

      {status === 'RUNNING' && onCancel && (
        <button onClick={onCancel} className="btn-danger" data-testid="cancel-btn">
          Cancel Mission
        </button>
      )}
    </div>
  );
}
