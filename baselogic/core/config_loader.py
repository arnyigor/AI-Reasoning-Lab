# baselogic/core/config_loader.py
import json
import logging
import os
import re
from json import JSONDecodeError
from typing import Any, Dict

from dotenv import load_dotenv

log = logging.getLogger(__name__)


class EnvConfigLoader:
    def __init__(self, prefix: str = "BC"):
        self.prefix = prefix
        self.env_vars = self._load_and_filter_env(prefix)

    def _load_and_filter_env(self, prefix: str) -> Dict[str, str]:
        load_dotenv()
        prefix_str = f"{prefix}_"
        return {key[len(prefix_str):]: value for key, value in os.environ.items() if key.startswith(prefix_str)}

    @staticmethod
    def _convert_type(value: str) -> Any:
        if not isinstance(value, str):
            return value
        val_lower = value.lower()
        if val_lower == 'true': return True
        if val_lower == 'false': return False
        if value.isdigit(): return int(value)
        if re.match(r"^\d+\.\d+$", value): return float(value)
        if value.startswith('[') and value.endswith(']'):
            try:
                import json
                return json.loads(value)
            except JSONDecodeError:
                pass

        return value

    def load_config(self) -> Dict[str, Any]:
        """
        Загружает и парсит конфигурацию из переменных окружения.

        Поддерживает структурированную конфигурацию моделей с вложенными секциями,
        такими как generation, inference, prompting, query и options.
        """
        config: Dict[str, Any] = {}
        models_data: Dict[int, Dict[str, Any]] = {}
        model_key_pattern = re.compile(r"MODELS?_(\d+)_(.*)", re.IGNORECASE)

        for key, value in self.env_vars.items():
            model_match = model_key_pattern.match(key)

            if model_match:
                index = int(model_match.group(1))
                path_str = model_match.group(2).lower()

                if index not in models_data:
                    models_data[index] = {}

                # --- ИСПРАВЛЕННАЯ ЛОГИКА: Добавляем "options" в список вложенных префиксов ---
                nested_prefixes = ['generation', 'inference', 'prompting', 'query', 'options']

                is_nested = False
                for prefix in nested_prefixes:
                    if path_str.startswith(prefix + '_'):
                        is_nested = True
                        section = prefix
                        param_key = path_str[len(prefix) + 1:]

                        section_dict = models_data[index].setdefault(section, {})
                        section_dict[param_key] = self._convert_type(value)
                        break

                if not is_nested:
                    models_data[index][path_str] = self._convert_type(value)

            elif key.upper() == "TESTS_TO_RUN":
                # Сначала попробуем распарсить как JSON, если не получится - как строку с разделителями
                converted_value = self._convert_type(value)
                if isinstance(converted_value, list):
                    config["tests_to_run"] = converted_value
                else:
                    # Fallback для старого формата
                    config["tests_to_run"] = [item.strip() for item in value.split(',')]
            else:
                config[key.lower()] = self._convert_type(value)

        if models_data:
            valid_models = [
                model_dict for _, model_dict in sorted(models_data.items())
                if 'name' in model_dict and model_dict['name']
            ]
            config["models_to_test"] = valid_models

        return config
