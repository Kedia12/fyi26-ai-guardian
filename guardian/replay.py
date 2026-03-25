import csv
import time
from pathlib import Path


def replay_csv(path, delay_s=0.1, sleep_enabled=True):
    """
    Replay telemetry rows from a CSV file.

    Args:
        path: path to the CSV scenario file
        delay_s: delay between rows in seconds
        sleep_enabled: if False, disables waiting (useful for tests)
    """
    csv_path = Path(path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {csv_path}")

    with csv_path.open("r", newline="") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        for row in reader:
            yield row
            if sleep_enabled:
                time.sleep(delay_s)
                