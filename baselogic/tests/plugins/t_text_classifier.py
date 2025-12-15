import re
from typing import Dict, Any, TypedDict, List, Union

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class ExpectedOutput(TypedDict):
    # correct: может быть строкой или списком строк
    correct: Union[str, List[str]]


class TextClassifierTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет задачи по классификации текста.
    Использует внутренний счетчик для переключения между тестами.
    """
    # Атрибут класса для отслеживания текущего индекса теста
    _test_counter = 0

    def __init__(self, test_id: str = None):
        super().__init__(test_id)

        # Тестовые случаи для разных настроений
        # Для спорных случаев можно указать список допустимых ответов
        self.test_cases = [
            {
                "review": "Этот продукт потрясающий! Рекомендую всем!",
                "expected": "положительное"
            },
            {
                "review": "Качество ужасное, деньги на ветер",
                "expected": ["отрицательное", "недовольное"]
            },
            {
                # Спорный случай: может быть как нейтральным, так и положительным
                "review": "Нормальный продукт за разумные деньги",
                "expected": ["нейтральное", "положительное"]
            },
            {
                "review": "Просто великолепно! Лучшее, что я покупал!",
                "expected": "положительное"
            },
            {
                "review": "Не работает, сломалось через неделю",
                "expected": ["отрицательное", "недовольное"]
            },
            {
                # Спорный случай: может быть как нейтральным, так и положительным
                "review": "Товар среднего качества, цена соответствует",
                "expected": ["нейтральное", "положительное"]
            },
            {
                "review": "Восхитительно! Превзошло все ожидания!",
                "expected": "положительное"
            },
            {
                "review": "Отвратительный сервис, никогда больше не куплю",
                "expected": ["отрицательное", "недовольное"]
            },
            {
                "review": "Обычный товар, ничего особенного",
                "expected": ["нейтральное", "положительное"]
            },
            {
                "review": "Идеальное соотношение цены и качества!",
                "expected": "положительное"
            },
            {
                "review": "Полный развод, не советую никому",
                "expected": ["отрицательное", "недовольное"]
            },
            {
                "review": "Товар соответствует описанию в каталоге",
                "expected": ["нейтральное", "положительное"]
            }
        ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует задачу классификации настроения отзыва.
        Использует внутренний счетчик для выбора тестового случая.

        Returns:
            Dict[str, Any]: Словарь с prompt и ожидаемым ответом.
        """
        # Получаем текущий индекс и увеличиваем счетчик для следующего вызова
        current_index = TextClassifierTestGenerator._test_counter
        TextClassifierTestGenerator._test_counter += 1

        # Выбираем тестовый случай циклически
        selected_case = self.test_cases[current_index % len(self.test_cases)]

        prompt = f"Классифицируй настроение отзыва как положительное, отрицательное или нейтральное: '{selected_case['review']}'. Ответь одним словом."
        expected_output: ExpectedOutput = {"correct": selected_case['expected']}

        return {
            "prompt": prompt,
            "expected_output": expected_output,
        }

    def verify(self, llm_output: str, expected_output: ExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет ответ модели, извлекая классификацию из различных форматов ответов.
        Поддерживает список допустимых ответов.

        Args:
            llm_output (str): Ответ, полученный от модели.
            expected_output (ExpectedOutput): Ожидаемый ответ (строка или список строк).

        Returns:
            Dict[str, Any]: Результат проверки.
        """
        # Обрабатываем ожидаемый ответ как список
        expected_answers_raw = expected_output["correct"]
        if isinstance(expected_answers_raw, str):
            expected_answers_list = [expected_answers_raw]
        else:
            expected_answers_list = expected_answers_raw

        # Приводим все ожидаемые ответы к нижнему регистру и убираем пробелы
        expected_clean_list = [ans.strip().lower() for ans in expected_answers_list]

        cleaned_output = self._cleanup_llm_response(llm_output).strip().lower()

        # Проверка на пустой вывод
        if not cleaned_output:
            return {
                "is_correct": False,
                "details": {
                    "reason": "Ответ модели пуст после очистки.",
                    "expected_one_of": expected_answers_list
                },
            }

        # Извлечение классификации из различных форматов
        extracted_classification = self._extract_classification(cleaned_output)

        # Проверка на принадлежность к одному из допустимых
        is_correct = extracted_classification in expected_clean_list

        details = {
            "reason": "OK" if is_correct else "Некорректный ответ",
            "expected_one_of": expected_answers_list,
            "actual": llm_output,
            "cleaned_actual": cleaned_output,
            "extracted_classification": extracted_classification,
            "is_in_expected_list": is_correct,
        }

        return {
            "is_correct": is_correct,
            "details": details,
        }

    def _extract_classification(self, text: str) -> str:
        """
        Извлекает классификацию из различных форматов ответов.

        Args:
            text (str): Текст ответа модели.

        Returns:
            str: Извлеченная классификация.
        """
        # Убираем пробелы и переводы строк в начале и конце
        text = text.strip()

        # Паттерны для извлечения классификации
        patterns = [
            # --- Для структурированных ответов с ключевыми словами ---
            r'(?:настроение|оценка|классификация)(?:\s+отзыва)?:\s*(.+?)(?:\n|$)',
            # "Настроение: <метка>", "Оценка: <метка>", "Классификация отзыва: <метка>"
            r'(?:настроение|оценка|классификация)(?:\s+отзыва)?\s*[-—–:]\s*\**(.+?)\**\s*(?:\n|$)',
            # "Настроение - <метка>", "Оценка — **<метка>**"

            # --- Для ответов с выделением звездочками ---
            r'\**(.+?)\**$',  # "**Положительное**" (в конце строки)
            r'\*\*(.+?)\*\*',  # "**Положительное**" (где угодно)

            # --- Более гибкие паттерны для извлечения из середины сложного текста ---
            r'(?:настроение|оценка|классификация)(?:\s+отзыва)?:?\s*\**(.+?)\**',  # Более гибкий вариант первых двух

            # --- Простые ответы в конце (последний приоритет) ---
            r'(.+?)$',  # "Положительное" (последняя строка или строка целиком)

            # --- Прямой поиск одной из меток (резервный вариант) ---
            r'\b(положительное|отрицательное|нейтральное)\b',
        ]

        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    classification = match.group(1).strip().lower()
                    # Убираем возможные знаки препинания в конце
                    classification = classification.rstrip('.,!?:;')
                    # Проверяем, что это одна из допустимых классификаций
                    valid_classifications = ['положительное', 'отрицательное', 'нейтральное']
                    if classification in valid_classifications:
                        return classification
            except re.error:
                # Игнорируем ошибки регулярных выражений
                continue

        # Если не удалось извлечь, возвращаем оригинальный текст
        return text
