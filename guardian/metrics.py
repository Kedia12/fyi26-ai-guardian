from pathlib import Path
import csv

from guardian.engine import GuardianEngine
from guardian.replay import replay_csv


def collect_metrics_for_scenario(path):
    engine = GuardianEngine()

    rows_processed = 0
    alerts_generated = 0
    warning_alerts = 0
    critical_alerts = 0
    reason_codes = []

    for row in replay_csv(path, sleep_enabled=False):
        alerts, _ = engine.process_row(row)
        rows_processed += 1
        alerts_generated += len(alerts)

        for alert in alerts:
            severity = alert.get("severity", "").upper()
            if severity == "WARNING":
                warning_alerts += 1
            elif severity == "CRITICAL":
                critical_alerts += 1

            reason_code = alert.get("reason_code")
            if reason_code and reason_code not in reason_codes:
                reason_codes.append(reason_code)

    return {
        "scenario": Path(path).name,
        "rows_processed": rows_processed,
        "alerts_generated": alerts_generated,
        "warning_alerts": warning_alerts,
        "critical_alerts": critical_alerts,
        "observed_reason_codes": ";".join(reason_codes) if reason_codes else "NONE",
    }


def generate_metrics_csv():
    project_root = Path(__file__).resolve().parent.parent
    scenarios_dir = project_root / "data" / "scenarios"
    results_dir = project_root / "results" / "metrics"
    results_dir.mkdir(parents=True, exist_ok=True)

    output_csv = results_dir / "scenario_metrics.csv"

    scenario_files = sorted(scenarios_dir.glob("*.csv"))

    rows = []
    for scenario_file in scenario_files:
        rows.append(collect_metrics_for_scenario(scenario_file))

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scenario",
                "rows_processed",
                "alerts_generated",
                "warning_alerts",
                "critical_alerts",
                "observed_reason_codes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Metrics written to: {output_csv}")


if __name__ == "__main__":
    generate_metrics_csv()
