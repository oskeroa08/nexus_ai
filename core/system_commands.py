
"""System command execution: apps, websites, keyboard, processes with custom commands."""

import random
from datetime import datetime
from core.ai_handler import AIHandler
from core.command_manager import CommandManager


class SystemCommands:
    """Parses and executes voice/system commands, including custom user commands."""

    def __init__(self):
        self._ai = AIHandler()
        self._command_manager = CommandManager()
        self._greetings = [
            "Привет! Как дела?",
            "Хай! Рад с тобой общаться!",
            "Приветствую! Чем могу помочь?",
            "Здравствуй! Чем могу быть полезен?",
        ]

    def process(self, text: str) -> str:
        try:
            if not text:
                return "Я не расслышал команду."

            lower_text = text.lower().strip()
            
            # Сначала пытаемся выполнить пользовательскую команду
            custom_response = self._command_manager.execute_command(lower_text)
            if custom_response:
                return custom_response
                
            # Если не нашли пользовательскую команду, проверяем встроенные
            greeting = self._check_greeting(lower_text)
            if greeting:
                return greeting

            time_resp = self._check_time(lower_text)
            if time_resp:
                return time_resp

            date_resp = self._check_date(lower_text)
            if date_resp:
                return date_resp

            # Если ничего не подошло, используем AI
            return self._ai.get_response(text)
            
        except Exception as e:
            print(f"[SystemCommands] Ошибка обработки команды: {e}")
            return f"Произошла ошибка при обработке команды: {e}"

    def _check_greeting(self, text: str) -> str | None:
        greetings = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "хай", "hello"]
        if any(g in text for g in greetings):
            return random.choice(self._greetings)
        return None

    @staticmethod
    def _check_time(text: str) -> str | None:
        triggers = ["который час", "сколько времени", "какое время", "время"]
        if any(t in text for t in triggers):
            now = datetime.now()
            return f"Сейчас {now.strftime('%H:%M')}."
        return None

    @staticmethod
    def _check_date(text: str) -> str | None:
        triggers = ["какое число", "какая дата", "сегодня число", "какой день"]
        if any(t in text for t in triggers):
            now = datetime.now()
            months = [
                "января", "февраля", "марта", "апреля", "мая", "июня",
                "июля", "августа", "сентября", "октября", "ноября", "декабря",
            ]
            return f"Сегодня {now.day} {months[now.month - 1]} {now.year} года."
        return None
