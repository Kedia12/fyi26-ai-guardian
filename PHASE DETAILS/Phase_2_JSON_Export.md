# Phase 2 — JSON Export & Structured Logging
**Fixes Gap 6: No JSON or structured log export — alerts only print to console**

---

## Why This Phase Comes Before the Database

Right now, every alert disappears when the program exits. The console is not persistence. Before building a database (Phase 3), you need a lightweight export format that the database, the dashboard, and any external tool can consume. A `.jsonl` file (newline-delimited JSON) is the simplest possible format: one JSON object per line, human-readable, machine-parseable, and appendable without loading the whole file.

This phase also lays the architectural pattern for how the engine interacts with persistence layers — a pattern that the database and dashboard will reuse.

---

## Prerequisite

Phase 1 must be complete. This phase reads `config["logging"]["json_export_enabled"]` and `config["logging"]["json_export_path"]` from the YAML config you created in Phase 1.

---

## Files You Will Create

```
guardian/export.py               ← AlertExporter class
tests/test_export.py             ← tests for write, batch, disabled mode
```

## Files You Will Modify

```
guardian/engine.py               ← wire in AlertExporter after process_row()
guardian/main.py                 ← print export path at end of run
```

## No new pip dependencies

This phase uses only Python's built-in `json` module and `pathlib`. Nothing to install.

---

## Step 1 — Create `guardian/export.py`

Create the file `guardian/export.py` with the following content. Every line is explained with comments.

```python
import json
from datetime import datetime, timezone
from pathlib import Path


class AlertExporter:
    """Writes alert dictionaries to a newline-delimited JSON (.jsonl) file.

    Each line in the output file is a self-contained JSON object with three
    top-level keys:
        - "alert"      : the alert dict produced by build_alert()
        - "telemetry"  : the raw telemetry row that triggered the alert
        - "exported_at": ISO 8601 UTC timestamp of when the line was written

    The file is opened in append mode so multiple runs accumulate into the
    same file. Call close() or use as a context manager to flush and close.

    Parameters
    ----------
    path : str or Path
        Destination file path. Parent directories are created automatically.
    enabled : bool
        When False, all write methods are no-ops and no file is created.
        This allows the exporter to be instantiated unconditionally and
        disabled via config without any if-checks in callers.
    """

    def __init__(self, path, enabled=True):
        self.enabled = enabled
        self._handle = None

        if not enabled:
            # Nothing to open. All write calls will be no-ops.
            return

        # Resolve to an absolute path and create any missing parent directories.
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Open in append mode so each run adds to the existing file rather
        # than overwriting it. UTF-8 encoding for unicode safety.
        self._handle = resolved.open("a", encoding="utf-8")

    def write_alert(self, alert, telemetry_row=None):
        """Write one alert as a single JSON line.

        Parameters
        ----------
        alert : dict
            An alert dict produced by build_alert(). Must be JSON-serialisable.
        telemetry_row : dict, optional
            The telemetry row that triggered the alert. Stored alongside the
            alert for traceability. If None, "telemetry" key is null in output.
        """
        if not self.enabled or self._handle is None:
            return

        record = {
            "alert": alert,
            "telemetry": telemetry_row,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        # json.dumps with default=str handles any non-serialisable values
        # (e.g. numpy floats from ML scoring) by converting them to strings.
        line = json.dumps(record, default=str)
        self._handle.write(line + "\n")

    def write_batch(self, alerts, telemetry_row=None):
        """Write multiple alerts, each as its own JSON line.

        Parameters
        ----------
        alerts : list[dict]
            List of alert dicts. Each is written as a separate line.
        telemetry_row : dict, optional
            The telemetry row shared by all alerts in this batch.
        """
        for alert in alerts:
            self.write_alert(alert, telemetry_row)

    def flush(self):
        """Force any buffered data to disk immediately.

        Call this during long-running ingestion sessions if you need to
        ensure alerts are visible on disk without closing the file.
        """
        if self._handle is not None:
            self._handle.flush()

    def close(self):
        """Flush and close the file handle.

        Safe to call even if the exporter is disabled or already closed.
        """
        if self._handle is not None:
            self._handle.flush()
            self._handle.close()
            self._handle = None

    def __enter__(self):
        """Support usage as a context manager: with AlertExporter(...) as exp:"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the file is closed when leaving the with block."""
        self.close()
        # Return False so any exception is re-raised normally.
        return False
```

---

## Step 2 — Create `tests/test_export.py`

Create the file `tests/test_export.py` with the following content.

```python
import json
import pytest
from pathlib import Path
from guardian.export import AlertExporter


# ---------------------------------------------------------------------------
# Shared helper — a minimal valid alert dict
# ---------------------------------------------------------------------------

def make_alert(**overrides):
    """Return a minimal alert dictionary for testing."""
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "severity": "WARNING",
        "confidence": 0.85,
        "reason_code": "TEST_ALERT",
        "reason_text": "Test alert for unit testing.",
        "recommended_action": "CHECK_LINK",
        "alert_status": "active",
    }
    base.update(overrides)
    return base


def make_row(**overrides):
    """Return a minimal telemetry row dictionary for testing."""
    base = {
        "timestamp_ms": 1000,
        "packet_id": 1,
        "node_id": "node_01",
        "accel_x_g": 0.01,
        "battery_voltage_v": 11.8,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_write_alert_creates_file(tmp_path):
    """write_alert() must create the output file when it does not exist."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    assert output_file.exists(), "Output file was not created."


def test_write_alert_produces_valid_json_line(tmp_path):
    """Each line written by write_alert() must be valid JSON."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1, "Expected exactly one line in the output file."

    parsed = json.loads(lines[0])
    assert isinstance(parsed, dict), "Parsed line must be a JSON object."


def test_write_alert_record_has_required_top_level_keys(tmp_path):
    """Each written record must contain 'alert', 'telemetry', 'exported_at'."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert(), telemetry_row=make_row())
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert "alert" in record
    assert "telemetry" in record
    assert "exported_at" in record


def test_write_alert_includes_telemetry_row_when_provided(tmp_path):
    """The 'telemetry' key must contain the row dict when one is passed."""
    output_file = tmp_path / "alerts.jsonl"
    row = make_row(battery_voltage_v=9.9)
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert(), telemetry_row=row)
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert record["telemetry"]["battery_voltage_v"] == 9.9


def test_write_alert_telemetry_is_null_when_not_provided(tmp_path):
    """When no telemetry row is passed, the 'telemetry' key must be null."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    record = json.loads(output_file.read_text(encoding="utf-8").strip())
    assert record["telemetry"] is None


def test_write_batch_produces_one_line_per_alert(tmp_path):
    """write_batch() with 3 alerts must produce exactly 3 lines."""
    output_file = tmp_path / "alerts.jsonl"
    alerts = [make_alert(reason_code=f"CODE_{i}") for i in range(3)]
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_batch(alerts)
    exporter.close()

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_write_batch_empty_list_writes_nothing(tmp_path):
    """write_batch() with an empty list must not write any lines."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=True)
    exporter.write_batch([])
    exporter.close()

    content = output_file.read_text(encoding="utf-8").strip()
    assert content == "", "File should be empty after writing an empty batch."


def test_disabled_exporter_creates_no_file(tmp_path):
    """When enabled=False, write_alert() must not create any file."""
    output_file = tmp_path / "alerts.jsonl"
    exporter = AlertExporter(path=output_file, enabled=False)
    exporter.write_alert(make_alert())
    exporter.close()

    assert not output_file.exists(), "File must not be created when exporter is disabled."


def test_context_manager_closes_file(tmp_path):
    """Using AlertExporter as a context manager must close the file on exit."""
    output_file = tmp_path / "alerts.jsonl"
    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert())

    # After the with block, the file handle should be closed.
    assert exp._handle is None, "File handle must be None after context manager exits."
    assert output_file.exists(), "File must still exist after context manager exits."


def test_append_mode_accumulates_across_calls(tmp_path):
    """Writing twice to the same file must accumulate lines, not overwrite."""
    output_file = tmp_path / "alerts.jsonl"

    # First write
    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert(reason_code="FIRST"))

    # Second write to same file
    with AlertExporter(path=output_file, enabled=True) as exp:
        exp.write_alert(make_alert(reason_code="SECOND"))

    lines = output_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2, "Both writes must be present (append mode)."
    codes = [json.loads(l)["alert"]["reason_code"] for l in lines]
    assert "FIRST" in codes
    assert "SECOND" in codes


def test_creates_parent_directories_automatically(tmp_path):
    """AlertExporter must create missing parent directories."""
    nested_path = tmp_path / "a" / "b" / "c" / "alerts.jsonl"
    exporter = AlertExporter(path=nested_path, enabled=True)
    exporter.write_alert(make_alert())
    exporter.close()

    assert nested_path.exists(), "File must be created including all parent directories."
```

---

## Step 3 — Modify `guardian/engine.py`

Open `guardian/engine.py`. You need to make two changes:

### 3a — Add imports at the top

Find the existing import block and add these two imports:

```python
from guardian.export import AlertExporter
from guardian.config import get_config
```

### 3b — Instantiate the exporter in `GuardianEngine.__init__()`

Find the `__init__` method of `GuardianEngine`. It currently looks something like this:

```python
def __init__(self):
    self.ml = GuardianML()
    # ... trains the model ...
    self.prev_row = None
```

Add the exporter instantiation **at the end of `__init__`**, after the existing lines:

```python
def __init__(self):
    self.ml = GuardianML()
    # ... existing training code stays here unchanged ...
    self.prev_row = None

    # Instantiate the alert exporter based on config settings.
    # If json_export_enabled is false (or config is missing), the exporter
    # is created in disabled mode and all write calls become no-ops.
    # This keeps all existing tests working without any changes.
    cfg = get_config()
    logging_cfg = cfg.get("logging", {})
    export_enabled = logging_cfg.get("json_export_enabled", False)
    export_path = logging_cfg.get("json_export_path", "results/logs/alerts.jsonl")
    self.exporter = AlertExporter(path=export_path, enabled=export_enabled)
```

### 3c — Call the exporter in `process_row()`

Find the `process_row()` method. It currently collects alerts from rules and the ML model, then returns them. Find the line just **before** the `return` statement and add:

```python
    # Export all alerts generated by this row to the .jsonl log file.
    if self.exporter:
        self.exporter.write_batch(alerts, row)

    return alerts, anomaly_score
```

The full `process_row()` structure should now look like this (your existing logic stays unchanged, only the export call and return are modified):

```python
def process_row(self, row):
    alerts = []

    # --- all your existing rule checks remain here unchanged ---
    # alerts += check_packet_loss(self.prev_row, row)
    # alerts += check_out_of_order_packet(self.prev_row, row)
    # ... etc ...

    # ML scoring
    anomaly_score = self.ml.score_row(row)

    # Update previous row for next iteration
    self.prev_row = row

    # Export alerts to JSON log
    if self.exporter:
        self.exporter.write_batch(alerts, row)

    return alerts, anomaly_score
```

---

## Step 4 — Modify `guardian/main.py`

Open `guardian/main.py`. Find the `run()` function. After the replay loop finishes and before the function returns, add these lines to print the export path:

```python
    # Print the JSON export path so the user knows where alerts were saved.
    from guardian.config import get_config
    cfg = get_config()
    logging_cfg = cfg.get("logging", {})
    if logging_cfg.get("json_export_enabled", False):
        export_path = logging_cfg.get("json_export_path", "results/logs/alerts.jsonl")
        print(f"\nAlerts exported to: {export_path}")
```

---

## Step 5 — Run Tests

```bash
# Run the new export tests
pytest tests/test_export.py -v
```

Expected: all 10 tests pass.

```bash
# Run the full suite to confirm nothing broke
pytest -q
```

Expected: zero failures.

---

## Step 6 — Test the Export End-to-End

```bash
# Run a scenario
python -m guardian.main data/scenarios/low_battery.csv
```

Expected console output includes a new line at the end:
```
Alerts exported to: results/logs/alerts.jsonl
```

```bash
# Verify the file was created and contains valid JSON
python -c "
import json
lines = open('results/logs/alerts.jsonl', encoding='utf-8').readlines()
for i, line in enumerate(lines):
    obj = json.loads(line)
    print(f'Line {i+1}: reason_code={obj[\"alert\"][\"reason_code\"]}')
print(f'Total alerts exported: {len(lines)}')
"
```

---

## Step 7 — Understand the Output Format

Each line in `results/logs/alerts.jsonl` looks like this (formatted for readability — the actual file has one compact JSON object per line):

```json
{
  "alert": {
    "timestamp_ms": 1000,
    "packet_id": 5,
    "node_id": "node_01",
    "severity": "WARNING",
    "confidence": 0.97,
    "reason_code": "LOW_BATTERY",
    "reason_text": "Battery voltage 10.3V is below the warning threshold.",
    "recommended_action": "ENTER_SAFE_MODE",
    "alert_status": "active"
  },
  "telemetry": {
    "timestamp_ms": 1000,
    "packet_id": 5,
    "battery_voltage_v": 10.3,
    "... all 22 telemetry fields ...": "..."
  },
  "exported_at": "2026-04-30T10:00:00.123456+00:00"
}
```

The database (Phase 3) and dashboard (Phase 6) will consume this exact format.

---

## Checklist — Phase 2 Complete When:

- [ ] `guardian/export.py` exists with `AlertExporter` class and all 6 methods
- [ ] `tests/test_export.py` exists with 10 tests, all passing
- [ ] `guardian/engine.py` imports `AlertExporter` and `get_config`
- [ ] `guardian/engine.py` `__init__` instantiates `self.exporter`
- [ ] `guardian/engine.py` `process_row()` calls `self.exporter.write_batch(alerts, row)`
- [ ] `guardian/main.py` prints the export path at the end of a run
- [ ] Running `python -m guardian.main data/scenarios/low_battery.csv` creates `results/logs/alerts.jsonl`
- [ ] `python -c "import json; [json.loads(l) for l in open('results/logs/alerts.jsonl')]"` raises no errors
- [ ] `pytest -q` passes with zero failures

---

## What Changes in the Codebase After This Phase

```
guardian/
├── export.py                    ← NEW — AlertExporter class
├── engine.py                    ← MODIFIED — wires in exporter
└── main.py                      ← MODIFIED — prints export path

tests/
└── test_export.py               ← NEW — 10 export tests

results/
└── logs/
    └── alerts.jsonl             ← GENERATED — created at runtime
```

---

## Proceed to Phase 3 →

Phase 3 builds the SQLite database. It follows the same integration pattern as the exporter: an optional object is passed into (or instantiated inside) `GuardianEngine`, and `process_row()` calls it after collecting alerts.
