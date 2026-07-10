
"""Диалог управления пользовательскими командами и профилями для Nexus AI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QSplitter,
    QWidget,
    QMessageBox
)

from core.command_manager import (
    CommandManager,
    ACTION_OPEN,
    ACTION_CLOSE,
    ACTION_VOLUME_UP,
    ACTION_VOLUME_DOWN,
    ACTION_VOLUME_MUTE,
    ACTION_TEXT,
    ACTION_KEY_PRESS,
    TARGET_WEBSITE,
    TARGET_APP,
    TARGET_PROCESS
)


class CommandsDialog(QDialog):
    """Диалог управления командами и профилями."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление командами")
        self.setMinimumSize(1000, 700)
        self.resize(1000, 700)
        self._manager = CommandManager()
        self._current_command_id: int | None = None
        self._build_ui()
        self._load_profiles()
        self._load_commands()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        
        # Профиль
        profile_group = QGroupBox("Профиль команд")
        profile_layout = QHBoxLayout(profile_group)
        profile_layout.addWidget(QLabel("Текущий профиль:"))
        self._profile_combo = QComboBox()
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_layout.addWidget(self._profile_combo)
        self._add_profile_btn = QPushButton("Добавить профиль")
        self._add_profile_btn.clicked.connect(self._add_profile)
        profile_layout.addWidget(self._add_profile_btn)
        self._delete_profile_btn = QPushButton("Удалить профиль")
        self._delete_profile_btn.clicked.connect(self._delete_profile)
        profile_layout.addWidget(self._delete_profile_btn)
        root_layout.addWidget(profile_group)
        
        # Разделитель
        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter, 1)
        
        # Левая панель - список команд
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.addWidget(QLabel("Список команд:"))
        self._commands_list = QListWidget()
        self._commands_list.itemClicked.connect(self._on_command_selected)
        left_layout.addWidget(self._commands_list)
        
        left_btn_layout = QHBoxLayout()
        self._add_cmd_btn = QPushButton("Добавить")
        self._add_cmd_btn.clicked.connect(self._add_command)
        left_btn_layout.addWidget(self._add_cmd_btn)
        self._delete_cmd_btn = QPushButton("Удалить")
        self._delete_cmd_btn.clicked.connect(self._delete_command)
        left_btn_layout.addWidget(self._delete_cmd_btn)
        left_layout.addLayout(left_btn_layout)
        
        # Правая панель - редактирование команды
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        form_group = QGroupBox("Редактирование команды")
        form_layout = QFormLayout(form_group)
        
        self._trigger_edit = QLineEdit()
        form_layout.addRow("Триггер:", self._trigger_edit)
        
        self._action_combo = QComboBox()
        self._action_combo.addItem("Текстовый ответ", ACTION_TEXT)
        self._action_combo.addItem("Открыть (сайт/приложение)", ACTION_OPEN)
        self._action_combo.addItem("Закрыть (процесс)", ACTION_CLOSE)
        self._action_combo.addItem("Громкость вверх", ACTION_VOLUME_UP)
        self._action_combo.addItem("Громкость вниз", ACTION_VOLUME_DOWN)
        self._action_combo.addItem("Громкость выкл", ACTION_VOLUME_MUTE)
        self._action_combo.addItem("Нажатие клавиши", ACTION_KEY_PRESS)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        form_layout.addRow("Действие:", self._action_combo)
        
        self._target_type_combo = QComboBox()
        self._target_type_combo.addItem("Сайт", TARGET_WEBSITE)
        self._target_type_combo.addItem("Приложение", TARGET_APP)
        self._target_type_combo.addItem("Процесс", TARGET_PROCESS)
        self._target_type_combo.setEnabled(False)
        form_layout.addRow("Тип цели:", self._target_type_combo)
        
        self._target_edit = QLineEdit()
        self._target_edit.setEnabled(False)
        form_layout.addRow("Цель:", self._target_edit)
        
        self._response_edit = QLineEdit()
        form_layout.addRow("Ответ:", self._response_edit)
        
        self._enabled_check = QCheckBox("Команда включена")
        form_layout.addRow("", self._enabled_check)
        
        right_layout.addWidget(form_group)
        
        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self._save_current_command)
        right_layout.addWidget(save_btn)
        right_layout.addStretch()
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        
        # Кнопки OK/Cancel
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        root_layout.addLayout(btn_layout)
        
    def _load_profiles(self):
        self._profile_combo.clear()
        for profile_id, profile_data in self._manager.profiles.items():
            self._profile_combo.addItem(profile_data["name"], profile_id)
        # Установить текущий профиль
        index = self._profile_combo.findData(self._manager.current_profile_name)
        if index >= 0:
            self._profile_combo.setCurrentIndex(index)
        self._update_delete_profile_btn()

    def _update_delete_profile_btn(self):
        current_id = self._profile_combo.currentData()
        self._delete_profile_btn.setEnabled(current_id != "default")

    def _on_profile_changed(self):
        profile_id = self._profile_combo.currentData()
        if profile_id:
            self._manager.set_current_profile(profile_id)
            self._load_commands()
            self._update_delete_profile_btn()

    def _load_commands(self):
        self._commands_list.clear()
        self._current_command_id = None
        self._clear_form()
        for cmd in self._manager.commands:
            self._commands_list.addItem(f"{cmd['trigger']} ({'✓' if cmd['enabled'] else '✗'})")
        self._update_delete_cmd_btn()

    def _update_delete_cmd_btn(self):
        self._delete_cmd_btn.setEnabled(self._commands_list.currentRow() >= 0)

    def _add_profile(self):
        text, ok = QMessageBox.getText(self, "Новый профиль", "Введите название профиля:")
        if ok and text.strip():
            self._manager.add_profile(text.strip())
            self._load_profiles()

    def _delete_profile(self):
        profile_id = self._profile_combo.currentData()
        if profile_id and profile_id != "default":
            reply = QMessageBox.question(
                self, "Подтверждение", 
                f"Вы уверены, что хотите удалить профиль '{self._profile_combo.currentText()}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._manager.delete_profile(profile_id)
                self._load_profiles()

    def _add_command(self):
        self._current_command_id = None
        self._clear_form()
        self._trigger_edit.setFocus()

    def _delete_command(self):
        if self._current_command_id is not None:
            reply = QMessageBox.question(
                self, "Подтверждение", "Вы уверены, что хотите удалить эту команду?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._manager.delete_command(self._current_command_id)
                self._load_commands()

    def _on_command_selected(self, item):
        if not item:
            return
        row = self._commands_list.row(item)
        if 0 <= row < len(self._manager.commands):
            cmd = self._manager.commands[row]
            self._current_command_id = cmd["id"]
            self._trigger_edit.setText(cmd["trigger"])
            
            # Найти и установить действие
            for i in range(self._action_combo.count()):
                if self._action_combo.itemData(i) == cmd["action"]:
                    self._action_combo.setCurrentIndex(i)
                    break
            
            # Найти и установить тип цели
            if cmd.get("target_type"):
                for i in range(self._target_type_combo.count()):
                    if self._target_type_combo.itemData(i) == cmd["target_type"]:
                        self._target_type_combo.setCurrentIndex(i)
                        break
            
            self._target_edit.setText(cmd.get("target", ""))
            self._response_edit.setText(cmd.get("response", ""))
            self._enabled_check.setChecked(cmd.get("enabled", True))
            self._on_action_changed()
        self._update_delete_cmd_btn()

    def _on_action_changed(self):
        action = self._action_combo.currentData()
        if action in [ACTION_OPEN, ACTION_CLOSE, ACTION_KEY_PRESS]:
            if action in [ACTION_OPEN, ACTION_CLOSE]:
                self._target_type_combo.setEnabled(True)
            else:
                self._target_type_combo.setEnabled(False)
            self._target_edit.setEnabled(True)
        else:
            self._target_type_combo.setEnabled(False)
            self._target_edit.setEnabled(False)

    def _clear_form(self):
        self._trigger_edit.clear()
        self._response_edit.clear()
        self._target_edit.clear()
        self._action_combo.setCurrentIndex(0)
        self._target_type_combo.setCurrentIndex(0)
        self._enabled_check.setChecked(True)
        self._on_action_changed()

    def _save_current_command(self):
        if not self._trigger_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите триггер команды!")
            return
        
        if self._current_command_id is None:
            # Добавляем новую команду
            self._current_command_id = self._manager.add_command(
                self._trigger_edit.text().strip(),
                self._action_combo.currentData(),
                self._target_type_combo.currentData() if self._target_type_combo.isEnabled() else None,
                self._target_edit.text().strip(),
                self._response_edit.text().strip(),
                self._enabled_check.isChecked()
            )
            QMessageBox.information(self, "Успешно", "Команда добавлена!")
        else:
            # Обновляем существующую команду
            self._manager.update_command(
                self._current_command_id,
                trigger=self._trigger_edit.text().strip(),
                action=self._action_combo.currentData(),
                target_type=self._target_type_combo.currentData() if self._target_type_combo.isEnabled() else None,
                target=self._target_edit.text().strip(),
                response=self._response_edit.text().strip(),
                enabled=self._enabled_check.isChecked()
            )
            QMessageBox.information(self, "Успешно", "Команда сохранена!")
        self._load_commands()
