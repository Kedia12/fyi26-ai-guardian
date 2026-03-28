from pathlib import Path
import csv

from guardian.engine import GuardianEngine
from guardian.expectations import EXPECTED_REASON_CODES
from guardian.replay import replay_csv


def collect_observed_reason_codes(path):
    engine = GuardianEngine()
    observed = []

    for row in replay_csv(path, sleep_enabled=False):
        alerts, _ = engine.process_row(row)
        for alert in alerts:
            code = alert.get("reason_code")
            if code and code not in observed:
                observed.append(code)

    return observed


def generate_expected_vs_observed_csv():
    project_root = Path(__file__).resolve().parent.parent
    scenarios_dir = project_root / "data" / "scenarios"
    results_dir = project_root / "results" / "metrics"
    results_dir.mkdir(parents=True, exist_ok=True)

    output_csv = results_dir / "expected_vs_observed.csv"

    rows = []
    for scenario_file in sorted(scenarios_dir.glob("*.csv")):
        scenario_name = scenario_file.name
        expected = EXPECTED_REASON_CODES.get(scenario_name, [])
        observed = collect_observed_reason_codes(scenario_file)

        expected_set = set(expected)
        observed_set = set(observed)

        missing_expected = sorted(expected_set - observed_set)
        unexpected_observed = sorted(observed_set - expected_set)

        if not expected and not observed:
            match = "PASS"
        elif expected_set.issubset(observed_set):
            match = "PASS"
        else:
            match = "FAIL"

        rows.append({
            "scenario": scenario_name,
            "expected_reason_codes": ";".join(expected) if expected else "NONE",
            "observed_reason_codes": ";".join(observed) if observed else "NONE",
            "missing_expected": ";".join(missing_expected) if missing_expected else "NONE",
            "unexpected_observed": ";".join(unexpected_observed) if unexpected_observed else "NONE",
            "match": match,
        })

    with output_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scenario",
                "expected_reason_codes",
                "observed_reason_codes",
                "missing_expected",
                "unexpected_observed",
                "match",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Validation written to: {output_csv}")


if __name__ == "__main__":
    generate_expected_vs_observed_csv()
