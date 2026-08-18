/** Mission result screen — final recommendation and details. */

import type { MissionResult } from '../api/types';
import { FlightCard } from './FlightCard';

interface Props {
  result: MissionResult;
  onNewMission: () => void;
}

export function MissionResultView({ result, onNewMission }: Props) {
  const isApproved = result.status === 'approved' || result.status === 'completed';

  return (
    <div className="mission-result" data-testid="mission-result">
      <div className={`status-badge ${isApproved ? 'approved' : 'failed'}`}>
        {isApproved ? 'Recommendation Approved' : `Status: ${result.status}`}
      </div>

      {result.recommendation && (
        <FlightCard flight={result.recommendation} confidence={result.confidence} />
      )}

      {result.alternatives.length > 0 && (
        <section className="alternatives">
          <h3>Alternatives</h3>
          {result.alternatives.map((alt, i) => (
            <div key={i} className="alt-card">
              <strong>{alt.flight_number}</strong> — {alt.carrier}
              <span>{alt.currency} {alt.price.toFixed(2)}</span>
              <span>Score: {alt.score.toFixed(1)}</span>
            </div>
          ))}
        </section>
      )}

      <section className="budget-section">
        <h3>Budget</h3>
        <pre>{JSON.stringify(result.budget, null, 2)}</pre>
      </section>

      {result.conflicts.count > 0 && (
        <section className="conflicts">
          <h3>Warnings</h3>
          <p>{result.conflicts.count} conflict(s) detected
            {result.conflicts.has_critical && ' (critical)'}
          </p>
        </section>
      )}

      {result.recovery.occurred && (
        <section className="recovery-info">
          <h3>Recovery</h3>
          <p>Recovery attempted: {result.recovery.attempts} attempt(s)</p>
          <p>Recovered: {result.recovery.recovered ? 'Yes' : 'No'}</p>
          {result.recovery.reason && <p>Reason: {result.recovery.reason}</p>}
        </section>
      )}

      <section className="execution-meta">
        <p>Mission: {result.mission_id}</p>
        <p>Duration: {result.execution_metadata.duration_ms}ms</p>
      </section>

      <button onClick={onNewMission} className="btn-primary" data-testid="new-mission-btn">
        New Mission
      </button>
    </div>
  );
}
