import { Alert } from '../types';

interface Props {
  alerts: Alert[];
}

const sevBadge: Record<string, string> = {
  CRITICAL: 'bg-red-900/50 text-red-400 border border-red-700/50',
  WARNING: 'bg-amber-900/50 text-amber-400 border border-amber-700/50',
  INFO: 'bg-green-900/50 text-green-400 border border-green-700/50',
};

const statusBadge: Record<string, string> = {
  acknowledged: 'text-amber-400',
  escalated: 'text-red-400 font-bold',
  resolved: 'text-green-400',
};

export default function AlertHistory({ alerts }: Props) {
  return (
    <div className="bg-guardian-card border border-guardian-border rounded-lg overflow-hidden">
      <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center gap-2">
        <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
          Alert History
        </span>
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-guardian-dim/20 text-guardian-muted border border-guardian-border">
          {alerts.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        {alerts.length === 0 ? (
          <p className="text-guardian-dim italic text-sm px-4 py-5 text-center">
            No resolved or acknowledged alerts yet.
          </p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-guardian-border">
                {['ID', 'Severity', 'Code', 'Reason', 'Packet', 'Confidence', 'Status'].map(
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
                  className="border-b border-guardian-border/50 hover:bg-white/[0.02] transition-colors"
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
                    {a.reason_code}
                  </td>
                  <td className="px-4 py-3 text-guardian-muted max-w-xs truncate">
                    {a.reason_text}
                  </td>
                  <td className="px-4 py-3 font-mono text-guardian-muted">
                    {a.packet_id}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <div className="h-1.5 w-16 bg-guardian-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-guardian-accent rounded-full"
                          style={{ width: `${Math.round(a.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-guardian-muted font-mono">
                        {Math.round(a.confidence * 100)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-[10px] font-semibold uppercase ${statusBadge[a.alert_status] ?? 'text-guardian-muted'}`}
                    >
                      {a.alert_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
