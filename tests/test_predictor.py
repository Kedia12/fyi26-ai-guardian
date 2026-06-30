from unittest.mock import patch

import pytest

from guardian.predictor import (
    TelemetryBuffer,
    predict_battery_depletion,
    predict_imu_drift,
)

_CFG_ON = {
    "prediction": {
        "enabled": True,
        "window_size": 5,
        "battery_slope_threshold": -0.0002,
        "imu_drift_threshold": 0.05,
    }
}
_CFG_OFF = {
    "prediction": {
        "enabled": False,
        "window_size": 5,
        "battery_slope_threshold": -0.0002,
        "imu_drift_threshold": 0.05,
    }
}


def _make_row(ts, voltage=11.5, gx=0.5, gy=1.2, gz=0.3):
    return {
        "timestamp_ms": ts,
        "packet_id": ts // 100,
        "node_id": "aircraft_1",
        "battery_voltage_v": voltage,
        "gyro_x_dps": gx,
        "gyro_y_dps": gy,
        "gyro_z_dps": gz,
        "accel_x_g": 0.02,
        "accel_y_g": -0.01,
        "accel_z_g": 1.00,
    }


def _fill_buffer(buf, rows):
    for row in rows:
        buf.push(row)


# ---------------------------------------------------------------------------
# TelemetryBuffer
# ---------------------------------------------------------------------------

def test_buffer_not_ready_when_underfilled():
    buf = TelemetryBuffer(window_size=5)
    for i in range(4):
        buf.push(_make_row(1000 + i * 100))
    assert not buf.is_ready()


def test_buffer_ready_when_full():
    buf = TelemetryBuffer(window_size=5)
    for i in range(5):
        buf.push(_make_row(1000 + i * 100))
    assert buf.is_ready()


def test_buffer_respects_maxlen():
    buf = TelemetryBuffer(window_size=3)
    for i in range(10):
        buf.push(_make_row(1000 + i * 100))
    assert len(buf) == 3


def test_buffer_to_dataframe_shape():
    buf = TelemetryBuffer(window_size=5)
    for i in range(5):
        buf.push(_make_row(1000 + i * 100))
    df = buf.to_dataframe()
    assert len(df) == 5
    assert "battery_voltage_v" in df.columns


# ---------------------------------------------------------------------------
# predict_battery_depletion
# ---------------------------------------------------------------------------

def test_battery_flat_voltage_no_alert():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, voltage=11.5) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_battery_depletion(buf, row)
    assert alerts == []


def test_battery_drain_triggers_alert():
    buf = TelemetryBuffer(window_size=5)
    # Drop 0.1 V per step → slope = -0.1/100ms = -0.001 V/ms (> threshold -0.0002)
    rows = [_make_row(1000 + i * 100, voltage=11.5 - i * 0.1) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_battery_depletion(buf, row)
    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "PREDICTED_LOW_BATTERY"
    assert alerts[0]["severity"] == "WARNING"


def test_battery_predictor_disabled_no_alert():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, voltage=11.5 - i * 0.1) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_OFF):
        alerts = predict_battery_depletion(buf, row)
    assert alerts == []


def test_battery_no_alert_when_buffer_not_ready():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, voltage=11.5 - i * 0.1) for i in range(3)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_battery_depletion(buf, row)
    assert alerts == []


# ---------------------------------------------------------------------------
# predict_imu_drift
# ---------------------------------------------------------------------------

def test_imu_stable_no_alert():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, gx=0.5, gy=1.2, gz=0.3) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_imu_drift(buf, row)
    assert alerts == []


def test_imu_drift_triggers_alert():
    buf = TelemetryBuffer(window_size=5)
    # Gyro magnitude grows steeply: each step adds 10 dps/axis → slope >> 0.05
    rows = [_make_row(1000 + i * 100, gx=0.5 + i * 10, gy=0.5, gz=0.3) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_imu_drift(buf, row)
    assert len(alerts) == 1
    assert alerts[0]["reason_code"] == "PREDICTED_IMU_DRIFT"
    assert alerts[0]["severity"] == "WARNING"


def test_imu_predictor_disabled_no_alert():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, gx=0.5 + i * 10, gy=0.5, gz=0.3) for i in range(5)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_OFF):
        alerts = predict_imu_drift(buf, row)
    assert alerts == []


def test_imu_no_alert_when_buffer_not_ready():
    buf = TelemetryBuffer(window_size=5)
    rows = [_make_row(1000 + i * 100, gx=0.5 + i * 10, gy=0.5, gz=0.3) for i in range(3)]
    _fill_buffer(buf, rows)
    row = rows[-1]
    with patch("guardian.predictor.get_config", return_value=_CFG_ON):
        alerts = predict_imu_drift(buf, row)
    assert alerts == []
