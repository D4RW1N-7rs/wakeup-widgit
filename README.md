# Wake Widget ⏰

A standalone, always-on-top desktop widget for Linux (X11) that monitors user inactivity to prevent unintended workstation locks and idle timeouts.

---

## 🎯 How It Works

1. **Active State (`ACTIVE`)**:
   - While you are moving the mouse, clicking, or typing on the keyboard, **the widget does nothing**.
   - Your session remains in the calm green "Active" state.
2. **15-Second Inactivity Gate**:
   - If you stop moving the mouse and stop touching the keyboard for **15 seconds**, it automatically starts a **4-minute timer**.
3. **4-Minute Warning Countdown (`COUNTDOWN`)**:
   - The widget turns amber and counts down from `04:00` to `00:00`.
   - If at **any moment** during these 4 minutes you move the mouse, click a button, or press a keyboard key, **the timer immediately cancels and resets back to the start**.
4. **Alert & Ticking Reminder (`ALERT`)**:
   - Once the 4 minutes of uninterrupted inactivity is reached (`15s + 4min = 4m15s` total idle):
     - A **desktop notification** appears on screen: *"Inactivity Warning! Move mouse or press any key!"*
     - A **mechanical clock ticking sound** begins playing rhythmically (`tick... tock... tick... tock...`).
   - The sound and notification continue **until you touch the keyboard, move the mouse, or click it**.
   - As soon as you interact, the ticking sound stops instantly, the notification is dismissed, and the entire cycle **starts over from the beginning**.

---

## 🚀 Quick Start

From the terminal inside this directory:

```bash
# Start in standard mode (15s inactivity -> 4m timer -> ticking alert)
make run

# Fast test mode for live demonstration (3s inactivity -> 5s timer -> ticking alert)
make fast-test

# Immediately test the alert ticking sound and notification
make sim-alert

# Stop the widget
make stop
```

---

## 🖱️ Controls & Features

* **Drag & Move**: Left-click and drag the pill to place it anywhere on your screen. The position is automatically saved in `~/.config/wake-widget/config.json`.
* **Expand / Collapse**: Left-click the pill to open the expanded card showing the digital countdown clock and controls.
* **Context Menu**: Right-click the pill to access:
  * 🔔 **Test Alert Now** (triggers alert immediately so you can test audio & notification)
  * 🔄 **Reset Timer**
  * 🔊 / 🔇 **Mute / Unmute Audio**
  * ✕ **Quit**
* **Instant Audio Cutoff**: The moment mouse movement or a keypress is detected, the audio thread interrupts playback in `< 10ms`.
* **Zero Dependencies**: Uses native X11 `libXss.so.1` via `ctypes` (0% CPU, no background loops, no `sudo`, and no external pip packages required).

---

## 🛠️ CLI Options

You can also run `run.py` directly with custom timings:

```bash
python3 run.py --idle-seconds 15 --timer-seconds 240
python3 run.py --fast-test
python3 run.py --test-alert
python3 run.py --mute
```

---

## 🧪 Testing

```bash
make test
```
Runs the automated test suite verifying state transitions, timer accuracy, activity detection, and audio services.
