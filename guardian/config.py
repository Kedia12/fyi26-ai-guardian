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
