
"""Менеджер пользовательских команд и профилей для Nexus AI."""

import os
import json
import random
import subprocess
import webbrowser
from typing import Dict, List, Optional, Any
from pynput.keyboard import Controller, Key
import psutil


# Константы для типов действий
ACTION_OPEN = "open"
ACTION_CLOSE = "close"
ACTION_VOLUME_UP = "volume_up"
ACTION_VOLUME_DOWN = "volume_down"
ACTION_VOLUME_MUTE = "volume_mute"
ACTION_TEXT = "text"  # Просто ответ текстом
ACTION_KEY_PRESS = "key_press"  # Нажатие клавиши

# Типы целей
TARGET_WEBSITE = "website"
TARGET_APP = "app"
TARGET_PROCESS = "process"


class CommandManager:
    """Менеджер команд и профилей."""

    def __init__(self):
        self._config_dir = self._get_config_dir()
        self._commands_file = os.path.join(self._config_dir, "commands.json")
        self._profiles_file = os.path.join(self._config_dir, "profiles.json")
        self.keyboard = Controller()
        
        # Загружаем профили и команды
        self.profiles: Dict[str, Dict] = self._load_profiles()
        self.current_profile_name: str = self._get_current_profile()
        self.commands: List[Dict] = self._load_commands()
        
    def _get_config_dir(self) -> str:
        """Получает путь к директории с конфигами."""
        if os.name == "nt":  # Windows
            base_dir = os.path.expandvars("%APPDATA%\\NexusAI")
        else:
            base_dir = os.path.expanduser("~/.nexusai")
        os.makedirs(base_dir, exist_ok=True)
        return base_dir
        
    def _load_profiles(self) -> Dict[str, Dict]:
        """Загружает профили из файла."""
        default_profiles = {
            "default": {
                "name": "По умолчанию",
                "description": "Стандартный набор команд"
            }
        }
        try:
            if os.path.exists(self._profiles_file):
                with open(self._profiles_file, "r", encoding="utf-8") as f:
                    return {**default_profiles, **json.load(f)}
            return default_profiles
        except Exception as e:
            print(f"[CommandManager] Ошибка загрузки профилей: {e}")
            return default_profiles
            
    def _save_profiles(self):
        """Сохраняет профили в файл."""
        try:
            with open(self._profiles_file, "w", encoding="utf-8") as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[CommandManager] Ошибка сохранения профилей: {e}")
            
    def _get_current_profile(self) -> str:
        """Получает имя текущего профиля (из основной конфигурации)."""
        try:
            from core.audio_manager import load_config
            config = load_config()
            return config.get("current_command_profile", "default")
        except Exception as e:
            print(f"[CommandManager] Ошибка получения текущего профиля: {e}")
            return "default"
            
    def set_current_profile(self, profile_name: str):
        """Устанавливает текущий профиль."""
        try:
            from core.audio_manager import load_config, save_config
            config = load_config()
            config["current_command_profile"] = profile_name
            save_config(config)
            self.current_profile_name = profile_name
            self.commands = self._load_commands()
        except Exception as e:
            print(f"[CommandManager] Ошибка установки профиля: {e}")
            
    def _load_commands(self) -> List[Dict]:
        """Загружает команды текущего профиля из файла."""
        try:
            if os.path.exists(self._commands_file):
                with open(self._commands_file, "r", encoding="utf-8") as f:
                    all_commands = json.load(f)
                    return all_commands.get(self.current_profile_name, self._get_default_commands())
            return self._get_default_commands()
        except Exception as e:
            print(f"[CommandManager] Ошибка загрузки команд: {e}")
            return self._get_default_commands()
            
    def _save_commands(self):
        """Сохраняет команды текущего профиля в файл."""
        try:
            all_commands = {}
            if os.path.exists(self._commands_file):
                with open(self._commands_file, "r", encoding="utf-8") as f:
                    all_commands = json.load(f)
            all_commands[self.current_profile_name] = self.commands
            with open(self._commands_file, "w", encoding="utf-8") as f:
                json.dump(all_commands, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[CommandManager] Ошибка сохранения команд: {e}")
            
    def _get_default_commands(self) -> List[Dict]:
        """Получает список стандартных команд."""
        return [
            {
                "id": 1,
                "trigger": "привет",
                "action": ACTION_TEXT,
                "target": None,
                "response": "Привет! Как дела?",
                "enabled": True
            },
            {
                "id": 2,
                "trigger": "как дела",
                "action": ACTION_TEXT,
                "target": None,
                "response": "У меня всё отлично, спасибо, что спросили!",
                "enabled": True
            },
            {
                "id": 3,
                "trigger": "открой ютуб",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://youtube.com",
                "response": "Открываю YouTube",
                "enabled": True
            },
            {
                "id": 4,
                "trigger": "ютуб",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://youtube.com",
                "response": "Открываю YouTube",
                "enabled": True
            },
            {
                "id": 5,
                "trigger": "youtube",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://youtube.com",
                "response": "Открываю YouTube",
                "enabled": True
            },
            {
                "id": 6,
                "trigger": "открой браузер",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://google.com",
                "response": "Открываю браузер",
                "enabled": True
            },
            {
                "id": 7,
                "trigger": "открой гугл",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://google.com",
                "response": "Открываю Google",
                "enabled": True
            },
            {
                "id": 8,
                "trigger": "google",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://google.com",
                "response": "Открываю Google",
                "enabled": True
            },
            {
                "id": 9,
                "trigger": "гугл",
                "action": ACTION_OPEN,
                "target_type": TARGET_WEBSITE,
                "target": "https://google.com",
                "response": "Открываю Google",
                "enabled": True
            },
            {
                "id": 10,
                "trigger": "громкость вверх",
                "action": ACTION_VOLUME_UP,
                "target": None,
                "response": "Увеличиваю громкость",
                "enabled": True
            },
            {
                "id": 11,
                "trigger": "громкость вниз",
                "action": ACTION_VOLUME_DOWN,
                "target": None,
                "response": "Уменьшаю громкость",
                "enabled": True
            }
        ]
        
    def add_command(self, trigger: str, action: str, target_type: Optional[str], 
                   target: Optional[str], response: str, enabled: bool = True):
        """Добавляет новую команду."""
        new_id = max([c["id"] for c in self.commands], default=0) + 1
        new_command = {
            "id": new_id,
            "trigger": trigger.lower().strip(),
            "action": action,
            "target_type": target_type,
            "target": target,
            "response": response,
            "enabled": enabled
        }
        self.commands.append(new_command)
        self._save_commands()
        return new_id
        
    def update_command(self, command_id: int, **kwargs):
        """Обновляет существующую команду."""
        for cmd in self.commands:
            if cmd["id"] == command_id:
                for key, value in kwargs.items():
                    if key in cmd:
                        cmd[key] = value
                self._save_commands()
                return True
        return False
        
    def delete_command(self, command_id: int):
        """Удаляет команду по ID."""
        self.commands = [c for c in self.commands if c["id"] != command_id]
        self._save_commands()
        
    def add_profile(self, name: str, description: str = ""):
        """Добавляет новый профиль."""
        profile_id = name.lower().replace(" ", "_")
        self.profiles[profile_id] = {
            "name": name,
            "description": description
        }
        self._save_profiles()
        
    def delete_profile(self, profile_id: str):
        """Удаляет профиль (нельзя удалить default)."""
        if profile_id != "default" and profile_id in self.profiles:
            del self.profiles[profile_id]
            self._save_profiles()
            if self.current_profile_name == profile_id:
                self.set_current_profile("default")
                
    def execute_command(self, text: str) -> Optional[str]:
        """Ищет и выполняет команду по тексту."""
        text_lower = text.lower().strip()
        
        # Ищем подходящую команду
        for cmd in self.commands:
            if not cmd.get("enabled", True):
                continue
            if cmd["trigger"] in text_lower:
                return self._execute_action(cmd)
                
        return None
        
    def _execute_action(self, cmd: Dict) -> str:
        """Выполняет действие команды."""
        action = cmd["action"]
        target_type = cmd.get("target_type")
        target = cmd.get("target")
        response = cmd.get("response", "Готово!")
        
        try:
            if action == ACTION_TEXT:
                return response
                
            elif action == ACTION_OPEN:
                if target_type == TARGET_WEBSITE:
                    webbrowser.open(target)
                elif target_type == TARGET_APP:
                    try:
                        os.startfile(target)
                    except Exception:
                        subprocess.Popen(target, shell=True)
                return response
                
            elif action == ACTION_CLOSE:
                if target_type == TARGET_PROCESS:
                    killed = 0
                    for proc in psutil.process_iter(["name", "pid"]):
                        try:
                            if target.lower() in proc.info["name"].lower():
                                proc.kill()
                                killed += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                return response
                
            elif action == ACTION_VOLUME_UP:
                for _ in range(5):
                    self.keyboard.press(Key.media_volume_up)
                    self.keyboard.release(Key.media_volume_up)
                return response
                
            elif action == ACTION_VOLUME_DOWN:
                for _ in range(5):
                    self.keyboard.press(Key.media_volume_down)
                    self.keyboard.release(Key.media_volume_down)
                return response
                
            elif action == ACTION_VOLUME_MUTE:
                self.keyboard.press(Key.media_volume_mute)
                self.keyboard.release(Key.media_volume_mute)
                return response
                
            elif action == ACTION_KEY_PRESS:
                # Цель - это имя клавиши (например, "enter", "ctrl+c")
                key_spec = target.lower().strip()
                if "+" in key_spec:
                    keys = key_spec.split("+")
                    for k in keys:
                        if hasattr(Key, k.strip()):
                            self.keyboard.press(getattr(Key, k.strip()))
                        else:
                            self.keyboard.press(k.strip())
                    for k in reversed(keys):
                        if hasattr(Key, k.strip()):
                            self.keyboard.release(getattr(Key, k.strip()))
                        else:
                            self.keyboard.release(k.strip())
                else:
                    if hasattr(Key, key_spec):
                        self.keyboard.press(getattr(Key, key_spec))
                        self.keyboard.release(getattr(Key, key_spec))
                    else:
                        self.keyboard.press(key_spec)
                        self.keyboard.release(key_spec)
                return response
                
            return response
        except Exception as e:
            print(f"[CommandManager] Ошибка выполнения команды: {e}")
            return f"Ошибка выполнения команды: {e}"
