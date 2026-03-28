from pathlib import Path
import subprocess
import sys
import csv


def run_step(label, command):
    print(f"\n=== {label} ===")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"\nStep failed: {label}")
        sys.exit(result.returncode)


def read_validation_summary(csv_path):
    total = 0
    passed = 0
    failed = 0
    failed_scenarios = []

    if not csv_path.exists():
        return total, passed, failed, failed_scenarios

    with csv_path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            if row.get("match") == "PASS":
                passed += 1
            else:
                failed += 1
                failed_scenarios.append(row.get("scenario", "unknown"))

    return total, passed, failed, failed_scenarios


def main():
    project_root = Path(__file__).resolve().parent.parent
    validation_csv = project_root / "results" / "metrics" / "expected_vs_observed.csv"

    run_step("Generate scenario metrics", "python3 -m guardian.metrics")
    run_step("Generate expected vs observed validation", "python3 -m guardian.validation")
    run_step("Run test suite", "python3 -m pytest -q")

    total, passed, failed, failed_scenarios = read_validation_summary(validation_csv)

    print("\n=== FINAL SUMMARY ===")
    print(f"Validation scenarios checked: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed_scenarios:
        print("\nFailed scenarios:")
        for scenario in failed_scenarios:
            print(f"- {scenario}")
    else:
        print("\nAll validation scenarios passed.")

    print("\nGuardian pipeline complete.")


if __name__ == "__main__":
    main()
