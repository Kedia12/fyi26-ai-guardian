from pathlib import Path
import subprocess
import sys
import csv

from guardian.config import get_config
from guardian.db import GuardianDB


def run_step(label, command):
    print(f"\n=== {label} ===")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"\nStep failed: {label}")
        sys.exit(result.returncode)


def read_precision_recall_summary(csv_path):
    if not csv_path.exists():
        return None
    total_precision = 0.0
    total_recall = 0.0
    count = 0
    with csv_path.open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                total_precision += float(row["precision"])
                total_recall += float(row["recall"])
                count += 1
            except (KeyError, ValueError):
                continue
    if count == 0:
        return None
    return {
        "count": count,
        "avg_precision": total_precision / count,
        "avg_recall": total_recall / count,
    }


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

    cfg = get_config()
    db_cfg = cfg.get("database", {})
    db = None
    if db_cfg.get("enabled", False):
        db_path = db_cfg.get("path", "results/guardian.db")
        if not Path(db_path).is_absolute():
            db_path = project_root / db_path
        db = GuardianDB(path=db_path)
        print(f"Database opened: {db_path}")

    exe = sys.executable
    run_step("Generate scenario metrics", f'"{exe}" -m guardian.metrics')
    run_step("Generate expected vs observed validation", f'"{exe}" -m guardian.validation')
    run_step("Run test suite", f'"{exe}" -m pytest -q')

    pr_csv = project_root / "results" / "metrics" / "precision_recall.csv"
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

    pr_summary = read_precision_recall_summary(pr_csv)
    if pr_summary:
        print(f"\nPrecision/Recall across {pr_summary['count']} labeled scenarios:")
        print(f"  Avg Precision : {pr_summary['avg_precision']:.3f}")
        print(f"  Avg Recall    : {pr_summary['avg_recall']:.3f}")

    if db is not None:
        db.close()

    print("\nGuardian pipeline complete.")


if __name__ == "__main__":
    main()
