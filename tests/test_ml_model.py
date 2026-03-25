from pathlib import Path

import pandas as pd

from guardian.ml_model import GuardianML


def make_training_df():
    return pd.DataFrame([
        {
            "accel_x_g": 0.01,
            "accel_y_g": 0.02,
            "accel_z_g": 1.00,
            "gyro_x_dps": 0.5,
            "gyro_y_dps": 0.4,
            "gyro_z_dps": 0.3,
            "altitude_est_m": 120.0,
            "battery_voltage_v": 11.1,
            "gps_speed_mps": 10.0,
        },
        {
            "accel_x_g": 0.02,
            "accel_y_g": 0.01,
            "accel_z_g": 1.01,
            "gyro_x_dps": 0.6,
            "gyro_y_dps": 0.3,
            "gyro_z_dps": 0.2,
            "altitude_est_m": 121.0,
            "battery_voltage_v": 11.0,
            "gps_speed_mps": 10.5,
        },
        {
            "accel_x_g": 0.00,
            "accel_y_g": 0.03,
            "accel_z_g": 0.99,
            "gyro_x_dps": 0.4,
            "gyro_y_dps": 0.5,
            "gyro_z_dps": 0.4,
            "altitude_est_m": 119.5,
            "battery_voltage_v": 11.2,
            "gps_speed_mps": 9.8,
        },
    ])


def make_row(**overrides):
    row = {
        "accel_x_g": 0.01,
        "accel_y_g": 0.02,
        "accel_z_g": 1.00,
        "gyro_x_dps": 0.5,
        "gyro_y_dps": 0.4,
        "gyro_z_dps": 0.3,
        "altitude_est_m": 120.0,
        "battery_voltage_v": 11.1,
        "gps_speed_mps": 10.0,
    }
    row.update(overrides)
    return row


def test_train_from_csv_sets_trained_flag(tmp_path):
    df = make_training_df()
    csv_path = tmp_path / "train.csv"
    df.to_csv(csv_path, index=False)

    ml = GuardianML()
    ml.train_from_csv(csv_path)

    assert ml.is_trained is True


def test_score_row_returns_none_if_not_trained():
    ml = GuardianML()
    row = make_row()

    assert ml.score_row(row) is None


def test_score_row_returns_float_after_training(tmp_path):
    df = make_training_df()
    csv_path = tmp_path / "train.csv"
    df.to_csv(csv_path, index=False)

    ml = GuardianML()
    ml.train_from_csv(csv_path)

    score = ml.score_row(make_row())

    assert isinstance(score, float)


def test_score_row_returns_none_for_missing_feature_after_training(tmp_path):
    df = make_training_df()
    csv_path = tmp_path / "train.csv"
    df.to_csv(csv_path, index=False)

    ml = GuardianML()
    ml.train_from_csv(csv_path)

    score = ml.score_row(make_row(gps_speed_mps=""))

    assert score is None
    