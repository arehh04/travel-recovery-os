/** Booking Confirmation page — flight summary + confirm booking flow. */

import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import type { FlightInfo } from '../api/types';

export function BookingConfirmationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as {
    flight?: FlightInfo;
    request?: { origin: string; destination: string; budget_limit: number; currency: string; departure_date: string; traveler_count: number };
    confidence?: number;
  }) || {};

  const flight = state.flight;
  const request = state.request;
  const confidence = state.confidence ?? 90;

  const [bookingConfirmed, setBookingConfirmed] = useState(false);
  const [bookingRef] = useState(() => `NV${Date.now().toString().slice(-6)}${Math.floor(Math.random() * 90 + 10)}`);

  if (!flight) {
    return (
      <main className="flex-1 flex items-center justify-center">
        <p className="text-on-surface-variant">No flight selected for booking.</p>
      </main>
    );
  }

  const currency = flight.currency || request?.currency || 'USD';
  const durationHours = Math.floor(flight.duration_minutes / 60);
  const durationMins = flight.duration_minutes % 60;
  const durationStr = `${durationHours}h ${durationMins}m`;
  const stopsLabel = flight.stops === 0 ? 'Direct' : `${flight.stops} Stop${flight.stops > 1 ? 's' : ''}`;

  // ── Success state ──
  if (bookingConfirmed) {
    return (
      <main className="flex-1 w-full max-w-xl mx-auto px-container-margin py-stack-lg flex flex-col gap-6 items-center justify-center min-h-[60vh]">
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-8 flex flex-col items-center gap-6 shadow-lg max-w-md w-full text-center">
          <div className="w-20 h-20 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center">
            <span className="material-symbols-outlined text-[40px]" style={{ fontVariationSettings: "'FILL' 1" }}>
              check_circle
            </span>
          </div>
          <div>
            <h1 className="font-headline-lg text-headline-lg text-on-surface mb-2">Booking Confirmed!</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Your recovery flight has been successfully booked.
            </p>
          </div>
          <div className="bg-surface rounded-lg px-6 py-4 flex flex-col gap-2 w-full">
            <div className="flex justify-between items-center">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Booking Reference</span>
              <span className="font-numeric-data text-numeric-data text-primary font-bold">{bookingRef}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Flight</span>
              <span className="font-label-md text-label-md text-on-surface">{flight.flight_number}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Route</span>
              <span className="font-label-md text-label-md text-on-surface">{request?.origin || 'Origin'} → {request?.destination || 'Destination'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Departure</span>
              <span className="font-label-md text-label-md text-on-surface">{flight.departure}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-label-sm text-label-sm text-on-surface-variant">Total Paid</span>
              <span className="font-headline-md text-headline-md text-primary">{currency} {flight.price.toFixed(2)}</span>
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="w-full bg-primary-container text-on-primary hover:bg-primary-container/90 font-label-md text-label-md py-3 px-6 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95"
          >
            <span className="material-symbols-outlined text-[20px]">home</span>
            Back to Home
          </button>
        </div>
      </main>
    );
  }

  // ── Booking summary state ──
  return (
    <main className="flex-1 w-full max-w-2xl mx-auto px-container-margin py-stack-lg flex flex-col gap-stack-lg pb-32">
      {/* Header */}
      <header className="flex flex-col gap-2 text-center">
        <div className="inline-flex items-center gap-2 bg-secondary-container px-3 py-1.5 rounded-full w-max mx-auto">
          <span className="material-symbols-outlined text-[16px] text-secondary">confirmation_number</span>
          <span className="font-label-sm text-label-sm text-on-secondary-container uppercase tracking-wider">Booking Summary</span>
        </div>
        <h1 className="font-headline-lg-mobile text-headline-lg-mobile text-on-background mt-2">Confirm your booking</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">Review your flight details and confirm the booking.</p>
      </header>

      {/* Flight Card */}
      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] overflow-hidden flex flex-col">
        <div className="p-stack-md border-b border-outline-variant flex justify-between items-start bg-surface-bright">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container">
              <span className="material-symbols-outlined">flight_takeoff</span>
            </div>
            <div>
              <div className="font-headline-md text-headline-md text-on-surface">{flight.flight_number}</div>
              <div className="font-body-md text-body-md text-on-surface-variant">{flight.carrier}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="font-numeric-data text-numeric-data text-on-surface">{currency} {flight.price.toFixed(2)}</div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Total price</div>
          </div>
        </div>
        <div className="p-stack-md flex flex-col gap-4">
          <div className="flex flex-col md:flex-row gap-stack-md justify-between items-center relative">
            <div className="flex flex-col text-left">
              <div className="font-headline-md text-headline-md text-on-surface">{flight.departure}</div>
              <div className="font-label-md text-label-md text-on-surface-variant">{request?.origin || 'Origin'}</div>
            </div>
            <div className="flex flex-col items-center flex-1 px-4">
              <div className="font-label-sm text-label-sm text-on-surface-variant mb-2">{durationStr} · {stopsLabel}</div>
              <div className="w-full flex items-center">
                <div className="h-[2px] bg-outline-variant flex-1"></div>
                <span className="material-symbols-outlined text-secondary mx-2">flight</span>
                <div className="h-[2px] bg-outline-variant flex-1"></div>
              </div>
            </div>
            <div className="flex flex-col text-right">
              <div className="font-headline-md text-headline-md text-on-surface">{flight.arrival}</div>
              <div className="font-label-md text-label-md text-on-surface-variant">{request?.destination || 'Destination'}</div>
            </div>
          </div>
        </div>
      </section>

      {/* Booking Details Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
            <span className="material-symbols-outlined">calendar_today</span>
          </div>
          <div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Date</div>
            <div className="font-label-md text-label-md text-on-surface">{request?.departure_date || 'N/A'}</div>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
            <span className="material-symbols-outlined">group</span>
          </div>
          <div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Travelers</div>
            <div className="font-label-md text-label-md text-on-surface">{request?.traveler_count || 1} Adult{(request?.traveler_count ?? 1) > 1 ? 's' : ''}</div>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
            <span className="material-symbols-outlined">payments</span>
          </div>
          <div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Budget Limit</div>
            <div className="font-label-md text-label-md text-on-surface">{request?.currency || currency} {(request?.budget_limit ?? 0).toFixed(2)}</div>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
            <span className="material-symbols-outlined">verified</span>
          </div>
          <div>
            <div className="font-label-sm text-label-sm text-on-surface-variant">Recovery Confidence</div>
            <div className="font-label-md text-label-md text-on-surface">{confidence}%</div>
          </div>
        </div>
      </section>

      {/* Price Summary */}
      <section className="bg-surface-container-lowest rounded-xl border border-outline-variant p-stack-md flex flex-col gap-3">
        <h3 className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-1">Price Summary</h3>
        <div className="flex justify-between items-center">
          <span className="font-body-md text-body-md text-on-surface-variant">Base fare</span>
          <span className="font-body-md text-body-md text-on-surface">{currency} {(flight.price * 0.85).toFixed(2)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="font-body-md text-body-md text-on-surface-variant">Taxes &amp; fees</span>
          <span className="font-body-md text-body-md text-on-surface">{currency} {(flight.price * 0.15).toFixed(2)}</span>
        </div>
        <div className="border-t border-outline-variant pt-3 flex justify-between items-center">
          <span className="font-headline-md text-headline-md text-on-surface">Total</span>
          <span className="font-headline-md text-headline-md text-primary">{currency} {flight.price.toFixed(2)}</span>
        </div>
      </section>

      {/* Actions */}
      <section className="flex flex-col gap-3">
        <button
          onClick={() => setBookingConfirmed(true)}
          className="w-full bg-primary-container text-on-primary hover:bg-primary-container/90 font-label-md text-label-md py-4 px-8 rounded-lg flex items-center justify-center gap-2 shadow-[0_4px_12px_rgba(19,27,46,0.15)] transition-all active:scale-95"
        >
          <span className="material-symbols-outlined text-[20px]">check_circle</span>
          Confirm &amp; Book
        </button>
        <button
          onClick={() => navigate(-1)}
          className="w-full bg-transparent text-on-surface-variant hover:text-on-surface font-label-md text-label-md py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">arrow_back</span>
          Back to Plan
        </button>
      </section>
    </main>
  );
}
