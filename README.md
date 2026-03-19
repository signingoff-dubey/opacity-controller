# Opacity Controller

Make any window semi-transparent on Windows so you can see through it to whatever is behind — VLC, YouTube, Spotify, VirtualBox, anything.

---

## Setup (one time)

### 1. Install Python
Download from https://python.org — make sure to tick **"Add Python to PATH"** during install.

### 2. Install dependencies
Open a terminal in this folder and run:

```
pip install -r requirements.txt
```

If pywin32 doesn't register its DLLs automatically, also run:
```
python -m pywin32_postinstall -install
```

### 3. Run the app
```
python main.py
```

A small icon will appear in your **system tray** (bottom-right, near the clock).

---

## How to use

### Method 1 — Tray icon (pick any window)
1. Right-click the tray icon
2. Click **"Select Window…"**
3. Double-click any open window from the list
4. Drag the opacity slider — the window goes transparent live
5. Use the presets: Ghost (20%), See-through (50%), Focus (70%), Solid (100%)

### Method 2 — Hotkey (quick toggle on focused window)
1. Click into the window you want to make transparent (e.g. VS Code)
2. Press **Alt+T**
3. It instantly applies your last saved opacity for that window (default 70%)
4. Press **Alt+T** again to restore it to fully solid

---

## Per-app memory

Every time you set an opacity, it's saved to `opacity_config.json` in the same folder.
Next time you press Alt+T on VS Code, it remembers your preferred opacity.

---

## Use cases that work great

| Foreground (transparent) | Background (solid) |
|---|---|
| VS Code | YouTube / VLC / local video |
| VirtualBox / WSL terminal | YouTube tutorial |
| VS Code | Spotify (just see the album art) |
| Any browser | Another browser tab |
| Android Studio | Reference docs |

---

## Known limitations

- Works only on **Windows 10 / 11**
- Some fullscreen exclusive apps (games) ignore the layered window style
- Netflix/Prime Video in browser may show a black box — use their **native app** instead (works fine)
- The `keyboard` hotkey library requires running as **administrator** on some systems if hotkeys don't register

---

## Run on startup (optional)

1. Press `Win+R`, type `shell:startup`, press Enter
2. Create a shortcut to `main.py` in that folder
3. Right-click shortcut → Properties → set target to:
   `pythonw.exe C:\path\to\opacity-controller\main.py`
   (`pythonw` runs without a terminal window)
