"""
Manages persistent configuration for retavortaropy CLI tools.
Stores settings in ~/.retavortaropy/config.json.
"""

import json
import pathlib


def get_config_path() -> pathlib.Path:
    """Returns the path to the config file: ~/.retavortaropy/config.json."""
    return pathlib.Path.home() / ".retavortaropy" / "config.json"


def load_config() -> dict:
    """Reads the config file and returns its contents. Returns {} if missing."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="UTF-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config: dict) -> None:
    """Writes config to the config file, creating the directory if needed."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="UTF-8") as f:
        json.dump(config, f, indent=2)


def get_revo_path() -> pathlib.Path | None:
    """Returns the saved revo path, or None if not configured."""
    config = load_config()
    revo_path = config.get("revo_fonto_path")
    if revo_path:
        return pathlib.Path(revo_path)
    return None
