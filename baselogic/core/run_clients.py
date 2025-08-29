import sys
from pathlib import Path
import logging
import os
import requests

from baselogic.core.GeminiClient import GeminiClient

# --- Настройка путей и импортов ---
# Добавляем корень проекта в sys.path, чтобы работали абсолютные импорты
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Теперь используем абсолютные импорты, так как скрипт запускается извне пакета
from baselogic.core.llm_client import LLMClient
from baselogic.core.openai_client import OpenAICompatibleClient


if __name__ == '__main__':
    # --- Импорты и настройка (остаются без изменений) ---
    from dotenv import load_dotenv
    import os
    import requests

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)-20s - %(levelname)-8s - %(message)s')
    log = logging.getLogger("LLMClientExample")
    load_dotenv()
    log.info("Переменные из .env файла загружены.")

    # --- Пример 1: Тестирование локального сервера ---
    log.info("\n--- Тестирование локального сервера (LM Studio / Jan / Ollama) ---")
    try:
        provider = OpenAICompatibleClient(api_key="local", base_url="http://localhost:1234/v1")
        client = LLMClient(provider=provider, model_config={"name": "deepseek/deepseek-r1-0528-qwen3-8b", "generation": {"temperature": 0.7}})

        # --- НЕПОТОКОВЫЙ ЗАПРОС ---
        log.info("\n--- Тест 1: Непотоковый запрос ---")
        response = client.chat([{"role": "user", "content": "Почему небо голубое? Ответь кратко."}])
        log.info("ПОЛУЧЕН ПОЛНЫЙ ОТВЕТ:\n%s", response)

        # --- ПОТОКОВЫЙ ЗАПРОС ---
        log.info("\n--- Тест 2: Потоковый запрос ---")
        stream = client.chat(
            [{"role": "user", "content": "Напиши страшную историю из 3 предложений."}],
            stream=True
        )

        # >>>>> НАЧАЛО ИСПРАВЛЕНИЙ <<<<<

        log.info("НАЧАЛО ПОТОКОВОГО ВЫВОДА:")
        # Мы итерируемся по генератору и сразу выводим каждый чанк.
        # Это и есть настоящий стриминг.
        full_streamed_response = ""
        # Используем print() для наглядной демонстрации "печатающегося" текста.
        # flush=True гарантирует, что текст появится в консоли немедленно.
        print(">>> ", end="")
        for chunk in stream:
            print(chunk, end="", flush=True)
            full_streamed_response += chunk
        print() # Перевод строки в конце

        log.info("КОНЕЦ ПОТОКОВОГО ВЫВОДА. (Собрано %d символов)", len(full_streamed_response))

        log.info("=" * 40)

    except requests.exceptions.ConnectionError:
        log.error("Не удалось подключиться к локальному серверу.")
    except Exception as e:
        log.error("Ошибка при тестировании локальной модели: %s", e, exc_info=True)