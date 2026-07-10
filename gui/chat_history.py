
"""Chat history widget with message bubbles and error displays."""

from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class ChatBubble(QFrame):
    """Single chat bubble for user or assistant."""

    def __init__(self, text: str, role: str, max_width_percent: int = 80, parent=None):
        super().__init__(parent)
        self._role = role
        self._max_width_percent = max_width_percent
        self.setObjectName("userBubble" if role == "user" else "assistantBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
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

    def set_text(self, text: str) -> None:
        self._text_label.setText(text)


class ErrorMessage(QFrame):
    """Error message display widget (centered, stretched)."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("errorMessage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._text_label.setObjectName("errorText")
        layout.addWidget(self._text_label)

    def set_text(self, text: str) -> None:
        self._text_label.setText(text)


class ChatHistory(QWidget):
    """Main chat history container with scrollable messages."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatHistory")
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(12)
        self._layout.setContentsMargins(8, 8, 8, 8)

    def add_user_message(self, text: str) -> None:
        """Add a user message bubble to the chat (right-aligned)."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addStretch()
        bubble = ChatBubble(text, "user")
        row_layout.addWidget(bubble)
        self._layout.addWidget(row)

    def add_assistant_message(self, text: str) -> None:
        """Add an assistant message bubble to the chat (left-aligned)."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        bubble = ChatBubble(text, "assistant")
        row_layout.addWidget(bubble)
        row_layout.addStretch()
        self._layout.addWidget(row)

    def add_error_message(self, text: str) -> None:
        """Add an error message to the chat (centered, stretched)."""
        error = ErrorMessage(text)
        self._layout.addWidget(error)

    def clear(self) -> None:
        """Clear all messages from the chat history."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
