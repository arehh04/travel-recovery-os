import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { missionsApi } from '../api/missions';

export function DevTools() {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ mission_id: string } | null>(null);
  const navigate = useNavigate();

  const handleSimulate = async () => {
    setLoading(true);
    setExpanded(false);
    try {
      const { mission_id } = await missionsApi.simulateWebhook();
      
      // Poll until complete
      const poll = async () => {
        const res = await missionsApi.getStatus(mission_id);
        if (res.status === 'COMPLETED') {
          setLoading(false);
          setToast({ mission_id });
          // Auto-hide toast after 15s
          setTimeout(() => setToast(null), 15000);
        } else if (res.status === 'FAILED') {
          setLoading(false);
          alert('Webhook simulation failed');
        } else {
          setTimeout(poll, 1000);
        }
      };
      poll();
    } catch (e) {
      setLoading(false);
      console.error(e);
      alert('Error triggering webhook');
    }
  };

  return (
    <>
      {/* Toast Notification (Mock WhatsApp/SMS) */}
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[100] w-full max-w-md px-4 animate-in fade-in slide-in-from-top-8 duration-500">
          <div 
            onClick={() => {
              setToast(null);
              navigate(`/recovery/plan?mission_id=${toast.mission_id}`);
            }}
            className="bg-surface/90 backdrop-blur-xl border border-outline-variant shadow-2xl rounded-2xl p-4 flex gap-4 cursor-pointer hover:bg-surface transition-colors"
          >
            <div className="w-12 h-12 bg-[#25D366] rounded-xl flex items-center justify-center shrink-0 shadow-sm">
              <span className="material-symbols-outlined text-white" style={{ fontVariationSettings: "'FILL' 1" }}>chat</span>
            </div>
            <div className="flex flex-col justify-center flex-1">
              <div className="flex justify-between items-center mb-1">
                <span className="font-label-sm font-bold text-on-surface">Navires Alerts</span>
                <span className="text-xs text-on-surface-variant">now</span>
              </div>
              <p className="text-sm text-on-surface leading-tight">
                ⚠️ Flight MH712 Cancelled. AI has secured a recovery flight for you. Tap to view and book.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Dev Tools FAB */}
      <div className="fixed bottom-[100px] md:bottom-6 right-6 z-[90] flex flex-col items-end gap-2">
        {expanded && (
          <div className="bg-surface border border-outline-variant rounded-xl shadow-lg p-2 flex flex-col gap-1 w-48 mb-2 animate-in slide-in-from-bottom-2 fade-in">
            <div className="px-3 py-1 font-label-sm text-on-surface-variant text-xs uppercase tracking-wider">Demo Tools</div>
            <button
              onClick={handleSimulate}
              disabled={loading}
              className="text-left px-3 py-2 text-sm font-label-md rounded hover:bg-surface-container transition-colors disabled:opacity-50 text-secondary"
            >
              {loading ? 'Simulating...' : 'Simulate Webhook'}
            </button>
          </div>
        )}
        <button
          onClick={() => setExpanded(!expanded)}
          className={`w-12 h-12 rounded-full shadow-lg flex items-center justify-center hover:scale-105 active:scale-95 transition-all ${loading ? 'bg-error text-on-error animate-pulse' : 'bg-surface-container-highest text-on-surface'}`}
        >
          <span className={`material-symbols-outlined ${loading ? 'animate-spin' : ''}`}>
            {loading ? 'sync' : 'code'}
          </span>
        </button>
      </div>
    </>
  );
}
