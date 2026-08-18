import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FlightCard } from './FlightCard';
import type { FlightInfo } from '../api/types';

const mockFlight: FlightInfo = {
  flight_number: 'MH70',
  carrier: 'Malaysia Airlines',
  departure: '202608200705',
  arrival: '202608201530',
  duration_minutes: 505,
  stops: 0,
  price: 450.50,
  currency: 'USD',
  score: 8.5,
};

describe('FlightCard', () => {
  it('renders flight info', () => {
    render(<FlightCard flight={mockFlight} confidence={0.92} />);
    const card = screen.getByTestId('flight-card');
    expect(card).toBeInTheDocument();
    expect(screen.getByText('MH70')).toBeInTheDocument();
    expect(screen.getByText('Malaysia Airlines')).toBeInTheDocument();
  });

  it('formats departure/arrival datetime', () => {
    render(<FlightCard flight={mockFlight} confidence={0.92} />);
    expect(screen.getByText('20 Aug 07:05')).toBeInTheDocument();
    expect(screen.getByText('20 Aug 15:30')).toBeInTheDocument();
  });

  it('shows "Direct" for zero stops', () => {
    render(<FlightCard flight={mockFlight} confidence={0.92} />);
    expect(screen.getByText('Direct')).toBeInTheDocument();
  });

  it('formats duration', () => {
    render(<FlightCard flight={mockFlight} confidence={0.92} />);
    expect(screen.getByText('8h 25m')).toBeInTheDocument();
  });

  it('shows confidence as percentage', () => {
    render(<FlightCard flight={mockFlight} confidence={0.87} />);
    expect(screen.getByText('87%')).toBeInTheDocument();
  });

  it('formats price with currency', () => {
    render(<FlightCard flight={mockFlight} confidence={0.92} />);
    expect(screen.getByText('USD 450.50')).toBeInTheDocument();
  });
});
