/** Offline banner — shown when network is unavailable. */

import { useState, useEffect } from 'react';

export function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);

  useEffect(() => {
    const handleOffline = () => setOffline(true);
    const handleOnline = () => setOffline(false);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('online', handleOnline);
    return () => {
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('online', handleOnline);
    };
  }, []);

  if (!offline) return null;

  return (
    <div className="offline-banner" data-testid="offline-banner">
      You are offline. Mission execution requires a network connection.
    </div>
  );
}
