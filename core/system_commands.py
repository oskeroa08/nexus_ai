"""System command execution: apps, websites, keyboard, processes."""

import os
import subprocess
import webbrowser
from datetime import datetime

import psutil
from pynput.keyboard import Controller, Key

from core.ai_handler import AIHandler


keyboard = Controller()


class SystemCommands:
    """Parses and executes voice/system commands."""

    def __init__(self):
        self._ai = AIHandler()

    def process(self, text: str) -> str:
        if not text:
            return "Я не расслышала команду."

        lower = text.lower().strip()

        greeting = self._check_greeting(lower)
        if greeting:
            return greeting

        time_resp = self._check_time(lower)
        if time_resp:
            return time_resp

        date_resp = self._check_date(lower)
        if date_resp:
            return date_resp

        open_resp = self._check_open(lower)
        if open_resp:
            return open_resp

        key_resp = self._check_keyboard(lower)
        if key_resp:
            return key_resp

        kill_resp = self._check_kill_process(lower)
        if kill_resp:
            return kill_resp

        volume_resp = self._check_volume(lower)
        if volume_resp:
            return volume_resp

        return self._ai.get_response(text)

    @staticmethod
    def _check_greeting(text: str) -> str | None:
        greetings = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "хай", "hello"]
        if any(g in text for g in greetings):
            return "Привет! Я Nexus AI, ваш голосовой помощник. Чем могу помочь?"
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

    def _check_open(self, text: str) -> str | None:
        if "открой" not in text and "запусти" not in text and "открыть" not in text:
            return None

        apps = {
            "браузер": self._open_browser,
            "browser": self._open_browser,
            "chrome": lambda: self._open_app("chrome"),
            "хром": lambda: self._open_app("chrome"),
            "firefox": lambda: self._open_app("firefox"),
            "edge": lambda: self._open_app("msedge"),
            "блокнот": lambda: self._open_app("notepad"),
            "notepad": lambda: self._open_app("notepad"),
            "калькулятор": lambda: self._open_app("calc"),
            "calculator": lambda: self._open_app("calc"),
            "проводник": lambda: self._open_app("explorer"),
            "explorer": lambda: self._open_app("explorer"),
            "youtube": lambda: webbrowser.open("https://youtube.com"),
            "ютуб": lambda: webbrowser.open("https://youtube.com"),
            "google": lambda: webbrowser.open("https://google.com"),
            "гугл": lambda: webbrowser.open("https://google.com"),
            "github": lambda: webbrowser.open("https://github.com"),
            "telegram": lambda: self._open_app("telegram"),
            "телеграм": lambda: self._open_app("telegram"),
            "discord": lambda: self._open_app("discord"),
            "дискорд": lambda: self._open_app("discord"),
            "spotify": lambda: self._open_app("spotify"),
            "спотифай": lambda: self._open_app("spotify"),
            "vscode": lambda: self._open_app("code"),
            "код": lambda: self._open_app("code"),
        }

        for keyword, action in apps.items():
            if keyword in text:
                try:
                    action()
                    return f"Открываю {keyword}."
                except Exception as e:
                    return f"Не удалось открыть {keyword}: {e}"

        if "сайт" in text or "http" in text:
            for word in text.split():
                if word.startswith("http"):
                    webbrowser.open(word)
                    return "Открываю сайт."

        return None

    @staticmethod
    def _open_browser() -> None:
        webbrowser.open("https://google.com")

    @staticmethod
    def _open_app(name: str) -> None:
        try:
            os.startfile(name)
        except OSError:
            subprocess.Popen(name, shell=True)

    @staticmethod
    def _check_keyboard(text: str) -> str | None:
        key_map = {
            "enter": Key.enter,
            "энтер": Key.enter,
            "escape": Key.esc,
            "эскейп": Key.esc,
            "tab": Key.tab,
            "таб": Key.tab,
            "space": Key.space,
            "пробел": Key.space,
            "backspace": Key.backspace,
            "бэкспейс": Key.backspace,
            "delete": Key.delete,
            "удалить": Key.delete,
        }

        if "нажми" in text or "нажать" in text:
            for name, key in key_map.items():
                if name in text:
                    keyboard.press(key)
                    keyboard.release(key)
                    return f"Нажала {name}."

            combos = {
                "ctrl c": [Key.ctrl, "c"],
                "контрол ц": [Key.ctrl, "c"],
                "ctrl v": [Key.ctrl, "v"],
                "контрол в": [Key.ctrl, "v"],
                "ctrl z": [Key.ctrl, "z"],
                "alt tab": [Key.alt, Key.tab],
                "альт таб": [Key.alt, Key.tab],
                "win d": [Key.cmd, "d"],
                "windows d": [Key.cmd, "d"],
            }
            for combo_name, keys in combos.items():
                if combo_name in text:
                    for k in keys:
                        keyboard.press(k)
                    for k in reversed(keys):
                        keyboard.release(k)
                    return f"Выполнила комбинацию {combo_name}."

        return None

    @staticmethod
    def _check_kill_process(text: str) -> str | None:
        triggers = ["закрой процесс", "заверши процесс", "убей процесс", "останови процесс"]
        if not any(t in text for t in triggers):
            return None

        words = text.split()
        process_name = None
        for i, word in enumerate(words):
            if word in ("процесс", "приложение", "программу") and i + 1 < len(words):
                process_name = words[i + 1]
                break

        if not process_name:
            for word in words:
                if word.endswith(".exe"):
                    process_name = word
                    break

        if not process_name:
            return "Укажите имя процесса, например: закрой процесс notepad."

        if not process_name.endswith(".exe"):
            process_name += ".exe"

        killed = 0
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == process_name.lower():
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed:
            return f"Завершила {killed} процесс(ов) {process_name}."
        return f"Процесс {process_name} не найден."

    @staticmethod
    def _check_volume(text: str) -> str | None:
        if "громкость" not in text:
            return None
        if "увелич" in text or "прибав" in text or "громче" in text:
            for _ in range(5):
                keyboard.press(Key.media_volume_up)
                keyboard.release(Key.media_volume_up)
            return "Увеличила громкость."
        if "уменьш" in text or "убав" in text or "тише" in text:
            for _ in range(5):
                keyboard.press(Key.media_volume_down)
                keyboard.release(Key.media_volume_down)
            return "Уменьшила громкость."
        if "выключ" in text or "без звука" in text or "mute" in text:
            keyboard.press(Key.media_volume_mute)
            keyboard.release(Key.media_volume_mute)
            return "Выключила звук."
        return None
