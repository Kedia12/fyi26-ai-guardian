# Phase 8 — Deployment & Packaging
**Fixes Gap 9: No deployment or packaging — no Dockerfile, no installable package, no CI/CD**

---

## What You Are Building

This phase contains no new Python logic. Everything here is infrastructure that makes the system:

1. **Installable** — `pip install -e .` works; entry-point commands like `guardian` and `guardian-dashboard` work from any terminal
2. **Containerized** — `docker build` produces a portable image; `docker-compose up` starts the full stack
3. **CI-tested** — every GitHub push runs the test suite automatically
4. **Reproducible** — anyone can clone the repo, run one command, and have a working system

---

## Prerequisites

All previous phases (1–7) must be complete. This phase only wraps what already exists.

---

## Files You Will Create

```
pyproject.toml
Dockerfile
.dockerignore
docker-compose.yml
.github/workflows/ci.yml
Makefile
```

## Files You Will Modify

```
requirements.txt                 ← add sync comment
README.md                        ← add Installation, Docker, CI sections
```

---

## Step 1 — Create `pyproject.toml`

`pyproject.toml` is the modern Python packaging standard (PEP 517/518). It replaces the old `setup.py`. Create the file `pyproject.toml` in the project root:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "fyi26-ai-guardian"
version = "0.2.0"
description = "Human-in-the-loop AI Guardian for connected aerospace systems (Airbus FYI26 2026)"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }

dependencies = [
    "pandas>=2.0",
    "scikit-learn>=1.3",
    "PyYAML>=6.0",
    "Flask>=3.0",
    "pyserial>=3.5",
]

[project.optional-dependencies]
mqtt = ["paho-mqtt>=1.6"]
mavlink = ["pymavlink>=2.4"]
dev = ["pytest>=8.0"]

[project.scripts]
# After `pip install -e .`, these commands become available in the terminal.
guardian           = "guardian.main:run"
guardian-dashboard = "dashboard.app:run_dashboard"
guardian-live      = "guardian.ingest_runner:run_live"

[tool.setuptools.packages.find]
# Automatically find all Python packages (guardian/, dashboard/, etc.)
where = ["."]

[tool.pytest.ini_options]
# Tell pytest where to find tests
testpaths = ["tests"]
# Show short test summary at the end
addopts = "-q"
```

### Install in editable mode

After creating `pyproject.toml`, run:

```bash
pip install -e .
```

This installs the package in "editable" mode — changes you make to the source files take effect immediately without reinstalling.

Now you can run these commands from anywhere:

```bash
guardian data/scenarios/low_battery.csv
guardian-dashboard
guardian-live
```

---

## Step 2 — Create `Dockerfile`

Create the file `Dockerfile` in the project root:

```dockerfile
# Use Python 3.11 slim as the base image.
# "slim" means no extra OS packages pre-installed — keeps the image small.
FROM python:3.11-slim

# Set the working directory inside the container.
WORKDIR /app

# Copy dependency files first (before the rest of the code).
# Docker caches each layer. By copying requirements first, the pip install
# layer is only rebuilt when requirements change, not on every code change.
COPY requirements.txt pyproject.toml ./

# Install all dependencies.
# --no-cache-dir keeps the image smaller by not storing the pip download cache.
# -e . installs the guardian and dashboard packages from pyproject.toml.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e ".[dev]"

# Copy the entire project into the container.
COPY . .

# Expose the Flask dashboard port.
EXPOSE 5000

# Default command: run the replay mode on the low_battery scenario.
# Override this in docker-compose.yml or with `docker run <image> <command>`.
CMD ["python", "-m", "guardian.main", "data/scenarios/low_battery.csv"]
```

### Build and test the Docker image

```bash
# Build the image
docker build -t fyi26-guardian .

# Run the tests inside the container
docker run --rm fyi26-guardian python -m pytest -q

# Run a scenario inside the container
docker run --rm fyi26-guardian python -m guardian.main data/scenarios/combined_fault.csv

# Start the dashboard inside the container
docker run --rm -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/config:/app/config \
  fyi26-guardian python -m dashboard.app
```

---

## Step 3 — Create `.dockerignore`

Create the file `.dockerignore` in the project root. This tells Docker which files to exclude from the build context (makes builds faster and images smaller):

```
# Python bytecode and caches
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/

# Git history (not needed in the container)
.git/
.gitignore

# Generated runtime files (these are mounted as volumes in docker-compose)
results/*.db
results/logs/*.jsonl

# Virtual environments
.venv/
venv/
env/

# IDE files
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Test cache
.pytest_cache/
.coverage

# Planning documents (not needed in the container)
PLANING.md
ProJect_Over_View.md
PHASE\ DETAILS/
```

---

## Step 4 — Create `docker-compose.yml`

`docker-compose.yml` defines how to run the full stack (Guardian engine + dashboard) with one command.

Create the file `docker-compose.yml` in the project root:

```yaml
version: "3.9"

services:

  # The Guardian replay + dashboard service
  guardian:
    build: .
    image: fyi26-guardian:latest
    container_name: fyi26-guardian

    # Mount local directories as volumes so:
    # 1. Scenario CSV files are available inside the container
    # 2. Results and database files are written to the host (not lost when container stops)
    # 3. Config changes on the host take effect without rebuilding the image
    volumes:
      - ./data:/app/data
      - ./results:/app/results
      - ./config:/app/config

    # Expose the Flask dashboard port
    ports:
      - "5000:5000"

    # Environment variables (override config values if needed)
    environment:
      - PYTHONUNBUFFERED=1   # ensures print() output appears immediately

    # Default command: start the Flask dashboard
    # To run a scenario instead: docker-compose run guardian python -m guardian.main data/scenarios/combined_fault.csv
    command: python -m dashboard.app

    # Restart policy: restart on crash but not on manual docker stop
    restart: unless-stopped
```

### Start the full stack

```bash
# Build and start in the background
docker-compose up -d

# Watch logs in real time
docker-compose logs -f

# Run a scenario to populate the database
docker-compose run guardian python -m guardian.main data/scenarios/combined_fault.csv

# Open browser: http://localhost:5000

# Stop everything
docker-compose down
```

---

## Step 5 — Create `.github/workflows/ci.yml`

This file defines the GitHub Actions CI pipeline. Every time you push a commit or open a pull request, GitHub will automatically:
1. Set up Python 3.11
2. Install all dependencies
3. Run the test suite
4. Run the metrics pipeline
5. Run the validation pipeline

Create the directory `.github/workflows/` and the file `ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    name: Run Test Suite
    runs-on: ubuntu-latest

    steps:
      # Step 1: Check out the code
      - name: Checkout repository
        uses: actions/checkout@v4

      # Step 2: Set up Python
      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"    # cache pip packages between runs for speed

      # Step 3: Install dependencies
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      # Step 4: Run unit tests
      - name: Run pytest
        run: python -m pytest -q

      # Step 5: Run metrics generation
      - name: Generate scenario metrics
        run: python -m guardian.metrics

      # Step 6: Run validation
      - name: Run validation
        run: python -m guardian.validation

      # Step 7: Upload results as artifacts (optional but useful)
      - name: Upload results
        if: always()   # upload even if tests fail
        uses: actions/upload-artifact@v4
        with:
          name: guardian-results
          path: results/
          retention-days: 7
```

### Push to GitHub and verify CI

```bash
git add .
git commit -m "Add Phase 8 deployment and packaging"
git push origin main
```

Go to your GitHub repository → click the **Actions** tab → you should see the CI workflow running. If everything is correct, all steps will show green checkmarks.

---

## Step 6 — Create `Makefile`

A `Makefile` provides short aliases for common developer tasks. Create the file `Makefile` in the project root:

```makefile
# FYI26 AI Guardian — Developer task shortcuts
# Usage: make <target>

.PHONY: test pipeline install dashboard live docker-build docker-run clean

# Run the test suite
test:
	python -m pytest -q

# Run the full pipeline (metrics + validation + tests)
pipeline:
	python -m guardian.run_pipeline

# Install in editable mode (run this once after cloning)
install:
	pip install -e ".[dev]"

# Start the Flask dashboard
dashboard:
	python -m dashboard.app

# Start live UDP ingestion
live:
	python -m guardian.ingest_runner

# Build the Docker image
docker-build:
	docker build -t fyi26-guardian .

# Run the tests inside Docker
docker-test:
	docker run --rm fyi26-guardian python -m pytest -q

# Start the full stack with docker-compose
docker-up:
	docker-compose up -d

# Stop the full stack
docker-down:
	docker-compose down

# Remove generated result files (not the DB or logs, just CSVs)
clean:
	rm -f results/metrics/scenario_metrics.csv
	rm -f results/metrics/expected_vs_observed.csv
	rm -f results/metrics/precision_recall.csv
	rm -f results/metrics/validation_summary.md
```

Usage examples:
```bash
make test          # run pytest
make pipeline      # run full validation
make dashboard     # start the web dashboard
make docker-build  # build Docker image
make docker-test   # run tests inside Docker
```

---

## Step 7 — Update `requirements.txt`

Open `requirements.txt` and add a comment at the top explaining it must stay in sync with `pyproject.toml`:

```
# Keep in sync with [project.dependencies] in pyproject.toml
pandas>=2.0
scikit-learn>=1.3
pytest>=8.0
PyYAML>=6.0
Flask>=3.0
pyserial>=3.5
pymavlink>=2.4
# optional: paho-mqtt>=1.6
```

---

## Step 8 — Update `README.md`

Open `README.md` and add the following sections at the end (after the existing content):

```markdown
## Installation

```bash
git clone https://github.com/your-username/fyi26-ai-guardian.git
cd fyi26-ai-guardian
pip install -e ".[dev]"
```

After installation, these CLI commands are available:
```bash
guardian data/scenarios/low_battery.csv    # run a scenario
guardian-dashboard                          # start the dashboard
guardian-live                              # start live UDP ingestion
```

## Running with Docker

```bash
# Build the image
docker build -t fyi26-guardian .

# Run tests inside the container
docker run --rm fyi26-guardian python -m pytest -q

# Start the dashboard (open http://localhost:5000)
docker-compose up -d
```

## Running with Make

```bash
make test       # run the test suite
make pipeline   # run full validation pipeline
make dashboard  # start the dashboard
```

## CI / CD

Every push to `main` runs the full test suite via GitHub Actions. See `.github/workflows/ci.yml`.
```

---

## Step 9 — Verify Everything

```bash
# 1. Install in editable mode
pip install -e .

# 2. Confirm entry points work
guardian data/scenarios/low_battery.csv

# 3. Run tests
pytest -q

# 4. Build Docker image
docker build -t fyi26-guardian .

# 5. Run tests inside Docker
docker run --rm fyi26-guardian python -m pytest -q

# 6. Commit and push
git add pyproject.toml Dockerfile .dockerignore docker-compose.yml \
        .github/workflows/ci.yml Makefile requirements.txt README.md
git commit -m "Phase 8: deployment packaging — Dockerfile, pyproject.toml, CI pipeline"
git push origin main

# 7. Check GitHub Actions tab — CI should be green
```

---

## Checklist — Phase 8 Complete When:

- [ ] `pyproject.toml` exists with all dependencies and 3 entry points
- [ ] `pip install -e .` completes without errors
- [ ] `guardian data/scenarios/low_battery.csv` works as a CLI command
- [ ] `Dockerfile` exists and builds without errors
- [ ] `docker run --rm fyi26-guardian python -m pytest -q` passes
- [ ] `.dockerignore` exists
- [ ] `docker-compose.yml` exists and `docker-compose up -d` starts the dashboard
- [ ] `.github/workflows/ci.yml` exists
- [ ] Pushing to GitHub triggers the CI pipeline and all steps pass green
- [ ] `Makefile` exists and `make test` works
- [ ] `requirements.txt` has sync comment and includes all 7 packages

---

## What Changes in the Codebase After This Phase

```
pyproject.toml                   ← NEW — package metadata and entry points
Dockerfile                       ← NEW — container definition
.dockerignore                    ← NEW — Docker build exclusions
docker-compose.yml               ← NEW — full-stack container orchestration
.github/
└── workflows/
    └── ci.yml                   ← NEW — GitHub Actions CI pipeline
Makefile                         ← NEW — developer task shortcuts
requirements.txt                 ← MODIFIED — sync comment added
README.md                        ← MODIFIED — installation and Docker docs
```

---

## Proceed to Phase 9 →

Phase 9 is the most complex phase. It integrates with real RC aircraft hardware via the MAVLink protocol, which delivers telemetry in dozens of different message types that must be assembled into the Guardian's 22-field telemetry schema. Only attempt Phase 9 when you have access to a flight controller or a MAVLink simulator (ArduPilot SITL).
