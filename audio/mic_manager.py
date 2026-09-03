"""
Microphone Manager with Dynamic Auto-Yielding
Continuously captures microphone audio using WASAPI and automatically yields
access whenever communication or recording software (Zoom, Discord, Teams, OBS)
requires the microphone.
"""

import time
import queue
import threading
import logging
import numpy as np
import sounddevice as sd
import psutil

logger = logging.getLogger("Ultron.MicManager")

class DynamicMicManager:
    def __init__(self, sample_rate: int = 16000, block_size: int = 1024, auto_yield_apps: list = None):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.auto_yield_apps = [app.lower() for app in (auto_yield_apps or [])]
        
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.is_yielded = False
        self.yield_reason = ""
        
        self._stream = None
        self._monitor_thread = None
        self._lock = threading.Lock()

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice on every new audio buffer."""
        if status:
            logger.debug(f"Audio stream status: {status}")
        
        # If currently yielded to another application, discard buffer to stay silent
        if self.is_yielded:
            return
            
        # Copy audio as float32 1D numpy array
        audio_data = indata[:, 0].copy()
        self.audio_queue.put(audio_data)

    def _check_conflicting_processes(self) -> str:
        """Checks if any configured communication/recording app is currently running."""
        try:
            for proc in psutil.process_iter(['name']):
                p_name = (proc.info['name'] or '').lower()
                if p_name in self.auto_yield_apps:
                    return p_name
        except Exception as e:
            logger.debug(f"Error checking processes: {e}")
        return ""

    def _monitor_loop(self):
        """Background thread checking if conflicting apps are active."""
        while self.is_running:
            conflicting_app = self._check_conflicting_processes()
            
            with self._lock:
                if conflicting_app and not self.is_yielded:
                    logger.info(f"[MicManager] Detected conflicting app '{conflicting_app}'. Auto-yielding microphone...")
                    self.is_yielded = True
                    self.yield_reason = conflicting_app
                    # Pause stream to release exclusive hardware channels if any
                    if self._stream and self._stream.active:
                        try:
                            self._stream.stop()
                        except Exception as e:
                            logger.error(f"Error pausing stream: {e}")
                            
                elif not conflicting_app and self.is_yielded:
                    logger.info(f"[MicManager] Conflicting app '{self.yield_reason}' closed. Re-engaging microphone...")
                    self.is_yielded = False
                    self.yield_reason = ""
                    # Resume stream
                    if self._stream and not self._stream.active:
                        try:
                            self._stream.start()
                        except Exception as e:
                            logger.error(f"Error restarting stream: {e}")

            time.sleep(2.0)

    def start(self):
        """Starts the microphone input stream and background watcher."""
        if self.is_running:
            return

        self.is_running = True
        logger.info(f"Initializing microphone stream at {self.sample_rate}Hz...")

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.block_size,
                callback=self._audio_callback
            )
            self._stream.start()
            logger.info("Microphone stream successfully activated.")
        except Exception as e:
            logger.error(f"Failed to open microphone stream: {e}")
            raise

        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def get_audio_frame(self, timeout: float = 0.5):
        """Fetches the next chunk of raw audio from the queue."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        """Safely terminates the microphone stream."""
        self.is_running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error closing stream: {e}")
        logger.info("Microphone stream stopped.")
