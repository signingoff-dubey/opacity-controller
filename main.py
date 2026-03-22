"""
Opacity Controller v3.0
=======================
Run:
  python main.py          → tray + hotkeys only
  python main.py --ui     → full UI + tray + hotkeys
  OpacityController.exe   → full UI + tray + hotkeys (auto)

Hotkeys:
  Alt+T       toggle transparency on focused window (customisable)
  Alt+↑/↓     nudge opacity ±5%
  Alt+1–9     set opacity 10%–90% instantly
  Alt+0       restore to solid
"""

import sys
import threading

from win32_utils import enable_dpi_awareness
from app import OpacityApp
from tray import TrayManager


def main() -> None:
    # Must be called before any Tk window opens
    enable_dpi_awareness()

    app  = OpacityApp()
    tray = TrayManager(app)
    app.tray = tray

    is_exe  = getattr(sys, "frozen", False)   # True when packaged by PyInstaller
    show_ui = is_exe or "--ui" in sys.argv

    if show_ui:
        from ui.main_window import MainUI
        ui      = MainUI(app)
        app.ui  = ui

        # Run tray on a background daemon thread — it will not block
        threading.Thread(target=tray.run, daemon=True).start()

        print("Opacity Controller v3.0 — UI mode")
        print(f"  Toggle hotkey : {app.config.get('hotkey','alt+t')}")
        print("  Alt+↑/↓       : nudge opacity")
        print("  Alt+1–9/0     : set exact opacity")
        ui.run()   # blocks until window is closed / minimised

    else:
        print("Opacity Controller v3.0 — tray mode")
        print(f"  {app.config.get('hotkey','alt+t'):<16} toggle transparency")
        print("  Alt+↑ / Alt+↓   nudge opacity ±5%")
        print("  Alt+1–9         set opacity 10%–90%")
        print("  Alt+0           restore to solid")
        print("  Tray icon       right-click for all options")
        print("  --ui flag       open the full UI window")
        tray.run()   # blocks


if __name__ == "__main__":
    main()
