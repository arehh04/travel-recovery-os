import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MissionProgress } from './MissionProgress';

describe('MissionProgress', () => {
  it('renders progress bar', () => {
    render(<MissionProgress status="RUNNING" phase="PLANNING" progress={0.25} elapsedMs={5000} />);
    expect(screen.getByTestId('mission-progress')).toBeInTheDocument();
    expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
  });

  it('shows progress percentage', () => {
    render(<MissionProgress status="RUNNING" phase="PLANNING" progress={0.5} elapsedMs={10000} />);
    expect(screen.getByText('50% — 10.0s')).toBeInTheDocument();
  });

  it('marks completed phases with checkmark', () => {
    const { container } = render(
      <MissionProgress status="RUNNING" phase="FLIGHT_SEARCH" progress={0.35} elapsedMs={15000} />
    );
    const items = container.querySelectorAll('.phase-item');
    // CONTEXT and PLANNING should have ✓ (before FLIGHT_SEARCH)
    expect(items[0].querySelector('.phase-icon')?.textContent).toBe('✓');
    expect(items[1].querySelector('.phase-icon')?.textContent).toBe('✓');
    // FLIGHT_SEARCH should have ● (current)
    expect(items[2].querySelector('.phase-icon')?.textContent).toBe('●');
  });

  it('shows cancel button when running', () => {
    render(<MissionProgress status="RUNNING" phase="CONTEXT" progress={0.1} elapsedMs={2000} onCancel={() => {}} />);
    expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
  });

  it('hides cancel button when not running', () => {
    render(<MissionProgress status="COMPLETED" phase="COMPLETED" progress={1} elapsedMs={30000} />);
    expect(screen.queryByTestId('cancel-btn')).not.toBeInTheDocument();
  });
});
