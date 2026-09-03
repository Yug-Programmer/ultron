"""
Minimalist Siri-Style Screen Border Glow & Dynamic Island Floating HUD Overlay
Renders:
1. Animated pulsing neon border around screen edges.
2. Floating Top-Center Siri/Dynamic Island Capsule displaying real-time
   status, speech transcriptions, and Ultron responses.
3. Hardware click-through (WS_EX_TRANSPARENT) so clicks pass to background apps.
"""

import sys
import math
import time
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect, QRectF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QApplication

if sys.platform == "win32":
    import win32gui
    import win32con

class OverlayState:
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    FOLLOWUP = "FOLLOWUP"
    PROACTIVE = "PROACTIVE"
    EXECUTING = "EXECUTING"

class OverlayController(QObject):
    """Bridge for thread-safe state and text communication to Qt GUI thread."""
    state_changed = pyqtSignal(str)
    subtitle_changed = pyqtSignal(str, str)  # (user_transcript, ultron_response)

    def set_state(self, state: str):
        self.state_changed.emit(state)

    def set_subtitles(self, user_text: str = "", ultron_text: str = ""):
        self.subtitle_changed.emit(user_text, ultron_text)

class BorderOverlayWindow(QWidget):
    def __init__(self, controller: OverlayController):
        super().__init__()
        self.controller = controller
        self.controller.state_changed.connect(self._on_state_changed)
        self.controller.subtitle_changed.connect(self._on_subtitle_changed)

        self.current_state = OverlayState.IDLE
        self.border_thickness = 10
        self.pulse_phase = 0.0

        self.user_transcript = ""
        self.ultron_response = ""
        self.last_activity_time = time.time()
        self.hud_opacity = 0.0

        # Window flags: Frameless, Always on Top, Click-Through, Tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # 30 FPS animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(33)

        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            hwnd = int(self.winId())
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOOLWINDOW
            )

    def _on_state_changed(self, state: str):
        self.current_state = state
        self.last_activity_time = time.time()
        self.update()

    def _on_subtitle_changed(self, user_text: str, ultron_text: str):
        if user_text:
            self.user_transcript = user_text
        if ultron_text:
            self.ultron_response = ultron_text
        self.last_activity_time = time.time()
        self.update()

    def _animate_step(self):
        self.pulse_phase = (self.pulse_phase + 0.08) % (2 * math.pi)

        # Handle smooth HUD fading
        now = time.time()
        if self.current_state != OverlayState.IDLE or (now - self.last_activity_time < 5.0):
            # Target opacity = 1.0
            self.hud_opacity = min(1.0, self.hud_opacity + 0.1)
        else:
            # Fade out
            self.hud_opacity = max(0.0, self.hud_opacity - 0.05)

        self.update()

    def _get_current_colors(self):
        if self.current_state == OverlayState.LISTENING:
            base = QColor(0, 229, 255)    # Cyan
        elif self.current_state == OverlayState.THINKING:
            base = QColor(156, 39, 176)   # Purple
        elif self.current_state == OverlayState.FOLLOWUP:
            base = QColor(33, 150, 243)   # Soft Electric Blue
        elif self.current_state == OverlayState.PROACTIVE:
            base = QColor(255, 171, 0)    # Amber
        elif self.current_state == OverlayState.EXECUTING:
            base = QColor(0, 230, 118)    # Emerald Green
        else:
            base = QColor(0, 229, 255, 60) # Subtle Idle

        alpha_factor = 0.5 + 0.5 * math.sin(self.pulse_phase)
        alpha = int(140 + 100 * alpha_factor)
        base.setAlpha(alpha)
        return base

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        color = self._get_current_colors()
        w = self.width()
        h = self.height()
        t = self.border_thickness

        # ----------------------------------------------------
        # 1. RENDER SCREEN BORDER GLOW (When active)
        # ----------------------------------------------------
        if self.current_state != OverlayState.IDLE:
            # Top
            grad_top = QLinearGradient(0, 0, 0, t)
            grad_top.setColorAt(0.0, color)
            grad_top.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(0, 0, w, t, grad_top)

            # Bottom
            grad_bottom = QLinearGradient(0, h, 0, h - t)
            grad_bottom.setColorAt(0.0, color)
            grad_bottom.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(0, h - t, w, t, grad_bottom)

            # Left
            grad_left = QLinearGradient(0, 0, t, 0)
            grad_left.setColorAt(0.0, color)
            grad_left.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(0, 0, t, h, grad_left)

            # Right
            grad_right = QLinearGradient(w, 0, w - t, 0)
            grad_right.setColorAt(0.0, color)
            grad_right.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.fillRect(w - t, 0, t, h, grad_right)

        # ----------------------------------------------------
        # 2. RENDER FLOATING SIRI / DYNAMIC ISLAND HUD CAPSULE
        # ----------------------------------------------------
        if self.hud_opacity > 0.02:
            hud_w = 460
            hud_h = 58
            hud_x = int((w - hud_w) / 2)
            hud_y = 20

            capsule_rect = QRect(hud_x, hud_y, hud_w, hud_h)

            # Dark Glass Background
            bg_alpha = int(220 * self.hud_opacity)
            painter.setBrush(QBrush(QColor(18, 20, 30, bg_alpha)))
            
            # Glowing border around capsule
            border_col = QColor(color)
            border_col.setAlpha(int(200 * self.hud_opacity))
            painter.setPen(QPen(border_col, 2))
            painter.drawRoundedRect(capsule_rect, 29, 29)

            # Glowing Orb on the left
            orb_center_x = hud_x + 30
            orb_center_y = hud_y + int(hud_h / 2)
            orb_radius = int(9 + 3 * math.sin(self.pulse_phase))
            
            orb_color = QColor(color)
            orb_color.setAlpha(int(255 * self.hud_opacity))
            painter.setBrush(QBrush(orb_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(orb_center_x - orb_radius, orb_center_y - orb_radius, orb_radius * 2, orb_radius * 2)

            # Status Title & Subtitle Text
            painter.setPen(QColor(255, 255, 255, int(255 * self.hud_opacity)))
            font_title = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
            painter.setFont(font_title)

            status_map = {
                OverlayState.IDLE: "Ultron: Standby",
                OverlayState.LISTENING: "Ultron: Listening...",
                OverlayState.THINKING: "Ultron: Processing...",
                OverlayState.FOLLOWUP: "Ultron: Listening for follow-up...",
                OverlayState.PROACTIVE: "Ultron: Proactive Assistance",
                OverlayState.EXECUTING: "Ultron: Executing Command"
            }
            status_text = status_map.get(self.current_state, "Ultron")
            if self.ultron_response:
                status_text = f"Ultron: {self.ultron_response}"

            # Truncate if too long
            if len(status_text) > 42:
                status_text = status_text[:40] + "..."

            painter.drawText(hud_x + 55, hud_y + 24, status_text)

            # User Transcript Subtitle
            sub_text = f'You: "{self.user_transcript}"' if self.user_transcript else "Speak 'Ultron' to command"
            if len(sub_text) > 48:
                sub_text = sub_text[:46] + '..."'
            painter.setFont(QFont("Segoe UI", 9))
            painter.setPen(QColor(170, 180, 205, int(220 * self.hud_opacity)))
            painter.drawText(hud_x + 55, hud_y + 44, sub_text)
