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
