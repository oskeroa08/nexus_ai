
"""Скрипт для сборки Nexus AI в EXE с помощью PyInstaller (оптимизированная версия)."""

import os
import sys
import subprocess


def main():
    # Путь к основному скрипту и иконке
    main_script = os.path.join(os.path.dirname(__file__), "main.py")
    icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")

    # Команда для PyInstaller: --onedir для быстреего запуска, чем --onefile
    pyinstaller_cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--onedir",  # Один каталог вместо одного файла - ускоряет запуск
        "--windowed",
        "--name", "NexusAI",
        "--icon", icon_path if os.path.exists(icon_path) else "NONE",
        # Скрытые импорты
        "--hidden-import", "PySide6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--hidden-import", "edge_tts",
        "--hidden-import", "speech_recognition",
        "--hidden-import", "pyaudio",
        "--hidden-import", "openai",
        "--hidden-import", "pynput",
        "--hidden-import", "psutil",
        "--hidden-import", "torch",
        "--hidden-import", "torchaudio",
        "--hidden-import", "soundfile",
        "--hidden-import", "numpy",
        "--hidden-import", "pyttsx3",
        "--hidden-import", "omegaconf",
        "--hidden-import", "omegaconf._utils",
        "--hidden-import", "omegaconf._iter",
        # Исключаем неиспользуемые модули для уменьшения размера и ускорения
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pandas",
        "--exclude-module", "scipy",
        "--exclude-module", "PIL",
        "--exclude-module", "notebook",
        "--exclude-module", "jupyter",
        "--exclude-module", "ipython",
        # Добавляем папку с Silero и иконку
        "--add-data", f"assets{os.pathsep}assets",
        "--add-data", f"icon.ico{os.pathsep}." if os.path.exists(icon_path) else "",
        # Добавляем остальные папки
        "--add-data", f"core{os.pathsep}core",
        "--add-data", f"gui{os.pathsep}gui",
        # Основной скрипт
        main_script
    ]

    # Удаляем пустые аргументы
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]

    print("Запускаем сборку EXE (оптимизированная сборка)...")
    print("Команда:", " ".join(pyinstaller_cmd))

    try:
        result = subprocess.run(
            pyinstaller_cmd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        print("\nСборка успешно завершена!")
        print("\nРезультат в папке dist/NexusAI")
        print("\nВывод PyInstaller:")
        print(result.stdout)
        print("\nОшибки (если есть):")
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print("\nОшибка при сборке!")
        print("Код возврата:", e.returncode)
        print("\nВывод:")
        print(e.stdout)
        print("\nОшибки:")
        print(e.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
