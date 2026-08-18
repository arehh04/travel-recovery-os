/** Mission creation form — mobile-first. */

import { useState } from 'react';
import type { MissionRequest } from '../api/types';

interface Props {
  onSubmit: (request: MissionRequest) => void;
  disabled?: boolean;
}

export function MissionForm({ onSubmit, disabled }: Props) {
  const [origin, setOrigin] = useState('KUL');
  const [destination, setDestination] = useState('NRT');
  const [departureDate, setDepartureDate] = useState('2026-08-20');
  const [travelerCount, setTravelerCount] = useState(1);
  const [currency, setCurrency] = useState('USD');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      origin: origin.toUpperCase(),
      destination: destination.toUpperCase(),
      departure_date: departureDate,
      traveler_count: travelerCount,
      currency,
      traveler_type: 'Business',
      disruption_type: 'FlightCancelled',
      budget_limit: 1000,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="mission-form" data-testid="mission-form">
      <h2>New Mission</h2>

      <label className="form-field">
        <span>Origin (IATA)</span>
        <input
          type="text"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          maxLength={3}
          placeholder="KUL"
          required
          disabled={disabled}
          data-testid="origin-input"
        />
      </label>

      <label className="form-field">
        <span>Destination (IATA)</span>
        <input
          type="text"
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
          maxLength={3}
          placeholder="NRT"
          required
          disabled={disabled}
          data-testid="destination-input"
        />
      </label>

      <label className="form-field">
        <span>Departure Date</span>
        <input
          type="date"
          value={departureDate}
          onChange={(e) => setDepartureDate(e.target.value)}
          required
          disabled={disabled}
          data-testid="date-input"
        />
      </label>

      <label className="form-field">
        <span>Travelers</span>
        <input
          type="number"
          value={travelerCount}
          onChange={(e) => setTravelerCount(Number(e.target.value))}
          min={1}
          max={10}
          required
          disabled={disabled}
        />
      </label>

      <label className="form-field">
        <span>Currency</span>
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value)}
          disabled={disabled}
        >
          <option value="USD">USD</option>
          <option value="EUR">EUR</option>
          <option value="GBP">GBP</option>
          <option value="MYR">MYR</option>
          <option value="JPY">JPY</option>
        </select>
      </label>

      <button type="submit" className="btn-primary" disabled={disabled} data-testid="submit-btn">
        {disabled ? 'Submitting...' : 'Start Mission'}
      </button>
    </form>
  );
}
