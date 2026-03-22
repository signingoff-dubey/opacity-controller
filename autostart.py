"""
autostart.py — Windows startup registry management.
"""

import os
import sys
import winreg

from config import APP_NAME

_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_autostart(enable: bool) -> bool:
    return _enable() if enable else _disable()


def get_autostart_state() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _enable() -> bool:
    try:
        if getattr(sys, "frozen", False):
            # Running as .exe — register the exe itself
            cmd = f'"{sys.executable}"'
        else:
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            exe     = pythonw if os.path.exists(pythonw) else sys.executable
            script  = os.path.abspath(__file__).replace("autostart.py", "main.py")
            cmd     = f'"{exe}" "{script}"'

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        print(f"[autostart] Enabled")
        return True
    except Exception as e:
        print(f"[autostart] Enable failed: {e}")
        return False


def _disable() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        print("[autostart] Disabled")
        return True
    except Exception as e:
        print(f"[autostart] Disable failed: {e}")
        return False
