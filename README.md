# Opacity Controller

Make any window on Windows semi-transparent so you can see through it to whatever is behind — VLC, YouTube, Spotify, VirtualBox, native streaming apps, anything.

---

## What's new in v2

- **Multi-window** — make as many windows transparent as you want simultaneously
- **Full UI** — a proper app window with dropdown selector, live slider, preset buttons, and scrollable active windows list
- **Custom hotkey** — change the toggle shortcut from Settings
- **Auto-start on boot** — toggle from tray or Settings
- **Alt+↑ / Alt+↓** — adjust opacity 5% at a time while focused in any window
- **Tray menu** — shows all active transparent windows, restore individually or all at once
- **Settings guard** — trying to open Settings while it's already open flashes and dings the window instead of opening a duplicate

---

## Setup

### 1. Install Python
Download from https://python.org — tick **"Add python.exe to PATH"** during install.

### 2. Install dependencies
```
pip install pywin32 pystray pillow keyboard
python -m pywin32_postinstall -install
```

### 3. Run

**With full UI window:**
```
python main.py --ui
```

**Tray + hotkeys only (no window):**
```
python main.py
```

---

## How to use

### Full UI mode (`--ui`)
1. Select a window from the dropdown
2. Drag the opacity slider — transparency applies live
3. Use presets: Ghost (20%), Half (50%), Focus (70%), Solid (100%)
4. Click **Apply** to lock it in, or **Restore solid** to undo
5. Active transparent windows appear in the scrollable list at the bottom
6. Minimise to tray — hotkeys stay active in the background

### Hotkey mode (always active)
| Hotkey | Action |
|---|---|
| `Alt+T` | Toggle transparency on the focused window |
| `Alt+↑` | Increase opacity by 5% |
| `Alt+↓` | Decrease opacity by 5% |

### Tray icon
Right-click the tray icon (bottom-right near the clock) to:
- See all currently transparent windows
- Restore any window individually
- Open Settings (custom hotkey + autostart)
- Restore all windows at once
- Quit

---

## Settings

Open via tray → **Settings** or the Settings button in the UI.

- **Keyboard shortcut** — click the field and press any key combo to change the toggle hotkey
- **Auto-start** — adds the app to Windows startup registry

---

## Use cases

| Foreground (transparent) | Background |
|---|---|
| VS Code | YouTube tutorial / VLC |
| VirtualBox / WSL terminal | YouTube |
| Browser | Another browser window |
| Android Studio | Reference docs |
| Any app | Spotify / music player |

---

## Known limitations

- Windows 10 / 11 only
- Fullscreen exclusive apps (games) may ignore the transparency
- Netflix/Prime Video in browser may show a black box — use their native Windows apps instead (works fine)
- The `keyboard` hotkey library may require running as administrator on some systems

---

## Changelog

### v2.0
- Added full UI window with dropdown, slider, presets, active list
- Multi-window transparency support
- Custom hotkey via Settings
- Auto-start on boot toggle
- Alt+↑/↓ opacity nudge hotkeys
- Scrollable active windows list
- Settings singleton with flash + ding guard
- DPI awareness fix (no more blurry text)

### v1.0
- System tray app
- Alt+T toggle on focused window
- Per-app opacity memory
- Opacity slider popup
