"""
Opacity Controller — Windows per-window transparency tool
Run: python main.py
Hotkey: Alt+T  →  toggle opacity on the currently focused window
Tray:   right-click icon  →  pick any open window and set opacity
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk

# ── Win32 imports ──────────────────────────────────────────────────────────────
try:
    import win32gui
    import win32con
    import win32api
    import win32process
except ImportError:
    sys.exit("pywin32 not found. Run:  pip install pywin32")

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("pystray / Pillow not found. Run:  pip install pystray pillow")

try:
    import keyboard
except ImportError:
    sys.exit("keyboard not found. Run:  pip install keyboard")


# ── Config ─────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "opacity_config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(config: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[config] Save failed: {e}")


# ── Win32 helpers ──────────────────────────────────────────────────────────────
def set_opacity(hwnd: int, percent: int):
    """Make a window semi-transparent. percent: 10–100"""
    percent = max(10, min(100, percent))
    alpha = int(percent / 100 * 255)
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)
    except Exception as e:
        print(f"[win32] set_opacity failed for hwnd {hwnd}: {e}")

def reset_opacity(hwnd: int):
    """Remove transparency — restore window to fully solid."""
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style & ~win32con.WS_EX_LAYERED)
    except Exception as e:
        print(f"[win32] reset_opacity failed for hwnd {hwnd}: {e}")

def get_visible_windows() -> list[tuple[int, str]]:
    """Return list of (hwnd, title) for all visible, titled windows."""
    results = []

    # Windows to skip (system/shell windows)
    skip_titles = {"", "Task Switching", "Program Manager", "Windows Input Experience"}

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title in skip_titles or len(title) < 2:
            return
        results.append((hwnd, title))

    win32gui.EnumWindows(_cb, None)
    # Sort alphabetically for easy scanning
    return sorted(results, key=lambda x: x[1].lower())


# ── UI ─────────────────────────────────────────────────────────────────────────
# Dark theme colours
BG      = "#141414"
BG2     = "#1e1e1e"
BG3     = "#2a2a2a"
ACCENT  = "#3b82f6"   # blue
FG      = "#e0e0e0"
FG2     = "#888888"
WHITE   = "#ffffff"

def _apply_dark(widget):
    """Recursively set dark bg/fg on tk widgets."""
    try:
        cls = widget.winfo_class()
        if cls in ("Frame", "Toplevel", "Tk"):
            widget.configure(bg=BG)
        elif cls == "Label":
            widget.configure(bg=BG, fg=FG)
        elif cls == "Button":
            widget.configure(bg=BG3, fg=FG, relief="flat",
                             activebackground=ACCENT, activeforeground=WHITE,
                             cursor="hand2")
        elif cls == "Listbox":
            widget.configure(bg=BG2, fg=FG, selectbackground=ACCENT,
                             selectforeground=WHITE, borderwidth=0,
                             highlightthickness=0)
        elif cls == "Scrollbar":
            widget.configure(bg=BG3, troughcolor=BG2, relief="flat",
                             borderwidth=0)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        _apply_dark(child)


class OpacityApp:
    def __init__(self):
        self.config: dict = load_config()          # title -> saved opacity %
        self.toggle_map: dict[int, bool] = {}       # hwnd -> is_transparent

    # ── hotkey ────────────────────────────────────────────────────────────────
    def on_hotkey(self):
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return

        currently_on = self.toggle_map.get(hwnd, False)
        if currently_on:
            reset_opacity(hwnd)
            self.toggle_map[hwnd] = False
            print(f"[hotkey] Restored: {title}")
        else:
            pct = self.config.get(title, 70)
            set_opacity(hwnd, pct)
            self.toggle_map[hwnd] = True
            print(f"[hotkey] Made transparent ({pct}%): {title}")

    # ── window picker ─────────────────────────────────────────────────────────
    def show_picker(self, icon=None, item=None):
        """Tray menu → 'Select Window…' opens this."""
        threading.Thread(target=self._picker_thread, daemon=True).start()

    def _picker_thread(self):
        windows = get_visible_windows()

        root = tk.Tk()
        root.title("Opacity Controller")
        root.geometry("420x520")
        root.configure(bg=BG)
        root.attributes("-topmost", True)
        root.resizable(False, True)

        # Header
        hdr = tk.Frame(root, bg=BG, padx=20, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Opacity Controller",
                 bg=BG, fg=WHITE,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Double-click a window to control its transparency",
                 bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 0))

        # Search box
        search_frame = tk.Frame(root, bg=BG2, padx=12, pady=0)
        search_frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(search_frame, text="🔍", bg=BG2, fg=FG2,
                 font=("Segoe UI", 10)).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var,
                               bg=BG2, fg=FG, insertbackground=FG,
                               font=("Segoe UI", 10), relief="flat",
                               borderwidth=6)
        search_entry.pack(side="left", fill="x", expand=True)

        # Listbox
        list_frame = tk.Frame(root, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=16)

        sb = tk.Scrollbar(list_frame)
        sb.pack(side="right", fill="y")

        lb = tk.Listbox(list_frame, yscrollcommand=sb.set,
                        bg=BG2, fg=FG,
                        selectbackground=ACCENT, selectforeground=WHITE,
                        font=("Segoe UI", 10),
                        borderwidth=0, highlightthickness=0,
                        activestyle="none", cursor="hand2")
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)

        # Populate list
        def refresh_list(*_):
            q = search_var.get().lower()
            lb.delete(0, "end")
            for hwnd, title in windows:
                if q in title.lower():
                    saved = self.config.get(title)
                    tag = f"  [{saved}%]" if saved else ""
                    disp = title[:52] + ("…" if len(title) > 52 else "")
                    lb.insert("end", disp + tag)

        search_var.trace_add("write", refresh_list)
        refresh_list()

        # Open slider on double-click
        def on_select(event=None):
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            # re-filter to get correct index
            q = search_var.get().lower()
            filtered = [(h, t) for h, t in windows if q in t.lower()]
            if idx >= len(filtered):
                return
            hwnd, title = filtered[idx]
            root.destroy()
            self._slider_thread(hwnd, title)

        lb.bind("<Double-Button-1>", on_select)

        # Bottom button
        btn_frame = tk.Frame(root, bg=BG, padx=16, pady=12)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="  Control Opacity →  ",
                  bg=ACCENT, fg=WHITE,
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=16, pady=8,
                  cursor="hand2",
                  command=on_select).pack(side="right")
        tk.Label(btn_frame, text="or double-click",
                 bg=BG, fg=FG2,
                 font=("Segoe UI", 9)).pack(side="right", padx=8)

        root.mainloop()

    # ── opacity slider ────────────────────────────────────────────────────────
    def _slider_thread(self, hwnd: int, title: str):
        saved_pct = self.config.get(title, 70)

        win = tk.Tk()
        win.title("Set Opacity")
        win.geometry("380x300")
        win.configure(bg=BG)
        win.attributes("-topmost", True)
        win.resizable(False, False)

        # Title
        hdr = tk.Frame(win, bg=BG, padx=20, pady=14)
        hdr.pack(fill="x")
        short = title[:38] + ("…" if len(title) > 38 else "")
        tk.Label(hdr, text=short, bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(hdr, text="Drag the slider to set transparency",
                 bg=BG, fg=FG2, font=("Segoe UI", 9)).pack(anchor="w")

        # Big % display
        pct_var = tk.IntVar(value=saved_pct)
        pct_label = tk.Label(win, text=f"{saved_pct}%",
                             bg=BG, fg=WHITE,
                             font=("Segoe UI", 42, "bold"))
        pct_label.pack(pady=(8, 0))

        desc_label = tk.Label(win, text=_opacity_desc(saved_pct),
                              bg=BG, fg=FG2, font=("Segoe UI", 9))
        desc_label.pack()

        # Slider
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Horizontal.TScale",
                        background=BG, troughcolor=BG3,
                        sliderlength=20, sliderrelief="flat")

        def on_change(val):
            v = int(float(val))
            pct_label.config(text=f"{v}%")
            desc_label.config(text=_opacity_desc(v))
            set_opacity(hwnd, v)
            self.config[title] = v
            self.toggle_map[hwnd] = True
            save_config(self.config)

        slider = ttk.Scale(win, from_=10, to=100,
                          orient="horizontal",
                          variable=pct_var,
                          command=on_change,
                          style="Custom.Horizontal.TScale",
                          length=300)
        slider.pack(pady=12, padx=40)

        # Apply immediately
        set_opacity(hwnd, saved_pct)
        self.toggle_map[hwnd] = True

        # Presets
        pf = tk.Frame(win, bg=BG)
        pf.pack(pady=4)
        for label, val in [("Ghost\n20%", 20), ("See-through\n50%", 50),
                           ("Focus\n70%", 70), ("Solid\n100%", 100)]:
            tk.Button(pf, text=label,
                     bg=BG3, fg=FG,
                     font=("Segoe UI", 8),
                     relief="flat", padx=10, pady=5, width=8, cursor="hand2",
                     command=lambda v=val: [pct_var.set(v), on_change(v)]
                     ).pack(side="left", padx=3)

        # Buttons
        bf = tk.Frame(win, bg=BG, pady=10)
        bf.pack(fill="x", padx=20)

        def do_reset():
            reset_opacity(hwnd)
            self.toggle_map[hwnd] = False
            win.destroy()

        tk.Button(bf, text="Reset to Solid",
                 bg=BG3, fg=FG2,
                 font=("Segoe UI", 9), relief="flat",
                 padx=12, pady=6, cursor="hand2",
                 command=do_reset).pack(side="left")

        tk.Button(bf, text="Done",
                 bg=ACCENT, fg=WHITE,
                 font=("Segoe UI", 9, "bold"),
                 relief="flat", padx=20, pady=6, cursor="hand2",
                 command=win.destroy).pack(side="right")

        win.mainloop()


def _opacity_desc(pct: int) -> str:
    if pct <= 25:  return "Ghost — barely visible"
    if pct <= 45:  return "See-through — content visible behind"
    if pct <= 65:  return "Translucent — comfortable overlap"
    if pct <= 85:  return "Focus mode — slight transparency"
    if pct <= 95:  return "Nearly solid"
    return "Fully solid"


# ── Tray icon ──────────────────────────────────────────────────────────────────
def _make_tray_icon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Outer square
    d.rectangle([4, 4, 59, 59], outline=(255, 255, 255, 220), width=3)
    # Inner square (offset — gives the "transparency" feel)
    d.rectangle([14, 14, 49, 49], fill=(59, 130, 246, 160))
    # Diagonal lines suggest transparency
    for i in range(0, 60, 10):
        d.line([(4, 4 + i), (4 + i, 4)], fill=(255, 255, 255, 60), width=1)
    return img


def build_tray(app: OpacityApp):
    image = _make_tray_icon()
    menu = pystray.Menu(
        pystray.MenuItem("Select Window…", app.show_picker),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda icon, item: (icon.stop(), os._exit(0))),
    )
    icon = pystray.Icon("OpacityCtrl", image, "Opacity Controller", menu)
    return icon


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = OpacityApp()

    # Register global hotkey Alt+T
    keyboard.add_hotkey("alt+t", app.on_hotkey, suppress=False)
    print("Opacity Controller started.")
    print("→ Right-click the tray icon to pick a window")
    print("→ Alt+T  toggles transparency on the focused window")

    tray = build_tray(app)
    tray.run()   # blocks — keyboard hotkey runs on its own thread
