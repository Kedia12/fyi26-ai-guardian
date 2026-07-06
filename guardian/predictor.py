"""
Predictive anomaly detection for the Guardian.

Maintains a rolling window (TelemetryBuffer) of recent telemetry rows and
runs lightweight linear-regression forecasters to warn operators *before*
an anomaly becomes a confirmed fault.

Two predictors are provided:
  - predict_battery_depletion: warns when the voltage drain rate suggests
    the battery will reach a critical level soon.
  - predict_imu_drift: warns when gyroscope magnitude is trending upward,
    indicating a possible sensor drift before a full dropout.

Both predictors are no-ops until the buffer holds at least window_size rows
and the prediction feature is enabled in guardian_config.yaml.
"""

from collections import deque

import numpy as np
import pandas as pd

from guardian.alerts import build_alert
from guardian.config import get_config


class TelemetryBuffer:
    """Rolling window of the last `window_size` telemetry row dicts."""

    def __init__(self, window_size: int):
        self.window_size = window_size
        self._rows: deque[dict] = deque(maxlen=window_size)

    def push(self, row: dict) -> None:
        self._rows.append(row)

    def is_ready(self) -> bool:
        return len(self._rows) >= self.window_size

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(list(self._rows))

    def __len__(self) -> int:
        return len(self._rows)


def _prediction_cfg() -> dict:
    return get_config().get("prediction", {})


def predict_battery_depletion(buffer: TelemetryBuffer, row: dict) -> list[dict]:
    """Return a PREDICTED_LOW_BATTERY alert if the drain rate is alarming.

    Uses linear regression on the voltage time series in the buffer.
    Fires only when the fitted slope is more negative than
    `battery_slope_threshold` (V/ms).
    """
    cfg = _prediction_cfg()
    if not cfg.get("enabled", False):
        return []
    if not buffer.is_ready():
        return []

    threshold = cfg.get("battery_slope_threshold", -0.0002)

    df = buffer.to_dataframe()
    try:
        t = pd.to_numeric(df["timestamp_ms"], errors="coerce").values
        v = pd.to_numeric(df["battery_voltage_v"], errors="coerce").values
    except KeyError:
        return []

    mask = ~(np.isnan(t) | np.isnan(v))
    t, v = t[mask], v[mask]
    if len(t) < 2 or np.ptp(t) == 0:
        return []

    t_norm = t - t[0]
    slope = float(np.polyfit(t_norm, v, 1)[0])  # V/ms

    if slope < threshold:
        current_v = float(v[-1])
        critical_v = 10.2
        if current_v > critical_v:
            secs = round((current_v - critical_v) / abs(slope) / 1000, 1)
            time_info = f" Estimated {secs}s until critical threshold ({critical_v}V)."
        else:
            time_info = ""

        return [build_alert(
            row=row,
            severity="WARNING",
            confidence=0.80,
            reason_code="PREDICTED_LOW_BATTERY",
            reason_text=(
                f"Battery draining at {slope * 1000:.4f} V/s "
                f"(current: {current_v:.2f}V).{time_info}"
            ),
            recommended_action="MONITOR_BATTERY_AND_PREPARE_LANDING",
        )]

    return []


def predict_imu_drift(buffer: TelemetryBuffer, row: dict) -> list[dict]:
    """Return a PREDICTED_IMU_DRIFT alert if gyro magnitude is trending upward.

    Uses linear regression on the total gyroscope magnitude over the buffer
    window. Fires when the fitted slope exceeds `imu_drift_threshold` (dps/ms).
    """
    cfg = _prediction_cfg()
    if not cfg.get("enabled", False):
        return []
    if not buffer.is_ready():
        return []

    threshold = cfg.get("imu_drift_threshold", 0.05)

    df = buffer.to_dataframe()
    try:
        t = pd.to_numeric(df["timestamp_ms"], errors="coerce").values
        gx = pd.to_numeric(df["gyro_x_dps"], errors="coerce").fillna(0).values
        gy = pd.to_numeric(df["gyro_y_dps"], errors="coerce").fillna(0).values
        gz = pd.to_numeric(df["gyro_z_dps"], errors="coerce").fillna(0).values
    except KeyError:
        return []

    t_mask = ~np.isnan(t)
    t = t[t_mask]
    gx, gy, gz = gx[t_mask], gy[t_mask], gz[t_mask]
    if len(t) < 2 or np.ptp(t) == 0:
        return []

    mag = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
    t_norm = t - t[0]
    slope = float(np.polyfit(t_norm, mag, 1)[0])  # dps/ms

    if slope > threshold:
        current_mag = float(mag[-1])
        return [build_alert(
            row=row,
            severity="WARNING",
            confidence=0.75,
            reason_code="PREDICTED_IMU_DRIFT",
            reason_text=(
                f"Gyroscope magnitude growing at {slope * 1000:.4f} dps/s "
                f"(current magnitude: {current_mag:.2f} dps). "
                f"Sensor drift may precede IMU failure."
            ),
            recommended_action="INSPECT_IMU_SENSOR",
        )]

    return []
