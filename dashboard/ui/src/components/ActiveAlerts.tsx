import { useState } from 'react';
import { Alert } from '../types';

interface Props {
  alerts: Alert[];
  isAdmin: boolean;
  isConnected: boolean;
  onConfirm: (id: number) => Promise<void>;
  onAction: (id: number, action: string) => Promise<void>;
}

const sevBadge: Record<string, string> = {
  CRITICAL:
    'bg-red-900/50 text-red-400 border border-red-700/50',
  WARNING:
    'bg-amber-900/50 text-amber-400 border border-amber-700/50',
  INFO: 'bg-green-900/50 text-green-400 border border-green-700/50',
};

function isPredicted(reasonCode: string): boolean {
  return reasonCode?.startsWith('PREDICTED_') ?? false;
}

export default function ActiveAlerts({ alerts, isAdmin, isConnected, onConfirm, onAction }: Props) {
  const [busy, setBusy] = useState<number | null>(null);

  async function doConfirm(id: number) {
    setBusy(id);
    await onConfirm(id);
    setBusy(null);
  }

  async function doAction(id: number, action: string) {
    setBusy(id);
    await onAction(id, action);
    setBusy(null);
  }

  return (
    <div className="bg-guardian-card border border-guardian-border rounded-lg overflow-hidden">
      <div className="w-full bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
            Active Alerts
          </span>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              alerts.length > 0
                ? 'bg-red-900/60 text-red-400 border border-red-700/50'
                : 'bg-guardian-dim/20 text-guardian-muted border border-guardian-border'
            }`}
          >
            {alerts.length}
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
          {!isConnected ? (
            <p className="text-guardian-dim italic text-sm px-4 py-5 text-center">
              Not connected to Mission Planner. Alerts will appear here once a live telemetry link is active.
            </p>
          ) : alerts.length === 0 ? (
            <p className="text-guardian-dim italic text-sm px-4 py-5 text-center">
              No active alerts.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-guardian-border">
                  {(isAdmin
                    ? ['ID', 'Severity', 'Code', 'Packet', 'Confirmation', 'Actions']
                    : ['ID', 'Severity', 'Code', 'Packet']
                  ).map(
                    (h) => (
                      <th
                        key={h}
                        className="text-left text-guardian-muted font-semibold uppercase tracking-wider text-[10px] px-4 py-2.5"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr
                    key={a.id}
                    className={`border-b border-guardian-border/50 transition-colors ${
                      isPredicted(a.reason_code)
                        ? 'bg-purple-900/10 hover:bg-purple-900/20'
                        : 'hover:bg-white/[0.02]'
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-guardian-muted">
                      #{a.id}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${sevBadge[a.severity] ?? ''}`}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-guardian-text">
                      <div className="flex items-center gap-1.5">
                        {a.reason_code}
                        {isPredicted(a.reason_code) && (
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-700/50 uppercase tracking-wide">
                            Predicted
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-guardian-muted">
                      {a.packet_id}
                    </td>
                    {isAdmin && (
                      <>
                        <td className="px-4 py-3">
                          <button
                            disabled={busy === a.id}
                            onClick={() => doConfirm(a.id)}
                            className={`text-[10px] font-semibold px-2.5 py-1 rounded border transition-colors disabled:opacity-50 ${
                              a.confirmed
                                ? 'border-green-700/50 text-green-400 bg-green-900/30 hover:bg-green-900/50'
                                : 'border-guardian-border text-guardian-muted hover:border-guardian-muted'
                            }`}
                          >
                            {a.confirmed ? '✓ Confirmed' : 'Unconfirmed'}
                          </button>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex gap-1.5">
                            {[
                              { key: 'acknowledge', label: 'ACK', cls: 'border-amber-700/50 text-amber-400 hover:bg-amber-900/30' },
                              { key: 'escalate', label: 'ESC', cls: 'border-red-700/50 text-red-400 hover:bg-red-900/30' },
                              { key: 'resolve', label: 'RES', cls: 'border-green-700/50 text-green-400 hover:bg-green-900/30' },
                            ].map(({ key, label, cls }) => (
                              <button
                                key={key}
                                disabled={busy === a.id}
                                onClick={() => doAction(a.id, key)}
                                className={`text-[10px] font-bold px-2 py-1 rounded border transition-colors disabled:opacity-50 ${cls}`}
                              >
                                {label}
                              </button>
                            ))}
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
    </div>
  );
}
