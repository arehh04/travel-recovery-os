/** Navires — Multi-page app with react-router. */

import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { StartRecoveryPage } from './pages/StartRecoveryPage';
import { LiveRecoveryPage } from './pages/LiveRecoveryPage';
import { RecoveryPlanPage } from './pages/RecoveryPlanPage';
import { RecoveryEnginePage } from './pages/RecoveryEnginePage';
import { EvidenceValidationPage } from './pages/EvidenceValidationPage';
import { AlternativesPage } from './pages/AlternativesPage';
import { HistoryPage } from './pages/HistoryPage';
import { ProfilePage } from './pages/ProfilePage';
import { BookingConfirmationPage } from './pages/BookingConfirmationPage';
import './styles/app.css';

// TR-OS PWA Phase 10

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<StartRecoveryPage />} />
        <Route path="/recovery/live" element={<LiveRecoveryPage />} />
        <Route path="/recovery/plan" element={<RecoveryPlanPage />} />
        <Route path="/recovery/engine" element={<RecoveryEnginePage />} />
        <Route path="/recovery/evidence" element={<EvidenceValidationPage />} />
        <Route path="/recovery/alternatives" element={<AlternativesPage />} />
        <Route path="/recovery/booking" element={<BookingConfirmationPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<StartRecoveryPage />} />
      </Route>
    </Routes>
  );
}
