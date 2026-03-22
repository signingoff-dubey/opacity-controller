"""
hotkeys.py — Global hotkey registration.

Active hotkeys:
  <toggle>        — configurable, default alt+t
  alt+up          — opacity +5%
  alt+down        — opacity -5%
  alt+1 .. alt+9  — set opacity 10% .. 90%
  alt+0           — restore to solid (100%)
"""

import sys

try:
    import keyboard
except ImportError:
    sys.exit("[error] keyboard not found.  Run: pip install keyboard")


class HotkeyManager:
    def __init__(self, app) -> None:
        self.app = app

    def register(self) -> None:
        self._clear()
        hk = self.app.config.get("hotkey", "alt+t")
        keyboard.add_hotkey(hk,         self.app.on_toggle,   suppress=False)
        keyboard.add_hotkey("alt+up",   self.app.on_increase, suppress=False)
        keyboard.add_hotkey("alt+down", self.app.on_decrease, suppress=False)
        for n in range(1, 10):
            pct = n * 10
            keyboard.add_hotkey(f"alt+{n}",
                                lambda p=pct: self.app.on_set_opacity(p),
                                suppress=False)
        keyboard.add_hotkey("alt+0",
                            lambda: self.app.on_set_opacity(100),
                            suppress=False)
        print(f"[hotkeys] Registered. Toggle: {hk}")

    def _clear(self) -> None:
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
