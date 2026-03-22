"""
ui/main_window.py — Main application window.
"""

import tkinter as tk
from tkinter import ttk

from win32_utils import (
    set_opacity, reset_opacity,
    set_always_on_top,
    get_visible_windows, get_window_title,
    opacity_desc,
)
from config import save_config
from ui.theme import (
    BG, SURFACE, RAISED, BORDER, ACCENT, ACCENT_H,
    SUCCESS, DANGER, TEXT, MUTED, DIM,
    F_H1, F_H2, F_BODY, F_BODYM, F_SMALL, F_NUM,
    btn, accent_stripe, apply_ttk_styles,
)


class MainUI:
    def __init__(self, app) -> None:
        self.app      = app
        self._windows = []
        self.root     = tk.Tk()
        apply_ttk_styles(self.root)
        self._build()

    def _build(self) -> None:
        r = self.root
        r.title("Opacity Controller")
        r.geometry("600x860")
        r.minsize(520, 700)
        r.configure(bg=BG)
        r.resizable(True, True)
        r.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(r, bg=SURFACE)
        hdr.pack(fill="x")

        left = tk.Frame(hdr, bg=SURFACE)
        left.pack(side="left", padx=22, pady=18)
        tk.Label(left, text="Opacity Controller",
                 font=F_H1, fg=TEXT, bg=SURFACE).pack(anchor="w")
        self._hk_lbl = tk.Label(left,
                                  text=f"Hotkey  ·  {self.app.config.get('hotkey','alt+t')}",
                                  font=F_SMALL, fg=MUTED, bg=SURFACE)
        self._hk_lbl.pack(anchor="w", pady=(2, 0))

        right = tk.Frame(hdr, bg=SURFACE)
        right.pack(side="right", padx=16, pady=14)
        btn(right, "Settings", lambda: self.app.show_settings(),
            bg=RAISED, fg=MUTED, font=F_SMALL, padx=14, pady=7
            ).pack(side="right", padx=(6, 0))
        btn(right, "Minimise", r.withdraw,
            bg=RAISED, fg=MUTED, font=F_SMALL, padx=14, pady=7
            ).pack(side="right")

        accent_stripe(r)

        # ── Window selector ──────────────────────────────────────────────────
        sec1 = tk.Frame(r, bg=BG, padx=22, pady=18)
        sec1.pack(fill="x")
        tk.Label(sec1, text="Window", font=F_H2, fg=TEXT, bg=BG).pack(anchor="w")
        tk.Label(sec1, text="Select the window you want to control",
                 font=F_SMALL, fg=MUTED, bg=BG).pack(anchor="w", pady=(1, 8))

        row = tk.Frame(sec1, bg=BG)
        row.pack(fill="x")
        self._win_var = tk.StringVar()
        self._combo   = ttk.Combobox(row, textvariable=self._win_var,
                                      font=F_BODY, state="readonly",
                                      style="Flat.TCombobox", height=14)
        self._combo.pack(side="left", fill="x", expand=True, ipady=5)
        self._combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        btn(row, "↻", self._refresh_windows,
            bg=SURFACE, fg=MUTED, font=("Segoe UI", 13),
            padx=10, pady=5).pack(side="left", padx=(8, 0))

        tk.Frame(r, bg=BORDER, height=1).pack(fill="x", padx=22)

        # ── Opacity control ──────────────────────────────────────────────────
        sec2 = tk.Frame(r, bg=BG, padx=22, pady=18)
        sec2.pack(fill="x")

        top_row = tk.Frame(sec2, bg=BG)
        top_row.pack(fill="x")
        tk.Label(top_row, text="Opacity", font=F_H2,
                 fg=TEXT, bg=BG).pack(side="left")
        self._pct_lbl = tk.Label(top_row, text="—", font=F_NUM,
                                   fg=ACCENT, bg=BG)
        self._pct_lbl.pack(side="right")

        self._desc_lbl = tk.Label(sec2, text="Pick a window to begin",
                                   font=F_SMALL, fg=MUTED, bg=BG)
        self._desc_lbl.pack(anchor="w", pady=(2, 10))

        self._slider_var = tk.IntVar(value=70)
        self._slider     = ttk.Scale(sec2, from_=10, to=100,
                                      orient="horizontal",
                                      variable=self._slider_var,
                                      command=self._on_slider,
                                      style="Flat.Horizontal.TScale")
        self._slider.pack(fill="x", pady=(0, 12))
        self._slider.state(["disabled"])

        # Preset pills
        pills = tk.Frame(sec2, bg=BG)
        pills.pack(fill="x", pady=(0, 14))
        for label, val, color in [
            ("Ghost · 20%",   20, "#1e3050"),
            ("Half · 50%",    50, "#1e3050"),
            ("Focus · 70%",   70, ACCENT),
            ("Solid · 100%", 100, RAISED),
        ]:
            tk.Button(pills, text=label,
                      bg=color, fg=TEXT if color != RAISED else MUTED,
                      font=F_SMALL, relief="flat", borderwidth=0,
                      padx=0, pady=7, cursor="hand2",
                      activebackground=ACCENT_H, activeforeground=TEXT,
                      highlightthickness=0,
                      command=lambda v=val: self._apply_preset(v)
                      ).pack(side="left", expand=True, fill="x", padx=2)

        # Action buttons
        act = tk.Frame(sec2, bg=BG)
        act.pack(fill="x")
        self._apply_btn = btn(act, "Apply", self._apply_current,
                               bg=ACCENT, fg=TEXT, font=F_BODYM,
                               padx=24, pady=9, state="disabled")
        self._apply_btn.pack(side="left")
        self._restore_btn = btn(act, "Restore solid", self._restore_current,
                                 bg=RAISED, fg=MUTED, font=F_BODY,
                                 padx=18, pady=9, state="disabled")
        self._restore_btn.pack(side="left", padx=8)
        self._restore_all_btn = btn(act, "Restore all", self._restore_all,
                                     bg=RAISED, fg=DANGER, font=F_BODY,
                                     padx=18, pady=9)
        self._restore_all_btn.pack(side="right")

        # Always on top toggle
        self._aot_var = tk.BooleanVar(value=False)
        tk.Checkbutton(sec2,
                       text="  Pin on top (always on top)",
                       variable=self._aot_var,
                       bg=BG, fg=MUTED, selectcolor=RAISED,
                       activebackground=BG, activeforeground=TEXT,
                       font=F_SMALL, cursor="hand2",
                       highlightthickness=0, relief="flat",
                       command=self._toggle_aot
                       ).pack(anchor="w", pady=(10, 0))

        tk.Frame(r, bg=BORDER, height=1).pack(fill="x", padx=22)

        # ── Active list (scrollable) ─────────────────────────────────────────
        sec3 = tk.Frame(r, bg=BG, padx=22, pady=16)
        sec3.pack(fill="both", expand=True)

        hdr3 = tk.Frame(sec3, bg=BG)
        hdr3.pack(fill="x")
        tk.Label(hdr3, text="Active", font=F_H2,
                 fg=TEXT, bg=BG).pack(side="left")
        self._count_lbl = tk.Label(hdr3, text="",
                                    font=F_SMALL, fg=MUTED, bg=BG)
        self._count_lbl.pack(side="right")
        tk.Label(sec3, text="Currently transparent windows",
                 font=F_SMALL, fg=MUTED, bg=BG).pack(anchor="w", pady=(1, 8))

        outer = tk.Frame(sec3, bg=BG)
        outer.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(outer, bg=BG, highlightthickness=0,
                                  bd=0, height=240)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb = tk.Scrollbar(outer, orient="vertical",
                           command=self._canvas.yview,
                           bg=RAISED, troughcolor=BG,
                           relief="flat", borderwidth=0)
        vsb.pack(side="right", fill="y")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._list_frame = tk.Frame(self._canvas, bg=BG)
        self._fid = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")
        self._list_frame.bind("<Configure>", lambda e:
            self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e:
            self._canvas.itemconfig(self._fid, width=e.width))
        self._canvas.bind_all("<MouseWheel>", lambda e:
            self._canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._refresh_windows()
        self.refresh_active_list()
        self._schedule_refresh()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _schedule_refresh(self) -> None:
        self.refresh_active_list()
        self.root.after(2000, self._schedule_refresh)

    def _refresh_windows(self) -> None:
        self._windows = get_visible_windows()
        titles = [t for _, t in self._windows]
        self._combo["values"] = titles
        if self._win_var.get() not in titles:
            self._win_var.set("")

    def _get_selected(self):
        title = self._win_var.get()
        for hwnd, t in self._windows:
            if t == title:
                return hwnd, title
        return None, None

    def _on_window_selected(self, event=None) -> None:
        hwnd, title = self._get_selected()
        if hwnd is None:
            return
        pct = self.app.active.get(hwnd,
              self.app.config["windows"].get(title, 70))
        self._slider_var.set(pct)
        self._pct_lbl.config(text=f"{pct}%")
        self._desc_lbl.config(text=opacity_desc(pct))
        self._slider.state(["!disabled"])
        self._apply_btn.config(state="normal")
        self._restore_btn.config(state="normal")
        self._aot_var.set(self.app.on_top.get(hwnd, False))

    def _on_slider(self, val) -> None:
        v = int(float(val))
        self._pct_lbl.config(text=f"{v}%")
        self._desc_lbl.config(text=opacity_desc(v))
        hwnd, title = self._get_selected()
        if hwnd:
            self.app._apply(hwnd, title, v)

    def _apply_preset(self, val: int) -> None:
        hwnd, title = self._get_selected()
        if hwnd is None:
            return
        self._slider_var.set(val)
        self._pct_lbl.config(text=f"{val}%")
        self._desc_lbl.config(text=opacity_desc(val))
        self.app._apply(hwnd, title, val)

    def _apply_current(self) -> None:
        hwnd, title = self._get_selected()
        if hwnd is None:
            return
        self.app._apply(hwnd, title, self._slider_var.get())

    def _restore_current(self) -> None:
        hwnd, _ = self._get_selected()
        if hwnd is None:
            return
        self.app.restore_window(hwnd)
        self._slider.state(["disabled"])
        self._apply_btn.config(state="disabled")
        self._restore_btn.config(state="disabled")
        self._pct_lbl.config(text="—")
        self._desc_lbl.config(text="Window restored to solid")
        self._aot_var.set(False)

    def _restore_all(self) -> None:
        self.app.restore_all()
        self._slider.state(["disabled"])
        self._apply_btn.config(state="disabled")
        self._restore_btn.config(state="disabled")
        self._pct_lbl.config(text="—")
        self._desc_lbl.config(text="All windows restored")

    def _toggle_aot(self) -> None:
        hwnd, _ = self._get_selected()
        if hwnd is None:
            return
        desired = self._aot_var.get()
        if desired != self.app.on_top.get(hwnd, False):
            self.app.toggle_always_on_top(hwnd)

    def refresh_active_list(self) -> None:
        for w in self._list_frame.winfo_children():
            w.destroy()

        count = len(self.app.active)
        self._count_lbl.config(
            text=f"{count} window{'s' if count != 1 else ''}" if count else "")

        if not count:
            tk.Label(self._list_frame,
                     text="No transparent windows yet",
                     font=F_SMALL, fg=DIM, bg=BG, pady=20
                     ).pack(expand=True)
            return

        for hwnd, pct in list(self.app.active.items()):
            title = get_window_title(hwnd)
            if not title:
                continue
            aot  = self.app.on_top.get(hwnd, False)
            card = tk.Frame(self._list_frame, bg=SURFACE,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", pady=3)
            tk.Frame(card, bg=ACCENT,
                     width=max(3, int(pct / 100 * 5))
                     ).pack(side="left", fill="y")
            inner = tk.Frame(card, bg=SURFACE)
            inner.pack(side="left", fill="both", expand=True, padx=12, pady=8)
            title_row = tk.Frame(inner, bg=SURFACE)
            title_row.pack(fill="x")
            tk.Label(title_row,
                     text=title[:46] + ("…" if len(title) > 46 else ""),
                     font=F_BODY, fg=TEXT, bg=SURFACE, anchor="w"
                     ).pack(side="left")
            if aot:
                tk.Label(title_row, text=" 📌",
                         font=F_SMALL, fg=MUTED, bg=SURFACE
                         ).pack(side="left")
            rside = tk.Frame(card, bg=SURFACE)
            rside.pack(side="right", padx=10, pady=6)
            tk.Label(rside, text=f"{pct}%",
                     font=F_BODYM, fg=ACCENT, bg=SURFACE
                     ).pack(side="left", padx=(0, 6))

            def _make_restore(h):
                def _r(): self.app.restore_window(h)
                return _r

            btn(rside, "✕", _make_restore(hwnd),
                bg=SURFACE, fg=MUTED, font=F_SMALL,
                padx=8, pady=3).pack(side="left")

        self._list_frame.update_idletasks()
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_close(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._refresh_windows()
        self._hk_lbl.config(
            text=f"Hotkey  ·  {self.app.config.get('hotkey','alt+t')}")

    def run(self) -> None:
        self.root.mainloop()
