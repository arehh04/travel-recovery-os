/** Flight recommendation card — stitch UI inspired Recovery Plan design.
 *
 * Premium card with route display, confidence badge, and evidence badges.
 * Preserves all text formats expected by tests.
 */

import type { FlightInfo } from '../api/types';

interface Props {
  flight: FlightInfo;
  confidence: number;
  evidenceBadges?: string[];
  highlight?: boolean;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

function formatDateTime(raw: string): string {
  if (!raw || raw.length < 8) return raw;
  // Input like "202608200705" → "20 Aug 07:05"
  if (raw.length >= 12) {
    const mo = raw.slice(4, 6);
    const d = raw.slice(6, 8);
    const h = raw.slice(8, 10);
    const mi = raw.slice(10, 12);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${d} ${months[parseInt(mo, 10) - 1]} ${h}:${mi}`;
  }
  return raw;
}

export function FlightCard({ flight, confidence, evidenceBadges, highlight }: Props) {
  return (
    <div
      className="flight-card"
      data-testid="flight-card"
      style={highlight ? { borderColor: 'var(--primary)', borderWidth: '2px' } : undefined}
    >
      {/* Header with flight number, carrier, confidence */}
      <div className="flight-header">
        <div>
          <div className="flight-number">{flight.flight_number}</div>
          <div className="carrier">{flight.carrier}</div>
        </div>
        <div className="confidence-badge">
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>verified</span>
          <span>{Math.round(confidence * 100)}%</span>
        </div>
      </div>

      {/* Route display */}
      <div className="flight-route">
        <div className="route-departure">
          <span className="route-time">{formatDateTime(flight.departure)}</span>
        </div>
        <div className="route-line">
          <span className="material-symbols-outlined route-arrow-icon">arrow_forward</span>
        </div>
        <div className="route-arrival">
          <span className="route-time">{formatDateTime(flight.arrival)}</span>
        </div>
      </div>

      {/* Details grid */}
      <div className="flight-details">
        <div className="detail">
          <span className="label">Price</span>
          <span className="value">{flight.currency} {flight.price.toFixed(2)}</span>
        </div>
        <div className="detail">
          <span className="label">Stops</span>
          <span className="value">{flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`}</span>
        </div>
        <div className="detail">
          <span className="label">Duration</span>
          <span className="value">{formatDuration(flight.duration_minutes)}</span>
        </div>
        <div className="detail">
          <span className="label">Score</span>
          <span className="value">{flight.score.toFixed(1)}</span>
        </div>
      </div>

      {/* Evidence badges */}
      {evidenceBadges && evidenceBadges.length > 0 && (
        <div className="evidence-badges">
          {evidenceBadges.map((badge, i) => (
            <span key={i} className="evidence-badge">
              <span className="material-symbols-outlined">check_circle</span>
              {badge}
            </span>
          ))}
        </div>
      )}

      {/* Score footer */}
      <div className="flight-score">
        Score: {flight.score.toFixed(1)}
      </div>
    </div>
  );
}
