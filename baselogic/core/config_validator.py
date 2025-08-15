import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ClientType(Enum):
    """Поддерживаемые типы клиентов"""
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class ModelConfig:
    """Конфигурация модели"""
    name: str
    client_type: ClientType
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if isinstance(self.client_type, str):
            self.client_type = ClientType(self.client_type)


@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    level: str = "INFO"
    format: str = "DETAILED"
    directory: str = "logs"
    
    def __post_init__(self):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        valid_formats = ["SIMPLE", "DETAILED", "JSON"]
        
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Неверный уровень логирования: {self.level}. Допустимые: {valid_levels}")
        
        if self.format.upper() not in valid_formats:
            raise ValueError(f"Неверный формат логирования: {self.format}. Допустимые: {valid_formats}")


@dataclass
class TestConfig:
    """Конфигурация тестирования"""
    tests_to_run: List[str]
    runs_per_test: int = 3
    
    def __post_init__(self):
        if self.runs_per_test < 1:
            raise ValueError(f"runs_per_test должно быть >= 1, получено: {self.runs_per_test}")
        
        if not self.tests_to_run:
            raise ValueError("tests_to_run не может быть пустым")


class ConfigValidator:
    """Валидатор конфигурации"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        self.config_data: Optional[Dict[str, Any]] = None
        self.models: List[ModelConfig] = []
        self.logging_config: Optional[LoggingConfig] = None
        self.test_config: Optional[TestConfig] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка парсинга YAML: {e}")
        except Exception as e:
            raise ValueError(f"Ошибка чтения файла конфигурации: {e}")
        
        return self.config_data
    
    def validate_models(self) -> List[ModelConfig]:
        """Валидирует конфигурацию моделей"""
        if not self.config_data:
            raise ValueError("Конфигурация не загружена")
        
        models_data = self.config_data.get('models_to_test', [])
        if not models_data:
            raise ValueError("Секция 'models_to_test' отсутствует или пуста")
        
        models = []
        for i, model_data in enumerate(models_data):
            try:
                model = self._validate_single_model(model_data, i)
                models.append(model)
            except Exception as e:
                raise ValueError(f"Ошибка в модели #{i+1}: {e}")
        
        self.models = models
        return models
    
    def _validate_single_model(self, model_data: Dict[str, Any], index: int) -> ModelConfig:
        """Валидирует конфигурацию одной модели"""
        # Проверяем обязательные поля
        if 'name' not in model_data:
            raise ValueError("Отсутствует обязательное поле 'name'")
        
        if 'client_type' not in model_data:
            raise ValueError("Отсутствует обязательное поле 'client_type'")
        
        name = model_data['name']
        client_type_str = model_data['client_type']
        
        # Валидируем имя модели
        if not name or not isinstance(name, str):
            raise ValueError("'name' должно быть непустой строкой")
        
        # Валидируем тип клиента
        try:
            client_type = ClientType(client_type_str)
        except ValueError:
            valid_types = [t.value for t in ClientType]
            raise ValueError(f"Неверный client_type: {client_type_str}. Допустимые: {valid_types}")
        
        # Валидируем специфичные для типа клиента поля
        api_base = model_data.get('api_base')
        api_key = model_data.get('api_key')
        
        if client_type == ClientType.OPENAI_COMPATIBLE:
            if not api_base:
                raise ValueError("Для openai_compatible клиента обязательно поле 'api_base'")
            if not isinstance(api_base, str):
                raise ValueError("'api_base' должно быть строкой")
        
        # Валидируем опции
        options = model_data.get('options', {})
        if options and not isinstance(options, dict):
            raise ValueError("'options' должно быть словарем")
        
        # Валидируем специфичные опции для каждого типа клиента
        if client_type == ClientType.OLLAMA:
            self._validate_ollama_options(options)
        elif client_type == ClientType.OPENAI_COMPATIBLE:
            self._validate_openai_options(options)
        
        return ModelConfig(
            name=name,
            client_type=client_type,
            api_base=api_base,
            api_key=api_key,
            options=options
        )
    
    def _validate_ollama_options(self, options: Dict[str, Any]):
        """Валидирует опции для Ollama клиента"""
        generation = options.get('generation', {})
        if generation and not isinstance(generation, dict):
            raise ValueError("'generation' должно быть словарем")
        
        # Проверяем temperature
        temperature = generation.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ValueError("'temperature' должно быть числом")
            if not 0 <= temperature <= 2:
                raise ValueError("'temperature' должно быть в диапазоне [0, 2]")
        
        # Проверяем query_timeout
        query_timeout = options.get('query_timeout')
        if query_timeout is not None:
            if not isinstance(query_timeout, int):
                raise ValueError("'query_timeout' должно быть целым числом")
            if query_timeout < 1:
                raise ValueError("'query_timeout' должно быть >= 1")
    
    def _validate_openai_options(self, options: Dict[str, Any]):
        """Валидирует опции для OpenAI-совместимого клиента"""
        generation = options.get('generation', {})
        if generation and not isinstance(generation, dict):
            raise ValueError("'generation' должно быть словарем")
        
        # Проверяем temperature
        temperature = generation.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ValueError("'temperature' должно быть числом")
            if not 0 <= temperature <= 2:
                raise ValueError("'temperature' должно быть в диапазоне [0, 2]")
        
        # Проверяем max_tokens
        max_tokens = generation.get('max_tokens')
        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                raise ValueError("'max_tokens' должно быть целым числом")
            if max_tokens < 1:
                raise ValueError("'max_tokens' должно быть >= 1")
    
    def validate_logging(self) -> LoggingConfig:
        """Валидирует конфигурацию логирования"""
        if not self.config_data:
            raise ValueError("Конфигурация не загружена")
        
        logging_data = self.config_data.get('logging', {})
        
        try:
            self.logging_config = LoggingConfig(**logging_data)
        except Exception as e:
            raise ValueError(f"Ошибка валидации конфигурации логирования: {e}")
        
        return self.logging_config
    
    def validate_tests(self) -> TestConfig:
        """Валидирует конфигурацию тестов"""
        if not self.config_data:
            raise ValueError("Конфигурация не загружена")
        
        tests_to_run = self.config_data.get('tests_to_run', [])
        runs_per_test = self.config_data.get('runs_per_test', 3)
        
        if not tests_to_run:
            raise ValueError("Секция 'tests_to_run' отсутствует или пуста")
        
        if not isinstance(tests_to_run, list):
            raise ValueError("'tests_to_run' должно быть списком")
        
        # Проверяем, что все тесты существуют
        valid_tests = [
            't01_simple_logic', 't02_instructions', 't03_code_gen',
            't04_data_extraction', 't05_summarization', 't06_mathematics'
        ]
        
        for test in tests_to_run:
            if test not in valid_tests:
                raise ValueError(f"Неизвестный тест: {test}. Допустимые: {valid_tests}")
        
        try:
            self.test_config = TestConfig(tests_to_run=tests_to_run, runs_per_test=runs_per_test)
        except Exception as e:
            raise ValueError(f"Ошибка валидации конфигурации тестов: {e}")
        
        return self.test_config
    
    def validate_all(self) -> Dict[str, Any]:
        """Валидирует всю конфигурацию"""
        # Загружаем конфигурацию
        self.load_config()
        
        # Валидируем все секции
        models = self.validate_models()
        logging_config = self.validate_logging()
        test_config = self.validate_tests()
        
        return {
            'models': models,
            'logging': logging_config,
            'tests': test_config,
            'raw_config': self.config_data
        }
    
    def get_validation_summary(self) -> str:
        """Возвращает сводку валидации"""
        try:
            result = self.validate_all()
            
            summary = "✅ Конфигурация валидна\n\n"
            summary += f"📊 Модели: {len(result['models'])}\n"
            for model in result['models']:
                summary += f"  - {model.name} ({model.client_type.value})\n"
            
            summary += f"\n🧪 Тесты: {len(result['tests'].tests_to_run)}\n"
            for test in result['tests'].tests_to_run:
                summary += f"  - {test}\n"
            
            summary += f"\n📝 Логирование: {result['logging'].level} ({result['logging'].format})\n"
            summary += f"🔄 Запусков на тест: {result['tests'].runs_per_test}\n"
            
            return summary
            
        except Exception as e:
            return f"❌ Ошибка валидации: {e}"


def validate_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Удобная функция для валидации конфигурации"""
    validator = ConfigValidator(config_path)
    return validator.validate_all()


def get_config_summary(config_path: Optional[Union[str, Path]] = None) -> str:
    """Удобная функция для получения сводки конфигурации"""
    validator = ConfigValidator(config_path)
    return validator.get_validation_summary()
