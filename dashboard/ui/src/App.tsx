import { useState, useCallback } from 'react';
import Sidebar, { View } from './components/Sidebar';
import TelemetryPanel from './components/TelemetryPanel';
import ActiveAlerts from './components/ActiveAlerts';
import AlertHistory from './components/AlertHistory';
import AircraftMap from './components/AircraftMap';
import ReportPanel from './components/ReportPanel';
import LandingPage from './components/LandingPage';
import CreateUser from './components/CreateUser';
import { Alert, Telemetry } from './types';
import { usePolling } from './hooks/usePolling';
import { useAuth } from './context/AuthContext';

const VIEW_TITLES: Record<View, string> = {
  telemetry: 'Live Telemetry',
  alerts: 'Active Alerts',
  map: 'Live Aircraft Map',
  history: 'Alert History',
  reports: 'Post-Flight AI Report',
  users: 'Manage Users',
};

export default function App() {
  const { user, loading } = useAuth();
  const [activeView, setActiveView] = useState<View>('telemetry');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const fetchAlerts = useCallback(async () => {
    if (!user) return;
    const r = await fetch('/api/alerts');
    if (r.ok) setAlerts(await r.json());
  }, [user]);

  usePolling(async () => {
    if (!user) return;
    const r = await fetch('/api/telemetry');
    if (r.ok) setTelemetry(await r.json());
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

  if (loading) {
    return (
      <div className="min-h-screen bg-guardian-bg text-guardian-muted flex items-center justify-center text-sm">
        Loading…
      </div>
    );
  }

  if (!user) {
    return <LandingPage />;
  }

  const isAdmin = user.role === 'admin';

  return (
    <div className="min-h-screen bg-guardian-bg text-guardian-text font-sans flex">
      <Sidebar
        activeView={activeView}
        onSelectView={setActiveView}
        activeAlertCount={activeAlerts.length}
        isAdmin={isAdmin}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="flex-1 min-w-0">
        <header className="px-4 sm:px-6 py-5 flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="md:hidden text-guardian-muted hover:text-guardian-text transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span className="text-guardian-accent text-xl">▷</span>
          <h1 className="text-guardian-accent font-semibold text-lg tracking-wide">
            AI Guardian
          </h1>
          <span className="bg-blue-800/60 text-blue-200 text-[10px] px-2.5 py-0.5 rounded-full font-bold tracking-widest uppercase border border-blue-700/50">
            FYI26
          </span>
          <span className="text-guardian-dim text-sm hidden sm:inline">/</span>
          <span className="text-guardian-muted text-sm hidden sm:inline">{VIEW_TITLES[activeView]}</span>
        </header>

        <main className="px-5 pb-5">
          {activeView === 'telemetry' && <TelemetryPanel telemetry={telemetry} />}
          {activeView === 'alerts' && (
            <ActiveAlerts
              alerts={activeAlerts}
              isAdmin={isAdmin}
              onConfirm={handleConfirm}
              onAction={handleAction}
            />
          )}
          {activeView === 'map' && <AircraftMap />}
          {activeView === 'history' && <AlertHistory alerts={alertHistory} />}
          {activeView === 'reports' && <ReportPanel isAdmin={isAdmin} />}
          {activeView === 'users' && isAdmin && <CreateUser />}
        </main>
      </div>
    </div>
  );
}
