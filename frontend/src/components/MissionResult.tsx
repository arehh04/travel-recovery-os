/** Mission result screen — stitch UI inspired Recovery Plan + Alternatives.
 *
 * Adopts the navires_recovery_plan and navires_alternatives designs with
 * status badge, recommendation card, alternatives comparison, budget summary,
 * recovery info, and evidence badges.
 */

import type { MissionResult } from '../api/types';
import { FlightCard } from './FlightCard';

interface Props {
  result: MissionResult;
  onNewMission: () => void;
}

export function MissionResultView({ result, onNewMission }: Props) {
  const isApproved = result.status === 'approved' || result.status === 'completed';
  const statusClass = isApproved ? 'approved' : result.status === 'conditional' ? 'conditional' : 'failed';

  const evidenceBadges = isApproved
    ? ['Within budget', 'Meets constraints', 'Highest score', 'Live Atlas data']
    : [];

  const budgetTotal = result.recommendation
    ? result.recommendation.price
    : 0;
  const budgetLimit = (result.budget as Record<string, unknown>)?.limit as number | undefined;
  const budgetRemaining = budgetLimit ? budgetLimit - budgetTotal : undefined;
  const budgetPct = budgetLimit ? Math.round((budgetTotal / budgetLimit) * 100) : undefined;

  return (
    <div className="mission-result" data-testid="mission-result">
      {/* Status badge */}
      <div className={`status-badge ${statusClass}`}>
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
          {isApproved ? 'check_circle' : result.status === 'conditional' ? 'warning' : 'error'}
        </span>
        {isApproved ? 'Recommendation Approved' : `Status: ${result.status}`}
      </div>

      {/* Recommendation flight card */}
      {result.recommendation && (
        <div className="recovery-card">
          <div className="recovery-card-title">
            <span className="material-symbols-outlined">recommend</span>
            Recommended Flight
          </div>
          <div className="recovery-card-decoration" />
          <FlightCard
            flight={result.recommendation}
            confidence={result.confidence}
            evidenceBadges={evidenceBadges}
            highlight
          />
        </div>
      )}

      {/* Alternatives */}
      {result.alternatives.length > 0 && (
        <section className="result-section alternatives">
          <h3>Alternative Flights</h3>
          {result.alternatives.map((alt, i) => (
            <div key={i} className="alt-card">
              <span className="alt-label">
                {i === 0 ? 'Best Alternative' : `Option ${i + 1}`}
              </span>
              <FlightCard flight={alt} confidence={result.confidence} />
            </div>
          ))}
        </section>
      )}

      {/* Budget summary */}
      <section className="result-section budget-section">
        <h3>Budget</h3>
        {budgetLimit ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '4px' }}>
              <span>Spent: {result.recommendation?.currency} {budgetTotal.toFixed(2)}</span>
              <span>Limit: {result.recommendation?.currency} {budgetLimit.toFixed(2)}</span>
            </div>
            {budgetRemaining !== undefined && (
              <div style={{ fontSize: '0.875rem', color: 'var(--on-surface-variant)' }}>
                Remaining: {result.recommendation?.currency} {budgetRemaining.toFixed(2)} ({budgetPct}% used)
              </div>
            )}
          </>
        ) : (
          <pre>{JSON.stringify(result.budget, null, 2)}</pre>
        )}
      </section>

      {/* Conflict warnings */}
      {result.conflicts.count > 0 && (
        <section className="result-section">
          <h3>Warnings</h3>
          <div className="conflict-warning">
            <span className="material-symbols-outlined" style={{ fontSize: 18, verticalAlign: 'middle' }}>
              warning
            </span>
            {' '}
            {result.conflicts.count} conflict(s) detected
            {result.conflicts.has_critical && ' (critical)'}
          </div>
        </section>
      )}

      {/* Recovery info */}
      {result.recovery.occurred && (
        <section className="result-section">
          <h3>Recovery</h3>
          <div style={{ fontSize: '0.875rem', color: 'var(--on-surface-variant)' }}>
            <p style={{ marginBottom: '4px' }}>
              Recovery attempted: {result.recovery.attempts} attempt(s)
            </p>
            <p style={{ marginBottom: '4px' }}>
              Recovered: {result.recovery.recovered ? 'Yes' : 'No'}
            </p>
            {result.recovery.reason && (
              <p>Reason: {result.recovery.reason}</p>
            )}
          </div>
        </section>
      )}

      {/* Execution metadata */}
      <section className="execution-meta">
        <p>Mission: {result.mission_id}</p>
        <p>Duration: {result.execution_metadata.duration_ms}ms</p>
      </section>

      {/* Actions */}
      <div className="result-actions">
        <button onClick={onNewMission} className="btn-primary" data-testid="new-mission-btn">
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>add</span>
          New Mission
        </button>
      </div>
    </div>
  );
}
