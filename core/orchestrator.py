"""
Ultron Master Orchestrator
Coordinates voice recognition, HUD display, proactive intervention,
continuous follow-up session flow, and hardware/OS tool actuation.
"""

import os
import re
import time
import logging
import threading
import pygame
from ui.border_overlay import OverlayState, OverlayController
from audio.mic_manager import DynamicMicManager
from audio.stt import STTEngine
from audio.tts import TTSEngine
from audio.listener import VoiceListener
from vision.screen_monitor import ScreenMonitor
from core.proactive_agent import ProactiveAgent
from core.intent_filter import FastIntentFilter
from core.router import ModelRouter
from tools.system_android import AndroidBridge
from tools.gui_automation import GUIAutomationTool
from tools.file_assistant import FileAssistantTool
from core.action_classifier import NeuralActionClassifier

logger = logging.getLogger("Ultron.Orchestrator")

class UltronOrchestrator:
    def __init__(self, config: dict, overlay_controller: OverlayController):
        self.config = config
        self.overlay = overlay_controller

        # 1. Initialize Vision & Screen Monitor
        self.screen_monitor = ScreenMonitor()

        # 2. Initialize Audio Subsystems
        audio_cfg = config.get("audio", {})
        self.mic_manager = DynamicMicManager(
            sample_rate=audio_cfg.get("sample_rate", 16000),
            auto_yield_apps=audio_cfg.get("auto_yield_apps", [])
        )
        groq_key = config.get("models", {}).get("groq", {}).get("api_key", "")
        self.stt = STTEngine(
            model_size=audio_cfg.get("stt_model", "base.en"),
            device=audio_cfg.get("stt_device", "auto"),
            groq_api_key=groq_key
        )
        self.tts = TTSEngine(
            voice=audio_cfg.get("tts_voice", "en-US-ChristopherNeural"),
            rate=audio_cfg.get("tts_rate", "+5%"),
            pitch=audio_cfg.get("tts_pitch", "+0Hz")
        )

        # 3. Initialize Intelligence & Model Routing
        self.router = ModelRouter(config)
        self.action_classifier = NeuralActionClassifier(
            api_key=groq_key,
            model=config.get("models", {}).get("groq", {}).get("model", "qwen/qwen3.8-27b")
        )

        # 4. Initialize Mobile Android Bridge
        mob_cfg = config.get("mobile", {})
        self.android_bridge = AndroidBridge(
            host=mob_cfg.get("server_host", "0.0.0.0"),
            port=mob_cfg.get("server_port", 8765)
        )

        # 5. Initialize Proactive Stagnation Agent
        screen_cfg = config.get("screen", {})
        self.proactive_agent = ProactiveAgent(
            screen_monitor=self.screen_monitor,
            check_interval=screen_cfg.get("snapshot_interval_seconds", 3.0),
            stagnation_seconds=screen_cfg.get("stagnation_seconds", 25.0),
            on_proactive_prompt=self._on_proactive_prompt
        )

        # 6. Initialize Listener Coordinator with follow-up and standby callbacks
        self.listener = VoiceListener(
            mic_manager=self.mic_manager,
            stt_engine=self.stt,
            wake_word=config.get("assistant", {}).get("wake_word", "ultron"),
            tts_engine=self.tts,
            energy_threshold=audio_cfg.get("energy_threshold", 0.015),
            silence_duration=audio_cfg.get("silence_duration", 0.8),
            on_wake_callback=self._on_wake,
            on_command_callback=self._on_command,
            on_session_idle_callback=self._on_session_idle
        )

    def _play_ack_chime(self):
        """Plays instant sub-10ms auditory acknowledgment chime."""
        chime_path = os.path.join("audio_cache", "ack_chime.wav")
        if os.path.exists(chime_path) and pygame.mixer.get_init():
            try:
                pygame.mixer.Sound(chime_path).play()
            except Exception:
                pass

    def _on_wake(self, raw_text: str = ""):
        """Triggered when wake word is spoken without a trailing command."""
        logger.info("[Orchestrator] Wake word detected. Initiating conversation session.")
        self._play_ack_chime()
        self.tts.stop()
        self.overlay.set_state(OverlayState.LISTENING)
        self.overlay.set_subtitles(user_text=raw_text or "Ultron", ultron_text="Yes, sir? Standing by.")
        self.tts.speak("Yes, sir?")
        # Keep overlay in follow-up mode awaiting the command
        threading.Timer(1.2, lambda: self.overlay.set_state(OverlayState.FOLLOWUP)).start()

    def _on_session_idle(self):
        """Called when follow-up conversation window expires with no further speech."""
        logger.info("[Orchestrator] Conversation session ended. Returning to Standby.")
        self.overlay.set_state(OverlayState.IDLE)
        self.overlay.set_subtitles(user_text="", ultron_text="Standby")

    def _on_proactive_prompt(self, message: str, context: dict):
        """Triggered when friction or an error dialog is detected on screen."""
        self.tts.stop()
        self.overlay.set_state(OverlayState.PROACTIVE)
        self.overlay.set_subtitles(user_text="", ultron_text=message)
        self.tts.speak(message)
        # Transition to follow-up to hear user's 'Yes' or 'No'
        threading.Timer(4.0, lambda: self.overlay.set_state(OverlayState.FOLLOWUP)).start()

    def _on_command(self, user_command: str, raw_transcript: str = ""):
        """Processes recognized spoken command."""
        if not user_command.strip():
            return

        cmd = user_command.strip()
        logger.info(f"[Orchestrator] Executing user command: '{cmd}'")
        self._play_ack_chime()
        self.overlay.set_subtitles(user_text=raw_transcript or cmd, ultron_text="Processing...")

        # 1. Check for proactive confirmation ("yes", "fix it", "do it", "help")
        if self.proactive_agent.pending_help_context:
            lower_cmd = cmd.lower()
            if any(affirm in lower_cmd for affirm in ["yes", "yeah", "do it", "fix it", "help", "please", "sure"]):
                self.overlay.set_state(OverlayState.EXECUTING)
                ctx = self.proactive_agent.pending_help_context
                self.proactive_agent.clear_pending()

                if ctx.get("type") == "error_dialog":
                    self.overlay.set_subtitles(user_text=cmd, ultron_text="Dismissing error dialog.")
                    self.tts.speak("Acknowledging dialog now.")
                    res = GUIAutomationTool.dismiss_active_dialog()
                    self.overlay.set_subtitles(user_text=cmd, ultron_text=res)
                    self.tts.speak(res)
                else:
                    self.overlay.set_subtitles(user_text=cmd, ultron_text="Analyzing screen context...")
                    self.tts.speak("Analyzing window context...")
                    info = self.screen_monitor.get_active_window_info()
                    explanation = self.router.generate_response("Explain this window and what the user can do next.", screen_context=info)
                    self.overlay.set_subtitles(user_text=cmd, ultron_text=explanation[:60])
                    self.tts.speak(explanation)

                # Maintain follow-up mode for 8s
                self.listener.extend_session(8.0)
                self.overlay.set_state(OverlayState.FOLLOWUP)
                return

        # 2. Check Fast Semantic Intent Filter (<1ms instant execution)
        deterministic_response = FastIntentFilter.evaluate(cmd)
        if deterministic_response:
            self.overlay.set_state(OverlayState.EXECUTING)
            self.overlay.set_subtitles(user_text=cmd, ultron_text=deterministic_response[:70])
            self.tts.speak(deterministic_response)
            
            # Maintain follow-up mode so user can give another command without saying Ultron again!
            self.listener.extend_session(8.0)
            threading.Timer(2.0, lambda: self.overlay.set_state(OverlayState.FOLLOWUP)).start()
            return

        # 3. AI Neural Action Classifier (Siri-Grade Intent Interpretation & Task Execution)
        if hasattr(self, "action_classifier"):
            ai_action_result = self.action_classifier.classify_and_execute(cmd, router=self.router)
            if ai_action_result:
                self.overlay.set_state(OverlayState.EXECUTING)
                self.overlay.set_subtitles(user_text=cmd, ultron_text=ai_action_result[:70])
                self.tts.speak(ai_action_result)
                self.listener.extend_session(6.0)
                threading.Timer(2.0, lambda: self.overlay.set_state(OverlayState.FOLLOWUP)).start()
                return

        # 3. Check AI-Powered Voice File Editing (e.g. "edit file notes.txt to add items", "in test.py change X to Y")
        m_ai_edit = re.search(r"(?:edit|modify|change|update)\s+(?:the\s+)?(?:file\s+)?([a-zA-Z0-9_\-\.]+)\s+(?:to\s+|and\s+)?(.*)", cmd.lower())
        if m_ai_edit:
            target_file = m_ai_edit.group(1)
            instructions = m_ai_edit.group(2)
            if instructions:
                self.overlay.set_state(OverlayState.EXECUTING)
                self.overlay.set_subtitles(user_text=cmd, ultron_text=f"Editing {target_file}...")
                edit_res = FileAssistantTool.edit_file_with_ai(target_file, instructions, self.router)
                self.overlay.set_subtitles(user_text=cmd, ultron_text=edit_res)
                self.tts.speak(edit_res)
                self.listener.extend_session(5.0)
                threading.Timer(2.0, lambda: self.overlay.set_state(OverlayState.FOLLOWUP)).start()
                return

        # 4. Model Routing & Web Grounding
        self.overlay.set_state(OverlayState.THINKING)
        screen_context = self.screen_monitor.get_active_window_info()

        def _async_process():
            try:
                response = self.router.generate_response(cmd, screen_context=screen_context)
                self.overlay.set_state(OverlayState.EXECUTING)
                self.overlay.set_subtitles(user_text=cmd, ultron_text=response[:70])
                self.tts.speak(response, block=True)
            except Exception as e:
                logger.error(f"Error generating response: {e}")
                err_msg = "I encountered an internal error while processing that request."
                self.overlay.set_subtitles(user_text=cmd, ultron_text=err_msg)
                self.tts.speak(err_msg)
            finally:
                # Maintain follow-up session after response
                self.listener.extend_session(8.0)
                self.overlay.set_state(OverlayState.FOLLOWUP)

        threading.Thread(target=_async_process, daemon=True).start()

    def start(self):
        """Starts all background services."""
        logger.info("Engaging Ultron systems...")
        self.android_bridge.start()
        self.proactive_agent.start()
        self.listener.start()
        self.overlay.set_state(OverlayState.FOLLOWUP)
        self.overlay.set_subtitles(user_text="", ultron_text="Online and operational")
        self.tts.speak("Ultron systems online and operational.")
        threading.Timer(4.0, lambda: self.overlay.set_state(OverlayState.IDLE)).start()

    def stop(self):
        """Gracefully terminates subsystems."""
        logger.info("Stopping Ultron...")
        self.listener.stop()
        self.proactive_agent.stop()
        self.android_bridge.stop()
        self.tts.stop()
