# Nexus AI - Voice Assistant

Проект для практики в универе.

Голосовой помощник для Windows с современным GUI, wake word, Edge TTS и OpenAI.

## Установка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Возможности

- Wake word «Нексус» (настраивается)
- Распознавание речи (Google STT)
- Синтез речи Edge TTS (ru-RU-SvetlanaNeural)
- OpenAI для умных ответов
- Системные команды: открытие программ, сайтов, клавиши, процессы
- Тёмная тема с неоновой анимацией

## Настройки

Все настройки сохраняются в `config.json`: микрофон, голос, API ключ, wake word.
