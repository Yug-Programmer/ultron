"""
Screen & Window Context Monitor
Provides high-performance screen capture (<10ms via mss) and tracks active window
metadata (window title, process name, window rect, error dialog states).
"""

import sys
import time
import logging
from io import BytesIO
from PIL import Image
import mss
import psutil

if sys.platform == "win32":
    import win32gui
    import win32process

logger = logging.getLogger("Ultron.ScreenMonitor")

class ScreenMonitor:
    def __init__(self):
        self._sct = mss.mss()

    def get_active_window_info(self) -> dict:
        """Retrieves details of the currently focused window on Windows."""
        info = {
            "title": "",
            "process": "",
            "pid": None,
            "rect": None,
            "is_error_dialog": False
        }

        if sys.platform != "win32":
            return info

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return info

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            rect = win32gui.GetWindowRect(hwnd) # (left, top, right, bottom)
            
            p_name = ""
            if pid:
                try:
                    p_name = psutil.Process(pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    p_name = "Unknown"

            # Quick heuristic check for error or warning dialogs
            lower_title = title.lower()
            is_error = any(keyword in lower_title for keyword in ["error", "fatal", "failed", "crash", "exception", "warning", "stopped working"])

            info.update({
                "title": title,
                "process": p_name,
                "pid": pid,
                "rect": rect,
                "is_error_dialog": is_error
            })
        except Exception as e:
            logger.debug(f"Error fetching active window info: {e}")

        return info

    def capture_screenshot(self, monitor_index: int = 1) -> Image.Image:
        """Grabs a screenshot of the display with multi-backend fallback (mss -> ImageGrab)."""
        # Attempt 1: Fast C-based mss
        try:
            monitors = self._sct.monitors
            if monitor_index >= len(monitors):
                monitor_index = 0

            sct_img = self._sct.grab(monitors[monitor_index])
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e_mss:
            logger.debug(f"mss grab failed: {e_mss}, attempting PIL ImageGrab fallback...")

        # Attempt 2: PIL ImageGrab fallback
        try:
            from PIL import ImageGrab
            return ImageGrab.grab(all_screens=True)
        except Exception as e_grab:
            logger.debug(f"ImageGrab fallback failed: {e_grab}")

        return None

    def capture_screenshot_bytes(self, max_dimension: int = 1024) -> bytes:
        """Captures a screenshot compressed to JPEG bytes for low-bandwidth LLM vision analysis."""
        img = self.capture_screenshot()
        if not img:
            return b""

        # Resize if dimensions exceed max_dimension
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=80)
        return buffer.getvalue()
