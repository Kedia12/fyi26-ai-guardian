# Phase 1 — Configuration System
**Fixes Gap 8: All thresholds are hardcoded in rules.py and ml_model.py**

---

## Why This Phase Comes First

Every other phase depends on being able to read settings from a config file. The dashboard needs to know the database path. The ingestion listener needs the UDP port. The ML model needs its threshold. If you skip this phase and build other features first, you will have to go back and refactor them all. Do this first.

The goal is simple: move every hardcoded number and string out of Python files and into one YAML file. After this phase, changing a threshold means editing one line in `config/guardian_config.yaml`, not hunting through Python code.

---

## Files You Will Create

```
config/guardian_config.yaml      ← the single source of truth for all settings
guardian/config.py               ← the Python module that reads the YAML
tests/test_config.py             ← tests that verify the config system works
```

## Files You Will Modify

```
guardian/rules.py                ← replace 8 hardcoded literals
guardian/ml_model.py             ← replace 3 hardcoded IsolationForest params
requirements.txt                 ← add PyYAML>=6.0
```

---

## Step 1 — Install PyYAML

Before writing any code, install the one new dependency this phase requires.

Open your terminal in the project root and run:

```bash
pip install "PyYAML>=6.0"
```

Then open `requirements.txt` and add this line at the bottom:

```
PyYAML>=6.0
```

Your full `requirements.txt` should now look like this:

```
pandas>=2.0
scikit-learn>=1.3
pytest>=8.0
PyYAML>=6.0
```

---

## Step 2 — Create the config directory

```bash
mkdir config
```

---

## Step 3 — Create `config/guardian_config.yaml`

Create the file `config/guardian_config.yaml` with the following exact content. Every value here was previously hardcoded somewhere in the Python source. Comments explain what each value controls.

```yaml
# Guardian configuration file
# All tuneable thresholds, hyperparameters, and paths live here.
# Edit this file to change behaviour without touching Python code.

rules:
  # Maximum allowed timestamp gap between consecutive packets (milliseconds).
  # Gaps larger than this are reported as PACKET_LOSS.
  packet_loss_gap_ms: 200

  # Battery voltage threshold for a WARNING alert.
  # Triggered when voltage drops below this value.
  battery_warning_v: 10.5

  # Battery voltage threshold for a CRITICAL alert.
  # Must be lower than battery_warning_v.
  battery_critical_v: 10.2

  # Maximum allowed latitude or longitude change between consecutive packets
  # (degrees). Changes larger than this are reported as GPS_JUMP.
  gps_jump_threshold_deg: 0.001

  # Maximum allowed GPS speed change between consecutive packets (m/s).
  # Changes larger than this are also part of GPS_JUMP detection.
  gps_speed_jump_mps: 15.0

  # Minimum number of satellites required for a valid GPS fix.
  # Fewer satellites triggers GPS_FIX_LOSS.
  min_satellites: 4

  # IMU acceleration magnitude below which the IMU is considered "not moving"
  # during GPS-IMU inconsistency checks (g).
  gps_imu_accel_mag_threshold: 0.2

  # IMU gyroscope magnitude below which the IMU is considered "not rotating"
  # during GPS-IMU inconsistency checks (degrees/sec).
  gps_imu_gyro_mag_threshold: 3.0

ml:
  # Number of trees in the Isolation Forest.
  n_estimators: 100

  # Expected fraction of anomalous rows in training data (0.0 to 0.5).
  contamination: 0.05

  # Random seed for reproducibility.
  random_state: 42

  # Anomaly score threshold above which the ML model generates a ML_ANOMALY alert.
  # Scores from score_row() are positive floats; higher means more anomalous.
  alert_threshold: 0.1

  # Severity level for ML-generated alerts. Options: WARNING, CRITICAL.
  alert_severity: WARNING

  # Confidence value for ML-generated alerts (0.0 to 1.0).
  # The actual confidence is computed dynamically; this is a fallback default.
  alert_confidence: 0.75

logging:
  # Set to true to write every alert to a .jsonl file as it is generated.
  json_export_enabled: true

  # Path (relative to project root) where the .jsonl alert log is written.
  json_export_path: results/logs/alerts.jsonl

database:
  # Set to true to persist telemetry rows and alerts into SQLite.
  enabled: false

  # Path (relative to project root) for the SQLite database file.
  path: results/guardian.db

ingestion:
  # Active ingestion mode. Options: replay, udp, serial, mavlink.
  mode: replay

  # UDP listener settings (used when mode: udp or mode: mavlink).
  udp_host: 0.0.0.0
  udp_port: 14550

  # Serial port settings (used when mode: serial).
  serial_port: /dev/ttyUSB0
  serial_baud: 57600
```

---

## Step 4 — Create `guardian/config.py`

Create the file `guardian/config.py` with the following content. Read every comment carefully — they explain every design decision.

```python
from pathlib import Path
import yaml

# Module-level cache. None means "not loaded yet."
# Once loaded, the config dict is stored here and reused for every call
# to get_config() without reading the file again.
_config = None

# Resolve the project root once at import time.
# guardian/config.py lives in guardian/, so .parent is guardian/ and
# .parent.parent is the project root (fyi26-ai-guardian/).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "guardian_config.yaml"


def load_config(path=None):
    """Read the YAML config file and store the result in the module cache.

    Parameters
    ----------
    path : str or Path, optional
        Path to a YAML config file. If None, uses
        config/guardian_config.yaml relative to the project root.

    Returns
    -------
    dict
        The parsed configuration dictionary.
    """
    global _config

    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        # Return empty dict with all sections as empty dicts.
        # This means every get_rule_threshold() call falls back to its default,
        # so the system works even without a config file (important for tests).
        _config = {"rules": {}, "ml": {}, "logging": {}, "database": {}, "ingestion": {}}
        return _config

    with open(config_path, "r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)

    # yaml.safe_load returns None for an empty file. Guard against that.
    _config = loaded if loaded is not None else {}

    # Ensure all top-level sections exist as dicts so callers never get KeyError.
    for section in ("rules", "ml", "logging", "database", "ingestion"):
        if section not in _config:
            _config[section] = {}

    return _config


def get_config():
    """Return the cached config dict, loading it on first access.

    Returns
    -------
    dict
        The full configuration dictionary.
    """
    global _config
    if _config is None:
        load_config()
    return _config


def get_rule_threshold(key, default=None):
    """Retrieve a value from the rules section of the config.

    Parameters
    ----------
    key : str
        The threshold name, e.g. "packet_loss_gap_ms".
    default : any, optional
        Value to return if the key is not found in the config.
        Always provide a sensible default so existing behaviour is
        preserved even when the config file is missing or incomplete.

    Returns
    -------
    The threshold value from the config, or default if not found.
    """
    return get_config().get("rules", {}).get(key, default)


def get_ml_param(key, default=None):
    """Retrieve a value from the ml section of the config.

    Parameters
    ----------
    key : str
        The parameter name, e.g. "alert_threshold".
    default : any, optional
        Value to return if the key is not found.

    Returns
    -------
    The ML parameter value from the config, or default if not found.
    """
    return get_config().get("ml", {}).get(key, default)


def reload_config(path=None):
    """Clear the cache and reload the config from disk.

    This is primarily used in tests to swap in a temporary config file
    without restarting the Python process.

    Parameters
    ----------
    path : str or Path, optional
        Path to reload from. If None, reloads from the default path.
    """
    global _config
    _config = None
    load_config(path)
```

---

## Step 5 — Create `tests/test_config.py`

Create the file `tests/test_config.py` with the following content.

```python
import pytest
from pathlib import Path
import guardian.config as cfg


def test_load_config_returns_dict_with_all_sections(tmp_path):
    """load_config() must return a dict containing rules and ml keys."""
    yaml_content = """
rules:
  packet_loss_gap_ms: 200
ml:
  n_estimators: 100
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg.reload_config(config_file)
    result = cfg.get_config()

    assert isinstance(result, dict)
    assert "rules" in result
    assert "ml" in result


def test_get_rule_threshold_returns_correct_value(tmp_path):
    """get_rule_threshold() must return the value from the YAML file."""
    yaml_content = """
rules:
  packet_loss_gap_ms: 200
  battery_warning_v: 10.5
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg.reload_config(config_file)

    assert cfg.get_rule_threshold("packet_loss_gap_ms") == 200
    assert cfg.get_rule_threshold("battery_warning_v") == 10.5


def test_get_rule_threshold_uses_default_when_key_missing(tmp_path):
    """get_rule_threshold() must return the default when key is absent."""
    yaml_content = "rules:\n  packet_loss_gap_ms: 200\n"
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg.reload_config(config_file)

    # "nonexistent_key" is not in the YAML; should return the provided default
    assert cfg.get_rule_threshold("nonexistent_key", 999) == 999


def test_get_ml_param_returns_correct_value(tmp_path):
    """get_ml_param() must return the value from the ml section."""
    yaml_content = """
ml:
  n_estimators: 100
  alert_threshold: 0.1
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg.reload_config(config_file)

    assert cfg.get_ml_param("n_estimators") == 100
    assert cfg.get_ml_param("alert_threshold") == 0.1


def test_reload_config_picks_up_new_values(tmp_path):
    """After reload_config(), get_rule_threshold() must reflect the new file."""
    # Write first config
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("rules:\n  packet_loss_gap_ms: 200\n", encoding="utf-8")
    cfg.reload_config(config_file)
    assert cfg.get_rule_threshold("packet_loss_gap_ms") == 200

    # Overwrite with new value
    config_file.write_text("rules:\n  packet_loss_gap_ms: 500\n", encoding="utf-8")
    cfg.reload_config(config_file)
    assert cfg.get_rule_threshold("packet_loss_gap_ms") == 500


def test_missing_config_file_returns_empty_sections():
    """When the config file does not exist, the system must not crash."""
    cfg.reload_config("/nonexistent/path/config.yaml")
    result = cfg.get_config()

    # All sections must be present as empty dicts (not raise KeyError)
    assert "rules" in result
    assert "ml" in result
    assert isinstance(result["rules"], dict)
    assert isinstance(result["ml"], dict)


def test_get_config_caches_result(tmp_path):
    """Calling get_config() twice must return the same dict object."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("rules:\n  packet_loss_gap_ms: 200\n", encoding="utf-8")
    cfg.reload_config(config_file)

    first_call = cfg.get_config()
    second_call = cfg.get_config()

    # Must be the exact same object in memory (cached, not reloaded)
    assert first_call is second_call
```

---

## Step 6 — Modify `guardian/rules.py`

Open `guardian/rules.py`. You need to:
1. Add one import line at the top of the file.
2. Replace 8 hardcoded literals throughout the file.

**Add this import at the top of `guardian/rules.py`** (after the existing imports):

```python
from guardian.config import get_rule_threshold
```

**Then replace each hardcoded literal** with a `get_rule_threshold()` call. Here is every change, shown as old → new:

### In `check_packet_loss()`

Find:
```python
if time_gap > 200:
```
Replace with:
```python
if time_gap > get_rule_threshold("packet_loss_gap_ms", 200):
```

### In `check_low_battery()`

Find:
```python
if voltage < 10.5:
```
Replace with:
```python
if voltage < get_rule_threshold("battery_warning_v", 10.5):
```

Find:
```python
if voltage < 10.2:
```
Replace with:
```python
if voltage < get_rule_threshold("battery_critical_v", 10.2):
```

### In `check_gps_fix_loss()`

Find:
```python
satellite_count < 4
```
Replace with:
```python
satellite_count < get_rule_threshold("min_satellites", 4)
```

### In `check_gps_jump()`

Find every occurrence of `0.001` used as a lat/lon threshold:
```python
lat_jump > 0.001 or lon_jump > 0.001
```
Replace with:
```python
lat_jump > get_rule_threshold("gps_jump_threshold_deg", 0.001) or lon_jump > get_rule_threshold("gps_jump_threshold_deg", 0.001)
```

Find the speed jump threshold:
```python
speed_jump > 15
```
Replace with:
```python
speed_jump > get_rule_threshold("gps_speed_jump_mps", 15.0)
```

### In `check_gps_imu_inconsistency()`

Find:
```python
accel_mag < 0.2
```
Replace with:
```python
accel_mag < get_rule_threshold("gps_imu_accel_mag_threshold", 0.2)
```

Find:
```python
gyro_mag < 3.0
```
Replace with:
```python
gyro_mag < get_rule_threshold("gps_imu_gyro_mag_threshold", 3.0)
```

---

## Step 7 — Modify `guardian/ml_model.py`

Open `guardian/ml_model.py`. You need to:
1. Add one import line at the top.
2. Replace the 3 hardcoded `IsolationForest` constructor arguments.

**Add this import at the top of `guardian/ml_model.py`** (after the existing imports):

```python
from guardian.config import get_ml_param
```

**Find the `IsolationForest` constructor call** in `__init__()`:

```python
self.model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)
```

**Replace it with:**

```python
self.model = IsolationForest(
    n_estimators=get_ml_param("n_estimators", 100),
    contamination=get_ml_param("contamination", 0.05),
    random_state=get_ml_param("random_state", 42)
)
```

---

## Step 8 — Run Tests to Confirm Everything Still Works

```bash
# Run the full test suite
pytest -q
```

Every existing test must still pass. The default values in every `get_rule_threshold()` and `get_ml_param()` call act as safety nets, so even if the YAML file is not found, the system behaves exactly as before.

```bash
# Run the new config tests
pytest tests/test_config.py -v
```

Expected output: all tests pass with green checkmarks.

```bash
# Run a scenario end-to-end to confirm nothing broke
python -m guardian.main data/scenarios/low_battery.csv
```

Expected output: same alert output as before. You should see `[WARNING] LOW_BATTERY` and `[CRITICAL] LOW_BATTERY` alerts.

---

## Step 9 — Optional: Change a Threshold and Confirm It Takes Effect

This step is not required but demonstrates the system is working correctly.

1. Open `config/guardian_config.yaml`
2. Change `battery_warning_v: 10.5` to `battery_warning_v: 13.0`
3. Run: `python -m guardian.main data/scenarios/normal_flight.csv`
4. You should now see LOW_BATTERY alerts on the normal flight (because 13V is above a normal battery)
5. Change it back to `10.5` when done

---

## Checklist — Phase 1 Complete When:

- [ ] `config/guardian_config.yaml` exists and contains all 5 sections (rules, ml, logging, database, ingestion)
- [ ] `guardian/config.py` exists with `load_config`, `get_config`, `get_rule_threshold`, `get_ml_param`, `reload_config`
- [ ] `tests/test_config.py` exists with 7 tests
- [ ] `guardian/rules.py` has no bare numeric literals for thresholds (uses `get_rule_threshold` for all 8)
- [ ] `guardian/ml_model.py` has no bare `n_estimators=100` etc (uses `get_ml_param` for all 3)
- [ ] `requirements.txt` includes `PyYAML>=6.0`
- [ ] `pytest -q` passes with zero failures
- [ ] `python -m guardian.main data/scenarios/low_battery.csv` produces the same output as before

---

## What Changes in the Codebase After This Phase

```
config/                          ← NEW directory
└── guardian_config.yaml         ← NEW — all settings in one place

guardian/
├── config.py                    ← NEW — YAML loader + accessor functions
├── rules.py                     ← MODIFIED — 8 literals replaced
└── ml_model.py                  ← MODIFIED — 3 literals replaced

tests/
└── test_config.py               ← NEW — 7 config system tests

requirements.txt                 ← MODIFIED — added PyYAML>=6.0
```

---

## Proceed to Phase 2 →

Phase 2 builds the JSON export system. It reads `config["logging"]["json_export_enabled"]` and `config["logging"]["json_export_path"]` from the YAML you just created — which is why Phase 1 must be done first.
