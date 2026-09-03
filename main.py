"""
Ultron: Autonomous AI Assistant for Windows & Android
Entrypoint: Initializes PyQt6 event loop, transparent border overlay, and background orchestrator.
"""

import os
import sys
import yaml
import signal
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.border_overlay import BorderOverlayWindow, OverlayController
from core.orchestrator import UltronOrchestrator

# Configure rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Ultron.Main")

def load_config(config_path: str = "config.yaml") -> dict:
    if not os.path.exists(config_path):
        logger.warning(f"Configuration file {config_path} not found. Using defaults.")
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    logger.info("Initializing Ultron Artificial Intelligence System...")
    config = load_config("config.yaml")

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Initialize Overlay Controller and Window
    overlay_controller = OverlayController()
    overlay_window = BorderOverlayWindow(overlay_controller)

    # Initialize Ultron Orchestrator
    try:
        orchestrator = UltronOrchestrator(config, overlay_controller)
        orchestrator.start()
    except Exception as e:
        logger.error(f"Critical error initializing orchestrator: {e}", exc_info=True)
        return

    # Handle Ctrl+C cleanly in Qt event loop
    signal.signal(signal.SIGINT, lambda *args: app.quit())
    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)  # Allows Python interpreter to process signals
    sigint_timer.start(500)

    try:
        exit_code = app.exec()
    finally:
        logger.info("Ultron shutting down subsystems...")
        orchestrator.stop()
        sys.exit(exit_code)

if __name__ == "__main__":
    main()
