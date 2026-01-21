import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from baselogic.core.jvm_runner import JVMRunner, JVMRunnerError


class AbstractTestGenerator(ABC):
    """
    Абстрактный базовый класс ("контракт") для всех генераторов тестов.
    """

    def __init__(self, test_id: str):
        self.test_id = test_id

    def parse_llm_output(self, llm_raw_output: str) -> Dict[str, str]:
        """
        Извлекает структурированный ответ из "сырого" вывода LLM.
        Каждый дочерний класс должен реализовать свою логику парсинга.

        Args:
            llm_raw_output: Полный, необработанный текстовый ответ от модели.

        Returns:
            Словарь со структурированным результатом. Должен содержать как минимум
            ключ 'answer' для передачи в verify().
            Пример: {'answer': 'Елена', 'thinking_log': 'Все рассуждения модели...'}
        """
        # Предоставляем реализацию по умолчанию, которая делает базовую очистку
        # и предполагает, что весь ответ является финальным.
        # Дочерние классы ДОЛЖНЫ переопределить это для сложной логики.
        clean_answer = self._cleanup_llm_response(llm_raw_output)
        return {
            'answer': clean_answer,
            'thinking_log': llm_raw_output  # Сохраняем оригинал для логов
        }

    @abstractmethod
    def generate(self) -> Dict[str, Any]:
        """
        Генерирует тестовый сценарий с промптом и ожидаемым результатом.
        """
        pass

    @abstractmethod
    def verify(self, llm_output: str, expected_output: Any) -> Dict[str, Any]:
        """
        Проверяет ответ модели на соответствие ожиданиям.

        Args:
            llm_output: Полный текстовый ответ от модели (может содержать thinking и т.д.)
            expected_output: Ожидаемый результат из self.generate().

        Returns:
            Dict с результатами валидации, включая:
            - is_correct: Boolean - прошел ли тест
            - details: Dict с детальной информацией о валидации
        """
        pass

    def _cleanup_llm_response(self, llm_output: str) -> str:
        """
        Общий вспомогательный метод для очистки ответа модели от "шума".
        """
        if not isinstance(llm_output, str):
            return ""

        # 1. Удаляем блоки <think>...</think>
        clean_output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL | re.IGNORECASE)

        # 2. Извлекаем содержимое из <response>...</response>
        response_match = re.search(r'<response>(.*?)</response>', clean_output, flags=re.DOTALL | re.IGNORECASE)
        if response_match:
            clean_output = response_match.group(1).strip()

        # 3. Удаляем служебные токены
        stop_tokens = [
            r"</s>.*$", r"<\|eot_id\|>.*$", r"<\|endoftext\|>.*$",
            r"<\|im_start\|>", r"<\|im_end\|>", r"<s>", r"assistant"
        ]
        for token in stop_tokens:
            clean_output = re.sub(token, "", clean_output, flags=re.DOTALL | re.IGNORECASE)

        # 4. Останавливаемся на повторяющемся контенте
        clean_output = re.sub(r"»\s*,\s*.*$", "", clean_output, flags=re.DOTALL)

        # 5. Удаляем Markdown форматирование
        clean_output = re.sub(r'[*_`~]', '', clean_output)

        return clean_output.strip()

    def _sanitize_code(self, code: str) -> str:
        """Замена типографских Unicode-символов на стандартные программные."""
        replacements = {
            chr(0x2014): '-',  # EM DASH → HYPHEN-MINUS
            chr(0x2013): '-',  # EN DASH → HYPHEN-MINUS
            chr(0x2018): "'",  # LEFT SINGLE QUOTATION MARK → APOSTROPHE
            chr(0x2019): "'",  # RIGHT SINGLE QUOTATION MARK → APOSTROPHE
            chr(0x201A): "'",  # SINGLE LOW-9 QUOTATION MARK → APOSTROPHE
            chr(0x201C): '"',  # LEFT DOUBLE QUOTATION MARK → QUOTATION MARK
            chr(0x201D): '"',  # RIGHT DOUBLE QUOTATION MARK → QUOTATION MARK
            chr(0x201E): '"',  # DOUBLE LOW-9 QUOTATION MARK → QUOTATION MARK
            chr(0x2026): '...',  # HORIZONTAL ELLIPSIS → THREE DOTS
            chr(0x00A0): ' ',  # NO-BREAK SPACE → SPACE
        }
        for old, new in replacements.items():
            code = code.replace(old, new)
        return code

    def _extract_kotlin_code(self, llm_output: str) -> Tuple[bool, str, str]:
        """
        Многоступенчатое извлечение Kotlin-кода из вывода LLM.

        Returns:
            (успех, код_или_сообщение_об_ошибке, метод_извлечения)
        """
        # ЭТАП 1: Санитизация ПЕРЕД извлечением (критично!)
        cleaned = self._sanitize_code(llm_output)

        # Удаляем <think> блоки
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Извлекаем из <response> если есть
        response_match = re.search(r'<response>(.*?)</response>', cleaned, flags=re.DOTALL | re.IGNORECASE)
        if response_match:
            cleaned = response_match.group(1).strip()

        # Удаляем служебные токены
        stop_tokens = [r"</s>.*$", r"<\|eot_id\|>.*$", r"<\|endoftext\|>.*$"]
        for token in stop_tokens:
            cleaned = re.sub(token, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # ЭТАП 2: Извлечение кода (3 стратегии с приоритетами)

        # Стратегия 1: Markdown блок с указанием языка kotlin
        pattern1 = r'```kotlin\s*\n(.*?)```'
        match = re.search(pattern1, cleaned, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            if len(code) > 20 and 'fun ' in code:
                return True, code, "markdown_with_kotlin_tag"

        # Стратегия 2: Любой markdown блок (без указания языка)
        pattern2 = r'```\s*\n(.*?)```'
        matches = re.findall(pattern2, cleaned, flags=re.DOTALL)
        for code in matches:
            code = code.strip()
            # Проверяем наличие Kotlin-ключевых слов
            kotlin_keywords = ['fun ', 'val ', 'var ', 'import ', 'class ', 'object ']
            if any(kw in code for kw in kotlin_keywords) and len(code) > 20:
                return True, code, "markdown_generic_with_validation"

        # Стратегия 3: Markdown с произвольным языком (```xxx)
        pattern3 = r'``````'
        match = re.search(pattern3, cleaned, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            kotlin_keywords = ['fun ', 'val ', 'var ', 'import ', 'class ', 'object ']
            if any(kw in code for kw in kotlin_keywords) and len(code) > 20:
                return True, code, "markdown_with_any_lang_tag"

        # Стратегия 4: Прямой поиск функций (fallback)
        func_match = re.search(
            r'((?:import\s+[^\n]+\n)*\s*fun\s+\w+.*)',
            cleaned,
            flags=re.DOTALL
        )
        if func_match:
            code = func_match.group(1).strip()
            # Проверяем наличие main()
            if 'fun main' in code and len(code) > 20:
                return True, code, "direct_function_search"

        # Провал: ничего не найдено
        preview = cleaned[:500].replace('\n', '\\n')
        return False, f"Код не найден. Превью: {preview}", "extraction_failed"

    def execute_kotlin_code(self, code: str, args: Optional[list[str]] = None) -> Dict[str, Any]:
        """
        Выполняет Kotlin-код через JVMRunner.
        """
        try:
            runner = JVMRunner()
            output = runner.run_kotlin_code(kotlin_source=code, args=args)
            return {'success': True, 'output': output}
        except JVMRunnerError as exc:
            return {
                'success': False,
                'error': f'Ошибка выполнения JVM: {exc}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка при запуске кода: {e}'
            }
