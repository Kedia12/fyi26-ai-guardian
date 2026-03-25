import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURES = [
    "accel_x_g",
    "accel_y_g",
    "accel_z_g",
    "gyro_x_dps",
    "gyro_y_dps",
    "gyro_z_dps",
    "altitude_est_m",
    "battery_voltage_v",
    "gps_speed_mps",
]


class GuardianML:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        self.is_trained = False

    def train_from_csv(self, path):
        df = pd.read_csv(path)

        missing_features = [feature for feature in FEATURES if feature not in df.columns]
        if missing_features:
            raise ValueError(
                f"Training data is missing required features: {missing_features}"
            )

        X = df[FEATURES].copy()
        X = X.apply(pd.to_numeric, errors="coerce")

        if X.isnull().any().any():
            raise ValueError("Training data contains missing or invalid feature values.")

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

    def score_row(self, row):
        if not self.is_trained:
            return None

        values = {}
        for feature in FEATURES:
            value = row.get(feature, None)
            if value in (None, ""):
                return None
            try:
                values[feature] = float(value)
            except (TypeError, ValueError):
                return None

        X = pd.DataFrame([values])
        X_scaled = self.scaler.transform(X)

        # decision_function: higher = more normal, lower = more abnormal
        normality_score = self.model.decision_function(X_scaled)[0]
        anomaly_score = -normality_score

        return float(anomaly_score)
        