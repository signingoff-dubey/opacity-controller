"""
ui/theme.py — Design tokens and widget helpers.
Import everything from here. Never hardcode colours elsewhere.
"""

import tkinter as tk
from tkinter import ttk

# ── Colours ────────────────────────────────────────────────────────────────────
BG       = "#111114"
SURFACE  = "#1a1a1f"
RAISED   = "#22222a"
BORDER   = "#2e2e38"
ACCENT   = "#3b82f6"
ACCENT_H = "#2563eb"
SUCCESS  = "#22c55e"
DANGER   = "#ef4444"
TEXT     = "#f0f0f2"
MUTED    = "#7c7c8a"
DIM      = "#3a3a48"

# ── Fonts ──────────────────────────────────────────────────────────────────────
F_H1    = ("Segoe UI", 17, "bold")
F_H2    = ("Segoe UI", 11, "bold")
F_BODY  = ("Segoe UI", 10)
F_BODYM = ("Segoe UI", 10, "bold")
F_SMALL = ("Segoe UI",  9)
F_NUM   = ("Segoe UI", 30, "bold")


def apply_ttk_styles(root: tk.Tk) -> None:
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure("Flat.TCombobox",
                fieldbackground=SURFACE, background=RAISED,
                foreground=TEXT, selectbackground=ACCENT,
                selectforeground=TEXT, borderwidth=0,
                arrowcolor=MUTED, padding=(8, 6))
    s.map("Flat.TCombobox",
          fieldbackground=[("readonly", SURFACE)],
          background=[("readonly", RAISED)])
    s.configure("Flat.Horizontal.TScale",
                background=BG, troughcolor=RAISED,
                sliderlength=18, sliderrelief="flat",
                troughrelief="flat")


def btn(parent, text, cmd,
        bg=None, fg=TEXT, font=F_BODY,
        padx=18, pady=9, state="normal") -> tk.Button:
    if bg is None:
        bg = RAISED
    return tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg=fg, font=font,
        relief="flat", borderwidth=0,
        padx=padx, pady=pady,
        activebackground=ACCENT_H if bg == ACCENT else BORDER,
        activeforeground=TEXT,
        cursor="hand2", state=state,
        highlightthickness=0,
    )


def accent_stripe(parent) -> tk.Frame:
    f = tk.Frame(parent, bg=ACCENT, height=2)
    f.pack(fill="x")
    return f
