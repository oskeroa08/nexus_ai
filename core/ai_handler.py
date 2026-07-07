"""Обработчик AI-ответов с поддержкой OpenAI, Groq и fallback-режима."""

import random
from typing import Optional

from openai import APIStatusError, OpenAI, RateLimitError

from core.audio_manager import load_config

PROVIDER_OPENAI = "openai"
PROVIDER_GROQ = "groq"
PROVIDER_NONE = "none"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

FALLBACK_RESPONSES = [
    "Я вас слушаю. Чем могу помочь?",
    "Интересный вопрос! Сейчас я работаю в автономном режиме.",
    "Попробуйте спросить меня о времени или попросить открыть браузер.",
    "Я Nexus AI — ваш голосовой помощник. Настройте AI-провайдер для умных ответов.",
    "Хороший вопрос! Добавьте API-ключ в настройках, и я смогу ответить подробнее.",
    "Пока я работаю в базовом режиме. Скажите «привет» или «который час».",
    "Я готов помочь! Выберите провайдер OpenAI или Groq в настройках.",
    "Отличный вопрос! В полном режиме я бы ответил намного интереснее.",
]

SYSTEM_PROMPT = (
    "Ты Nexus AI — голосовой помощник для Windows. "
    "Отвечай кратко и по-русски, максимум 2-3 предложения. "
    "Будь дружелюбным и полезным."
)


class AIHandler:
    """Обрабатывает запросы через OpenAI, Groq или локальные ответы."""

    def __init__(self):
        self._client: Optional[OpenAI] = None
        self._provider: str = PROVIDER_NONE
        self._model: str = ""
        self._refresh_client()

    def _refresh_client(self) -> None:
        config = load_config()
        provider = config.get("ai_provider", PROVIDER_NONE)

        if provider == PROVIDER_NONE:
            self._client = None
            self._provider = PROVIDER_NONE
            return

        if provider == PROVIDER_GROQ:
            api_key = config.get("groq_api_key", "").strip()
            if api_key:
                self._client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
                self._provider = PROVIDER_GROQ
                self._model = config.get("groq_model", GROQ_MODEL)
                return

        if provider == PROVIDER_OPENAI:
            api_key = config.get("openai_api_key", "").strip()
            if api_key:
                self._client = OpenAI(api_key=api_key)
                self._provider = PROVIDER_OPENAI
                self._model = config.get("openai_model", "gpt-4o-mini")
                return

        self._client = None
        self._provider = PROVIDER_NONE

    def get_response(self, query: str) -> str:
        self._refresh_client()
        if not self._client:
            return random.choice(FALLBACK_RESPONSES)

        try:
            return self._request_completion(query)
        except RateLimitError:
            print("[AIHandler] Квота исчерпана (429) — переключаюсь на fallback")
            return random.choice(FALLBACK_RESPONSES)
        except APIStatusError as e:
            if e.status_code == 429:
                print("[AIHandler] Квота исчерпана (429) — переключаюсь на fallback")
                return random.choice(FALLBACK_RESPONSES)
            print(f"[AIHandler] API error {e.status_code}: {e}")
            return random.choice(FALLBACK_RESPONSES)
        except Exception as e:
            print(f"[AIHandler] Ошибка API: {e}")
            return random.choice(FALLBACK_RESPONSES)

    def _request_completion(self, query: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    def is_ai_available(self) -> bool:
        self._refresh_client()
        return self._client is not None

    def current_provider(self) -> str:
        self._refresh_client()
        return self._provider
