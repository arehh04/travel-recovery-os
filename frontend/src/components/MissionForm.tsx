/** Mission creation form — stitch UI inspired Start Recovery screen.
 *
 * Adopts the navires_start_recovery_1 design with bento card layout,
 * route group, details grid, and configurable defaults.
 */

import { useState } from 'react';
import type { MissionRequest } from '../api/types';

interface Props {
  onSubmit: (request: MissionRequest) => void;
  disabled?: boolean;
  defaultOrigin?: string;
  defaultDestination?: string;
  defaultDate?: string;
  defaultBudget?: number;
  defaultCurrency?: string;
  onViewTrips?: () => void;
}

export function MissionForm({
  onSubmit,
  disabled,
  defaultOrigin = 'KUL',
  defaultDestination = 'NRT',
  defaultDate = '2026-08-20',
  defaultBudget = 1000,
  defaultCurrency = 'USD',
  onViewTrips,
}: Props) {
  const [origin, setOrigin] = useState(defaultOrigin);
  const [destination, setDestination] = useState(defaultDestination);
  const [departureDate, setDepartureDate] = useState(defaultDate);
  const [travelerCount, setTravelerCount] = useState(1);
  const [currency, setCurrency] = useState(defaultCurrency);
  const [budgetLimit, setBudgetLimit] = useState(defaultBudget);
  const [travelerType, setTravelerType] = useState('Business');
  const [disruptionType, setDisruptionType] = useState('FlightCancelled');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      origin: origin.toUpperCase(),
      destination: destination.toUpperCase(),
      departure_date: departureDate,
      traveler_count: travelerCount,
      currency,
      traveler_type: travelerType,
      disruption_type: disruptionType,
      budget_limit: budgetLimit,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="mission-form" data-testid="mission-form">
      <h2>Recover my trip</h2>

      {/* Route group */}
      <div className="route-group">
        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">flight_takeoff</span>
            Origin
          </span>
          <input
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            maxLength={3}
            placeholder="City or Airport"
            className="tr-input"
            style={{ textTransform: 'uppercase', fontWeight: 700 }}
            required
            disabled={disabled}
            data-testid="origin-input"
          />
        </label>

        <div className="route-arrow">
          <span className="material-symbols-outlined">arrow_right_alt</span>
        </div>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">flight_land</span>
            Destination
          </span>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            maxLength={3}
            placeholder="City or Airport"
            className="tr-input"
            style={{ textTransform: 'uppercase', fontWeight: 700 }}
            required
            disabled={disabled}
            data-testid="destination-input"
          />
        </label>
      </div>

      {/* Details grid */}
      <div className="details-grid">
        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">calendar_today</span>
            Target Date
          </span>
          <input
            type="date"
            value={departureDate}
            onChange={(e) => setDepartureDate(e.target.value)}
            className="tr-input"
            required
            disabled={disabled}
            data-testid="date-input"
          />
        </label>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">person</span>
            Travelers
          </span>
          <select
            value={travelerCount}
            onChange={(e) => setTravelerCount(Number(e.target.value))}
            className="tr-input"
            disabled={disabled}
          >
            <option value={1}>1 Adult</option>
            <option value={2}>2 Adults</option>
            <option value={3}>3 Adults</option>
            <option value={4}>4 Adults</option>
            <option value={5}>5 Adults</option>
          </select>
        </label>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">payments</span>
            Max Budget
          </span>
          <input
            type="number"
            value={budgetLimit}
            onChange={(e) => setBudgetLimit(Number(e.target.value))}
            min={0}
            step={50}
            className="tr-input"
            required
            disabled={disabled}
            data-testid="budget-input"
          />
        </label>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">paid</span>
            Currency
          </span>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="tr-input"
            disabled={disabled}
          >
            <option value="USD">USD ($)</option>
            <option value="EUR">EUR (€)</option>
            <option value="GBP">GBP (£)</option>
            <option value="MYR">MYR (RM)</option>
            <option value="JPY">JPY (¥)</option>
          </select>
        </label>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">work</span>
            Traveler Type
          </span>
          <select
            value={travelerType}
            onChange={(e) => setTravelerType(e.target.value)}
            className="tr-input"
            disabled={disabled}
          >
            <option value="Business">Business</option>
            <option value="Leisure">Leisure</option>
            <option value="Family">Family</option>
          </select>
        </label>

        <label className="form-field">
          <span className="form-field-label">
            <span className="material-symbols-outlined">error</span>
            Disruption Type
          </span>
          <select
            value={disruptionType}
            onChange={(e) => setDisruptionType(e.target.value)}
            className="tr-input"
            disabled={disabled}
          >
            <option value="FlightCancelled">Flight Cancelled</option>
            <option value="FlightDelayed">Flight Delayed</option>
            <option value="MissedConnection">Missed Connection</option>
          </select>
        </label>
      </div>

      <hr className="form-divider" />

      {/* Actions */}
      <div className="form-actions">
        {onViewTrips && (
          <button type="button" className="btn-secondary" onClick={onViewTrips}>
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>history</span>
            View previous trips
          </button>
        )}
        <button type="submit" className="btn-primary" disabled={disabled} data-testid="submit-btn">
          {disabled ? 'Submitting...' : 'Start Recovery'}
          {!disabled && (
            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>
              arrow_forward
            </span>
          )}
        </button>
      </div>
    </form>
  );
}
