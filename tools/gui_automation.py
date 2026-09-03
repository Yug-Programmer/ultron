"""
Autonomous GUI Automation Agent
Enables Ultron to interact with user interfaces, click buttons, type text,
dismiss error dialogs, and manipulate windows on the user's behalf.
"""

import time
import logging
import pyautogui

# Safety fail-safe: moving mouse to corner triggers an abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2

logger = logging.getLogger("Ultron.GUIAutomation")

class GUIAutomationTool:
    @staticmethod
    def dismiss_active_dialog() -> str:
        """Attempts to cleanly acknowledge or close an active error dialog."""
        try:
            # Press Enter first (default 'OK' or 'Acknowledge')
            pyautogui.press("enter")
            time.sleep(0.3)
            return "Sent acknowledgement (Enter) to active window."
        except Exception as e:
            return f"Failed to dismiss dialog: {e}"

    @staticmethod
    def force_close_active_window() -> str:
        """Sends Alt+F4 to cleanly close the foreground window."""
        try:
            pyautogui.hotkey("alt", "f4")
            return "Sent close command (Alt+F4) to foreground window."
        except Exception as e:
            return f"Failed to close window: {e}"

    @staticmethod
    def show_desktop() -> str:
        """Toggles show desktop (Win+D)."""
        try:
            pyautogui.hotkey("win", "d")
            return "Toggled desktop view."
        except Exception as e:
            return f"Error toggling desktop: {e}"

    @staticmethod
    def type_text(text: str) -> str:
        """Types string directly into the currently focused input."""
        try:
            pyautogui.write(text, interval=0.02)
            return f"Typed {len(text)} characters into active input."
        except Exception as e:
            return f"Failed to type text: {e}"

    @staticmethod
    def press_shortcut(*keys: str) -> str:
        """Presses a hotkey combination (e.g. 'ctrl', 's')."""
        try:
            pyautogui.hotkey(*keys)
            return f"Triggered shortcut: {'+'.join(keys)}"
        except Exception as e:
            return f"Failed to press shortcut: {e}"

    @staticmethod
    def click_coordinate(x: int, y: int) -> str:
        """Moves and clicks at a specific screen coordinate."""
        try:
            pyautogui.click(x=x, y=y)
            return f"Clicked at ({x}, {y})."
        except Exception as e:
            return f"Failed to click coordinate: {e}"
