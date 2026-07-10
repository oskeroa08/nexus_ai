
# Nexus AI - Voice Assistant

Проект для практики в универе. Голосовой помощник для Windows с современным GUI, wake word, Silero/Edge TTS и OpenAI/Groq.

## Возможности

- **Wake word**: «Нексус» (настраивается в конфиге)
- **Распознавание речи**: Google STT
- **Синтез речи**:
  - Silero (офлайн, ru-RU)
  - Edge TTS (онлайн, разные голоса)
  - pyttsx3 (офлайн fallback)
- **ИИ-помощник**: OpenAI/Groq (настраивается)
- **Системные команды**:
  - Открытие сайтов/приложений
  - Закрытие процессов
  - Управление громкостью
  - Нажатие клавиш/комбинаций
  - Текстовые ответы
- **Пользовательские команды**: Добавляйте свои команды, управляйте профилями!
- **GUI**: Темная тема с визуализатором, история диалога
- **Оптимизация EXE-сборки**: Быстрый запуск, офлайн Silero

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv venv
```
2. Активируйте:
```bash
# Windows
venv\Scripts\activate
```
3. Установите зависимости:
```bash
pip install -r requirements.txt
```
4. Скачайте Silero модель (для офлайн ТТС):
```bash
python download_silero.py
```

## Запуск

```bash
python main.py
```

## Сборка EXE

1. Скачайте Silero модель (если ещё не):
```bash
python download_silero.py
```
2. Запустите сборку:
```bash
python build_exe.py
```
3. Готовая сборка будет в папке `dist/NexusAI/`

## Настройки

Все настройки сохраняются в:
- **Windows**: `%APPDATA%/NexusAI/config.json`
- Пользовательские команды: `%APPDATA%/NexusAI/commands.json`
- Профили команд: `%APPDATA%/NexusAI/profiles.json`

### Основные настройки:
- `wake_word`: Ключевое слово для активации
- `input_device_index`: Индекс микрофона
- `tts_provider`: Провайдер ТТС (`silero`/`edge`/`none`)
- `silero_voice`: Голос Silero (`aidar`/`baya`/`kseniya`/`xenia`/`eugene`)
- `openai_api_key`/`groq_api_key`: API ключи
- И многое другое!

## Лицензия

MIT License
