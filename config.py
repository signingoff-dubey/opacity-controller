"""
config.py — App constants, default config, load/save helpers.
"""

import os
import sys
import json

APP_NAME    = "OpacityController"
APP_VERSION = "3.0"

# Config file sits next to the script / .exe
_base       = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_FILE = os.path.join(_base, "opacity_config.json")

DEFAULT_CONFIG: dict = {
    "hotkey":    "alt+t",
    "autostart": False,
    "windows":   {},        # window title -> saved opacity %
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception as e:
            print(f"[config] Load failed, using defaults: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[config] Save failed: {e}")
