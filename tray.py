"""
tray.py — System tray icon and menu.

FIX: Never unpack menu.items from another menu object.
     Always build a fresh pystray.Menu() directly.
"""

import sys

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("[error] pystray / Pillow not found.  Run: pip install pystray pillow")

from win32_utils import get_window_title


def _make_icon() -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    d.rectangle([4,  4,  59, 59], outline=(255, 255, 255, 220), width=3)
    d.rectangle([14, 14, 49, 49], fill=(59, 130, 246, 160))
    for i in range(0, 64, 10):
        d.line([(4, 4 + i), (4 + i, 4)], fill=(255, 255, 255, 55), width=1)
    return img


class TrayManager:
    def __init__(self, app) -> None:
        self.app  = app
        self.icon = pystray.Icon(
            "OpacityController",
            _make_icon(),
            "Opacity Controller",
            menu=self._build()
        )

    # ── Menu builder — always returns a fresh Menu ────────────────────────────
    def _build(self) -> pystray.Menu:
        items = []

        # One entry per active transparent window
        for hwnd, pct in list(self.app.active.items()):
            title = get_window_title(hwnd)
            if not title:
                continue
            aot   = self.app.on_top.get(hwnd, False)
            short = title[:32] + ("…" if len(title) > 32 else "")

            def _make_restore(h):
                def _r(icon, item): self.app.restore_window(h)
                return _r

            def _make_aot(h):
                def _a(icon, item): self.app.toggle_always_on_top(h)
                return _a

            sub = pystray.Menu(
                pystray.MenuItem(f"Opacity: {pct}%", None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Always on top  ✓" if aot else "Always on top",
                    _make_aot(hwnd)
                ),
                pystray.MenuItem("Restore solid", _make_restore(hwnd)),
            )
            items.append(pystray.MenuItem(f"◈  {short}  [{pct}%]", sub))

        if self.app.active:
            items.append(pystray.MenuItem(
                "Restore all",
                lambda icon, item: self.app.restore_all()
            ))
            items.append(pystray.Menu.SEPARATOR)

        # Open UI (only relevant in --ui / .exe mode)
        items.append(pystray.MenuItem("Open", self._open_ui, default=True))
        items.append(pystray.Menu.SEPARATOR)

        hk = self.app.config.get("hotkey", "alt+t")
        items.append(pystray.MenuItem(f"Hotkey: {hk}", self.app.show_settings))

        as_label = "Auto-start  ✓" if self.app.config.get("autostart") else "Auto-start on boot"
        items.append(pystray.MenuItem(
            as_label,
            lambda icon, item: self.app.toggle_autostart()
        ))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", lambda icon, item: self.app.quit(icon)))

        return pystray.Menu(*items)

    def _open_ui(self, icon=None, item=None) -> None:
        if self.app.ui:
            try:
                self.app.ui.root.after(0, self.app.ui.show)
            except Exception:
                pass

    def refresh(self) -> None:
        try:
            self.icon.menu = self._build()
            self.icon.update_menu()
        except Exception as e:
            print(f"[tray] refresh error: {e}")

    def run(self) -> None:
        self.icon.run()
