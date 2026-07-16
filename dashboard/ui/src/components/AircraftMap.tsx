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
import { AircraftPosition, TrailPoint } from '../types';
import { usePolling } from '../hooks/usePolling';

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

// ── Map auto-center on first monitored aircraft, then re-center whenever it
// drifts outside the currently visible bounds (without fighting manual
// pan/zoom while the aircraft is still on screen) ──────────────────────────
function MapAutoCenter({ positions }: { positions: AircraftPosition[] }) {
  const map = useMap();
  const hasCenteredOnce = useRef(false);

  useEffect(() => {
    if (positions.length === 0) return;
    const pos = positions[0];
    const lat = parseFloat(String(pos.gps_lat_deg));
    const lon = parseFloat(String(pos.gps_lon_deg));
    if (isNaN(lat) || isNaN(lon)) return;

    const latlng = L.latLng(lat, lon);

    if (!hasCenteredOnce.current) {
      map.setView(latlng, 14);
      hasCenteredOnce.current = true;
      return;
    }

    if (!map.getBounds().contains(latlng)) {
      map.panTo(latlng);
    }
  }, [positions, map]);

  return null;
}

// ── Types ─────────────────────────────────────────────────────────────────────
type Trails = Record<string, [number, number][]>;

// ── Main component ────────────────────────────────────────────────────────────
export default function AircraftMap() {
  const [positions, setPositions] = useState<AircraftPosition[]>([]);
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
  }, 500);

  const statusText = useMemo(() => {
    if (positions.length > 0) {
      return `Monitored: ${positions.length} · ${statusTime}`;
    }
    return 'Fetching telemetry…';
  }, [positions.length, statusTime]);

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
          className="h-[480px] sm:h-[600px] lg:h-[720px] w-full"
          zoomControl
        >
          <MapAutoCenter positions={positions} />

          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
            maxZoom={19}
          />

          {/* Monitored aircraft — blue, rotated by heading */}
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
        </MapContainer>
      </div>
    </div>
  );
}
