import requests
import json
from typing import Dict, Any, Optional

from .logger import llm_logger


class OpenAICompatibleClient:
    """
    HTTP-клиент для взаимодействия с любым сервером, предоставляющим
    OpenAI-совместимый эндпоинт /chat/completions.
    (например, LM Studio, Jan, vLLM).
    """
    def __init__(self, model_name: str, api_base: str, api_key: Optional[str] = None, model_options: Optional[Dict[str, Any]] = None):
        """
        Инициализирует HTTP-клиент.

        Args:
            model_name (str): Имя модели, которое будет передано в теле запроса.
            api_base (str): Базовый URL сервера (например, "http://localhost:1234/v1").
            api_key (Optional[str]): Необязательный ключ API.
            model_options (Optional[Dict[str, Any]]): Словарь с опциями.
        """
        self.model_name = model_name
        self.api_url = f"{api_base.rstrip('/')}/chat/completions"
        self.api_key = api_key
        self.model_options = model_options if model_options else {}

        # Разбираем опции для удобства
        self.generation_options = self.model_options.get('generation', {})
        self.prompting_options = self.model_options.get('prompting', {})

        # Извлекаем системный промпт
        self.system_prompt = self.prompting_options.get('system_prompt')

    def query(self, user_prompt: str) -> str:
        """
        Отправляет HTTP POST-запрос на сервер и возвращает текстовый ответ.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = []
        if self.system_prompt:
            messages.append({'role': 'system', 'content': self.system_prompt})
        messages.append({'role': 'user', 'content': user_prompt})

        # Собираем тело запроса в соответствии со спецификацией OpenAI
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            **self.generation_options # Добавляем все опции генерации: temp, stop, etc.
        }

        # --- Логирование запроса ---
        log_message = (
            f"REQUEST (HTTP):\n"
            f"  URL: {self.api_url}\n"
            f"  Headers: {headers}\n"
            f"  Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
        )

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=180) # Таймаут 3 минуты
            response.raise_for_status()  # Вызовет исключение для кодов 4xx/5xx

            data = response.json()

            if not data.get('choices'):
                raise ValueError("Ответ API не содержит ключ 'choices'")

            full_response_text = data['choices'][0]['message']['content']

            log_message += f"RESPONSE (Success):\n{full_response_text}"
            llm_logger.info(log_message)
            return full_response_text.strip()

        except requests.exceptions.RequestException as e:
            error_details = f"RESPONSE (HTTP Request Error):\n{e}"
            log_message += error_details
            llm_logger.error(log_message, exc_info=True)
            return f"HTTP_ERROR: {e}"
        except (ValueError, KeyError, IndexError) as e:
            error_details = f"RESPONSE (JSON Parsing Error):\n{e}\nRaw Response: {response.text}"
            log_message += error_details
            llm_logger.error(log_message, exc_info=True)
            return f"JSON_PARSING_ERROR: {e}"