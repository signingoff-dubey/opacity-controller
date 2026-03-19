"""
Opacity Controller v2.0
Features:
  - Multi-window transparency (track multiple windows simultaneously)
  - Custom hotkey (change from tray → Settings)
  - Auto-start on Windows boot (toggle from tray)
  - Scroll hotkeys to adjust opacity up/down on focused window
  - Tray shows all currently transparent windows
"""

import os
import sys
import json
import threading
import winreg
import tkinter as tk
from tkinter import ttk

# ── Win32 ──────────────────────────────────────────────────────────────────────
try:
    import win32gui
    import win32con
except ImportError:
    sys.exit("pywin32 not found. Run: pip install pywin32")

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("pystray / Pillow not found. Run: pip install pystray pillow")

try:
    import keyboard
except ImportError:
    sys.exit("keyboard not found. Run: pip install keyboard")


# ── Constants ──────────────────────────────────────────────────────────────────
APP_NAME    = "OpacityController"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opacity_config.json")
EXE_PATH    = os.path.abspath(sys.argv[0])

BG     = "#141414"
BG2    = "#1e1e1e"
BG3    = "#2a2a2a"
ACCENT = "#3b82f6"
FG     = "#e0e0e0"
FG2    = "#888888"
WHITE  = "#ffffff"
GREEN  = "#22c55e"
RED    = "#ef4444"

DEFAULT_CONFIG = {
    "hotkey":    "alt+t",
    "autostart": False,
    "windows":   {}      # title -> opacity %
}


# ── Config ─────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # merge with defaults so old configs still work
                for k, v in DEFAULT_CONFIG.items():
                    data.setdefault(k, v)
                return data
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(config: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[config] Save failed: {e}")


# ── Autostart ──────────────────────────────────────────────────────────────────
STARTUP_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

def set_autostart(enable: bool):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY,
                             0, winreg.KEY_SET_VALUE)
        if enable:
            # Use pythonw.exe so no terminal window on startup
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(pythonw):
                pythonw = sys.executable
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ,
                              f'"{pythonw}" "{os.path.abspath(__file__)}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[autostart] Failed: {e}")
        return False

def get_autostart() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY,
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ── Win32 helpers ──────────────────────────────────────────────────────────────
def set_opacity(hwnd: int, percent: int):
    percent = max(10, min(100, percent))
    alpha   = int(percent / 100 * 255)
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)
    except Exception as e:
        print(f"[win32] set_opacity({hwnd}): {e}")

def reset_opacity(hwnd: int):
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style & ~win32con.WS_EX_LAYERED)
    except Exception as e:
        print(f"[win32] reset_opacity({hwnd}): {e}")

def get_visible_windows() -> list[tuple[int, str]]:
    results = []
    skip    = {"", "Task Switching", "Program Manager", "Windows Input Experience"}
    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title in skip or len(title) < 2:
            return
        results.append((hwnd, title))
    win32gui.EnumWindows(_cb, None)
    return sorted(results, key=lambda x: x[1].lower())

def _opacity_desc(pct: int) -> str:
    if pct <= 25: return "Ghost — barely visible"
    if pct <= 45: return "See-through — content visible behind"
    if pct <= 65: return "Translucent — comfortable overlap"
    if pct <= 85: return "Focus mode — slight transparency"
    if pct <= 95: return "Nearly solid"
    return "Fully solid"


# ── Main app ───────────────────────────────────────────────────────────────────
class OpacityApp:
    def __init__(self):
        self.config    = load_config()
        # hwnd -> current opacity % (only windows that are transparent)
        self.active: dict[int, int] = {}
        self.tray_icon = None
        self._hotkey   = self.config.get("hotkey", "alt+t")
        self._register_hotkeys()

    # ── hotkeys ───────────────────────────────────────────────────────────────
    def _register_hotkeys(self):
        try:
            keyboard.unhook_all_hotkeys()
        except AttributeError:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        keyboard.add_hotkey(self._hotkey,  self.on_toggle,   suppress=False)
        keyboard.add_hotkey("alt+up",      self.on_increase, suppress=False)
        keyboard.add_hotkey("alt+down",    self.on_decrease, suppress=False)

    def on_toggle(self):
        """Alt+T — toggle transparency on focused window."""
        hwnd  = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        if not title or hwnd == 0:
            return
        if hwnd in self.active:
            reset_opacity(hwnd)
            del self.active[hwnd]
            print(f"[toggle] Restored: {title}")
        else:
            pct = self.config["windows"].get(title, 70)
            set_opacity(hwnd, pct)
            self.active[hwnd] = pct
            print(f"[toggle] Transparent ({pct}%): {title}")
        self._refresh_tray()

    def on_increase(self):
        """Alt+↑ — increase opacity by 5% on focused window."""
        self._nudge(+5)

    def on_decrease(self):
        """Alt+↓ — decrease opacity by 5% on focused window."""
        self._nudge(-5)

    def _nudge(self, delta: int):
        hwnd  = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        if not title or hwnd == 0:
            return
        current = self.active.get(hwnd, self.config["windows"].get(title, 70))
        new_pct = max(10, min(100, current + delta))
        set_opacity(hwnd, new_pct)
        self.active[hwnd] = new_pct
        self.config["windows"][title] = new_pct
        save_config(self.config)
        print(f"[nudge] {title}: {new_pct}%")

    # ── tray ──────────────────────────────────────────────────────────────────
    def _refresh_tray(self):
        """Rebuild the tray menu to reflect current transparent windows."""
        if self.tray_icon:
            self.tray_icon.menu = self._build_menu()
            self.tray_icon.update_menu()

    def _build_menu(self):
        items = []

        # Active transparent windows section
        if self.active:
            for hwnd, pct in list(self.active.items()):
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    continue
                label = f"✦ {title[:35]} [{pct}%]"
                def make_restore(h):
                    def _restore(icon, item):
                        reset_opacity(h)
                        if h in self.active:
                            del self.active[h]
                        self._refresh_tray()
                    return _restore
                items.append(pystray.MenuItem(label, make_restore(hwnd)))
            items.append(pystray.MenuItem(
                "Restore all",
                lambda icon, item: self._restore_all()
            ))
            items.append(pystray.Menu.SEPARATOR)

        items += [
            pystray.MenuItem("Select Window…",  self.show_picker),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                f"Hotkey: {self._hotkey}",
                self.show_settings
            ),
            pystray.MenuItem(
                "Auto-start on boot  ✓" if self.config.get("autostart") else "Auto-start on boot",
                self._toggle_autostart
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: self._quit(icon)),
        ]
        return pystray.Menu(*items)

    def _restore_all(self):
        for hwnd in list(self.active.keys()):
            reset_opacity(hwnd)
        self.active.clear()
        self._refresh_tray()
        print("[tray] Restored all windows")

    def _toggle_autostart(self, icon=None, item=None):
        new_state = not self.config.get("autostart", False)
        if set_autostart(new_state):
            self.config["autostart"] = new_state
            save_config(self.config)
            print(f"[autostart] {'Enabled' if new_state else 'Disabled'}")
        self._refresh_tray()

    def _quit(self, icon):
        self._restore_all()
        icon.stop()
        os._exit(0)

    # ── window picker ─────────────────────────────────────────────────────────
    def show_picker(self, icon=None, item=None):
        threading.Thread(target=self._picker_thread, daemon=True).start()

    def _picker_thread(self):
        windows = get_visible_windows()
        root    = tk.Tk()
        root.title("Opacity Controller")
        root.geometry("440x540")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.resizable(False, True)

        # Header
        hdr = tk.Frame(root, bg=BG, padx=20, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Opacity Controller",
                 bg=BG, fg=WHITE, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Double-click any window to control its transparency",
                 bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        # Active count badge
        if self.active:
            tk.Label(hdr, text=f"  {len(self.active)} window(s) currently transparent",
                     bg=BG, fg=GREEN, font=("Segoe UI", 9)).pack(anchor="w")

        # Search
        sf = tk.Frame(root, bg=BG2, padx=12)
        sf.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(sf, text="⌕", bg=BG2, fg=FG2, font=("Segoe UI", 12)).pack(side="left")
        sv = tk.StringVar()
        tk.Entry(sf, textvariable=sv, bg=BG2, fg=FG, insertbackground=FG,
                 font=("Segoe UI", 10), relief="flat", borderwidth=6
                 ).pack(side="left", fill="x", expand=True)

        # Listbox
        lf = tk.Frame(root, bg=BG)
        lf.pack(fill="both", expand=True, padx=16)
        sb = tk.Scrollbar(lf)
        sb.pack(side="right", fill="y")
        lb = tk.Listbox(lf, yscrollcommand=sb.set, bg=BG2, fg=FG,
                        selectbackground=ACCENT, selectforeground=WHITE,
                        font=("Segoe UI", 10), borderwidth=0,
                        highlightthickness=0, activestyle="none", cursor="hand2")
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)

        def refresh(*_):
            q = sv.get().lower()
            lb.delete(0, "end")
            for hwnd, title in windows:
                if q not in title.lower():
                    continue
                saved  = self.config["windows"].get(title)
                active = hwnd in self.active
                tag    = f"  [active {self.active[hwnd]}%]" if active else (f"  [{saved}%]" if saved else "")
                disp   = title[:50] + ("…" if len(title) > 50 else "")
                lb.insert("end", disp + tag)
                if active:
                    lb.itemconfig("end", fg=GREEN)

        sv.trace_add("write", refresh)
        refresh()

        def on_select(event=None):
            sel = lb.curselection()
            if not sel:
                return
            q        = sv.get().lower()
            filtered = [(h, t) for h, t in windows if q in t.lower()]
            if sel[0] >= len(filtered):
                return
            hwnd, title = filtered[sel[0]]
            root.destroy()
            threading.Thread(target=self._slider_thread,
                             args=(hwnd, title), daemon=True).start()

        lb.bind("<Double-Button-1>", on_select)

        bf = tk.Frame(root, bg=BG, padx=16, pady=12)
        bf.pack(fill="x")
        tk.Button(bf, text="  Control Opacity →  ",
                  bg=ACCENT, fg=WHITE, font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=8, cursor="hand2",
                  command=on_select).pack(side="right")
        if self.active:
            tk.Button(bf, text="Restore All",
                      bg=BG3, fg=RED, font=("Segoe UI", 9),
                      relief="flat", padx=12, pady=8, cursor="hand2",
                      command=lambda: [self._restore_all(), root.destroy()]
                      ).pack(side="right", padx=8)

        root.mainloop()

    # ── opacity slider ────────────────────────────────────────────────────────
    def _slider_thread(self, hwnd: int, title: str):
        saved = self.config["windows"].get(title, 70)
        if hwnd in self.active:
            saved = self.active[hwnd]

        win = tk.Tk()
        win.title("Set Opacity")
        win.geometry("380x320")
        win.configure(bg=BG)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        hdr = tk.Frame(win, bg=BG, padx=20, pady=14)
        hdr.pack(fill="x")
        short = title[:40] + ("…" if len(title) > 40 else "")
        tk.Label(hdr, text=short, bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(hdr, text="Alt+↑ / Alt+↓ also adjusts while focused",
                 bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(anchor="w")

        pct_var   = tk.IntVar(value=saved)
        pct_label = tk.Label(win, text=f"{saved}%", bg=BG, fg=WHITE,
                             font=("Segoe UI", 42, "bold"))
        pct_label.pack(pady=(8, 0))
        desc_label = tk.Label(win, text=_opacity_desc(saved),
                              bg=BG, fg=FG2, font=("Segoe UI", 9))
        desc_label.pack()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("C.Horizontal.TScale", background=BG,
                        troughcolor=BG3, sliderlength=20, sliderrelief="flat")

        def on_change(val):
            v = int(float(val))
            pct_label.config(text=f"{v}%")
            desc_label.config(text=_opacity_desc(v))
            set_opacity(hwnd, v)
            self.active[hwnd] = v
            self.config["windows"][title] = v
            save_config(self.config)
            self._refresh_tray()

        ttk.Scale(win, from_=10, to=100, orient="horizontal",
                  variable=pct_var, command=on_change,
                  style="C.Horizontal.TScale", length=300
                  ).pack(pady=12, padx=40)

        # Apply immediately
        set_opacity(hwnd, saved)
        self.active[hwnd] = saved
        self._refresh_tray()

        # Presets
        pf = tk.Frame(win, bg=BG)
        pf.pack(pady=4)
        for lbl, val in [("Ghost\n20%", 20), ("See-through\n50%", 50),
                         ("Focus\n70%", 70), ("Solid\n100%", 100)]:
            tk.Button(pf, text=lbl, bg=BG3, fg=FG,
                      font=("Segoe UI", 8), relief="flat",
                      padx=10, pady=5, width=8, cursor="hand2",
                      command=lambda v=val: [pct_var.set(v), on_change(v)]
                      ).pack(side="left", padx=3)

        bf = tk.Frame(win, bg=BG, pady=10)
        bf.pack(fill="x", padx=20)

        def do_reset():
            reset_opacity(hwnd)
            if hwnd in self.active:
                del self.active[hwnd]
            self._refresh_tray()
            win.destroy()

        tk.Button(bf, text="Reset to Solid", bg=BG3, fg=FG2,
                  font=("Segoe UI", 9), relief="flat", padx=12, pady=6,
                  cursor="hand2", command=do_reset).pack(side="left")
        tk.Button(bf, text="Done", bg=ACCENT, fg=WHITE,
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=20, pady=6,
                  cursor="hand2", command=win.destroy).pack(side="right")

        win.mainloop()

    # ── settings (singleton — flash + ding if already open) ─────────────────────
    def show_settings(self, icon=None, item=None):
        # If already open, flash the window and play Windows alert sound
        if getattr(self, "_settings_win", None):
            try:
                w = self._settings_win
                # bring to front
                w.deiconify()
                w.lift()
                w.focus_force()
                # Windows flash effect via FlashWindowEx
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.FindWindowW(None, "Settings — Opacity Controller")
                    if hwnd:
                        class FLASHWINFO(ctypes.Structure):
                            _fields_ = [("cbSize",    ctypes.c_uint),
                                        ("hwnd",      ctypes.c_void_p),
                                        ("dwFlags",   ctypes.c_uint),
                                        ("uCount",    ctypes.c_uint),
                                        ("dwTimeout", ctypes.c_uint)]
                        fi = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3, 4, 0)
                        ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))
                except Exception:
                    pass
                # Windows "ding" sound
                try:
                    import ctypes as _ct
                    _ct.windll.user32.MessageBeep(0x00000030)  # MB_ICONEXCLAMATION
                except Exception:
                    pass
            except Exception:
                self._settings_win = None
            return
        threading.Thread(target=self._settings_thread, daemon=True).start()

    def _settings_thread(self):
        S_BG  = "#111114"
        S_SUR = "#1a1a1f"
        S_RAI = "#22222a"
        S_BOR = "#2e2e38"
        S_ACC = "#3b82f6"
        S_MUT = "#7c7c8a"
        S_TXT = "#f0f0f2"
        S_GRN = "#22c55e"
        S_RED = "#ef4444"

        win = tk.Tk()
        self._settings_win = win
        win.title("Settings — Opacity Controller")
        win.geometry("560x600")
        win.minsize(560, 600)
        win.configure(bg=S_BG)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        def on_close():
            self._settings_win = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=S_SUR)
        hdr.pack(fill="x")

        tk.Label(hdr, text="Settings",
                 font=("Segoe UI", 16, "bold"),
                 fg=S_TXT, bg=S_SUR).pack(side="left", padx=28, pady=20)

        tk.Label(hdr, text="Opacity Controller",
                 font=("Segoe UI", 10),
                 fg=S_MUT, bg=S_SUR).pack(side="right", padx=24, pady=18)

        tk.Frame(win, bg=S_ACC, height=2).pack(fill="x")

        # ── Body ────────────────────────────────────────────────────────────
        body = tk.Frame(win, bg=S_BG, padx=32, pady=26)
        body.pack(fill="both", expand=True)

        # Section: Hotkey
        tk.Label(body, text="Keyboard shortcut",
                 font=("Segoe UI", 11, "bold"),
                 fg=S_TXT, bg=S_BG).pack(anchor="w")

        tk.Label(body,
                 text="This hotkey toggles transparency on whichever window is in focus.",
                 font=("Segoe UI", 9), fg=S_MUT, bg=S_BG,
                 wraplength=480, justify="left").pack(anchor="w", pady=(4, 14))

        hk_var    = tk.StringVar(value=self._hotkey)
        recording = [False]

        # Field label row
        field_lbl_row = tk.Frame(body, bg=S_BG)
        field_lbl_row.pack(fill="x", pady=(0, 6))
        tk.Label(field_lbl_row, text="Current shortcut",
                 font=("Segoe UI", 9), fg=S_MUT, bg=S_BG).pack(side="left")
        self._status_lbl = tk.Label(field_lbl_row, text="",
                                     font=("Segoe UI", 9), fg=S_GRN, bg=S_BG)
        self._status_lbl.pack(side="right")

        hk_box = tk.Frame(body, bg=S_SUR, highlightthickness=1,
                          highlightbackground=S_BOR)
        hk_box.pack(fill="x")

        hk_entry = tk.Entry(hk_box, textvariable=hk_var,
                            bg=S_SUR, fg=S_ACC,
                            insertbackground=S_ACC,
                            font=("Segoe UI", 14, "bold"),
                            relief="flat", borderwidth=0,
                            justify="center", highlightthickness=0)
        hk_entry.pack(fill="x", ipady=12, padx=16)

        hint = tk.Label(body,
                        text="Click the field above, then press your desired key combination",
                        font=("Segoe UI", 9), fg=S_MUT, bg=S_BG)
        hint.pack(anchor="w", pady=(8, 0))

        def start_record(event):
            recording[0] = True
            hk_var.set("")
            hint.config(text="Listening… press your combo now  (click elsewhere to cancel)",
                        fg=S_ACC)
            hk_box.config(highlightbackground=S_ACC)
            try:
                keyboard.unhook_all_hotkeys()
            except AttributeError:
                try:
                    keyboard.unhook_all()
                except Exception:
                    pass

        def stop_record(event):
            if not recording[0]:
                return
            recording[0] = False
            hk_box.config(highlightbackground=S_BOR)
            new_hk = hk_var.get().strip()
            if not new_hk:
                hk_var.set(self._hotkey)
                hint.config(text="Nothing recorded — previous shortcut kept", fg=S_RED)
                self._register_hotkeys()
                return
            try:
                keyboard.add_hotkey(new_hk, lambda: None)
                keyboard.remove_hotkey(new_hk)
                self._hotkey = new_hk
                self.config["hotkey"] = new_hk
                save_config(self.config)
                self._register_hotkeys()
                self._refresh_tray()
                hint.config(text=f"Saved  ·  {new_hk}", fg=S_GRN)
            except Exception:
                hk_var.set(self._hotkey)
                hint.config(text="Invalid combination — previous shortcut kept", fg=S_RED)
                self._register_hotkeys()

        def on_key(event):
            if not recording[0]:
                return
            parts = []
            if event.state & 0x4: parts.append("ctrl")
            if event.state & 0x1: parts.append("shift")
            if event.state & 0x8: parts.append("alt")
            key = event.keysym.lower()
            if key not in ("control_l","control_r","shift_l","shift_r",
                           "alt_l","alt_r","super_l","super_r"):
                parts.append(key)
            hk_var.set("+".join(parts) if parts else "")

        hk_entry.bind("<FocusIn>",  start_record)
        hk_entry.bind("<FocusOut>", stop_record)
        hk_entry.bind("<KeyPress>", on_key)

        # ── Section: Startup ────────────────────────────────────────────────
        tk.Frame(body, bg=S_BOR, height=1).pack(fill="x", pady=(28, 22))

        tk.Label(body, text="Startup",
                 font=("Segoe UI", 11, "bold"),
                 fg=S_TXT, bg=S_BG).pack(anchor="w")
        tk.Label(body,
                 text="Run Opacity Controller when Windows starts.",
                 font=("Segoe UI", 9), fg=S_MUT, bg=S_BG).pack(anchor="w", pady=(4, 12))

        as_row = tk.Frame(body, bg=S_SUR, highlightthickness=1,
                          highlightbackground=S_BOR)
        as_row.pack(fill="x")

        as_var = tk.BooleanVar(value=self.config.get("autostart", False))

        tk.Checkbutton(as_row,
                       text="  Launch automatically on Windows startup",
                       variable=as_var,
                       bg=S_SUR, fg=S_TXT,
                       selectcolor=S_RAI,
                       activebackground=S_SUR,
                       activeforeground=S_TXT,
                       font=("Segoe UI", 10),
                       cursor="hand2",
                       highlightthickness=0,
                       relief="flat",
                       command=lambda: self._set_autostart_from_ui(as_var.get())
                       ).pack(anchor="w", padx=12, pady=12)

        # ── Footer ──────────────────────────────────────────────────────────
        tk.Frame(win, bg=S_BOR, height=1).pack(fill="x")
        foot = tk.Frame(win, bg=S_SUR)
        foot.pack(fill="x")

        tk.Button(foot, text="Close",
                  bg=S_ACC, fg=S_TXT,
                  font=("Segoe UI", 11, "bold"),
                  relief="flat", borderwidth=0,
                  padx=40, pady=14,
                  activebackground="#2563eb",
                  activeforeground=S_TXT,
                  cursor="hand2",
                  highlightthickness=0,
                  command=on_close
                  ).pack(side="right", padx=20, pady=14)

        win.mainloop()

    def _set_autostart_from_ui(self, enable: bool):
        if set_autostart(enable):
            self.config["autostart"] = enable
            save_config(self.config)
            self._refresh_tray()


# ── Tray icon image ────────────────────────────────────────────────────────────
def _make_icon() -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    d.rectangle([4, 4, 59, 59], outline=(255, 255, 255, 220), width=3)
    d.rectangle([14, 14, 49, 49], fill=(59, 130, 246, 160))
    for i in range(0, 60, 10):
        d.line([(4, 4 + i), (4 + i, 4)], fill=(255, 255, 255, 60), width=1)
    return img



# ── DPI fix — must run before any Tk window ────────────────────────────────────
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ── Design tokens ──────────────────────────────────────────────────────────────
C_BG      = "#111114"
C_SURFACE = "#1a1a1f"
C_RAISED  = "#22222a"
C_BORDER  = "#2e2e38"
C_ACCENT  = "#3b82f6"
C_ACCENTD = "#2563eb"
C_SUCCESS = "#22c55e"
C_DANGER  = "#ef4444"
C_TEXT    = "#f0f0f2"
C_MUTED   = "#7c7c8a"
C_DIM     = "#3a3a48"

F_BODY  = ("Segoe UI", 10)
F_BODYM = ("Segoe UI", 10, "bold")
F_SMALL = ("Segoe UI",  9)
F_H1    = ("Segoe UI", 17, "bold")
F_H2    = ("Segoe UI", 11, "bold")
F_NUM   = ("Segoe UI", 30, "bold")


def _btn(parent, text, cmd, bg=C_RAISED, fg=C_TEXT, font=F_BODY,
         padx=18, pady=9, width=None, cursor="hand2", state="normal"):
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, font=font,
                  relief="flat", borderwidth=0,
                  padx=padx, pady=pady,
                  activebackground=C_ACCENTD if bg == C_ACCENT else C_BORDER,
                  activeforeground=C_TEXT,
                  cursor=cursor, state=state,
                  highlightthickness=0)
    if width:
        b.config(width=width)
    return b


# ── Tray icon image ────────────────────────────────────────────────────────────
def _make_icon() -> Image.Image:
    size = 64
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d    = ImageDraw.Draw(img)
    d.rectangle([4, 4, 59, 59], outline=(255, 255, 255, 220), width=3)
    d.rectangle([14, 14, 49, 49], fill=(59, 130, 246, 160))
    for i in range(0, 60, 10):
        d.line([(4, 4 + i), (4 + i, 4)], fill=(255, 255, 255, 60), width=1)
    return img


# ── Main UI ────────────────────────────────────────────────────────────────────
class MainUI:
    def __init__(self, app: "OpacityApp"):
        self.app      = app
        self._windows = []
        self.root     = tk.Tk()
        self._build()

    def _build(self):
        r = self.root
        r.title("Opacity Controller")
        r.geometry("600x860")
        r.configure(bg=C_BG)
        r.resizable(True, True)
        r.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(r, bg=C_SURFACE)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=C_SURFACE)
        left.pack(side="left", padx=22, pady=18)

        tk.Label(left, text="Opacity Controller", font=F_H1,
                 fg=C_TEXT, bg=C_SURFACE).pack(anchor="w")

        self._hk_lbl = tk.Label(left,
                                 text=f"Hotkey  ·  {self.app._hotkey}",
                                 font=F_SMALL, fg=C_MUTED, bg=C_SURFACE)
        self._hk_lbl.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(hdr, bg=C_SURFACE)
        right.pack(side="right", padx=16, pady=14)

        _btn(right, "Settings", lambda: self.app.show_settings(),
             bg=C_RAISED, fg=C_MUTED, font=F_SMALL, padx=14, pady=7
             ).pack(side="right", padx=(6, 0))
        _btn(right, "Minimise", r.withdraw,
             bg=C_RAISED, fg=C_MUTED, font=F_SMALL, padx=14, pady=7
             ).pack(side="right")

        # accent stripe
        tk.Frame(r, bg=C_ACCENT, height=2).pack(fill="x")

        # ── Window selector ─────────────────────────────────────────────────
        sec1 = tk.Frame(r, bg=C_BG, padx=22, pady=18)
        sec1.pack(fill="x")

        tk.Label(sec1, text="Window", font=F_H2,
                 fg=C_TEXT, bg=C_BG).pack(anchor="w")
        tk.Label(sec1, text="Select the window you want to control",
                 font=F_SMALL, fg=C_MUTED, bg=C_BG).pack(anchor="w", pady=(1, 8))

        row = tk.Frame(sec1, bg=C_BG)
        row.pack(fill="x")

        self._win_var = tk.StringVar()

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Flat.TCombobox",
                        fieldbackground=C_SURFACE, background=C_RAISED,
                        foreground=C_TEXT, selectbackground=C_ACCENT,
                        selectforeground=C_TEXT, borderwidth=0,
                        arrowcolor=C_MUTED, padding=(8, 6))
        style.configure("Flat.Horizontal.TScale",
                        background=C_BG, troughcolor=C_RAISED,
                        sliderlength=18, sliderrelief="flat",
                        troughrelief="flat")
        style.map("Flat.TCombobox",
                  fieldbackground=[("readonly", C_SURFACE)],
                  background=[("readonly", C_RAISED)])

        self._combo = ttk.Combobox(row, textvariable=self._win_var,
                                   font=F_BODY, state="readonly",
                                   style="Flat.TCombobox", height=14)
        self._combo.pack(side="left", fill="x", expand=True, ipady=5)
        self._combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        _btn(row, "↻", self._refresh_windows,
             bg=C_SURFACE, fg=C_MUTED, font=("Segoe UI", 13),
             padx=10, pady=5).pack(side="left", padx=(8, 0))

        # ── Divider ─────────────────────────────────────────────────────────
        tk.Frame(r, bg=C_BORDER, height=1).pack(fill="x", padx=22)

        # ── Opacity control ─────────────────────────────────────────────────
        sec2 = tk.Frame(r, bg=C_BG, padx=22, pady=18)
        sec2.pack(fill="x")

        row2 = tk.Frame(sec2, bg=C_BG)
        row2.pack(fill="x")
        tk.Label(row2, text="Opacity", font=F_H2, fg=C_TEXT, bg=C_BG).pack(side="left")
        self._pct_lbl = tk.Label(row2, text="—", font=F_NUM,
                                  fg=C_ACCENT, bg=C_BG)
        self._pct_lbl.pack(side="right")

        self._desc_lbl = tk.Label(sec2, text="Pick a window to begin",
                                   font=F_SMALL, fg=C_MUTED, bg=C_BG)
        self._desc_lbl.pack(anchor="w", pady=(2, 10))

        self._slider_var = tk.IntVar(value=70)
        self._slider = ttk.Scale(sec2, from_=10, to=100,
                                  orient="horizontal",
                                  variable=self._slider_var,
                                  command=self._on_slider,
                                  style="Flat.Horizontal.TScale")
        self._slider.pack(fill="x", pady=(0, 12))
        self._slider.state(["disabled"])

        # Preset pills
        pills = tk.Frame(sec2, bg=C_BG)
        pills.pack(fill="x", pady=(0, 14))
        for lbl, val, accent in [
            ("Ghost · 20%",  20, "#1e3050"),
            ("Half · 50%",   50, "#1e3050"),
            ("Focus · 70%",  70, C_ACCENT),
            ("Solid · 100%", 100, C_RAISED),
        ]:
            b = tk.Button(pills, text=lbl,
                          bg=accent, fg=C_TEXT if accent != C_RAISED else C_MUTED,
                          font=F_SMALL, relief="flat", borderwidth=0,
                          padx=0, pady=7, cursor="hand2",
                          activebackground=C_ACCENTD,
                          activeforeground=C_TEXT,
                          highlightthickness=0,
                          command=lambda v=val: self._apply_preset(v))
            b.pack(side="left", expand=True, fill="x", padx=2)

        # Action row
        act = tk.Frame(sec2, bg=C_BG)
        act.pack(fill="x")

        self._apply_btn = _btn(act, "Apply", self._apply_current,
                                bg=C_ACCENT, fg=C_TEXT, font=F_BODYM,
                                padx=24, pady=9, state="disabled")
        self._apply_btn.pack(side="left")

        self._restore_btn = _btn(act, "Restore solid", self._restore_current,
                                  bg=C_RAISED, fg=C_MUTED, font=F_BODY,
                                  padx=18, pady=9, state="disabled")
        self._restore_btn.pack(side="left", padx=8)

        self._restore_all_btn = _btn(act, "Restore all", self._restore_all,
                                      bg=C_RAISED, fg=C_DANGER, font=F_BODY,
                                      padx=18, pady=9)
        self._restore_all_btn.pack(side="right")

        # ── Divider ─────────────────────────────────────────────────────────
        tk.Frame(r, bg=C_BORDER, height=1).pack(fill="x", padx=22)

        # ── Active list (scrollable) ─────────────────────────────────────────
        sec3 = tk.Frame(r, bg=C_BG, padx=22, pady=16)
        sec3.pack(fill="both", expand=True)

        hdr3 = tk.Frame(sec3, bg=C_BG)
        hdr3.pack(fill="x")
        tk.Label(hdr3, text="Active", font=F_H2, fg=C_TEXT, bg=C_BG).pack(side="left")
        self._active_count = tk.Label(hdr3, text="", font=F_SMALL, fg=C_MUTED, bg=C_BG)
        self._active_count.pack(side="right")
        tk.Label(sec3, text="Currently transparent windows",
                 font=F_SMALL, fg=C_MUTED, bg=C_BG).pack(anchor="w", pady=(1, 8))

        # Scrollable container — shows at least 5 rows, scrolls if more
        list_outer = tk.Frame(sec3, bg=C_BG)
        list_outer.pack(fill="both", expand=True)

        self._list_canvas = tk.Canvas(list_outer, bg=C_BG, highlightthickness=0,
                                      bd=0, height=240)
        self._list_canvas.pack(side="left", fill="both", expand=True)

        _vsb = tk.Scrollbar(list_outer, orient="vertical",
                            command=self._list_canvas.yview,
                            bg=C_RAISED, troughcolor=C_BG,
                            relief="flat", borderwidth=0)
        _vsb.pack(side="right", fill="y")
        self._list_canvas.configure(yscrollcommand=_vsb.set)

        self._active_frame = tk.Frame(self._list_canvas, bg=C_BG)
        self._active_frame_id = self._list_canvas.create_window(
            (0, 0), window=self._active_frame, anchor="nw")

        def _on_frame_configure(event):
            self._list_canvas.configure(scrollregion=self._list_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self._list_canvas.itemconfig(self._active_frame_id, width=event.width)

        self._active_frame.bind("<Configure>", _on_frame_configure)
        self._list_canvas.bind("<Configure>", _on_canvas_configure)

        # Mousewheel scroll
        def _on_mousewheel(event):
            self._list_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self._list_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._refresh_windows()
        self._update_active_list()
        self._schedule_refresh()

    # ── Internals ──────────────────────────────────────────────────────────────
    def _schedule_refresh(self):
        self._update_active_list()
        self.root.after(2000, self._schedule_refresh)

    def _refresh_windows(self):
        self._windows = get_visible_windows()
        titles = [t for _, t in self._windows]
        self._combo["values"] = titles
        if self._win_var.get() not in titles:
            self._win_var.set("")

    def _get_selected_hwnd(self):
        title = self._win_var.get()
        for hwnd, t in self._windows:
            if t == title:
                return hwnd, title
        return None, None

    def _on_window_selected(self, event=None):
        hwnd, title = self._get_selected_hwnd()
        if hwnd is None:
            return
        pct = self.app.active.get(hwnd,
              self.app.config["windows"].get(title, 70))
        self._slider_var.set(pct)
        self._pct_lbl.config(text=f"{pct}%")
        self._desc_lbl.config(text=_opacity_desc(pct))
        self._slider.state(["!disabled"])
        self._apply_btn.config(state="normal")
        self._restore_btn.config(state="normal")

    def _on_slider(self, val):
        v = int(float(val))
        self._pct_lbl.config(text=f"{v}%")
        self._desc_lbl.config(text=_opacity_desc(v))
        hwnd, title = self._get_selected_hwnd()
        if hwnd:
            set_opacity(hwnd, v)
            self.app.active[hwnd] = v
            self.app.config["windows"][title] = v
            save_config(self.app.config)
            self.app._refresh_tray()
            self._update_active_list()

    def _apply_preset(self, val):
        hwnd, title = self._get_selected_hwnd()
        if hwnd is None:
            return
        self._slider_var.set(val)
        self._pct_lbl.config(text=f"{val}%")
        self._desc_lbl.config(text=_opacity_desc(val))
        set_opacity(hwnd, val)
        self.app.active[hwnd] = val
        self.app.config["windows"][title] = val
        save_config(self.app.config)
        self.app._refresh_tray()
        self._update_active_list()

    def _apply_current(self):
        hwnd, title = self._get_selected_hwnd()
        if hwnd is None:
            return
        pct = self._slider_var.get()
        set_opacity(hwnd, pct)
        self.app.active[hwnd] = pct
        self.app.config["windows"][title] = pct
        save_config(self.app.config)
        self.app._refresh_tray()
        self._update_active_list()

    def _restore_current(self):
        hwnd, _ = self._get_selected_hwnd()
        if hwnd is None:
            return
        reset_opacity(hwnd)
        self.app.active.pop(hwnd, None)
        self.app._refresh_tray()
        self._slider.state(["disabled"])
        self._apply_btn.config(state="disabled")
        self._restore_btn.config(state="disabled")
        self._pct_lbl.config(text="—")
        self._desc_lbl.config(text="Window restored to solid")
        self._update_active_list()

    def _restore_all(self):
        self.app._restore_all()
        self._slider.state(["disabled"])
        self._apply_btn.config(state="disabled")
        self._restore_btn.config(state="disabled")
        self._pct_lbl.config(text="—")
        self._desc_lbl.config(text="All windows restored")
        self._update_active_list()

    def _update_active_list(self):
        for w in self._active_frame.winfo_children():
            w.destroy()

        count = len(self.app.active)
        if hasattr(self, "_active_count"):
            self._active_count.config(
                text=f"{count} window{'s' if count != 1 else ''}" if count else "")

        if not self.app.active:
            tk.Label(self._active_frame,
                     text="No transparent windows yet",
                     font=F_SMALL, fg=C_DIM, bg=C_BG,
                     pady=20).pack(expand=True)
            return

        for hwnd, pct in list(self.app.active.items()):
            title = win32gui.GetWindowText(hwnd)
            if not title:
                continue

            card = tk.Frame(self._active_frame, bg=C_SURFACE,
                            pady=0, highlightthickness=1,
                            highlightbackground=C_BORDER)
            card.pack(fill="x", pady=3)

            # left accent bar (width scales with opacity)
            bar_w = max(3, int(pct / 100 * 5))
            tk.Frame(card, bg=C_ACCENT, width=bar_w).pack(side="left", fill="y")

            inner = tk.Frame(card, bg=C_SURFACE)
            inner.pack(side="left", fill="both", expand=True, padx=12, pady=8)

            tk.Label(inner, text=title[:44] + ("…" if len(title) > 44 else ""),
                     font=F_BODY, fg=C_TEXT, bg=C_SURFACE,
                     anchor="w").pack(side="left")

            right_side = tk.Frame(card, bg=C_SURFACE)
            right_side.pack(side="right", padx=10, pady=6)

            tk.Label(right_side, text=f"{pct}%",
                     font=F_BODYM, fg=C_ACCENT,
                     bg=C_SURFACE).pack(side="left", padx=(0, 8))

            def make_restore(h):
                def _r():
                    reset_opacity(h)
                    self.app.active.pop(h, None)
                    self.app._refresh_tray()
                    self._update_active_list()
                return _r

            _btn(right_side, "✕", make_restore(hwnd),
                 bg=C_SURFACE, fg=C_MUTED, font=F_SMALL,
                 padx=8, pady=3).pack(side="left")

    def _on_close(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._refresh_windows()

    def run(self):
        self.root.mainloop()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = OpacityApp()

    real_state = get_autostart()
    if real_state != app.config.get("autostart", False):
        app.config["autostart"] = real_state
        save_config(app.config)

    is_exe  = getattr(sys, "frozen", False)
    show_ui = is_exe or "--ui" in sys.argv

    icon = pystray.Icon(APP_NAME, _make_icon(),
                        "Opacity Controller", app._build_menu())
    app.tray_icon = icon

    if show_ui:
        ui = MainUI(app)

        def open_ui(ico, item):
            ui.root.after(0, ui.show)

        icon.menu = pystray.Menu(
            pystray.MenuItem("Open", open_ui, default=True),
            *list(app._build_menu().items)
        )
        app.tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()
        ui.run()
    else:
        print("Opacity Controller v2.0")
        print(f"  {app._hotkey}        toggle on focused window")
        print("  Alt+Up/Down   adjust opacity 5%")
        print("  Tray icon     right-click for all options")
        print("  --ui flag     open the full UI window")
        icon.run()