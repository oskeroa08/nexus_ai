"""Главное окно Nexus AI — премиум glassmorphism UI."""

import os
from datetime import datetime

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.audio_manager import AudioManager, load_config, save_config
from core.speech_engine import SpeechEngine
from core.system_commands import SystemCommands
from gui.settings_window import SettingsWindow
from gui.theme import (
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    TOP_BAR_HEIGHT,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from gui.visualizer import AudioVisualizer


class VoiceWorker(QObject):
    """Фоновый обработчик голоса — режим «всегда слушает»."""

    status_changed = Signal(str)
    user_message = Signal(str)
    assistant_message = Signal(str)
    visualizer_state = Signal(str)
    speak_requested = Signal(str)

    def __init__(self, speech: SpeechEngine, commands: SystemCommands):
        super().__init__()
        self._speech = speech
        self._commands = commands
        self._running = True
        self._paused = False

    def set_paused(self, paused: bool) -> None:
        self._paused = paused

    def stop(self) -> None:
        self._running = False

    @Slot()
    def run_loop(self) -> None:
        """Непрерывное прослушивание с проверкой wake word в каждой фразе."""
        while self._running:
            if self._paused:
                self.visualizer_state.emit(AudioVisualizer.STATE_IDLE)
                QThread.msleep(500)
                continue

            config = load_config()
            wake_word = config.get("wake_word", "Нексус")
            device_index = config.get("input_device_index")

            self.visualizer_state.emit(AudioVisualizer.STATE_LISTENING)
            self.status_changed.emit("Слушаю...")

            try:
                text = self._speech.listen(
                    device_index=device_index,
                    timeout=5.0,
                    phrase_limit=5.0,
                )
            except Exception as e:
                print(f"[VoiceWorker] Ошибка прослушивания: {e}")
                QThread.msleep(500)
                continue

            if not self._running or self._paused:
                continue

            if not text:
                continue

            command = SpeechEngine.extract_command(text, wake_word)
            if not command:
                continue

            self._handle_command(text, command)

    def _handle_command(self, full_text: str, command: str) -> None:
        """Обработка распознанной команды."""
        self.visualizer_state.emit(AudioVisualizer.STATE_WAKE)
        self.status_changed.emit("Думаю...")
        self.user_message.emit(full_text)

        self.visualizer_state.emit(AudioVisualizer.STATE_PROCESSING)
        response = self._commands.process(command)
        self.assistant_message.emit(response)

        config = load_config()
        if not config.get("muted", False):
            self.speak_requested.emit(response)

        self.visualizer_state.emit(AudioVisualizer.STATE_IDLE)
        self.status_changed.emit("Слушаю...")


class TTSWorker(QObject):
    """Озвучка ответов в отдельном QThread."""

    speak_start = Signal()
    speak_end = Signal()

    def __init__(self, speech: SpeechEngine):
        super().__init__()
        self._speech = speech
        self._speech.set_speak_callbacks(
            on_start=lambda: self.speak_start.emit(),
            on_end=lambda: self.speak_end.emit(),
        )

    @Slot(str)
    def speak(self, text: str) -> None:
        self._speech.speak(text, blocking=True)


class TTSPreloadWorker(QObject):
    """Предзагрузка Silero при старте."""

    preload_done = Signal(bool)

    def __init__(self, speech: SpeechEngine):
        super().__init__()
        self._speech = speech

    @Slot()
    def run(self) -> None:
        self._speech.preload_tts()
        self.preload_done.emit(self._speech.silero_loaded)


class ChatBubble(QFrame):
    """Пузырь сообщения с текстом и временем."""

    def __init__(self, text: str, role: str, max_width: int, parent=None):
        super().__init__(parent)
        self._role = role
        self._max_width = max_width
        self.setObjectName("userBubble" if role == "user" else "assistantBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 16, 12)
        layout.setSpacing(4)

        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._text_label.setObjectName("bubbleText")
        layout.addWidget(self._text_label)

        time_str = datetime.now().strftime("%H:%M")
        self._time_label = QLabel(time_str)
        self._time_label.setObjectName("bubbleTime")
        self._time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight if role == "user" else Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self._time_label)

        self._apply_max_width()

    def _apply_max_width(self) -> None:
        self.setMaximumWidth(self._max_width)
        self._text_label.setMaximumWidth(self._max_width - 28)

    def update_max_width(self, max_width: int) -> None:
        self._max_width = max_width
        self._apply_max_width()
        self.adjustSize()


class MainWindow(QMainWindow):
    """Главное окно с визуализатором, чатом и голосовым управлением."""

    audio_level = Signal(float)

    def __init__(self):
        super().__init__()
        self._audio = AudioManager()
        self._speech = SpeechEngine()
        self._commands = SystemCommands()
        self._paused = False
        self._has_messages = False
        self._empty_label = None

        self._setup_window()
        self._build_ui()
        self._connect_ui_signals()
        self._setup_voice_thread()
        self._setup_tts_thread()
        self._setup_tts_preload()
        self._start_audio_monitor()

        self._set_status("Готово")
        self._show_empty_state()

    def _setup_window(self) -> None:
        self.setWindowTitle("Nexus AI")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        styles_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(styles_path):
            with open(styles_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _bubble_max_width(self) -> int:
        """70% ширины окна для пузырей."""
        return max(int(self.width() * 0.7), 200)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        max_w = self._bubble_max_width()
        for i in range(self._chat_layout.count()):
            item = self._chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QWidget) and widget.objectName() == "messageRow":
                    bubble = widget.findChild(ChatBubble)
                    if isinstance(bubble, ChatBubble):
                        bubble.update_max_width(max_w)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        root.setSpacing(SPACE_MD)

        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_visualizer(), stretch=2)
        root.addWidget(self._build_chat_area(), stretch=3)

        config = load_config()
        self._mute_btn.setChecked(config.get("muted", False))
        self._update_mute_button()

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(TOP_BAR_HEIGHT)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(SPACE_MD, SPACE_XS, SPACE_MD, SPACE_XS)
        layout.setSpacing(SPACE_SM)

        title = QLabel("NEXUS AI")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addStretch(1)

        self._status_label = QLabel("Инициализация...")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        layout.addStretch(1)

        self._mic_btn = QPushButton("●")
        self._mic_btn.setObjectName("iconButton")
        self._mic_btn.setCheckable(True)
        self._mic_btn.setChecked(True)
        self._mic_btn.setToolTip("Пауза / возобновление")
        self._mic_btn.clicked.connect(self._toggle_mic)
        layout.addWidget(self._mic_btn)

        self._mute_btn = QPushButton("♪")
        self._mute_btn.setObjectName("iconButton")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setToolTip("Вкл/выкл звук")
        self._mute_btn.clicked.connect(self._toggle_mute)
        layout.addWidget(self._mute_btn)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("iconButton")
        settings_btn.setToolTip("Настройки")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        return bar

    def _build_visualizer(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, SPACE_SM, 0, SPACE_SM)

        self._visualizer = AudioVisualizer()
        self._visualizer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._visualizer, alignment=Qt.AlignmentFlag.AlignCenter)

        return container

    def _build_chat_area(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("chatFrame")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(SPACE_SM)

        section = QLabel("ДИАЛОГ")
        section.setObjectName("chatSectionLabel")
        layout.addWidget(section)

        self._chat_scroll = QScrollArea()
        self._chat_scroll.setWidgetResizable(True)
        self._chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._chat_container = QWidget()
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chat_layout.setSpacing(SPACE_MD)
        self._chat_layout.setContentsMargins(SPACE_XS, SPACE_XS, SPACE_XS, SPACE_XS)

        self._chat_scroll.setWidget(self._chat_container)
        layout.addWidget(self._chat_scroll)

        return frame

    def _connect_ui_signals(self) -> None:
        self.audio_level.connect(self._visualizer.set_audio_level)

    def _setup_voice_thread(self) -> None:
        self._voice_thread = QThread()
        self._voice_worker = VoiceWorker(self._speech, self._commands)
        self._voice_worker.moveToThread(self._voice_thread)

        self._voice_thread.started.connect(self._voice_worker.run_loop)
        self._voice_worker.status_changed.connect(self._set_status)
        self._voice_worker.user_message.connect(lambda t: self._add_chat_message(t, "user"))
        self._voice_worker.assistant_message.connect(lambda t: self._add_chat_message(t, "assistant"))
        self._voice_worker.visualizer_state.connect(self._visualizer.set_state)
        self._voice_worker.speak_requested.connect(self._speak_response)

        self._voice_thread.start()

    def _setup_tts_thread(self) -> None:
        self._tts_thread = QThread()
        self._tts_worker = TTSWorker(self._speech)
        self._tts_worker.moveToThread(self._tts_thread)
        self._tts_worker.speak_start.connect(
            lambda: self._visualizer.set_state(AudioVisualizer.STATE_SPEAKING)
        )
        self._tts_worker.speak_end.connect(self._on_speak_finished)
        self._tts_thread.start()

    def _setup_tts_preload(self) -> None:
        """Предзагрузка Silero в отдельном потоке при старте."""
        self._preload_thread = QThread()
        self._preload_worker = TTSPreloadWorker(self._speech)
        self._preload_worker.moveToThread(self._preload_thread)
        self._preload_thread.started.connect(self._preload_worker.run)
        self._preload_worker.preload_done.connect(self._on_preload_done)
        self._preload_thread.start()

    def _on_preload_done(self, success: bool) -> None:
        if success:
            print("[MainWindow] Silero TTS предзагружен")
        else:
            print("[MainWindow] Silero не загружен — будет использован fallback")
        self._preload_thread.quit()

    def _on_speak_finished(self) -> None:
        self._visualizer.set_state(AudioVisualizer.STATE_IDLE)
        if not self._paused:
            self._set_status("Слушаю...")

    def _speak_response(self, text: str) -> None:
        """Отправка текста на озвучку через TTS-поток."""
        QMetaObject.invokeMethod(
            self._tts_worker,
            "speak",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text),
        )

    def _start_audio_monitor(self) -> None:
        config = load_config()
        device_index = config.get("input_device_index")

        def on_level(level: float):
            self.audio_level.emit(level)

        try:
            self._audio.start_level_monitor(on_level, device_index)
        except Exception as e:
            print(f"[MainWindow] Ошибка аудио-монитора: {e}")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _show_empty_state(self) -> None:
        """Пустое состояние чата."""
        config = load_config()
        wake_word = config.get("wake_word", "Нексус")
        self._empty_label = QLabel(f"Скажи «{wake_word}» и задай вопрос")
        self._empty_label.setObjectName("emptyStateLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._chat_layout.addWidget(self._empty_label)

    def _remove_empty_state(self) -> None:
        if self._empty_label:
            self._chat_layout.removeWidget(self._empty_label)
            self._empty_label.deleteLater()
            self._empty_label = None

    def _add_chat_message(self, text: str, role: str) -> None:
        if not self._has_messages:
            self._remove_empty_state()
            self._has_messages = True

        row = QWidget()
        row.setObjectName("messageRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        bubble = ChatBubble(text, role, self._bubble_max_width())

        if role == "user":
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            row_layout.addWidget(bubble)
            row_layout.addStretch()

        count = self._chat_layout.count()
        self._chat_layout.insertWidget(count, row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> None:
        scrollbar = self._chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _toggle_mic(self) -> None:
        self._paused = not self._mic_btn.isChecked()
        self._voice_worker.set_paused(self._paused)
        if self._paused:
            self._mic_btn.setProperty("active", False)
            self._set_status("Пауза")
            self._visualizer.set_state(AudioVisualizer.STATE_IDLE)
        else:
            self._mic_btn.setProperty("active", True)
            self._set_status("Слушаю...")
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)

    def _toggle_mute(self) -> None:
        config = load_config()
        config["muted"] = self._mute_btn.isChecked()
        save_config(config)
        self._update_mute_button()

    def _update_mute_button(self) -> None:
        self._mute_btn.setText("⊘" if self._mute_btn.isChecked() else "♪")

    def _open_settings(self) -> None:
        self._voice_worker.set_paused(True)
        self._paused = True
        self._set_status("Настройки")

        dialog = SettingsWindow(self._audio, self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

        self._paused = not self._mic_btn.isChecked()
        self._voice_worker.set_paused(self._paused)

    def _on_settings_saved(self) -> None:
        self._audio.stop_level_monitor()
        config = load_config()
        self._mute_btn.setChecked(config.get("muted", False))
        self._update_mute_button()

        def on_level(level: float):
            self.audio_level.emit(level)

        try:
            self._audio.start_level_monitor(on_level, config.get("input_device_index"))
        except Exception as e:
            print(f"[MainWindow] Перезапуск монитора: {e}")

        if not self._paused:
            self._set_status("Слушаю...")

    def closeEvent(self, event) -> None:
        self._voice_worker.stop()
        self._voice_thread.quit()
        self._voice_thread.wait(3000)
        self._tts_thread.quit()
        self._tts_thread.wait(3000)
        self._speech.stop_speaking()
        self._audio.cleanup()
        event.accept()
