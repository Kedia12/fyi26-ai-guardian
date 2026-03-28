from pathlib import Path
import subprocess
import sys


def run_command(command):
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    project_root = Path(__file__).resolve().parent.parent
    print("Running automated metrics generation...")
    run_command("python3 -m guardian.metrics")

    print("Running expected vs observed validation...")
    run_command("python3 -m guardian.validation")

    print("Running test suite...")
    run_command("python3 -m pytest -q")

    print("\nGuardian automation complete.")


if __name__ == "__main__":
    main()
