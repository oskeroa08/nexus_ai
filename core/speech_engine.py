"""Движок распознавания и синтеза речи."""

import asyncio
import os
import subprocess
import tempfile
import threading
from typing import Callable, Optional

import edge_tts
import numpy as np
import speech_recognition as sr

from core.audio_manager import load_config

# Провайдеры TTS
TTS_SILERO = "silero"
TTS_EDGE = "edge"
TTS_NONE = "none"

SILERO_VOICES = ["aidar", "baya", "kseniya", "xenia", "eugene"]
SILERO_SAMPLE_RATE = 48000


class SileroEngine:
    """Оффлайн TTS через Silero v3_4."""

    def __init__(self):
        self._model = None
        self._device = None
        self._loaded = False
        self._load_error: Optional[str] = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def preload(self) -> bool:
        """Загрузка модели Silero (вызывать из фонового потока)."""
        with self._lock:
            if self._loaded:
                return True
            try:
                import torch

                self._device = torch.device("cpu")
                self._model, _ = torch.hub.load(
                    repo_or_dir="snakers4/silero-models",
                    model="silero_tts",
                    language="ru",
                    speaker="v3_4",
                    trust_repo=True,
                )
                self._model.to(self._device)
                self._loaded = True
                self._load_error = None
                print("[Silero] Модель загружена успешно")
                return True
            except Exception as e:
                self._load_error = str(e)
                print(f"[Silero] Ошибка загрузки: {e}")
                return False

    def synthesize(
        self,
        text: str,
        speaker: str = "aidar",
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
    ) -> Optional[np.ndarray]:
        """Синтез речи в numpy-массив."""
        if not self._loaded or self._model is None:
            return None

        with self._lock:
            try:
                audio = self._model.apply_tts(
                    text=text,
                    speaker=speaker,
                    sample_rate=SILERO_SAMPLE_RATE,
                    put_accent=True,
                    put_yo=True,
                )
                audio = np.array(audio, dtype=np.float32)

                # Тон — изменение частоты дискретизации (простой pitch-shift)
                if pitch != 1.0:
                    new_len = int(len(audio) / pitch)
                    indices = np.linspace(0, len(audio) - 1, new_len)
                    audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

                # Скорость — ресемплинг
                if speed != 1.0:
                    new_len = int(len(audio) / speed)
                    indices = np.linspace(0, len(audio) - 1, max(new_len, 1))
                    audio = np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

                # Громкость
                if volume != 1.0:
                    audio = np.clip(audio * volume, -1.0, 1.0)

                return audio
            except Exception as e:
                print(f"[Silero] Ошибка синтеза: {e}")
                return None


class SpeechEngine:
    """STT через SpeechRecognition, TTS через Silero / Edge / pyttsx3."""

    def __init__(self):
        self._recognizer = sr.Recognizer()
        self._apply_energy_threshold()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.6
        self._speaking = False
        self._stop_speaking = threading.Event()
        self._on_speak_start: Optional[Callable] = None
        self._on_speak_end: Optional[Callable] = None
        self._silero = SileroEngine()
        self._pyttsx3_engine = None

    def _apply_energy_threshold(self) -> None:
        config = load_config()
        self._recognizer.energy_threshold = config.get("energy_threshold", 300)

    def set_speak_callbacks(self, on_start: Callable, on_end: Callable) -> None:
        """Колбэки вызываются из фонового потока — только emit сигналов!"""
        self._on_speak_start = on_start
        self._on_speak_end = on_end

    def preload_tts(self) -> None:
        """Предзагрузка Silero в фоне."""
        config = load_config()
        if config.get("tts_provider", TTS_SILERO) == TTS_SILERO:
            self._silero.preload()

    @property
    def silero_loaded(self) -> bool:
        return self._silero.is_loaded

    def listen(
        self,
        device_index: Optional[int] = None,
        timeout: float = 5.0,
        phrase_limit: float = 5.0,
    ) -> Optional[str]:
        """Непрерывное прослушивание одной фразы."""
        self._apply_energy_threshold()
        try:
            with sr.Microphone(device_index=device_index) as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.2)
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
            config = load_config()
            text = self._recognizer.recognize_google(
                audio, language=config.get("language", "ru-RU")
            )
            return text.strip()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"[SpeechEngine] Ошибка прослушивания: {e}")
            return None

    @staticmethod
    def extract_command(text: str, wake_word: str) -> Optional[str]:
        """Извлекает команду, если фраза начинается с wake word."""
        if not text or not wake_word:
            return None

        text_clean = text.strip()
        text_lower = text_clean.lower()
        wake_lower = wake_word.lower().strip()

        # Прямое совпадение в начале
        if text_lower.startswith(wake_lower):
            command = text_clean[len(wake_word):].strip().lstrip(",.:;!?—–- ")
            return command if command else None

        # Wake word как первое слово (с учётом запятых)
        words = text_lower.replace(",", " ").split()
        wake_parts = wake_lower.split()
        if len(words) >= len(wake_parts):
            matched = all(words[i] == wake_parts[i] for i in range(len(wake_parts)))
            if matched:
                # Восстанавливаем команду из оригинального текста
                original_words = text_clean.split()
                command = " ".join(original_words[len(wake_parts):]).strip().lstrip(",.:;!?—–- ")
                return command if command else None

        return None

    def speak(self, text: str, blocking: bool = True) -> None:
        if not text:
            return
        config = load_config()
        if config.get("muted", False):
            return

        provider = config.get("tts_provider", TTS_SILERO)
        if provider == TTS_NONE:
            return

        if blocking:
            self._do_speak(text, config)
        else:
            thread = threading.Thread(target=self._do_speak, args=(text, config), daemon=True)
            thread.start()

    def stop_speaking(self) -> None:
        self._stop_speaking.set()

    def _do_speak(self, text: str, config: dict) -> None:
        self._speaking = True
        self._stop_speaking.clear()
        if self._on_speak_start:
            self._on_speak_start()

        try:
            provider = config.get("tts_provider", TTS_SILERO)
            if provider == TTS_SILERO:
                success = self._speak_silero(text, config)
                if not success:
                    self._speak_pyttsx3(text)
            elif provider == TTS_EDGE:
                self._speak_edge(text, config)
        except Exception as e:
            print(f"[SpeechEngine] Ошибка озвучки: {e}")
        finally:
            self._speaking = False
            if self._on_speak_end:
                self._on_speak_end()

    def _speak_silero(self, text: str, config: dict) -> bool:
        """Silero TTS с fallback на pyttsx3."""
        if not self._silero.is_loaded:
            if not self._silero.preload():
                return False

        speaker = config.get("silero_voice", "aidar")
        speed = float(config.get("tts_speed", 1.0))
        pitch = float(config.get("tts_pitch", 1.0))
        volume = float(config.get("tts_volume_level", 1.0))

        audio = self._silero.synthesize(text, speaker, speed, pitch, volume)
        if audio is None:
            return False

        if self._stop_speaking.is_set():
            return True

        return self._play_wav_array(audio, SILERO_SAMPLE_RATE)

    def _speak_pyttsx3(self, text: str) -> None:
        """Fallback TTS через pyttsx3."""
        try:
            import pyttsx3

            if self._pyttsx3_engine is None:
                self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        except Exception as e:
            print(f"[SpeechEngine] pyttsx3 fallback ошибка: {e}")

    def _speak_edge(self, text: str, config: dict) -> None:
        """Edge TTS (онлайн)."""
        tmp_path = None
        try:
            voice = config.get("tts_voice", "ru-RU-SvetlanaNeural")
            rate = config.get("tts_rate", "+0%")
            volume = config.get("tts_volume", "+0%")

            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(tmp_fd)

            asyncio.run(self._synthesize_edge(text, voice, rate, volume, tmp_path))

            if self._stop_speaking.is_set():
                return

            self._play_file(tmp_path)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    async def _synthesize_edge(text: str, voice: str, rate: str, volume: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
        await communicate.save(output_path)

    def _play_wav_array(self, audio: np.ndarray, sample_rate: int) -> bool:
        """Сохранение и воспроизведение WAV."""
        import soundfile as sf

        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)
            sf.write(tmp_path, audio, sample_rate)
            if self._stop_speaking.is_set():
                return True
            self._play_file(tmp_path)
            return True
        except Exception as e:
            print(f"[SpeechEngine] Ошибка воспроизведения WAV: {e}")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def _play_file(self, path: str) -> None:
        """Воспроизведение аудиофайла через PowerShell."""
        safe_path = path.replace("'", "''")
        script = (
            "Add-Type -AssemblyName presentationCore; "
            f"$player = New-Object System.Windows.Media.MediaPlayer; "
            f"$player.Open([Uri]::new('file:///{safe_path.replace(chr(92), '/')}')); "
            "$player.Play(); "
            "Start-Sleep -Milliseconds 500; "
            "while ($player.NaturalDuration.HasTimeSpan -eq $false) { Start-Sleep -Milliseconds 100 }; "
            "$duration = $player.NaturalDuration.TimeSpan.TotalSeconds + 0.5; "
            "Start-Sleep -Seconds $duration"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=False,
                capture_output=True,
            )
        except Exception as e:
            print(f"[SpeechEngine] Ошибка воспроизведения: {e}")

    @property
    def is_speaking(self) -> bool:
        return self._speaking
