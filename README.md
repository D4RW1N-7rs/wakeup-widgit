# Wake Widget ⏰

A standalone, always-on-top desktop widget for Linux (X11) that monitors user inactivity to prevent unintended workstation locks and idle timeouts.

---

## 🎯 How It Works

1. **Active State (`ACTIVE`)**: While you are moving the mouse, clicking, or typing, **the widget does nothing**.
2. **10-Second Inactivity Gate**: If you stop all input for **10 seconds**, it starts a **4-minute countdown**.
3. **4-Minute Warning Countdown (`COUNTDOWN`)**: The widget turns amber and counts down from `04:00`. Any mouse/keyboard activity **instantly resets** the timer.
4. **Alert & Chime Reminder (`ALERT`)**: Once the countdown hits zero (`10s + 4min = 4m10s` total idle):
   - A **desktop notification** appears.
   - A **repeating chime sound** plays until you move the mouse, click, or press a key.
   - Any interaction stops the chime and **resets the cycle**.

---

## 🚀 Quick Start

```bash
# Clone and enter the directory
git clone <repo-url> wake-widgit
cd wake-widgit

# Start the widget
make run

# Fast test mode (3s idle -> 5s timer -> chime)
make fast-test

# Test the alert sound immediately
make sim-alert

# Stop the widget
make stop

# Run automated tests
make test
```

---

## 📦 Requirements

- **Linux with X11** (GNOME, XFCE, i3, etc.)
- **Python 3.8+**
- **GTK 3** (`python3-gi`, `gir1.2-gtk-3.0`) — pre-installed on most distros
- **PulseAudio** (`paplay`) — pre-installed on Ubuntu/Fedora/Arch
- **libXss** (`libxss1` or `libXScrnSaver`) — for idle time detection

On Debian/Ubuntu, if anything is missing:
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 libxss1 pulseaudio-utils
```

---

## 🖱️ Controls & Features

* **Drag & Move**: Left-click and drag the pill to reposition it. Position is saved to `~/.config/wake-widget/config.json`.
* **Expand / Collapse**: Click the pill to open the detail card with countdown clock and controls.
* **Buttons**:
  * 🔔 **Test Alert Now**: Toggle — triggers alert immediately, stays until clicked again.
  * 🔄 **Reset Timer**: Reset the state machine back to the start.
  * 🔊 / 🔇 **Mute / Unmute Audio**: Toggle sound on/off.
  * ✕ **Quit**: Close the widget.

---

## 🛠️ CLI Options

```bash
python3 run.py --idle-seconds 10 --timer-seconds 240
python3 run.py --fast-test
python3 run.py --test-alert
python3 run.py --mute
```

---

## 🏗️ Install (Autostart on Login)

```bash
make install    # Copies to ~/.local/bin and creates autostart entry
make uninstall  # Removes both
```

---

## 🧪 Testing

```bash
make test
```

Runs 11 automated tests covering state transitions, timer accuracy, activity detection, config serialization, and audio services. **Zero pip dependencies** — everything uses the Python standard library + GTK3 + ctypes.
