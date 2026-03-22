"""
win32_utils.py — All Windows API calls in one place.
"""

import sys
import ctypes

try:
    import win32gui
    import win32con
except ImportError:
    sys.exit("[error] pywin32 not found.  Run: pip install pywin32")


def enable_dpi_awareness() -> None:
    """Must be called before any Tk window is created."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ── Opacity ────────────────────────────────────────────────────────────────────
def set_opacity(hwnd: int, percent: int) -> None:
    percent = max(10, min(100, percent))
    alpha   = int(percent / 100 * 255)
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, 0, alpha, win32con.LWA_ALPHA)
    except Exception as e:
        print(f"[win32] set_opacity({hwnd}): {e}")


def reset_opacity(hwnd: int) -> None:
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE,
                               style & ~win32con.WS_EX_LAYERED)
    except Exception as e:
        print(f"[win32] reset_opacity({hwnd}): {e}")


# ── Always on top ──────────────────────────────────────────────────────────────
def set_always_on_top(hwnd: int, enable: bool) -> None:
    flag = win32con.HWND_TOPMOST if enable else win32con.HWND_NOTOPMOST
    try:
        win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception as e:
        print(f"[win32] set_always_on_top({hwnd}): {e}")


# ── Window list ────────────────────────────────────────────────────────────────
_SKIP = {"", "Task Switching", "Program Manager", "Windows Input Experience"}

def get_visible_windows() -> list:
    results = []
    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title in _SKIP or len(title) < 2:
            return
        results.append((hwnd, title))
    win32gui.EnumWindows(_cb, None)
    return sorted(results, key=lambda x: x[1].lower())


def get_foreground_window() -> tuple:
    hwnd  = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    return hwnd, title


def get_window_title(hwnd: int) -> str:
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""


# ── Flash + sound (singleton guard) ───────────────────────────────────────────
def flash_window(hwnd: int, count: int = 4) -> None:
    try:
        class FLASHWINFO(ctypes.Structure):
            _fields_ = [("cbSize",    ctypes.c_uint),
                        ("hwnd",      ctypes.c_void_p),
                        ("dwFlags",   ctypes.c_uint),
                        ("uCount",    ctypes.c_uint),
                        ("dwTimeout", ctypes.c_uint)]
        fi = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd, 3, count, 0)
        ctypes.windll.user32.FlashWindowEx(ctypes.byref(fi))
    except Exception:
        pass


def play_alert_sound() -> None:
    try:
        ctypes.windll.user32.MessageBeep(0x00000030)
    except Exception:
        pass


# ── Opacity description ────────────────────────────────────────────────────────
def opacity_desc(pct: int) -> str:
    if pct <= 25: return "Ghost — barely visible"
    if pct <= 45: return "See-through — content visible behind"
    if pct <= 65: return "Translucent — comfortable overlap"
    if pct <= 85: return "Focus mode — slight transparency"
    if pct <= 95: return "Nearly solid"
    return "Fully solid"
