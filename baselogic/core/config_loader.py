import os
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

class ConfigLoader:
    """Загружает конфигурацию из файла и переменных окружения"""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        Загружает конфигурацию из .env файла, затем из YAML,
        и в конце переопределяет переменными окружения.
        """
        # 1. Загружаем переменные из .env файла в окружение
        # Ищет .env файл в текущей директории или выше по дереву
        load_dotenv()

        # 2. Загружаем базовую конфигурацию из YAML
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 3. Переопределяем переменными окружения (которые теперь включают .env)
        ConfigLoader._override_from_env(config, 'models_to_test')
        ConfigLoader._override_from_env(config, 'tests_to_run')
        ConfigLoader._override_from_env(config, 'runs_per_test')
        
        return config
    
    @staticmethod
    def _override_from_env(config: Dict[str, Any], key: str):
        """
        Переопределяет значение в конфигурации из переменной окружения.

        Имя переменной окружения формируется по правилу: BASELOGIC_{KEY_IN_UPPERCASE}.
        Например, для ключа 'runs_per_test' переменная будет BASELOGIC_RUNS_PER_TEST.

        Args:
            config (Dict[str, Any]): Словарь с конфигурацией.
            key (str): Ключ для переопределения.
        """
        env_key = f"BASELOGIC_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value:
            # Преобразуем значение в нужный тип
            if key == 'runs_per_test':
                config[key] = int(env_value)
            elif key in ['models_to_test', 'tests_to_run']:
                # Для списков ожидаем строку, разделенную запятыми
                config[key] = [item.strip() for item in env_value.split(',')]
            else:
                config[key] = env_value
            
            print(f"INFO: Конфигурация '{key}' переопределена значением из переменной окружения '{env_key}'.")