"""Audio device management and microphone level monitoring."""

import json
import os
import struct
import threading
import time
from typing import Callable, Optional

import pyaudio

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


class AudioManager:
    """Manages audio input/output devices and microphone level."""

    def __init__(self):
        self._pyaudio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._level_callback: Optional[Callable[[float], None]] = None
        self._current_level = 0.0

    def list_input_devices(self) -> list[dict]:
        devices = []
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": info["name"],
                    "channels": info["maxInputChannels"],
                    "sample_rate": int(info["defaultSampleRate"]),
                })
        return devices

    def list_output_devices(self) -> list[dict]:
        devices = []
        for i in range(self._pyaudio.get_device_count()):
            info = self._pyaudio.get_device_info_by_index(i)
            if info["maxOutputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": info["name"],
                    "channels": info["maxOutputChannels"],
                    "sample_rate": int(info["defaultSampleRate"]),
                })
        return devices

    def get_default_input_index(self) -> Optional[int]:
        try:
            info = self._pyaudio.get_default_input_device_info()
            return info["index"]
        except OSError:
            return None

    def get_default_output_index(self) -> Optional[int]:
        try:
            info = self._pyaudio.get_default_output_device_info()
            return info["index"]
        except OSError:
            return None

    @property
    def current_level(self) -> float:
        return self._current_level

    def start_level_monitor(self, callback: Callable[[float], None], device_index: Optional[int] = None) -> None:
        if self._monitoring:
            self.stop_level_monitor()

        self._level_callback = callback
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(device_index,), daemon=True)
        self._monitor_thread.start()

    def stop_level_monitor(self) -> None:
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _monitor_loop(self, device_index: Optional[int]) -> None:
        try:
            self._stream = self._pyaudio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK,
            )
            while self._monitoring:
                try:
                    data = self._stream.read(CHUNK, exception_on_overflow=False)
                    level = self._calculate_level(data)
                    self._current_level = level
                    if self._level_callback:
                        self._level_callback(level)
                except Exception:
                    time.sleep(0.05)
        except Exception as e:
            print(f"[AudioManager] Monitor error: {e}")
        finally:
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    @staticmethod
    def _calculate_level(data: bytes) -> float:
        count = len(data) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", data)
        rms = (sum(s * s for s in shorts) / count) ** 0.5
        normalized = min(rms / 32768.0 * 5.0, 1.0)
        return normalized

    def cleanup(self) -> None:
        self.stop_level_monitor()
        self._pyaudio.terminate()
