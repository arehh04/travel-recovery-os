/** Root application component. */

import { useMission } from './hooks/useMission';
import { MissionForm } from './components/MissionForm';
import { MissionProgress } from './components/MissionProgress';
import { MissionResultView } from './components/MissionResult';
import { ErrorDisplay } from './components/ErrorDisplay';
import { OfflineBanner } from './components/OfflineBanner';
import './styles/app.css';

export function App() {
  const { state, createMission, cancelMission, reset } = useMission();

  return (
    <div className="app">
      <header className="app-header">
        <h1>TR-OS</h1>
        <span className="subtitle">Travel Recovery Operating System</span>
      </header>

      <OfflineBanner />

      <main className="app-main">
        {state.phase === 'idle' && (
          <MissionForm onSubmit={createMission} />
        )}

        {state.phase === 'submitting' && (
          <div className="loading-state" data-testid="loading">
            <div className="spinner" />
            <p>Submitting mission...</p>
          </div>
        )}

        {state.phase === 'running' && (
          <MissionProgress
            status={state.status.status}
            phase={state.status.phase}
            progress={state.status.progress}
            elapsedMs={state.status.elapsed_ms}
            onCancel={cancelMission}
          />
        )}

        {state.phase === 'completed' && (
          <MissionResultView result={state.result} onNewMission={reset} />
        )}

        {state.phase === 'error' && (
          <ErrorDisplay message={state.message} onRetry={reset} />
        )}
      </main>

      <footer className="app-footer">
        <span>Phase 8 — API + PWA</span>
      </footer>
    </div>
  );
}
