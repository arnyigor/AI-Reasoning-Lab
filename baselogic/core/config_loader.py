# config_loader.py
import os
import re
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

class EnvConfigLoader:
    """
    Загружает и парсит конфигурацию приложения исключительно из переменных окружения.

    Поддерживает вложенные структуры и списки с помощью именования переменных
    в формате: PREFIX_KEY_INDEX__SUBKEY.
    Использует двойное подчеркивание '__' как разделитель вложенности.
    """

    def __init__(self, prefix: str = "BC"):
        self.prefix = prefix
        self.env_vars = self._load_and_filter_env(prefix)

    def _load_and_filter_env(self, prefix: str) -> Dict[str, str]:
        load_dotenv()
        prefix_str = f"{prefix}_"
        filtered_vars = {}
        for key, value in os.environ.items():
            if key.startswith(prefix_str):
                clean_key = key[len(prefix_str):]
                filtered_vars[clean_key] = value
        return filtered_vars

    @staticmethod
    def _set_nested_value(d: Dict[str, Any], path: str, value: Any) -> None:
        """
        Устанавливает значение во вложенный словарь по пути.
        Использует двойное подчеркивание '__' в качестве разделителя вложенности.
        """
        keys = path.lower().split('__')
        current_level = d
        for key in keys[:-1]:
            current_level = current_level.setdefault(key, {})

        last_key = keys[-1]
        try:
            if isinstance(value, str):
                if value.isdigit():
                    value = int(value)
                elif re.match(r"^\d+?\.\d+?$", value):
                    value = float(value)
                elif value.lower() in ['true', 'false']:
                    value = value.lower() == 'true'
        except (ValueError, TypeError):
            pass
        current_level[last_key] = value

    def load_config(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        models_data: Dict[int, Dict[str, Any]] = {}
        model_pattern = re.compile(r"MODELS_(\d+)_(.*)")

        for key, value in self.env_vars.items():
            match = model_pattern.match(key)
            if match:
                index = int(match.group(1))
                path = match.group(2)
                if index not in models_data:
                    models_data[index] = {}
                EnvConfigLoader._set_nested_value(models_data[index], path, value)
            elif key == "TESTS_TO_RUN":
                config["tests_to_run"] = [item.strip() for item in value.split(',')]
            else:
                EnvConfigLoader._set_nested_value(config, key, value)

        if models_data:
            sorted_models = sorted(models_data.items())
            config["models_to_test"] = [model for _, model in sorted_models]

        return config

# --- Пример использования ---
if __name__ == "__main__":
    print("Загрузка конфигурации из переменных окружения...")

    # Предполагается, что у вас есть .env файл в директории проекта
    # или переменные окружения установлены системно.

    config_loader = EnvConfigLoader(prefix="BC")
    final_config = config_loader.load_config()

    # Красивый вывод для проверки
    import json
    print("\nИтоговая конфигурация:")
    print(json.dumps(final_config, indent=2, ensure_ascii=False))