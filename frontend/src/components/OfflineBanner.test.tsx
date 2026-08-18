import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { OfflineBanner } from './OfflineBanner';

describe('OfflineBanner', () => {
  it('shows banner when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
    render(<OfflineBanner />);
    expect(screen.getByTestId('offline-banner')).toBeInTheDocument();
    expect(screen.getByText(/offline/i)).toBeInTheDocument();
  });

  it('hides banner when online', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
    render(<OfflineBanner />);
    expect(screen.queryByTestId('offline-banner')).not.toBeInTheDocument();
  });
});
