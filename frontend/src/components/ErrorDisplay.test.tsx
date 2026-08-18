import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ErrorDisplay } from './ErrorDisplay';

describe('ErrorDisplay', () => {
  it('renders error message', () => {
    render(<ErrorDisplay message="Network error" />);
    expect(screen.getByTestId('error-display')).toBeInTheDocument();
    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('shows retry button when onRetry is provided', () => {
    render(<ErrorDisplay message="Error" onRetry={() => {}} />);
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('hides retry button when onRetry is not provided', () => {
    render(<ErrorDisplay message="Error" />);
    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
  });
});
