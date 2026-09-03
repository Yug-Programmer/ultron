"""
Proactive Assistance & Friction Detector
Monitors user interaction and active screen context to detect when the user is stuck,
facing an error dialog, or experiencing friction, offering targeted help proactively.
"""

import time
import logging
import threading
from vision.screen_monitor import ScreenMonitor

logger = logging.getLogger("Ultron.ProactiveAgent")

class ProactiveAgent:
    def __init__(
        self,
        screen_monitor: ScreenMonitor,
        check_interval: float = 3.0,
        stagnation_seconds: float = 25.0,
        on_proactive_prompt = None
    ):
        self.screen_monitor = screen_monitor
        self.check_interval = check_interval
        self.stagnation_seconds = stagnation_seconds
        self.on_proactive_prompt = on_proactive_prompt

        self.is_running = False
        self._thread = None

        self.last_window_title = ""
        self.window_focus_start_time = time.time()
        self.has_prompted_current_state = False
        self.pending_help_context = None

    def _monitor_loop(self):
        logger.info("Proactive assistance monitor engaged.")
        while self.is_running:
            try:
                time.sleep(self.check_interval)
                info = self.screen_monitor.get_active_window_info()
                current_title = info.get("title", "")
                is_error = info.get("is_error_dialog", False)
                process = info.get("process", "")

                now = time.time()

                if current_title != self.last_window_title:
                    self.last_window_title = current_title
                    self.window_focus_start_time = now
                    self.has_prompted_current_state = False
                    continue

                duration = now - self.window_focus_start_time

                # Trigger 1: Immediate prompt on critical error dialog (stuck > 4 seconds)
                if is_error and not self.has_prompted_current_state and duration >= 4.0:
                    self.has_prompted_current_state = True
                    self.pending_help_context = {
                        "type": "error_dialog",
                        "title": current_title,
                        "process": process
                    }
                    msg = f"I noticed an error dialog in {process or 'your application'}. Would you like me to resolve this for you?"
                    logger.info(f"[Proactive] Triggering help for error: {current_title}")
                    if self.on_proactive_prompt:
                        self.on_proactive_prompt(msg, self.pending_help_context)

                # Trigger 2: Prolonged stagnation only on non-responsive or crash-prone windows
                elif duration >= max(120.0, self.stagnation_seconds) and not self.has_prompted_current_state and current_title:
                    lower_title = current_title.lower()
                    trouble_keywords = ["not responding", "unresponsive", "crash", "error", "problem", "stopped working", "troubleshoot"]
                    if any(kw in lower_title for kw in trouble_keywords):
                        self.has_prompted_current_state = True
                        self.pending_help_context = {
                            "type": "stagnation",
                            "title": current_title,
                            "process": process
                        }
                        msg = f"It looks like {process or current_title} may be unresponsive. Would you like me to close or recover it?"
                        logger.info(f"[Proactive] Triggering trouble assistance for: {current_title}")
                        if self.on_proactive_prompt:
                            self.on_proactive_prompt(msg, self.pending_help_context)

            except Exception as e:
                logger.debug(f"Error in proactive monitor loop: {e}")

    def clear_pending(self):
        """Clears pending proactive prompt state."""
        self.pending_help_context = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.is_running = False
