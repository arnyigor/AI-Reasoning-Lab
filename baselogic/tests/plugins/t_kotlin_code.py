import json
from pathlib import Path
from typing import Dict, Any, Optional

from pydantic.v1 import ConfigError

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class KotlinCodeGenTestGenerator(AbstractTestGenerator):
    """
    Универсальный генератор тестов для Kotlin, управляемый через JSON-конфиг.
    Позволяет менять промпты и проверки без правки кода.
    """

    def __init__(self, test_id: str, config: Optional[Dict] = None, *, config_path: Optional[str | Path] = None) -> None:
        super().__init__(test_id)
        if config is not None:
            self.config = dict(config)
            return

        # 1. Если путь явно не указан – ищем рядом с файлом класса
        if config_path is None:
            default_cfg = Path(__file__).with_name("test_config.json")
            config_path = default_cfg if default_cfg.is_file() else None

        if config_path is None:
            raise ConfigError(
                "Either `config` dict or `config_path` must be supplied"
            )

        cfg_file = Path(config_path)
        try:
            with cfg_file.open("r", encoding="utf-8") as f:
                self.config = json.load(f)
        except FileNotFoundError as exc:
            raise ConfigError(
                f"Config file {cfg_file} not found"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"Invalid JSON in {cfg_file}"
            ) from exc

    def generate(self) -> Dict[str, Any]:
        """Генерирует тестовый кейс на основе загруженного конфига."""

        # Можно добавить динамическую подстановку переменных в промпт, если нужно
        prompt = self.config['prompt_template']

        return {
            'prompt': prompt,
            'expected_output': {
                'function_name': self.config['execution']['function_name'],
                'test_input': self.config['execution']['input_args'],
                'expected_result': self.config['execution']['expected_output'],
                'validation_type': self.config['validation']['type'],
                'output_type': self.config['validation']['output_type']
            }
        }

    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """Универсальная верификация на основе правил из конфига."""

        # 1. Извлечение кода (используем ваш существующий метод)
        success, code_to_exec, method = self._extract_kotlin_code(llm_output)

        if not success:
            return self._error_response("Блок кода Kotlin не найден", method, code_to_exec)

        # 2. Подготовка аргументов
        input_args = expected_output['test_input']  # List ["abc"]

        # 3. Выполнение кода
        try:
            # Передаем аргументы в JVM runner
            exec_result = self.execute_kotlin_code(code_to_exec, args=input_args)
        except Exception as e:
            return self._error_response(f"Ошибка вызова execute_code: {e}", method, code_to_exec)

        if not exec_result.get('success'):
            return self._error_response(
                "Ошибка выполнения/компиляции",
                method,
                code_to_exec,
                exec_result.get('error') or exec_result.get('stderr')
            )

        # 4. Валидация результата
        output_str = exec_result.get('output', '').strip()
        last_line = output_str.split('\n')[-1] if output_str else ""

        expected_val = expected_output['expected_result']
        out_type = expected_output.get('output_type', 'str')

        try:
            # Приведение типов на основе конфига
            if out_type == 'int':
                actual_val = int(last_line)
            elif out_type == 'float':
                actual_val = float(last_line)
            elif out_type == 'bool':
                actual_val = last_line.lower() == 'true'
            else:
                actual_val = last_line

            # Сравнение
            is_correct = (actual_val == expected_val)

            return {
                'is_correct': is_correct,
                'details': {
                    'actual': actual_val,
                    'expected': expected_val,
                    'extraction_method': method,
                    'status': '✓ OK' if is_correct else '✗ Mismatch'
                }
            }

        except ValueError as e:
            return self._error_response(f"Не удалось привести вывод к типу {out_type}", method, output_str, str(e))

    def _error_response(self, error_msg: str, method: str, preview: str, raw_err: str = "") -> Dict:
        return {
            'is_correct': False,
            'details': {
                'error': error_msg,
                'extraction_method': method,
                'code_preview': preview[:300],
                'raw_error': raw_err
            }
        }
