# Wake Widget ⏰

> A lightweight, always-on-top desktop widget for Linux (X11) that keeps you aware of workstation inactivity — before your session locks or times out.

---

## 🎯 How It Works

```
You're active → [ACTIVE 🟢]
      ↓ 10s of no input
  [COUNTDOWN 🟡] 04:00 → 03:59 → ... → 00:00
      ↓ 4 minutes elapsed
  [ALERT 🔴] chime plays + notification
      ↓ any mouse / keyboard input
  resets back to [ACTIVE 🟢]
```

| State | Trigger | What happens |
|-------|---------|--------------|
| 🟢 **ACTIVE** | You're using the machine | Nothing — widget is idle |
| 🟡 **COUNTDOWN** | No input for **10 seconds** | 4-minute timer starts counting down |
| 🔴 **ALERT** | Countdown hits `00:00` | Desktop notification + repeating chime until you interact |

Any mouse movement, click, or keypress during COUNTDOWN or ALERT instantly resets everything back to ACTIVE.

---

## 🚀 Quick Start

```bash
git clone git@github.com:D4RW1N-7rs/wakeup-widgit.git
cd wakeup-widgit

make run        # start the widget
make stop       # stop it
make fast-test  # demo mode: 3s idle → 5s timer → alert
make sim-alert  # trigger alert immediately to test sound & notification
make test       # run automated test suite
```

---

## 📦 Requirements

- **Linux + X11** (GNOME, XFCE, i3, KDE, etc.) — Wayland not supported
- **Python 3.8+**
- **GTK 3** — pre-installed on most distros
- **libXss** — for idle time detection
- **PulseAudio** (`paplay`) — for sound playback

**Debian / Ubuntu:**
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 libxss1 pulseaudio-utils
```

**Fedora:**
```bash
sudo dnf install python3-gobject gtk3 libXScrnSaver pulseaudio-utils
```

**Arch:**
```bash
sudo pacman -S python-gobject gtk3 libxss pulseaudio
```

> **Zero pip dependencies** — everything uses the Python standard library + GTK3 + ctypes.

---

## 🖱️ Controls

| Action | How |
|--------|-----|
| Open detail card | Left-click the pill |
| Move the widget | Click & drag the pill |
| Test alert immediately | Click pill → **Test Alert** (toggle — stays on until clicked again) |
| Reset the timer | Click pill → **Reset Timer** |
| Mute / unmute sound | Click pill → **🔊 / 🔇** |
| Quit | Click pill → **✕ Quit** |

Position is auto-saved to `~/.config/wake-widget/config.json`.

---

## 🛠️ CLI Options

```bash
python3 run.py                              # standard mode
python3 run.py --idle-seconds 10           # custom idle gate (default: 10)
python3 run.py --timer-seconds 240         # custom countdown (default: 240)
python3 run.py --fast-test                 # 3s gate / 5s timer for quick demo
python3 run.py --test-alert                # start directly in ALERT state
python3 run.py --mute                      # start with sound off
```

---

## 🏗️ Autostart on Login

```bash
make install    # installs to ~/.local/bin + creates ~/.config/autostart entry
make uninstall  # removes both
```

After `make install`, the widget launches automatically every time you log in.

---

## 🧪 Testing

```bash
make test
```

Runs **11 automated tests** covering:
- State machine transitions (ACTIVE → COUNTDOWN → ALERT → reset)
- Timer accuracy
- Activity detection
- Config serialization / roundtrip
- Sound service start / stop

---

## 📁 Project Structure

```
wakeup-widgit/
├── run.py                        # entrypoint
├── Makefile                      # run / stop / test / install
├── assets/
│   ├── chime.wav                 # alert sound
│   └── icon.svg / alert.svg
├── wake_widget/
│   ├── constants.py              # timings & paths
│   ├── config.py                 # persistent JSON config
│   ├── core/
│   │   ├── activity_monitor.py   # X11 idle detection via libXss
│   │   └── state_machine.py      # ACTIVE / COUNTDOWN / ALERT logic
│   ├── services/
│   │   ├── sound_service.py      # threaded audio playback
│   │   └── notification_service.py
│   └── ui/
│       ├── pill_window.py        # top-bar pill widget
│       ├── popup_window.py       # expandable detail card
│       ├── ring_widget.py        # Cairo progress ring
│       └── styles.py             # GTK3 CSS
└── tests/
    └── test_wake_widget.py
```

---

## 📄 License

MIT
