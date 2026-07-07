"""Окно настроек Nexus AI — карточный премиум-стиль."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.ai_handler import PROVIDER_GROQ, PROVIDER_NONE, PROVIDER_OPENAI
from core.audio_manager import AudioManager, load_config, save_config
from core.speech_engine import SILERO_VOICES, TTS_EDGE, TTS_NONE, TTS_SILERO
from gui.theme import GROQ_MODELS, OPENAI_MODELS, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL


class SettingsWindow(QDialog):
    """Диалог настроек с карточной компоновкой."""

    settings_saved = Signal()

    def __init__(self, audio_manager: AudioManager, parent=None):
        super().__init__(parent)
        self._audio = audio_manager
        self.setObjectName("settingsDialog")
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_MD)
        layout.setContentsMargins(SPACE_XL, SPACE_XL, SPACE_XL, SPACE_XL)

        title = QLabel("Настройки")
        title.setObjectName("settingsTitle")
        layout.addWidget(title)

        layout.addWidget(self._build_general_card())
        layout.addWidget(self._build_ai_card())
        layout.addWidget(self._build_audio_card())
        layout.addLayout(self._build_buttons())

    def _build_card(self, title_text: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        card_layout.setSpacing(SPACE_SM)

        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        card_layout.addWidget(title)

        return card, card_layout

    def _add_field(self, grid: QGridLayout, row: int, label_text: str, widget: QWidget) -> None:
        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        grid.addWidget(label, row, 0)
        grid.addWidget(widget, row, 1)

    def _build_general_card(self) -> QFrame:
        card, card_layout = self._build_card("Общие")
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE_MD)
        grid.setVerticalSpacing(SPACE_SM)
        grid.setColumnStretch(1, 1)

        self._wake_word = QLineEdit()
        self._wake_word.setPlaceholderText("Нексус")
        self._add_field(grid, 0, "Имя ассистента", self._wake_word)

        card_layout.addLayout(grid)
        return card

    def _build_ai_card(self) -> QFrame:
        card, card_layout = self._build_card("Искусственный интеллект")
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE_MD)
        grid.setVerticalSpacing(SPACE_SM)
        grid.setColumnStretch(1, 1)

        self._provider = QComboBox()
        self._provider.addItem("OpenAI", PROVIDER_OPENAI)
        self._provider.addItem("Groq", PROVIDER_GROQ)
        self._provider.addItem("Без AI", PROVIDER_NONE)
        self._provider.currentIndexChanged.connect(self._on_provider_changed)
        self._add_field(grid, 0, "Провайдер", self._provider)

        self._openai_key = QLineEdit()
        self._openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._openai_key.setPlaceholderText("sk-...")
        self._add_field(grid, 1, "OpenAI Key", self._openai_key)

        self._groq_key = QLineEdit()
        self._groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._groq_key.setPlaceholderText("gsk_...")
        self._add_field(grid, 2, "Groq Key", self._groq_key)

        self._openai_model = QComboBox()
        self._openai_model.addItems(OPENAI_MODELS)
        self._add_field(grid, 3, "OpenAI Модель", self._openai_model)

        self._groq_model = QComboBox()
        self._groq_model.addItems(GROQ_MODELS)
        self._add_field(grid, 4, "Groq Модель", self._groq_model)

        card_layout.addLayout(grid)
        return card

    def _build_audio_card(self) -> QFrame:
        card, card_layout = self._build_card("Аудио")
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACE_MD)
        grid.setVerticalSpacing(SPACE_SM)
        grid.setColumnStretch(1, 1)

        self._input_device = QComboBox()
        self._populate_input_devices()
        self._add_field(grid, 0, "Микрофон", self._input_device)

        self._output_device = QComboBox()
        self._populate_output_devices()
        self._add_field(grid, 1, "Вывод", self._output_device)

        # Порог чувствительности микрофона
        energy_row = QHBoxLayout()
        self._energy_threshold = QSlider(Qt.Orientation.Horizontal)
        self._energy_threshold.setRange(100, 800)
        self._energy_threshold.setValue(300)
        self._energy_label = QLabel("300")
        self._energy_label.setObjectName("fieldLabel")
        self._energy_threshold.valueChanged.connect(
            lambda v: self._energy_label.setText(str(v))
        )
        energy_row.addWidget(self._energy_threshold)
        energy_row.addWidget(self._energy_label)
        self._add_field(grid, 2, "Чувствительность", self._wrap_layout(energy_row))

        # Провайдер TTS
        self._tts_provider = QComboBox()
        self._tts_provider.addItem("Silero (оффлайн)", TTS_SILERO)
        self._tts_provider.addItem("Edge TTS (онлайн)", TTS_EDGE)
        self._tts_provider.addItem("Без озвучки", TTS_NONE)
        self._tts_provider.currentIndexChanged.connect(self._on_tts_provider_changed)
        self._add_field(grid, 3, "TTS провайдер", self._tts_provider)

        # Стек настроек голоса для Silero / Edge
        self._tts_settings_stack = QStackedWidget()

        # Silero настройки
        silero_widget = QWidget()
        silero_grid = QGridLayout(silero_widget)
        silero_grid.setHorizontalSpacing(SPACE_MD)
        silero_grid.setVerticalSpacing(SPACE_SM)
        silero_grid.setColumnStretch(1, 1)

        self._silero_voice = QComboBox()
        self._silero_voice.addItems(SILERO_VOICES)
        silero_grid.addWidget(QLabel("Голос"), 0, 0)
        silero_grid.addWidget(self._silero_voice, 0, 1)

        self._tts_speed = QSlider(Qt.Orientation.Horizontal)
        self._tts_speed.setRange(80, 150)
        self._tts_speed.setValue(100)
        self._speed_label = QLabel("1.0x")
        self._speed_label.setObjectName("fieldLabel")
        self._tts_speed.valueChanged.connect(self._on_speed_changed)
        speed_row = QHBoxLayout()
        speed_row.addWidget(self._tts_speed)
        speed_row.addWidget(self._speed_label)
        silero_grid.addWidget(QLabel("Скорость"), 1, 0)
        silero_grid.addWidget(self._wrap_layout(speed_row), 1, 1)

        self._tts_pitch = QSlider(Qt.Orientation.Horizontal)
        self._tts_pitch.setRange(80, 120)
        self._tts_pitch.setValue(100)
        self._pitch_label = QLabel("1.0")
        self._pitch_label.setObjectName("fieldLabel")
        self._tts_pitch.valueChanged.connect(self._on_pitch_changed)
        pitch_row = QHBoxLayout()
        pitch_row.addWidget(self._tts_pitch)
        pitch_row.addWidget(self._pitch_label)
        silero_grid.addWidget(QLabel("Тон"), 2, 0)
        silero_grid.addWidget(self._wrap_layout(pitch_row), 2, 1)

        self._tts_volume_level = QSlider(Qt.Orientation.Horizontal)
        self._tts_volume_level.setRange(50, 150)
        self._tts_volume_level.setValue(100)
        self._vol_level_label = QLabel("100%")
        self._vol_level_label.setObjectName("fieldLabel")
        self._tts_volume_level.valueChanged.connect(self._on_vol_level_changed)
        vol_row = QHBoxLayout()
        vol_row.addWidget(self._tts_volume_level)
        vol_row.addWidget(self._vol_level_label)
        silero_grid.addWidget(QLabel("Громкость"), 3, 0)
        silero_grid.addWidget(self._wrap_layout(vol_row), 3, 1)

        self._tts_settings_stack.addWidget(silero_widget)

        # Edge TTS настройки
        edge_widget = QWidget()
        edge_grid = QGridLayout(edge_widget)
        edge_grid.setHorizontalSpacing(SPACE_MD)
        edge_grid.setVerticalSpacing(SPACE_SM)
        edge_grid.setColumnStretch(1, 1)

        self._tts_voice = QComboBox()
        self._tts_voice.addItems([
            "ru-RU-SvetlanaNeural",
            "ru-RU-DmitryNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
        ])
        edge_grid.addWidget(QLabel("Голос"), 0, 0)
        edge_grid.addWidget(self._tts_voice, 0, 1)

        self._tts_rate = QSlider(Qt.Orientation.Horizontal)
        self._tts_rate.setRange(-50, 50)
        self._tts_rate.setValue(0)
        self._rate_label = QLabel("+0%")
        self._rate_label.setObjectName("fieldLabel")
        self._tts_rate.valueChanged.connect(self._on_rate_changed)
        rate_row = QHBoxLayout()
        rate_row.addWidget(self._tts_rate)
        rate_row.addWidget(self._rate_label)
        edge_grid.addWidget(QLabel("Скорость"), 1, 0)
        edge_grid.addWidget(self._wrap_layout(rate_row), 1, 1)

        self._tts_volume = QSlider(Qt.Orientation.Horizontal)
        self._tts_volume.setRange(-50, 50)
        self._tts_volume.setValue(0)
        self._volume_label = QLabel("+0%")
        self._volume_label.setObjectName("fieldLabel")
        self._tts_volume.valueChanged.connect(self._on_volume_changed)
        volume_row = QHBoxLayout()
        volume_row.addWidget(self._tts_volume)
        volume_row.addWidget(self._volume_label)
        edge_grid.addWidget(QLabel("Громкость"), 2, 0)
        edge_grid.addWidget(self._wrap_layout(volume_row), 2, 1)

        self._tts_settings_stack.addWidget(edge_widget)

        # Пустой виджет для TTS None
        none_widget = QWidget()
        none_layout = QVBoxLayout(none_widget)
        none_label = QLabel("Озвучка отключена")
        none_label.setObjectName("fieldLabel")
        none_layout.addWidget(none_label)
        self._tts_settings_stack.addWidget(none_widget)

        self._add_field(grid, 4, "Настройки TTS", self._tts_settings_stack)

        self._muted = QCheckBox("Без звука")
        self._add_field(grid, 5, "", self._muted)

        card_layout.addLayout(grid)
        return card

    @staticmethod
    def _wrap_layout(layout: QHBoxLayout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _build_buttons(self) -> QHBoxLayout:
        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("ghostButton")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)

        return buttons

    def _populate_input_devices(self) -> None:
        self._input_device.clear()
        self._input_device.addItem("По умолчанию", None)
        for dev in self._audio.list_input_devices():
            self._input_device.addItem(dev["name"], dev["index"])

    def _populate_output_devices(self) -> None:
        self._output_device.clear()
        self._output_device.addItem("По умолчанию", None)
        for dev in self._audio.list_output_devices():
            self._output_device.addItem(dev["name"], dev["index"])

    def _on_provider_changed(self) -> None:
        provider = self._provider.currentData()
        openai_on = provider == PROVIDER_OPENAI
        groq_on = provider == PROVIDER_GROQ

        self._openai_key.setEnabled(openai_on)
        self._openai_model.setEnabled(openai_on)
        self._groq_key.setEnabled(groq_on)
        self._groq_model.setEnabled(groq_on)

    def _on_tts_provider_changed(self) -> None:
        provider = self._tts_provider.currentData()
        if provider == TTS_SILERO:
            self._tts_settings_stack.setCurrentIndex(0)
        elif provider == TTS_EDGE:
            self._tts_settings_stack.setCurrentIndex(1)
        else:
            self._tts_settings_stack.setCurrentIndex(2)

    def _on_speed_changed(self, value: int) -> None:
        self._speed_label.setText(f"{value / 100:.1f}x")

    def _on_pitch_changed(self, value: int) -> None:
        self._pitch_label.setText(f"{value / 100:.1f}")

    def _on_vol_level_changed(self, value: int) -> None:
        self._vol_level_label.setText(f"{value}%")

    def _on_rate_changed(self, value: int) -> None:
        sign = "+" if value >= 0 else ""
        self._rate_label.setText(f"{sign}{value}%")

    def _on_volume_changed(self, value: int) -> None:
        sign = "+" if value >= 0 else ""
        self._volume_label.setText(f"{sign}{value}%")

    def _load_settings(self) -> None:
        config = load_config()

        self._wake_word.setText(config.get("wake_word", "Нексус"))
        self._openai_key.setText(config.get("openai_api_key", ""))
        self._groq_key.setText(config.get("groq_api_key", ""))

        provider = config.get("ai_provider", PROVIDER_GROQ)
        for i in range(self._provider.count()):
            if self._provider.itemData(i) == provider:
                self._provider.setCurrentIndex(i)
                break

        openai_model = config.get("openai_model", "gpt-4o-mini")
        idx = self._openai_model.findText(openai_model)
        if idx >= 0:
            self._openai_model.setCurrentIndex(idx)

        groq_model = config.get("groq_model", GROQ_MODELS[0])
        gidx = self._groq_model.findText(groq_model)
        if gidx >= 0:
            self._groq_model.setCurrentIndex(gidx)

        self._set_device_index(self._input_device, config.get("input_device_index"))
        self._set_device_index(self._output_device, config.get("output_device_index"))

        self._energy_threshold.setValue(config.get("energy_threshold", 300))

        tts_provider = config.get("tts_provider", TTS_SILERO)
        for i in range(self._tts_provider.count()):
            if self._tts_provider.itemData(i) == tts_provider:
                self._tts_provider.setCurrentIndex(i)
                break

        silero_voice = config.get("silero_voice", "aidar")
        svidx = self._silero_voice.findText(silero_voice)
        if svidx >= 0:
            self._silero_voice.setCurrentIndex(svidx)

        speed = config.get("tts_speed", 1.0)
        self._tts_speed.setValue(int(float(speed) * 100))

        pitch = config.get("tts_pitch", 1.0)
        self._tts_pitch.setValue(int(float(pitch) * 100))

        vol_level = config.get("tts_volume_level", 1.0)
        self._tts_volume_level.setValue(int(float(vol_level) * 100))

        voice = config.get("tts_voice", "ru-RU-SvetlanaNeural")
        vidx = self._tts_voice.findText(voice)
        if vidx >= 0:
            self._tts_voice.setCurrentIndex(vidx)

        self._set_slider_value(self._tts_rate, config.get("tts_rate", "+0%"))
        self._set_slider_value(self._tts_volume, config.get("tts_volume", "+0%"))
        self._muted.setChecked(config.get("muted", False))
        self._on_provider_changed()
        self._on_tts_provider_changed()

    @staticmethod
    def _set_device_index(combo: QComboBox, index) -> None:
        if index is not None:
            for i in range(combo.count()):
                if combo.itemData(i) == index:
                    combo.setCurrentIndex(i)
                    break

    def _set_slider_value(self, slider: QSlider, value_str: str) -> None:
        try:
            slider.setValue(int(value_str.replace("%", "").replace("+", "")))
        except ValueError:
            slider.setValue(0)

    def _save(self) -> None:
        rate_val = self._tts_rate.value()
        vol_val = self._tts_volume.value()
        rate_sign = "+" if rate_val >= 0 else ""
        vol_sign = "+" if vol_val >= 0 else ""

        config = load_config()
        config["wake_word"] = self._wake_word.text().strip() or "Нексус"
        config["ai_provider"] = self._provider.currentData()
        config["openai_api_key"] = self._openai_key.text().strip()
        config["groq_api_key"] = self._groq_key.text().strip()
        config["openai_model"] = self._openai_model.currentText()
        config["groq_model"] = self._groq_model.currentText()
        config["input_device_index"] = self._input_device.currentData()
        config["output_device_index"] = self._output_device.currentData()
        config["energy_threshold"] = self._energy_threshold.value()
        config["tts_provider"] = self._tts_provider.currentData()
        config["silero_voice"] = self._silero_voice.currentText()
        config["tts_speed"] = round(self._tts_speed.value() / 100, 2)
        config["tts_pitch"] = round(self._tts_pitch.value() / 100, 2)
        config["tts_volume_level"] = round(self._tts_volume_level.value() / 100, 2)
        config["tts_voice"] = self._tts_voice.currentText()
        config["tts_rate"] = f"{rate_sign}{rate_val}%"
        config["tts_volume"] = f"{vol_sign}{vol_val}%"
        config["muted"] = self._muted.isChecked()

        save_config(config)
        self.settings_saved.emit()
        self.accept()
