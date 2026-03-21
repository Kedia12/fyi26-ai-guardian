import csv
import time


def replay_csv(path):
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row
            time.sleep(0.1)