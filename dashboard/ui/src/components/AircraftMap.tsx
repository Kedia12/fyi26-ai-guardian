import { useState, useEffect, useRef, useMemo } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import { AircraftPosition, LiveAircraft, TrailPoint } from '../types';
import { usePolling } from '../hooks/usePolling';

// ── Altitude colour scale (matches ADS-B Exchange rainbow) ────────────────────
function getAltitudeColor(altM: number | null): string {
  if (altM === null) return '#718096';
  const a = Math.max(0, altM);
  if (a < 500)    return '#00e5ff';
  if (a < 1500)   return '#00e676';
  if (a < 4000)   return '#c6ff00';
  if (a < 7000)   return '#ffff00';
  if (a < 10000)  return '#ff9100';
  if (a < 13000)  return '#ff1744';
  return '#d500f9';
}

// ── SVG airplane icon (Material Design "flight" path, nose points north) ──────
const _iconCache = new Map<string, L.DivIcon>();

function getAircraftIcon(heading: number | null, color: string, size = 18): L.DivIcon {
  const rot = Math.round((heading ?? 0) / 5) * 5;
  const key = `${rot}_${color}_${size}`;
  if (!_iconCache.has(key)) {
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" ` +
      `width="${size}" height="${size}" ` +
      `style="transform:rotate(${rot}deg);display:block;filter:drop-shadow(0 0 1.5px rgba(0,0,0,0.9))">` +
      `<path fill="${color}" d="M21,16V14L13,9V3.5A1.5,1.5 0 0,0 11.5,2A1.5,1.5 0 0,0 10,3.5V9L2,14V16L10,13.5V19L8,20.5V22L11.5,21L15,22V20.5L13,19V13.5L21,16Z"/>` +
      `</svg>`;
    _iconCache.set(
      key,
      L.divIcon({
        html: svg,
        className: '',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
        popupAnchor: [0, -size / 2 - 2],
      }),
    );
  }
  return _iconCache.get(key)!;
}

// ── Altitude legend ───────────────────────────────────────────────────────────
const LEGEND_BANDS = [
  { label: '0 m',       color: '#00e5ff' },
  { label: '500 m',     color: '#00e676' },
  { label: '1 500 m',   color: '#c6ff00' },
  { label: '4 000 m',   color: '#ffff00' },
  { label: '7 000 m',   color: '#ff9100' },
  { label: '10 000 m',  color: '#ff1744' },
  { label: '13 000+ m', color: '#d500f9' },
];

function AltitudeLegend() {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 28,
        right: 10,
        zIndex: 1000,
        background: 'rgba(26,29,46,0.90)',
        border: '1px solid #2d3748',
        borderRadius: 6,
        padding: '8px 10px',
        fontSize: 10,
        backdropFilter: 'blur(4px)',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          fontWeight: 700,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: 6,
          color: '#90cdf4',
          fontSize: 9,
        }}
      >
        Altitude
      </div>
      {LEGEND_BANDS.map((b) => (
        <div
          key={b.label}
          style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}
        >
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: 2,
              background: b.color,
              flexShrink: 0,
              boxShadow: `0 0 4px ${b.color}80`,
            }}
          />
          <span style={{ color: '#a0aec0', fontFamily: 'monospace' }}>{b.label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Map auto-center on first monitored aircraft ───────────────────────────────
function MapAutoCenter({ positions }: { positions: AircraftPosition[] }) {
  const map = useMap();
  const centered = useRef(false);

  useEffect(() => {
    if (!centered.current && positions.length > 0) {
      const pos = positions[0];
      const lat = parseFloat(String(pos.gps_lat_deg));
      const lon = parseFloat(String(pos.gps_lon_deg));
      if (!isNaN(lat) && !isNaN(lon)) {
        map.setView([lat, lon], 14);
        centered.current = true;
      }
    }
  }, [positions, map]);

  return null;
}

// ── Types ─────────────────────────────────────────────────────────────────────
type Trails = Record<string, [number, number][]>;

// ── Main component ────────────────────────────────────────────────────────────
export default function AircraftMap() {
  const [positions, setPositions] = useState<AircraftPosition[]>([]);
  const [liveAircraft, setLiveAircraft] = useState<LiveAircraft[]>([]);
  const [trails, setTrails] = useState<Trails>({});
  const [statusTime, setStatusTime] = useState('');
  usePolling(async () => {
    const r = await fetch('/api/aircraft-positions');
    const data: AircraftPosition[] = await r.json();
    setPositions(data);
    setStatusTime(new Date().toLocaleTimeString());

    const trailFetches = data
      .filter((pos) => pos.gps_lat_deg && pos.gps_lon_deg)
      .map(async (pos): Promise<[string, [number, number][]] | null> => {
        try {
          const tr = await fetch(
            `/api/flight-trail?node_id=${encodeURIComponent(pos.node_id)}&limit=100`,
          );
          const trail: TrailPoint[] = await tr.json();
          const pts = trail
            .filter((p) => p.gps_lat_deg && p.gps_lon_deg)
            .map((p): [number, number] => [
              parseFloat(String(p.gps_lat_deg)),
              parseFloat(String(p.gps_lon_deg)),
            ]);
          return [pos.node_id, pts];
        } catch {
          return null;
        }
      });

    const results = await Promise.all(trailFetches);
    setTrails((prev) => {
      const next = { ...prev };
      for (const entry of results) {
        if (entry) next[entry[0]] = entry[1];
      }
      return next;
    });
  }, 5000);

  usePolling(async () => {
    const r = await fetch('/api/live-traffic');
    if (!r.ok) return;
    const data = await r.json();
    if (Array.isArray(data)) {
      setLiveAircraft(
        data.filter((ac: LiveAircraft) => ac.latitude != null && ac.longitude != null),
      );
    }
  }, 30000);

  const statusText = useMemo(() => {
    if (positions.length > 0 || liveAircraft.length > 0) {
      return `Monitored: ${positions.length} · Live: ${liveAircraft.length} · ${statusTime}`;
    }
    return 'Fetching live traffic…';
  }, [positions.length, liveAircraft.length, statusTime]);

  return (
    <div className="bg-guardian-card border border-guardian-border rounded-lg overflow-hidden">
      <div className="bg-guardian-header px-4 py-2.5 border-b border-guardian-border flex items-center justify-between">
        <span className="text-[#90cdf4] text-xs font-bold uppercase tracking-widest">
          Live Aircraft Map
        </span>
        <span className="text-guardian-muted text-[10px] font-mono">{statusText}</span>
      </div>

      <div className="relative">
        <MapContainer
          center={[50, 10]}
          zoom={5}
          style={{ height: '420px', width: '100%' }}
          zoomControl
        >
          <MapAutoCenter positions={positions} />

          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            maxZoom={19}
          />

          {/* Monitored aircraft — blue, larger, rotated by heading */}
          {positions.map((pos) => {
            const lat = parseFloat(String(pos.gps_lat_deg));
            const lon = parseFloat(String(pos.gps_lon_deg));
            if (isNaN(lat) || isNaN(lon)) return null;
            const heading =
              pos.heading_deg != null ? parseFloat(String(pos.heading_deg)) : null;
            return (
              <Marker
                key={pos.node_id}
                position={[lat, lon]}
                icon={getAircraftIcon(heading, '#63b3ed', 26)}
              >
                <Popup>
                  <div style={{ fontFamily: 'monospace', fontSize: '12px', minWidth: '170px', lineHeight: '1.7' }}>
                    <b style={{ color: '#63b3ed' }}>{pos.node_id}</b><br />
                    <span style={{ color: '#718096' }}>Alt:</span>{' '}
                    {parseFloat(String(pos.altitude_est_m || 0)).toFixed(1)} m<br />
                    <span style={{ color: '#718096' }}>Speed:</span>{' '}
                    {parseFloat(String(pos.gps_speed_mps || 0)).toFixed(1)} m/s<br />
                    <span style={{ color: '#718096' }}>Heading:</span>{' '}
                    {heading != null ? `${heading.toFixed(0)}°` : 'N/A'}<br />
                    <span style={{ color: '#718096' }}>Battery:</span>{' '}
                    {parseFloat(String(pos.battery_voltage_v || 0)).toFixed(2)} V<br />
                    <span style={{ color: '#718096' }}>GPS Fix:</span>{' '}
                    {pos.gps_fix_status ? '✓ Yes' : '✗ No'}<br />
                    <span style={{ color: '#718096' }}>Satellites:</span>{' '}
                    {pos.satellite_count}
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Flight trails */}
          {Object.entries(trails).map(([nodeId, pts]) =>
            pts.length > 1 ? (
              <Polyline
                key={nodeId}
                positions={pts}
                color="#63b3ed"
                weight={2}
                opacity={0.55}
                dashArray="5 5"
              />
            ) : null,
          )}

          {/* Live traffic — altitude-coloured SVG icons rotated by heading */}
          {liveAircraft.map((ac) => (
            <Marker
              key={ac.icao24}
              position={[ac.latitude, ac.longitude]}
              icon={getAircraftIcon(ac.heading_deg, getAltitudeColor(ac.altitude_m), 18)}
            >
              <Popup>
                <div style={{ fontFamily: 'monospace', fontSize: '12px', minWidth: '160px', lineHeight: '1.7' }}>
                  <b style={{ color: getAltitudeColor(ac.altitude_m) }}>{ac.callsign}</b>{' '}
                  <span style={{ color: '#4a5568', fontSize: '10px' }}>{ac.icao24}</span><br />
                  <span style={{ color: '#718096' }}>Alt:</span>{' '}
                  {ac.altitude_m != null
                    ? `${parseFloat(String(ac.altitude_m)).toFixed(0)} m`
                    : 'N/A'}<br />
                  <span style={{ color: '#718096' }}>Speed:</span>{' '}
                  {ac.velocity_mps != null
                    ? `${(parseFloat(String(ac.velocity_mps)) * 1.944).toFixed(0)} kt`
                    : 'N/A'}<br />
                  <span style={{ color: '#718096' }}>Heading:</span>{' '}
                  {ac.heading_deg != null
                    ? `${parseFloat(String(ac.heading_deg)).toFixed(0)}°`
                    : 'N/A'}
                </div>
              </Popup>
            </Marker>
          ))}

        </MapContainer>

        <AltitudeLegend />
      </div>
    </div>
  );
}
