/** Flight recommendation card — mobile-first. */

import type { FlightInfo } from '../api/types';

interface Props {
  flight: FlightInfo;
  confidence: number;
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
    const y = raw.slice(0, 4);
    const mo = raw.slice(4, 6);
    const d = raw.slice(6, 8);
    const h = raw.slice(8, 10);
    const mi = raw.slice(10, 12);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${d} ${months[parseInt(mo, 10) - 1]} ${h}:${mi}`;
  }
  return raw;
}

export function FlightCard({ flight, confidence }: Props) {
  return (
    <div className="flight-card" data-testid="flight-card">
      <div className="flight-header">
        <span className="flight-number">{flight.flight_number}</span>
        <span className="carrier">{flight.carrier}</span>
      </div>

      <div className="flight-route">
        <span className="departure">{formatDateTime(flight.departure)}</span>
        <span className="arrow">→</span>
        <span className="arrival">{formatDateTime(flight.arrival)}</span>
      </div>

      <div className="flight-details">
        <div className="detail">
          <span className="label">Price</span>
          <span className="value">{flight.currency} {flight.price.toFixed(2)}</span>
        </div>
        <div className="detail">
          <span className="label">Stops</span>
          <span className="value">{flight.stops === 0 ? 'Direct' : `${flight.stops} stop`}</span>
        </div>
        <div className="detail">
          <span className="label">Duration</span>
          <span className="value">{formatDuration(flight.duration_minutes)}</span>
        </div>
        <div className="detail">
          <span className="label">Confidence</span>
          <span className="value">{Math.round(confidence * 100)}%</span>
        </div>
      </div>

      <div className="flight-score">
        Score: {flight.score.toFixed(1)}
      </div>
    </div>
  );
}
