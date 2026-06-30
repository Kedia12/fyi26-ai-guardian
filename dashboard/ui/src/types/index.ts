export interface Telemetry {
  packet_id: number;
  node_id: string;
  timestamp_ms: number;
  battery_voltage_v: number;
  altitude_est_m: number;
  gps_lat_deg: number;
  gps_lon_deg: number;
  gps_speed_mps: number;
  satellite_count: number;
  gps_fix_status: boolean;
  accel_x_g: number;
  accel_y_g: number;
  accel_z_g: number;
  gyro_x_dps: number;
  gyro_y_dps: number;
  gyro_z_dps: number;
  ml_anomaly_score: number | null;
}

export interface Alert {
  id: number;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  reason_code: string;
  reason_text: string;
  packet_id: number;
  confidence: number;
  alert_status: 'active' | 'acknowledged' | 'escalated' | 'resolved';
  confirmed: boolean;
}

export interface AircraftPosition {
  node_id: string;
  gps_lat_deg: number;
  gps_lon_deg: number;
  altitude_est_m: number;
  gps_speed_mps: number;
  battery_voltage_v: number;
  gps_fix_status: boolean;
  satellite_count: number;
}

export interface LiveAircraft {
  icao24: string;
  callsign: string;
  origin_country: string;
  latitude: number;
  longitude: number;
  altitude_m: number | null;
  velocity_mps: number | null;
  heading_deg: number | null;
  vertical_rate: number | null;
}

export interface TrailPoint {
  gps_lat_deg: number;
  gps_lon_deg: number;
}

