import { useState, useCallback } from 'react';
import Header from './components/Header';
import TelemetryPanel from './components/TelemetryPanel';
import ActiveAlerts from './components/ActiveAlerts';
import AlertHistory from './components/AlertHistory';
import AircraftMap from './components/AircraftMap';
import ReportPanel from './components/ReportPanel';
import { Alert, Telemetry } from './types';
import { usePolling } from './hooks/usePolling';

export default function App() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const fetchAlerts = useCallback(async () => {
    const r = await fetch('/api/alerts');
    setAlerts(await r.json());
  }, []);

  usePolling(async () => {
    const r = await fetch('/api/telemetry');
    setTelemetry(await r.json());
  }, 3000);

  usePolling(fetchAlerts, 5000);

  const activeAlerts = alerts.filter((a) => a.alert_status === 'active');
  const alertHistory = alerts.filter((a) => a.alert_status !== 'active');

  async function handleConfirm(alertId: number) {
    await fetch(`/api/alerts/${alertId}/confirm`, { method: 'POST' });
    await fetchAlerts();
  }

  async function handleAction(alertId: number, action: string) {
    await fetch(`/api/alerts/${alertId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action_type: action }),
    });
    await fetchAlerts();
  }

  return (
    <div className="min-h-screen bg-guardian-bg text-guardian-text font-sans">
      <Header activeCount={activeAlerts.length} />
      <main className="p-5 grid grid-cols-1 xl:grid-cols-2 gap-5">
        <TelemetryPanel telemetry={telemetry} />
        <div className="xl:col-span-2">
          <ActiveAlerts
            alerts={activeAlerts}
            onConfirm={handleConfirm}
            onAction={handleAction}
          />
        </div>
        <div className="xl:col-span-2">
          <AircraftMap />
        </div>
        <div className="xl:col-span-2">
          <AlertHistory alerts={alertHistory} />
        </div>
        <div className="xl:col-span-2">
          <ReportPanel />
        </div>
      </main>
    </div>
  );
}
