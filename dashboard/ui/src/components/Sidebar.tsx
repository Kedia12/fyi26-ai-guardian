import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import ChangePassword from './ChangePassword';

export type View = 'telemetry' | 'alerts' | 'map' | 'history' | 'reports' | 'users';

interface SidebarProps {
  activeView: View;
  onSelectView: (view: View) => void;
  activeAlertCount: number;
  isAdmin: boolean;
  isOpen: boolean;
  onClose: () => void;
}

type IconName = 'activity' | 'bell' | 'map-pin' | 'history' | 'file' | 'users' | 'lock' | 'log-out' | 'person' | 'x';

function Icon({ name }: { name: IconName }) {
  const common = {
    width: 17,
    height: 17,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };

  switch (name) {
    case 'activity':
      return (
        <svg {...common}>
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      );
    case 'bell':
      return (
        <svg {...common}>
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      );
    case 'map-pin':
      return (
        <svg {...common}>
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      );
    case 'history':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      );
    case 'file':
      return (
        <svg {...common}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      );
    case 'users':
      return (
        <svg {...common}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case 'lock':
      return (
        <svg {...common}>
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case 'log-out':
      return (
        <svg {...common}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      );
    case 'person':
      return (
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      );
    case 'x':
      return (
        <svg {...common}>
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      );
  }
}

const NAV_ITEMS: { view: View; label: string; icon: IconName; adminOnly?: boolean }[] = [
  { view: 'telemetry', label: 'Telemetry', icon: 'activity' },
  { view: 'alerts', label: 'Alerts', icon: 'bell' },
  { view: 'map', label: 'Aircraft Map', icon: 'map-pin' },
  { view: 'history', label: 'Alert History', icon: 'history' },
  { view: 'reports', label: 'Reports', icon: 'file' },
  { view: 'users', label: 'Manage Users', icon: 'users', adminOnly: true },
];

export default function Sidebar({
  activeView,
  onSelectView,
  activeAlertCount,
  isAdmin,
  isOpen,
  onClose,
}: SidebarProps) {
  const { user, logout } = useAuth();
  const [showChangePassword, setShowChangePassword] = useState(false);

  function selectView(view: View) {
    onSelectView(view);
    onClose();
  }

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`w-64 shrink-0 bg-guardian-card border border-guardian-border flex flex-col overflow-hidden
          fixed inset-y-0 left-0 z-50 rounded-r-2xl transition-transform duration-200 ease-in-out
          md:static md:z-auto md:rounded-2xl md:m-4 md:mr-0 md:self-start md:sticky md:top-4 md:max-h-[calc(100vh-2rem)]
          ${isOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}
      >
        <button
          onClick={onClose}
          aria-label="Close menu"
          className="md:hidden absolute top-3 right-3 text-guardian-dim hover:text-guardian-text transition-colors"
        >
          <Icon name="x" />
        </button>

        <div className="flex flex-col items-center pt-8 pb-6 px-4 border-b border-guardian-border">
          <div className="w-16 h-16 rounded-full bg-guardian-header border border-guardian-border flex items-center justify-center mb-3 text-guardian-accent">
            <Icon name="person" />
          </div>
          <span className="text-guardian-text text-sm font-semibold">{user?.username}</span>
          <span className="text-guardian-muted text-[10px] uppercase tracking-wider mt-1 border border-guardian-border rounded px-1.5 py-0.5">
            {user?.role}
          </span>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map((item) => (
            <button
              key={item.view}
              onClick={() => selectView(item.view)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-colors
                ${
                  activeView === item.view
                    ? 'bg-guardian-accent/15 text-guardian-accent'
                    : 'text-guardian-muted hover:bg-guardian-header hover:text-guardian-text'
                }`}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.view === 'alerts' && activeAlertCount > 0 && (
                <span className="ml-auto bg-red-900/60 text-red-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {activeAlertCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-guardian-border space-y-1">
          <button
            onClick={() => setShowChangePassword(true)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium text-guardian-muted hover:bg-guardian-header hover:text-guardian-text transition-colors"
          >
            <Icon name="lock" />
            <span>Change Password</span>
          </button>
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium text-guardian-muted hover:bg-guardian-header hover:text-guardian-text transition-colors"
          >
            <Icon name="log-out" />
            <span>Logout</span>
          </button>
        </div>

        {showChangePassword && (
          <ChangePassword onClose={() => setShowChangePassword(false)} />
        )}
      </aside>
    </>
  );
}
