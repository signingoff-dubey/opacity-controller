"""
app.py — Core application state and logic.
UI and tray are injected after construction so this file has no UI imports.
"""

from config import load_config, save_config
from autostart import set_autostart, get_autostart_state
from hotkeys import HotkeyManager
from win32_utils import (
    set_opacity, reset_opacity,
    set_always_on_top,
    get_foreground_window, get_window_title,
)


class OpacityApp:
    def __init__(self) -> None:
        self.config: dict = load_config()
        self.active: dict = {}   # hwnd -> opacity %
        self.on_top: dict = {}   # hwnd -> bool

        # Injected later
        self.tray = None
        self.ui   = None

        self._hk = HotkeyManager(self)
        self._hk.register()

        # Sync registry state into config
        real = get_autostart_state()
        if real != self.config.get("autostart", False):
            self.config["autostart"] = real
            save_config(self.config)

    # ── Hotkey callbacks ──────────────────────────────────────────────────────
    def on_toggle(self) -> None:
        hwnd, title = get_foreground_window()
        if not title or hwnd == 0:
            return
        if hwnd in self.active:
            self.restore_window(hwnd)
        else:
            pct = self.config["windows"].get(title, 70)
            self._apply(hwnd, title, pct)

    def on_increase(self) -> None:
        self._nudge(+5)

    def on_decrease(self) -> None:
        self._nudge(-5)

    def on_set_opacity(self, pct: int) -> None:
        hwnd, title = get_foreground_window()
        if not title or hwnd == 0:
            return
        if pct >= 100:
            if hwnd in self.active:
                self.restore_window(hwnd)
            return
        self._apply(hwnd, title, pct)

    def _nudge(self, delta: int) -> None:
        hwnd, title = get_foreground_window()
        if not title or hwnd == 0:
            return
        current = self.active.get(hwnd, self.config["windows"].get(title, 70))
        self._apply(hwnd, title, max(10, min(100, current + delta)))

    # ── Core operations ───────────────────────────────────────────────────────
    def _apply(self, hwnd: int, title: str, pct: int) -> None:
        set_opacity(hwnd, pct)
        self.active[hwnd] = pct
        self.config["windows"][title] = pct
        save_config(self.config)
        self._notify()
        print(f"[app] {title}: {pct}%")

    def restore_window(self, hwnd: int) -> None:
        reset_opacity(hwnd)
        self.active.pop(hwnd, None)
        if self.on_top.pop(hwnd, False):
            set_always_on_top(hwnd, False)
        self._notify()
        print(f"[app] Restored: {get_window_title(hwnd)}")

    def restore_all(self) -> None:
        for hwnd in list(self.active.keys()):
            reset_opacity(hwnd)
            if self.on_top.pop(hwnd, False):
                set_always_on_top(hwnd, False)
        self.active.clear()
        self._notify()
        print("[app] Restored all")

    def toggle_always_on_top(self, hwnd: int) -> None:
        new = not self.on_top.get(hwnd, False)
        set_always_on_top(hwnd, new)
        self.on_top[hwnd] = new
        self._notify()

    # ── Settings / autostart ──────────────────────────────────────────────────
    def toggle_autostart(self) -> None:
        new = not self.config.get("autostart", False)
        if set_autostart(new):
            self.config["autostart"] = new
            save_config(self.config)
        self._notify()

    def set_hotkey(self, new_hk: str) -> None:
        self.config["hotkey"] = new_hk
        save_config(self.config)
        self._hk.register()
        self._notify()

    def show_settings(self, icon=None, item=None) -> None:
        from ui.settings_window import SettingsWindow
        SettingsWindow.open(self)

    # ── Notify UI + tray of state change ─────────────────────────────────────
    def _notify(self) -> None:
        if self.tray:
            try:
                self.tray.refresh()
            except Exception:
                pass
        if self.ui:
            try:
                self.ui.root.after(0, self.ui.refresh_active_list)
            except Exception:
                pass

    # ── Quit ──────────────────────────────────────────────────────────────────
    def quit(self, icon=None) -> None:
        self.restore_all()
        if self.tray:
            try:
                self.tray.icon.stop()
            except Exception:
                pass
        import os as _os
        _os._exit(0)
