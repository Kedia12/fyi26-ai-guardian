import { Telemetry } from '../types';

interface Props {
  telemetry: Telemetry | null;
  connected: boolean;
}

function MetricCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: 'ok' | 'warn' | 'error';
}) {
  const highlightClass =
    highlight === 'ok'
      ? 'border-l-2 border-green-500/60'
      : highlight === 'warn'
        ? 'border-l-2 border-amber-500/60'
        : highlight === 'error'
          ? 'border-l-2 border-red-500/60'
          : '';

  return (
    <div className={`bg-guardian-header rounded-lg px-4 py-3 ${highlightClass}`}>
      <div className="text-guardian-muted text-[10px] uppercase tracking-widest mb-1 font-semibold">
        {label}
      </div>
      <div className="text-guardian-text font-mono font-semibold text-sm leading-tight">
        {value}
      </div>
      {sub && (
        <div className="text-guardian-dim text-[10px] mt-0.5 font-mono">{sub}</div>
      )}
    </div>
  );
}

export default function TelemetryPanel({ telemetry: d, connected }: Props) {
  return (
    <div className="bg-guardian-card border border-guardian-border rounded-lg overflow-hidden">
      <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between">
        <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
          Live Telemetry
        </span>
        {d && (
          <span className="text-guardian-dim text-[10px] font-mono">
            PKT #{d.packet_id} · {d.node_id}
          </span>
        )}
      </div>

      {!d ? (
        <div className="px-4 py-8 text-center text-guardian-dim text-sm italic">
          No telemetry received yet.
        </div>
      ) : (
        <div className="p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
          <MetricCard
            label="Battery"
            value={`${parseFloat(String(d.battery_voltage_v)).toFixed(2)} V`}
            highlight={
              parseFloat(String(d.battery_voltage_v)) < 10.5
                ? 'error'
                : parseFloat(String(d.battery_voltage_v)) < 11.0
                  ? 'warn'
                  : 'ok'
            }
          />
          <MetricCard
            label="Altitude"
            value={`${parseFloat(String(d.altitude_est_m)).toFixed(1)} m`}
          />
          <MetricCard
            label="GPS Speed"
            value={`${parseFloat(String(d.gps_speed_mps)).toFixed(1)} m/s`}
          />
          <MetricCard
            label="GPS"
            value={`${parseFloat(String(d.gps_lat_deg)).toFixed(5)}°`}
            sub={`${parseFloat(String(d.gps_lon_deg)).toFixed(5)}°`}
          />
          <MetricCard
            label="GPS Fix"
            value={d.gps_fix_status ? '✓ Acquired' : '✗ No Fix'}
            sub={`${d.satellite_count} satellites`}
            highlight={d.gps_fix_status ? 'ok' : 'error'}
          />
          <MetricCard
            label="Timestamp"
            value={`${d.timestamp_ms} ms`}
          />
          <MetricCard
            label="Armed"
            value={
              !connected
                ? '○ DISARMED'
                : d.armed == null
                  ? 'Unknown'
                  : d.armed
                    ? '● ARMED'
                    : '○ DISARMED'
            }
            sub={!connected ? 'no live link' : undefined}
            highlight={
              !connected ? 'ok' : d.armed == null ? undefined : d.armed ? 'warn' : 'ok'
            }
          />
          <MetricCard
            label="Accel (x/y/z)"
            value={`${parseFloat(String(d.accel_x_g)).toFixed(3)} g`}
            sub={`${parseFloat(String(d.accel_y_g)).toFixed(3)} / ${parseFloat(String(d.accel_z_g)).toFixed(3)} g`}
          />
          <MetricCard
            label="Gyro (x/y/z)"
            value={`${parseFloat(String(d.gyro_x_dps)).toFixed(2)} dps`}
            sub={`${parseFloat(String(d.gyro_y_dps)).toFixed(2)} / ${parseFloat(String(d.gyro_z_dps)).toFixed(2)} dps`}
          />
          <MetricCard
            label="ML Score"
            value={
              d.ml_anomaly_score != null
                ? parseFloat(String(d.ml_anomaly_score)).toFixed(4)
                : 'N/A'
            }
            highlight={
              d.ml_anomaly_score != null && d.ml_anomaly_score > 0.8
                ? 'error'
                : d.ml_anomaly_score != null && d.ml_anomaly_score > 0.5
                  ? 'warn'
                  : 'ok'
            }
          />
        </div>
      )}
    </div>
  );
}
