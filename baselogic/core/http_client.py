import requests
import json
import logging
from typing import Dict, Any, Optional

from .interfaces import LLMClientError, LLMTimeoutError, LLMConnectionError, LLMResponseError
from .base_client import BaseLLMClient
from .types import ModelOptions


class OpenAICompatibleClient(BaseLLMClient):
    """
    HTTP-клиент для взаимодействия с любым сервером, предоставляющим
    OpenAI-совместимый эндпоинт /chat/completions.
    (например, LM Studio, Jan, vLLM).
    """
    def __init__(self, model_name: str, api_base: str, api_key: Optional[str] = None, model_options: Optional[ModelOptions] = None):
        """
        Инициализирует HTTP-клиент.

        Args:
            model_name (str): Имя модели, которое будет передано в теле запроса.
            api_base (str): Базовый URL сервера (например, "http://localhost:1234/v1").
            api_key (Optional[str]): Необязательный ключ API.
            model_options (Optional[ModelOptions]): Словарь с опциями.
        """
        super().__init__(model_name, model_options)
        
        self.api_url = f"{api_base.rstrip('/')}/chat/completions"
        self.api_key = api_key
        
        self.logger.info("✅ OpenAICompatibleClient инициализирован для '%s' по адресу: %s", model_name, self.api_url)

    def _execute_query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Отправляет HTTP POST-запрос на OpenAI-совместимый сервер,
        поддерживает стриминг и возвращает структурированный ответ.
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = self._prepare_messages(user_prompt)

        # Безопасно извлекаем опцию стриминга, чтобы не передавать ее дважды
        # .pop() удаляет ключ из словаря, что предотвращает ошибки
        use_stream = self.generation_opts.pop('stream', False)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": use_stream,
            **self.generation_opts  # Добавляем остальные опции: temp, stop, etc.
        }

        # Возвращаем 'stream' обратно в опции для логирования, если это необходимо
        self.generation_opts['stream'] = use_stream

        log_message = (
            f"REQUEST (HTTP):\n"
            f"  URL: {self.api_url}\n"
            f"  Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}\n\n"
        )
        self.logger.debug(log_message)

        try:
            self.logger.info("    🚀 Отправляем запрос к API (stream=%s, timeout=%dс)...", use_stream, self.query_timeout)

            # Используем контекстный менеджер для надежного управления соединением
            with requests.post(self.api_url, headers=headers, json=payload, timeout=self.query_timeout, stream=use_stream) as response:
                response.raise_for_status() # Вызовет исключение для кодов 4xx/5xx

                if use_stream:
                    # --- Обработка потокового ответа ---
                    full_response_content = []
                    print("    [STREAM] Ответ модели: ", end='', flush=True)
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith('data: '):
                                json_str = decoded_line[6:]
                                if json_str.strip() == '[DONE]':
                                    break
                                try:
                                    chunk = json.loads(json_str)
                                    content_part = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                    if content_part:
                                        print(content_part, end='', flush=True)
                                        full_response_content.append(content_part)
                                except json.JSONDecodeError:
                                    self.logger.debug("Пропущена не-JSON строка в стриме: %s", decoded_line)
                    print() # Перенос строки после завершения стрима
                    final_content = "".join(full_response_content)
                else:
                    # --- Обработка обычного (блокирующего) ответа ---
                    data = response.json()
                    if not data.get('choices'):
                        raise ValueError("Ответ API не содержит ключ 'choices'")
                    final_content = data['choices']['message']['content']

            self.logger.info("    ✅ Ответ от API успешно получен.")

            validated_response = self._validate_response(final_content)

            # Возвращаем словарь, соответствующий новому контракту ILLMClient
            return {
                "thinking_response": "", # OpenAI-совместимые клиенты не поддерживают "thinking"
                "llm_response": validated_response
            }

        except requests.exceptions.Timeout:
            error_details = "RESPONSE (HTTP Timeout Error): Сервер не ответил за установленное время."
            self.logger.error(error_details)
            raise LLMTimeoutError(error_details)
        except requests.exceptions.RequestException as e:
            error_details = f"RESPONSE (HTTP Request Error):\n{e}"
            self.logger.error(error_details, exc_info=True)
            raise LLMConnectionError(f"HTTP_ERROR: {e}") from e
        except (ValueError, KeyError, IndexError, json.JSONDecodeError) as e:
            # Обработка ошибок парсинга и структуры ответа
            raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else "No response received"
            error_details = f"RESPONSE (Parsing Error):\n{e}\nRaw Response: {raw_response_text[:500]}"
            self.logger.error(error_details, exc_info=True)
            raise LLMResponseError(f"PARSING_ERROR: {e}") from e

    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели.
        Для HTTP-клиентов генерируем стандартную информацию.
        """
        self.logger.info("    ⚙️ Генерация стандартных деталей для API-модели: %s", self.model_name)
        
        # Базовая информация
        base_info = super().get_model_info()
        
        # Добавляем специфичную для HTTP клиента информацию
        http_info = {
            "client_type": "openai_compatible",
            "api_url": self.api_url,
            "modelfile": "N/A (API)",
            "parameters": "N/A (API)",
            "template": self.prompting_opts.get('template', 'N/A (API)'),
            "details": {
                "family": "api",  # Идентификатор для группировки
                "parameter_size": "N/A",
                "quantization_level": "API",
                "format": "api"
            },
            "object": "model"
        }
        
        base_info.update(http_info)
        return base_info

