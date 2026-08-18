import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MissionForm } from './MissionForm';

describe('MissionForm', () => {
  it('renders with default values', () => {
    render(<MissionForm onSubmit={() => {}} />);
    expect(screen.getByTestId('mission-form')).toBeInTheDocument();
    expect(screen.getByTestId('origin-input')).toHaveValue('KUL');
    expect(screen.getByTestId('destination-input')).toHaveValue('NRT');
  });

  it('calls onSubmit with form data', () => {
    const onSubmit = vi.fn();
    render(<MissionForm onSubmit={onSubmit} />);
    fireEvent.click(screen.getByTestId('submit-btn'));
    expect(onSubmit).toHaveBeenCalledWith({
      origin: 'KUL',
      destination: 'NRT',
      departure_date: '2026-08-20',
      traveler_count: 1,
      currency: 'USD',
      traveler_type: 'Business',
      disruption_type: 'FlightCancelled',
      budget_limit: 1000,
    });
  });

  it('uppercases origin and destination', () => {
    const onSubmit = vi.fn();
    render(<MissionForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId('origin-input'), { target: { value: 'sin' } });
    fireEvent.change(screen.getByTestId('destination-input'), { target: { value: 'nrt' } });
    fireEvent.click(screen.getByTestId('submit-btn'));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      origin: 'SIN',
      destination: 'NRT',
    }));
  });

  it('disables form when disabled prop is true', () => {
    render(<MissionForm onSubmit={() => {}} disabled />);
    expect(screen.getByTestId('submit-btn')).toBeDisabled();
    expect(screen.getByTestId('origin-input')).toBeDisabled();
  });

  it('shows "Submitting..." text when disabled', () => {
    render(<MissionForm onSubmit={() => {}} disabled />);
    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Submitting...');
  });
});
