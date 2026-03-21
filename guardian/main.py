from pathlib import Path
from replay import replay_csv
from engine import GuardianEngine


def run(path):
    engine = GuardianEngine()

    for row in replay_csv(path):
        alerts = engine.process_row(row)

        if alerts:
            for alert in alerts:
                print(alert)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "data" / "scenarios" / "packet_loss.csv"
    run(csv_path)