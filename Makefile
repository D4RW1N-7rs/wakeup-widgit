# ==============================================================================
# Wake Widget - Inactivity Detector & 4-Minute Warning Ticking Reminder
# ==============================================================================

BIN_DIR        := $(HOME)/.local/bin
INSTALL_BIN    := $(BIN_DIR)/wake-widget
AUTOSTART_DIR  := $(HOME)/.config/autostart
AUTOSTART_FILE := $(AUTOSTART_DIR)/wake-widget.desktop

.PHONY: all run stop fast-test sim-alert check test install uninstall help

all: run

run:
	@pkill -f "wake-widgit/[r]un.py" 2>/dev/null || true
	@(nohup python3 "$(CURDIR)/run.py" >/dev/null 2>&1 & disown)
	@echo "✔ Wake Widget started in standard mode (15s inactivity -> 4min timer -> alert ticking)!"

fast-test:
	@pkill -f "wake-widgit/[r]un.py" 2>/dev/null || true
	@(nohup python3 "$(CURDIR)/run.py" --fast-test >/dev/null 2>&1 & disown)
	@echo "✔ Wake Widget started in Fast Test mode (3s inactivity -> 5s timer -> alert ticking)!"

sim-alert:
	@pkill -f "wake-widgit/[r]un.py" 2>/dev/null || true
	@(nohup python3 "$(CURDIR)/run.py" --test-alert >/dev/null 2>&1 & disown)
	@echo "✔ Wake Widget started with immediate alert ticking sound & notification!"

stop:
	@pkill -f "wake-widgit/[r]un.py" 2>/dev/null || true
	@pkill -f "\.local/bin/[w]ake-widget" 2>/dev/null || true
	@echo "✔ Wake Widget stopped."

check:
	@python3 -m compileall -q run.py wake_widget tests
	@echo "✔ Syntax check passed."

test: check
	@python3 -m unittest discover -s tests -v

install:
	@mkdir -p "$(BIN_DIR)" "$(AUTOSTART_DIR)"
	@cp -f "$(CURDIR)/run.py" "$(INSTALL_BIN)"
	@chmod +x "$(INSTALL_BIN)"
	@printf '[Desktop Entry]\nType=Application\nName=Wake Widget\nComment=Inactivity Detector & Warning Reminder\nExec=python3 %s/run.py\nTerminal=false\nX-GNOME-Autostart-enabled=true\n' "$(CURDIR)" > "$(AUTOSTART_FILE)"
	@echo "✔ Installed to $(INSTALL_BIN)"
	@echo "✔ Autostart configured at $(AUTOSTART_FILE)"

uninstall: stop
	@rm -f "$(INSTALL_BIN)" "$(AUTOSTART_FILE)"
	@echo "✔ Uninstalled Wake Widget."

help:
	@echo "Available commands:"
	@echo "  make run        - Start widget in standard mode (15s idle -> 4m timer -> tick)"
	@echo "  make fast-test  - Run fast test demonstration (3s idle -> 5s timer -> tick)"
	@echo "  make sim-alert  - Trigger alert ticking sound & notification immediately"
	@echo "  make stop       - Stop all running widget instances"
	@echo "  make test       - Run automated test suite"
	@echo "  make install    - Enable desktop autostart on login"
	@echo "  make uninstall  - Remove desktop autostart"
