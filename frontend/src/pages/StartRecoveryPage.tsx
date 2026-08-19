/** Start Recovery page — stitch home page with dynamic form + validation. */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { MissionRequest } from '../api/types';

interface Props {
  defaultOrigin?: string;
  defaultDestination?: string;
  defaultDate?: string;
  defaultBudget?: number;
  defaultCurrency?: string;
}

// Common airport name → IATA code mapping for user-friendly input
const AIRPORT_MAP: Record<string, string> = {
  // Kuala Lumpur
  'kuala lumpur': 'KUL', 'klia': 'KUL', 'kul': 'KUL',
  // Singapore
  'singapore': 'SIN', 'changi': 'SIN', 'sin': 'SIN',
  // Tokyo
  'tokyo': 'NRT', 'narita': 'NRT', 'nrt': 'NRT', 'haneda': 'HND', 'hnd': 'HND',
  // Bangkok
  'bangkok': 'BKK', 'suvarnabhumi': 'BKK', 'bkk': 'BKK', 'dmk': 'DMK', 'don mueang': 'DMK',
  // Hong Kong
  'hong kong': 'HKG', 'hkg': 'HKG',
  // London
  'london': 'LHR', 'heathrow': 'LHR', 'lhr': 'LHR', 'lgw': 'LGW', 'gatwick': 'LGW',
  // New York
  'new york': 'JFK', 'jfk': 'JFK', 'lga': 'LGA', 'la guardia': 'LGA', 'newark': 'EWR', 'ewr': 'EWR',
  // Other common
  'osaka': 'KIX', 'kix': 'KIX', 'seoul': 'ICN', 'icn': 'ICN', 'taipei': 'TPE', 'tpe': 'TPE',
  'sydney': 'SYD', 'syd': 'SYD', 'melbourne': 'MEL', 'mel': 'MEL',
  'bali': 'DPS', 'denpasar': 'DPS', 'dps': 'DPS',
  'penang': 'PEN', 'pen': 'PEN', 'kota kinabalu': 'BKI', 'bki': 'BKI',
  'jakarta': 'CGK', 'cgk': 'CGK', 'manila': 'MNL', 'mnl': 'MNL',
  'shanghai': 'PVG', 'pvg': 'PVG', 'beijing': 'PEK', 'pek': 'PEK',
  'delhi': 'DEL', 'del': 'DEL', 'mumbai': 'BOM', 'bom': 'BOM',
  'paris': 'CDG', 'cdg': 'CDG', 'dubai': 'DXB', 'dxb': 'DXB',
  'istanbul': 'IST', 'ist': 'IST', 'frankfurt': 'FRA', 'fra': 'FRA',
  'amsterdam': 'AMS', 'ams': 'AMS',
};

function resolveIATA(input: string): string | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  // If already 3 uppercase letters, use as-is
  if (/^[A-Z]{3}$/.test(trimmed.toUpperCase())) {
    return trimmed.toUpperCase();
  }
  // Try city/airport name lookup
  const lower = trimmed.toLowerCase();
  if (AIRPORT_MAP[lower]) {
    return AIRPORT_MAP[lower];
  }
  // Try partial match
  for (const [name, code] of Object.entries(AIRPORT_MAP)) {
    if (name.includes(lower) || lower.includes(name)) {
      return code;
    }
  }
  return null;
}

export function StartRecoveryPage({
  defaultOrigin = '',
  defaultDestination = '',
  defaultDate = '',
  defaultBudget = 1000,
  defaultCurrency = 'USD',
}: Props = {}) {
  const navigate = useNavigate();
  const [origin, setOrigin] = useState(defaultOrigin);
  const [destination, setDestination] = useState(defaultDestination);
  const [date, setDate] = useState(defaultDate);
  const [travelers, setTravelers] = useState(1);
  const [budget, setBudget] = useState(defaultBudget);
  const [currency, setCurrency] = useState(defaultCurrency);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): { valid: boolean; originCode: string | null; destCode: string | null } => {
    const newErrors: Record<string, string> = {};

    const originCode = resolveIATA(origin);
    if (!origin) {
      newErrors.origin = 'Origin is required';
    } else if (!originCode) {
      newErrors.origin = 'Enter a valid airport code (e.g., KUL) or city name (e.g., Kuala Lumpur)';
    }

    const destCode = resolveIATA(destination);
    if (!destination) {
      newErrors.destination = 'Destination is required';
    } else if (!destCode) {
      newErrors.destination = 'Enter a valid airport code (e.g., SIN) or city name (e.g., Singapore)';
    }

    if (originCode && destCode && originCode === destCode) {
      newErrors.destination = 'Destination must be different from origin';
    }

    if (!date) {
      newErrors.date = 'Date is required';
    }

    if (budget <= 0) {
      newErrors.budget = 'Budget must be greater than 0';
    }

    setErrors(newErrors);
    return { valid: Object.keys(newErrors).length === 0, originCode, destCode };
  };

  const handleSubmit = () => {
    const { valid, originCode, destCode } = validate();
    if (!valid || !originCode || !destCode) return;

    const request: MissionRequest = {
      origin: originCode,
      destination: destCode,
      departure_date: date,
      traveler_count: travelers,
      currency,
      traveler_type: 'Business',
      disruption_type: 'FlightCancelled',
      budget_limit: budget,
    };
    navigate('/recovery/live', { state: { request } });
  };

  return (
    <>
      <main className="flex-grow w-full max-w-[1280px] mx-auto px-container-margin py-stack-lg pb-32 md:pb-stack-lg flex flex-col gap-12">
        {/* Hero Section */}
        <section className="flex flex-col gap-4 max-w-2xl mt-4 md:mt-12">
          <div className="inline-flex items-center gap-2 bg-surface-container px-3 py-1.5 rounded-full w-max">
            <span className="w-2 h-2 rounded-full bg-secondary shadow-[0_0_8px_rgba(0,102,138,0.8)] animate-pulse"></span>
            <span className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider">Assistant Ready</span>
          </div>
          <h1 className="font-display-lg text-display-lg text-on-background lg:text-[56px] lg:leading-[64px]">
            Navires Travel Recovery
          </h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant max-w-xl">
            Your journey changed, let's navigate the unexpected together. We'll help you explore alternative routes and find the best rebooking options tailored to your needs.
          </p>
        </section>

        {/* Recovery Card (Bento Layout) */}
        <section className="bg-surface-container-lowest rounded-xl shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] border border-outline-variant p-6 md:p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-secondary-container/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
          <h2 className="font-headline-md text-headline-md text-on-background mb-8 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>
              add_circle
            </span>
            Recover my trip
          </h2>
          <form className="flex flex-col gap-6" onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
            {/* Route Group */}
            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-center bg-surface p-4 rounded-lg border border-outline-variant/50">
              <div className="flex flex-col gap-2 w-full">
                <label className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">flight_takeoff</span> Origin
                </label>
                <input
                  className={`tr-input font-numeric-data text-numeric-data uppercase ${errors.origin ? 'border-error' : ''}`}
                  placeholder="City or Airport (e.g., KUL)"
                  type="text"
                  value={origin}
                  onChange={(e) => { setOrigin(e.target.value); if (errors.origin) setErrors({ ...errors, origin: '' }); }}
                  data-testid="origin-input"
                />
                {errors.origin && <p className="text-error text-sm font-label-sm">{errors.origin}</p>}
              </div>
              <div className="hidden md:flex w-10 h-10 items-center justify-center rounded-full bg-surface-container border border-outline-variant/30 text-on-surface-variant mt-6">
                <span className="material-symbols-outlined">arrow_right_alt</span>
              </div>
              <div className="flex flex-col gap-2 w-full">
                <label className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">flight_land</span> Destination
                </label>
                <input
                  className={`tr-input font-numeric-data text-numeric-data uppercase ${errors.destination ? 'border-error' : ''}`}
                  placeholder="City or Airport (e.g., SIN)"
                  type="text"
                  value={destination}
                  onChange={(e) => { setDestination(e.target.value); if (errors.destination) setErrors({ ...errors, destination: '' }); }}
                  data-testid="destination-input"
                />
                {errors.destination && <p className="text-error text-sm font-label-sm">{errors.destination}</p>}
              </div>
            </div>
            {/* Details Group */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="flex flex-col gap-2">
                <label className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">calendar_today</span> Target Date
                </label>
                <input
                  className={`tr-input font-body-md text-body-md font-medium ${errors.date ? 'border-error' : ''}`}
                  type="date"
                  value={date}
                  onChange={(e) => { setDate(e.target.value); if (errors.date) setErrors({ ...errors, date: '' }); }}
                />
                {errors.date && <p className="text-error text-sm font-label-sm">{errors.date}</p>}
              </div>
              <div className="flex flex-col gap-2">
                <label className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">person</span> Travelers
                </label>
                <select
                  className="tr-input font-body-md text-body-md font-medium appearance-none pr-10"
                  value={travelers}
                  onChange={(e) => setTravelers(Number(e.target.value))}
                >
                  <option value={1}>1 Adult</option>
                  <option value={2}>2 Adults</option>
                  <option value={3}>3 Adults</option>
                  <option value={4}>4 Adults</option>
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="font-label-sm text-label-sm text-on-surface-variant flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px]">payments</span> Max Budget
                </label>
                <div className="flex gap-2">
                  <select
                    className="tr-input font-body-md text-body-md font-medium w-20"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                  >
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="GBP">GBP</option>
                    <option value="MYR">MYR</option>
                    <option value="JPY">JPY</option>
                  </select>
                  <input
                    className={`tr-input font-body-md text-body-md font-medium flex-1 ${errors.budget ? 'border-error' : ''}`}
                    type="number"
                    value={budget}
                    onChange={(e) => setBudget(Number(e.target.value))}
                  />
                </div>
                {errors.budget && <p className="text-error text-sm font-label-sm">{errors.budget}</p>}
              </div>
            </div>
            <hr className="border-outline-variant/30 my-2" />
            {/* Actions */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-6 pt-2">
              <button
                type="button"
                onClick={() => navigate('/history')}
                className="w-full md:w-auto font-label-md text-label-md text-secondary hover:text-secondary-container transition-colors flex items-center justify-center gap-2 py-2 px-4 rounded-lg hover:bg-secondary/5"
              >
                <span className="material-symbols-outlined text-[20px]">history</span>
                View previous trips
              </button>
              <button
                type="submit"
                className="w-full md:w-auto bg-primary-container text-on-primary hover:bg-primary-container/90 active:scale-95 transition-all duration-200 font-label-md text-label-md py-4 px-8 rounded-lg flex items-center justify-center gap-2 shadow-[0_4px_12px_rgba(19,27,46,0.15)] group"
                data-testid="submit-btn"
              >
                Start Recovery
                <span className="material-symbols-outlined text-[20px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
              </button>
            </div>
          </form>
        </section>
      </main>
    </>
  );
}
