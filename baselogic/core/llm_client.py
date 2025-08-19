# baselogic/clients/ollama_client.py
import logging
import re
from typing import Dict, Any, Optional

import ollama

# Ваши импорты
from .base_client import BaseLLMClient
from .interfaces import LLMResponseError, LLMConnectionError
from .types import ModelOptions

# Используем ваш логгер
log = logging.getLogger(__name__)

import time


class OllamaClient(BaseLLMClient):
    """
    Класс-клиент для инкапсуляции взаимодействия с API Ollama.
    С автоопределением размера контекста и улучшенной обработкой ошибок.
    """

    def __init__(self, model_name: str, model_options: Optional[ModelOptions] = None):
        """
        Инициализирует клиент.
        """
        # Сначала вызываем super().__init__(), чтобы все базовые поля были на месте
        super().__init__(model_name, model_options)

        # --- ИСПРАВЛЕНИЕ 1: Инициализируем клиент Ollama ЗДЕСЬ ---
        try:
            self.client = ollama.Client()
        except Exception as e:
            # Если Ollama не запущена, это вызовет ошибку. Перехватываем ее.
            raise LLMConnectionError(f"Не удалось подключиться к Ollama. Убедитесь, что сервис запущен. Ошибка: {e}")

        # Проверяем модель, но НЕ завершаем программу
        skip_validation = self.model_options.get('skip_model_validation', False)
        if not skip_validation:
            self._check_model_exists()
        else:
            log.warning("⚠️ Проверка существования модели пропущена")

        # Теперь, когда клиент есть, конфигурируем контекст
        self._configure_context_window()

    def _configure_context_window(self):
        """
        Автоматически определяет и настраивает размер контекстного окна.
        Приоритет:
        1. Значение из inference_opts (например, из .env).
        2. Автоопределение из `ollama show`.
        3. Если ничего нет, используется безопасное значение по умолчанию (4096).
        """
        # 1. Проверяем ручную установку
        manual_num_ctx = self.inference_opts.get('num_ctx')
        if manual_num_ctx:
            log.info(f"Используется размер контекста, заданный вручную: {manual_num_ctx}")
            self.generation_opts['num_ctx'] = int(manual_num_ctx)
            return

        # 2. Автоопределение
        log.info(f"Размер контекста не задан вручную. Попытка автоопределения для модели '{self.model_name}'...")
        try:
            model_info = self.client.show(self.model_name)

            # Ищем ключ в структурированных данных
            context_length = model_info.get('details', {}).get('parameter_size_context')

            # Fallback: извлечение через регулярное выражение из строки параметров
            if not context_length:
                params_str = model_info.get('parameters', '')
                match = re.search(r'num_ctx\s+(\d+)', params_str)
                if match:
                    context_length = int(match.group(1))

            # Если всё ещё не найдено, устанавливаем безопасный дефолт
            if not context_length:
                context_length = 4096
                log.warning(
                    f"⚠️ Не удалось автоматически определить размер контекста для '{self.model_name}'. "
                    f"Установлено безопасное значение по умолчанию: {context_length}. "
                    f"Рекомендуется указать 'num_ctx' вручную в .env."
                )
            else:
                log.info(f"✅ Автоматически определен размер контекста: {context_length}")

            self.generation_opts['num_ctx'] = int(context_length)

        except ollama.ResponseError as e:
            log.warning(
                f"⚠️ Модель '{self.model_name}' не найдена при автоопределении контекста. Ошибка: {e.status_code}"
            )
            self._set_default_context()
        except Exception as e:
            log.warning(
                f"⚠️ Ошибка при автоопределении размера контекста: {e}. "
                f"Установлено значение по умолчанию: 4096."
            )
            self._set_default_context()

    def _set_default_context(self, default_value: int = 4096):
        """Устанавливает безопасное значение контекста по умолчанию."""
        self.generation_opts['num_ctx'] = default_value

    def _check_model_exists(self):
        """
        Проверяет наличие модели через `ollama.list()` с улучшенной,
        безопасной логикой извлечения имени.
        """
        try:
            log.info("Проверка наличия модели '%s' через API Ollama...", self.model_name)
            # self.client.list() возвращает словарь, нам нужен ключ 'models'
            models_list = self.client.list().get('models', [])

            if not models_list:
                log.warning("⚠️ Список моделей от Ollama пуст. Невозможно проверить существование модели.")
                return

            # --- ИСПРАВЛЕНИЕ: Безопасное извлечение имени модели ---
            # Используем .get() и проверяем оба возможных ключа: 'name' и 'model'
            available_models = []
            for m in models_list:
                # m - это словарь. .get() безопасен и вернет None, если ключа нет.
                # Мы проверяем 'name', и если его нет, проверяем 'model'.
                model_identifier = m.get('name') or m.get('model')
                if model_identifier:
                    available_models.append(model_identifier)
                else:
                    log.debug(f"Не удалось найти ключ 'name' или 'model' в элементе списка: {m}")

            if not available_models:
                log.warning("⚠️ Не удалось извлечь имена из списка доступных моделей.")
                return

            # Остальная логика остается без изменений
            target_base_name = self.model_name.split(':')[0]
            is_found = any(
                self.model_name == m_name or target_base_name == m_name.split(':')[0]
                for m_name in available_models
            )

            if is_found:
                log.info("✅ Модель '%s' найдена локально.", self.model_name)
            else:
                log.warning("⚠️ Модель '%s' не найдена. Доступные модели: %s",
                            self.model_name, [m[:40] for m in available_models[:5]])

        except Exception as e:
            # Логируем ошибку, но не останавливаем выполнение
            log.warning("⚠️ Не удалось проверить список моделей: %s. Пропускаем проверку.", e, exc_info=True)

    def get_model_info(self) -> Dict[str, Any]:
        """
        Возвращает информацию о модели. Переписан для большей безопасности.
        """
        base_info = super().get_model_info()
        try:
            log.debug("Запрос деталей для модели: %s", self.model_name)
            response = self.client.show(self.model_name)

            # Объединяем информацию безопасно
            base_info['details'] = response.get('details', {})
            base_info['parameters'] = response.get('parameters', 'N/A')
            base_info['modelfile'] = response.get('modelfile', 'N/A')

            return base_info
        except Exception as e:
            error_msg = f"Ошибка при получении деталей модели от Ollama: {e}"
            log.error(error_msg)
            base_info['error'] = error_msg
            return base_info

    def _execute_query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Выполняет запрос к Ollama и возвращает структурированный результат
        с "мыслями" и финальным ответом. Поддерживает режимы 'think' и 'stream'.
        """
        messages = self._prepare_messages(user_prompt)

        use_think = self.inference_opts.get('think', False)
        use_stream = self.inference_opts.get('stream', False)
        is_streaming_mode = use_think or use_stream

        # === ДИАГНОСТИКА: ЛОГИРУЕМ ПРОМПТ ===
        log.info("🔍 ПРОМПТ ОТПРАВЛЯЕТСЯ:")
        for i, msg in enumerate(messages):
            log.info("  Сообщение %d: %s", i, msg)
        log.info("🔍 ПАРАМЕТРЫ: stream=%s, think=%s", is_streaming_mode, use_think)
        log.info("🔍 ОПЦИИ ГЕНЕРАЦИИ: %s", self.generation_opts)

        log.info("    🚀 Отправка запроса к модели '%s' (think=%s, stream=%s)...",
                 self.model_name, use_think, is_streaming_mode)

        try:
            # === ЗАСЕКАЕМ ВРЕМЯ API ВЫЗОВА ===
            api_start_time = time.time()
            log.info("🚀 API вызов начался в %s", time.strftime("%H:%M:%S"))

            # Единый вызов API для всех режимов
            response_iterator = self.client.chat(
                model=self.model_name,
                messages=messages,
                options=self.generation_opts,
                think=use_think,
                stream=is_streaming_mode
            )

            log.info("⚡ API ответил за %.3f сек", time.time() - api_start_time)

            thinking_parts = []
            content_parts = []
            has_printed_thinking_header = False
            has_printed_answer_header = False

            if not is_streaming_mode:
                response_iterator = [response_iterator]

            stream_start_time = time.time()

            # === ПЕРЕДАЕМ max_chunks КАК ПАРАМЕТР ===
            max_chunks = self.inference_opts.get('max_chunks', 1000)

            self.process_query(content_parts, has_printed_answer_header, has_printed_thinking_header,
                               response_iterator, thinking_parts, max_chunks)

            elapsed_time = time.time() - stream_start_time
            log.info("    ⏱️ Обработка стрима заняла %.2f секунд", elapsed_time)

            print()  # Финальный перенос строки

            # 3. Собираем результат
            final_thinking = "".join(thinking_parts).strip()
            final_content = "".join(content_parts).strip()

            if not final_content and not final_thinking:
                raise LLMResponseError("Получен пустой ответ от модели")

            log.info("    ✅ Полный ответ успешно собран.")

            return {
                "thinking_response": final_thinking,
                "llm_response": final_content,
            }

        except ollama.ResponseError as e:
            log.error("    🚫 Ollama API Error (Status %d): %s", e.status_code, e.error)
            return {
                "thinking_response": "",
                "llm_response": f"[API_ERROR] {e.error}"
            }
        except Exception as e:
            log.error("    💥 Неожиданная ошибка: %s", e, exc_info=True)
            return {
                "thinking_response": "",
                "llm_response": f"[ERROR] {str(e)}"
            }

    def process_query(
            self,
            content_parts: list[str],
            has_printed_answer_header: bool,
            has_printed_thinking_header: bool,
            response_iterator,
            thinking_parts: list[str],
            max_chunks: int = 1000
    ) -> None:
        """
        Обрабатывает потоковый ответ Ollama, разделяя «мысли» (thinking) и основной контент.

        Параметры
        ----------
        content_parts : list[str]
            Список, куда накапливаются части основного ответа.
        has_printed_answer_header : bool
            Флаг, показывающий, печатали ли заголовок [ANSWER].
        has_printed_thinking_header : bool
            Флаг, показывающий, печатали ли заголовок [THINKING].
        response_iterator : Iterable
            Итератор chunk-ов, возвращаемых Ollama.
        thinking_parts : list[str]
            Список, куда накапливаются части «мыслей» модели.
        max_chunks : int, optional
            Защитный лимит на количество chunk-ов (по умолчанию 1000).
        """
        import time

        chunk_counter = 0
        stream_start = time.time()

        for chunk in response_iterator:
            chunk_counter += 1
            # current_time = time.time() - stream_start
            # log.info("⏱️ Chunk #%d через %.3f сек", chunk_counter, current_time)

            # === Извлечение полей из chunk'а ===
            try:
                done = getattr(chunk, "done", False) if hasattr(chunk, "done") else chunk.get("done", False)
                message = getattr(chunk, "message", {}) if hasattr(chunk, "message") else chunk.get("message", {})

                if isinstance(message, dict):
                    content_part  = message.get("content")
                    thinking_part = message.get("thinking")
                    finish_reason = message.get("finish_reason")
                else:  # message может быть объектом
                    content_part  = getattr(message, "content",  None) if message else None
                    thinking_part = getattr(message, "thinking", None) if message else None
                    finish_reason = getattr(message, "finish_reason", None) if message else None
            except Exception as exc:
                log.error("Ошибка извлечения данных из chunk #%d: %s", chunk_counter, exc)
                content_part = thinking_part = finish_reason = None
                done = False

            # === Печать и накопление thinking ===
            if thinking_part:
                if not has_printed_thinking_header:
                    print("\n    [THINKING]: ", end="", flush=True)
                    has_printed_thinking_header = True
                print(thinking_part, end="", flush=True)
                thinking_parts.append(thinking_part)

            # === Печать и накопление content ===
            if content_part:
                if not has_printed_answer_header:
                    if has_printed_thinking_header:
                        print()  # перенос строки после блока thinking
                    print("    [ANSWER]:   ", end="", flush=True)
                    has_printed_answer_header = True
                print(content_part, end="", flush=True)
                content_parts.append(content_part)

            # === Условия завершения ===
            if done:
                log.info("    ✅ Модель завершила генерацию (done=True) на chunk #%d", chunk_counter)
                break

            if finish_reason:
                log.info("    ✅ Модель завершила генерацию (finish_reason=%s) на chunk #%d",
                         finish_reason, chunk_counter)
                break

            # === Защита от бесконечного стрима ===
            if chunk_counter > max_chunks:
                log.warning("⚠️ Достигнут лимит chunk'ов (%d) — прерываем стрим.", max_chunks)
                break

