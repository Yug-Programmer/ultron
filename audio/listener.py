"""
Voice Listener Coordinator
Features:
1. Strict Standby Wake-Word Detection (ignoring casual room conversation).
2. Continuous Follow-Up Session (stays open for 8s so user doesn't repeat 'Ultron').
3. Voice Barge-In / Interruption (speaking cuts off Ultron's voice immediately).
4. Phonetic & Number-word speech normalization.
"""

import re
import time
import logging
import threading
import numpy as np
from audio.mic_manager import DynamicMicManager
from audio.stt import STTEngine
from core.intent_filter import FastIntentFilter

logger = logging.getLogger("Ultron.Listener")

class VoiceListener:
    def __init__(
        self,
        mic_manager: DynamicMicManager,
        stt_engine: STTEngine,
        wake_word: str = "ultron",
        tts_engine = None,
        energy_threshold: float = 0.015,
        silence_duration: float = 0.8,
        on_wake_callback = None,
        on_command_callback = None,
        on_session_idle_callback = None
    ):
        self.mic = mic_manager
        self.stt = stt_engine
        self.wake_word = wake_word.lower()
        self.tts = tts_engine
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.on_wake_callback = on_wake_callback
        self.on_command_callback = on_command_callback
        self.on_session_idle_callback = on_session_idle_callback

        self.is_running = False
        self.is_active_session = False
        self.session_expiry_time = 0.0
        self.followup_window_seconds = 5.0
        self._listener_thread = None

        # AI Neural Voice Activity Detector (Silero VAD)
        try:
            from faster_whisper.vad import get_vad_model
            self.vad_model = get_vad_model()
            logger.info("Silero Neural VAD engaged for Siri-grade speech detection.")
        except Exception as e:
            self.vad_model = None
            logger.warning(f"Could not load Silero VAD ({e}), using energy fallback.")

    def _normalize_speech(self, raw_text: str) -> str:
        """Fixes common Whisper mis-transcriptions and converts number words to digits."""
        text = raw_text.lower().strip()

        # Phonetic mis-transcription corrections
        phonetic_fixes = {
            r"\bvotes my\b": "what is my",
            r"\bvotes\b": "what is",
            r"\bsaid brightness\b": "set brightness",
            r"\bsaid the rightness\b": "set the brightness",
            r"\bthe rightness\b": "the brightness",
            r"\bsaid volume\b": "set volume",
            r"\bopen mode effect\b": "open notepad",
            r"\bdoc my pc\b": "lock my pc",
            r"\bmobile host port\b": "mobile hotspot",
            r"\bnight light\b": "nightlight",
            r"\bthe late\b": "delete",
            r"\bask manager\b": "task manager",
            r"\bpedia\b": "pdf",
            r"\bi've drawn\b": "ultron",
            r"\bi have drawn\b": "ultron",
            r"\b(?:new\s+volume\s+(?:by|why|buy)|volume\s+(?:by|why|buy))\b": "new volume y",
            r"\b(?:drive\s+(?:by|why|buy)|y\s+drive|drive\s+y)\b": "y drive",
            r"\b(?:c\s+drive|drive\s+c|see\s+drive|sea\s+drive)\b": "c drive",
            r"\b(?:note\s*pack|notepack|open\s*note)\b": "open notepad",
            r"\b(?:open\s*world|open\s*word)\b": "open word",
            r"\b(?:1\s*c\s*drive|1c\s*drive|one\s*c\s*drive|1\s*disk\s*c)\b": "c drive",
            r"\b(?:the\s+local\s+disk\s+c|local\s+disk\s+c)\b": "local disk c",
        }
        for pattern, replacement in phonetic_fixes.items():
            text = re.sub(pattern, replacement, text)

        # Number-word to digit conversion
        num_map = {
            r"\bzero\b": "0",
            r"\bone\b": "1",
            r"\btwo\b": "2",
            r"\bthree\b": "3",
            r"\bfour\b": "4",
            r"\bfive\b": "5",
            r"\bsix\b": "6",
            r"\bseven\b": "7",
            r"\beight\b": "8",
            r"\bnine\b": "9",
            r"\bten\b": "10",
            r"\btwenty\b": "20",
            r"\bthirty\b": "30",
            r"\bforty\b": "40",
            r"\bfifty\b": "50",
            r"\bsixty\b": "60",
            r"\bseventy\b": "70",
            r"\beighty\b": "80",
            r"\bninety\b": "90",
            r"\bhundred\b": "100",
        }
        for pattern, replacement in num_map.items():
            text = re.sub(pattern, replacement, text)

        return text

    def _listen_loop(self):
        audio_buffer = []
        is_speaking = False
        silence_start = None

        logger.info(f"Voice listening loop started. Wake word: '{self.wake_word}'")

        while self.is_running:
            now = time.time()

            # Handle session expiration back to Standby
            if self.is_active_session and (now > self.session_expiry_time):
                if not (self.tts and self.tts.is_speaking):
                    logger.info("[Listener] Follow-up session expired. Returning to Standby.")
                    self.is_active_session = False
                    if self.on_session_idle_callback:
                        self.on_session_idle_callback()

            if self.mic.is_yielded:
                time.sleep(0.2)
                continue

            frame = self.mic.get_audio_frame(timeout=0.1)
            if frame is None:
                continue

            # Calculate RMS energy of current audio block
            energy = float(np.sqrt(np.mean(frame ** 2)))

            # Voice Barge-In / Interruption:
            # Acoustic Echo Suppression:
            # While Ultron is speaking, suppress microphone recording to completely prevent
            # self-interruption and echo-loop hallucinations.
            if self.tts and self.tts.is_speaking:
                self._last_tts_end_time = now
                audio_buffer = []
                is_speaking = False
                continue

            # 250ms room reverberation grace period: let room echo decay before listening
            if hasattr(self, "_last_tts_end_time") and (now - self._last_tts_end_time < 0.25):
                audio_buffer = []
                is_speaking = False
                continue

            # Siri-Grade AI Voice Activity Detection (Silero Neural Network)
            speech_prob = 0.0
            if self.vad_model is not None and frame.shape[0] % 512 == 0:
                try:
                    speech_prob = float(np.max(self.vad_model(frame)))
                except Exception:
                    speech_prob = 1.0 if energy > self.energy_threshold else 0.0
            else:
                speech_prob = 1.0 if energy > self.energy_threshold else 0.0

            # High-confidence human vocal cord vibration (>0.40)
            is_voice = speech_prob > 0.40

            if is_voice:
                if not is_speaking:
                    is_speaking = True
                    audio_buffer = []
                silence_start = None
                audio_buffer.append(frame)
            elif is_speaking:
                audio_buffer.append(frame)
                if silence_start is None:
                    silence_start = now
                elif now - silence_start >= self.silence_duration:
                    # Speech segment finished
                    is_speaking = False
                    silence_start = None

                    full_audio = np.concatenate(audio_buffer, axis=0)
                    audio_buffer = []

                    # Discard tiny blips (<0.35s)
                    duration = len(full_audio) / float(self.mic.sample_rate)
                    if duration < 0.35:
                        continue

                    # Transcribe using Groq Whisper-Large-V3-Turbo
                    transcript = self.stt.transcribe(full_audio, sample_rate=self.mic.sample_rate)
                    if transcript:
                        self._process_transcript(transcript)

    HALLUCINATIONS = {
        "thank you", "thank you.", "thank you very much", "thank you for watching",
        "thanks for watching", "please subscribe", "subtitles by", "you", "bye",
        "bye.", "bye bye", "so", "yeah", "oh", "ah", "okay", "okay.", "mbc",
        "the", "i", "a", "like", "and", "goodbye", "see you", "tron", "tron.",
        "thanks", "thanks."
    }

    def _process_transcript(self, raw_transcript: str):
        normalized = self._normalize_speech(raw_transcript)
        logger.info(f"[Listener] Recognized: \"{normalized}\"")

        # Discard empty, single-character, or common Whisper silence hallucinations
        if not normalized or len(normalized) <= 2 or normalized in self.HALLUCINATIONS:
            return

        # Immediate session cancellation
        if any(c == normalized for c in ["never mind", "cancel", "stop", "go to sleep", "standby", "dismiss"]):
            logger.info("[Listener] Session cancelled by user. Returning to Standby.")
            self.reset_session()
            if self.on_session_idle_callback:
                self.on_session_idle_callback()
            return

        wake_pattern = r"\b(ultron|altron|alltron|eltron|oltron|haltron|are you drawn|i've drawn)\b"
        matched_wake = bool(re.search(wake_pattern, normalized))

        # Check if this is an explicit direct system command (e.g. "open task manager", "delete file", "set volume to 50")
        is_direct_cmd = FastIntentFilter.is_direct_system_command(normalized)

        # In Standby, we execute if EITHER the wake word was spoken OR it is an explicit direct system command!
        # Casual room conversation (stories, casual chat) will be completely ignored.
        if not self.is_active_session and not matched_wake and not is_direct_cmd:
            logger.debug(f"[Listener] Ignored casual background speech: '{normalized}'")
            return

        # Engage / extend active follow-up conversation window
        self.is_active_session = True
        self.session_expiry_time = time.time() + self.followup_window_seconds

        # Clean wake word prefix
        cleaned_cmd = re.sub(wake_pattern, "", normalized).strip(".,?! ")

        # If user just said "Ultron" without a command
        if not cleaned_cmd:
            if self.on_wake_callback:
                self.on_wake_callback(raw_transcript)
        else:
            if self.on_command_callback:
                self.on_command_callback(cleaned_cmd, raw_transcript)

    def reset_session(self):
        """Manually resets session back to standby."""
        self.is_active_session = False

    def extend_session(self, seconds: float = 8.0):
        """Extends active follow-up conversation window."""
        self.is_active_session = True
        self.session_expiry_time = time.time() + seconds

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.mic.start()
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def stop(self):
        self.is_running = False
        self.mic.stop()
