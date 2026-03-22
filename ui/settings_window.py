"""
ui/settings_window.py — Settings dialog (singleton).
Trying to open a second instance flashes + dings the existing one.
"""

import threading
import tkinter as tk

try:
    import keyboard
except ImportError:
    pass

import win32gui
from win32_utils import flash_window, play_alert_sound
from autostart import set_autostart
from config import save_config
from ui.theme import (
    BG, SURFACE, RAISED, BORDER, ACCENT,
    SUCCESS, DANGER, TEXT, MUTED,
    F_H1, F_H2, F_BODY, F_BODYM, F_SMALL,
    btn, accent_stripe,
)


class SettingsWindow:
    _instance = None

    @classmethod
    def open(cls, app) -> None:
        if cls._instance is not None:
            try:
                w    = cls._instance.win
                hwnd = win32gui.FindWindowW(None, "Settings — Opacity Controller")
                if hwnd:
                    flash_window(hwnd, count=4)
                    play_alert_sound()
                w.deiconify()
                w.lift()
                w.focus_force()
                return
            except Exception:
                cls._instance = None

        threading.Thread(target=lambda: cls(app)._run(), daemon=True).start()

    def __init__(self, app) -> None:
        self.app = app
        SettingsWindow._instance = self
        self.win = tk.Tk()

    def _run(self) -> None:
        app = self.app
        win = self.win
        win.title("Settings — Opacity Controller")
        win.geometry("560x600")
        win.minsize(560, 600)
        win.configure(bg=BG)
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self._close)

        # Header
        hdr = tk.Frame(win, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Settings", font=F_H1,
                 fg=TEXT, bg=SURFACE).pack(side="left", padx=28, pady=20)
        tk.Label(hdr, text="Opacity Controller", font=F_SMALL,
                 fg=MUTED, bg=SURFACE).pack(side="right", padx=28)
        accent_stripe(win)

        body = tk.Frame(win, bg=BG, padx=32, pady=24)
        body.pack(fill="both", expand=True)

        # ── Hotkey section ───────────────────────────────────────────────────
        tk.Label(body, text="Keyboard shortcut", font=F_H2,
                 fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(body,
                 text="This hotkey toggles transparency on whichever window is in focus.",
                 font=F_SMALL, fg=MUTED, bg=BG,
                 wraplength=480, justify="left").pack(anchor="w", pady=(4, 14))

        hk_var    = tk.StringVar(value=app.config.get("hotkey", "alt+t"))
        recording = [False]

        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=(0, 4))
        tk.Label(row, text="Current shortcut",
                 font=F_SMALL, fg=MUTED, bg=BG).pack(side="left")
        saved_lbl = tk.Label(row, text="", font=F_SMALL, fg=SUCCESS, bg=BG)
        saved_lbl.pack(side="right")

        hk_box = tk.Frame(body, bg=SURFACE, highlightthickness=1,
                          highlightbackground=BORDER)
        hk_box.pack(fill="x")
        hk_entry = tk.Entry(hk_box, textvariable=hk_var,
                            bg=SURFACE, fg=ACCENT, insertbackground=ACCENT,
                            font=("Segoe UI", 14, "bold"),
                            relief="flat", borderwidth=0,
                            justify="center", highlightthickness=0)
        hk_entry.pack(fill="x", ipady=12, padx=16)

        hint = tk.Label(body,
                        text="Click the field above, then press your desired combination",
                        font=F_SMALL, fg=MUTED, bg=BG)
        hint.pack(anchor="w", pady=(8, 0))

        def start_record(event):
            recording[0] = True
            hk_var.set("")
            hint.config(text="Listening…  press your combo now", fg=ACCENT)
            hk_box.config(highlightbackground=ACCENT)
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
            hk_box.config(highlightbackground=BORDER)
            new_hk = hk_var.get().strip()
            if not new_hk:
                hk_var.set(app.config.get("hotkey", "alt+t"))
                hint.config(text="Nothing recorded — previous shortcut kept", fg=DANGER)
                app._hk.register()
                return
            try:
                keyboard.add_hotkey(new_hk, lambda: None)
                keyboard.remove_hotkey(new_hk)
                app.set_hotkey(new_hk)
                hint.config(text=f"Saved  ·  {new_hk}", fg=SUCCESS)
                saved_lbl.config(text="✓ Saved")
            except Exception:
                hk_var.set(app.config.get("hotkey", "alt+t"))
                hint.config(text="Invalid combination — previous shortcut kept", fg=DANGER)
                app._hk.register()

        def on_key(event):
            if not recording[0]:
                return
            parts = []
            if event.state & 0x4: parts.append("ctrl")
            if event.state & 0x1: parts.append("shift")
            if event.state & 0x8: parts.append("alt")
            key = event.keysym.lower()
            if key not in ("control_l", "control_r", "shift_l", "shift_r",
                           "alt_l", "alt_r", "super_l", "super_r"):
                parts.append(key)
            hk_var.set("+".join(parts) if parts else "")

        hk_entry.bind("<FocusIn>",  start_record)
        hk_entry.bind("<FocusOut>", stop_record)
        hk_entry.bind("<KeyPress>", on_key)

        # ── Startup section ──────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(24, 20))
        tk.Label(body, text="Startup", font=F_H2, fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(body, text="Run Opacity Controller when Windows starts.",
                 font=F_SMALL, fg=MUTED, bg=BG).pack(anchor="w", pady=(4, 12))

        as_frame = tk.Frame(body, bg=SURFACE, highlightthickness=1,
                            highlightbackground=BORDER)
        as_frame.pack(fill="x")
        as_var = tk.BooleanVar(value=app.config.get("autostart", False))
        tk.Checkbutton(as_frame,
                       text="  Launch automatically on Windows startup",
                       variable=as_var,
                       bg=SURFACE, fg=TEXT, selectcolor=RAISED,
                       activebackground=SURFACE, activeforeground=TEXT,
                       font=F_BODY, cursor="hand2",
                       highlightthickness=0, relief="flat",
                       command=lambda: self._toggle_autostart(as_var.get())
                       ).pack(anchor="w", padx=12, pady=12)

        # ── Hotkey reference ─────────────────────────────────────────────────
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(20, 16))
        tk.Label(body, text="Hotkey reference", font=F_H2,
                 fg=TEXT, bg=BG).pack(anchor="w")
        refs = [
            (app.config.get("hotkey","alt+t"), "Toggle on focused window"),
            ("Alt + ↑ / ↓",                   "Nudge opacity ±5%"),
            ("Alt + 1–9",                      "Set opacity 10%–90%"),
            ("Alt + 0",                        "Restore to fully solid"),
        ]
        rf = tk.Frame(body, bg=BG)
        rf.pack(fill="x", pady=(8, 0))
        for hk_text, desc in refs:
            r2 = tk.Frame(rf, bg=BG)
            r2.pack(fill="x", pady=2)
            tk.Label(r2, text=hk_text, font=("Segoe UI", 9, "bold"),
                     fg=ACCENT, bg=BG, width=16, anchor="w").pack(side="left")
            tk.Label(r2, text=desc, font=F_SMALL,
                     fg=MUTED, bg=BG).pack(side="left", padx=(8, 0))

        # ── Footer ───────────────────────────────────────────────────────────
        tk.Frame(win, bg=BORDER, height=1).pack(fill="x")
        foot = tk.Frame(win, bg=SURFACE)
        foot.pack(fill="x")
        btn(foot, "Close", self._close,
            bg=ACCENT, fg=TEXT, font=F_BODYM,
            padx=40, pady=14).pack(side="right", padx=20, pady=14)

        win.mainloop()

    def _toggle_autostart(self, enable: bool) -> None:
        if set_autostart(enable):
            self.app.config["autostart"] = enable
            save_config(self.app.config)
            if self.app.tray:
                self.app.tray.refresh()

    def _close(self) -> None:
        SettingsWindow._instance = None
        self.win.destroy()
