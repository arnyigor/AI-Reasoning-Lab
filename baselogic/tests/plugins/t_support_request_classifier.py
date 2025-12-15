from typing import Dict, Any, TypedDict

from baselogic.tests.abstract_test_generator import AbstractTestGenerator


class ExpectedOutput(TypedDict):
    correct: str


class SupportRequestClassifierTestGenerator(AbstractTestGenerator):
    """
    Генерирует и проверяет задачи по категоризации обращений в службу поддержки.
    Использует test_id для выбора разных тестовых случаев.
    """

    def __init__(self, test_id: str = None):
        super().__init__(test_id)

        # Тестовые случаи для разных категорий
        self.test_cases = [
            {
                "request": "Не могу войти в свой аккаунт, выдает ошибку",
                "expected": "техническая проблема"
            },
            {
                "request": "Как получить счет за прошлый месяц?",
                "expected": "информационный запрос"
            },
            {
                "request": "Хочу вернуть товар, он не подошел по размеру",
                "expected": "запрос возврата"
            },
            {
                "request": "Почему с меня списали дополнительную комиссию?",
                "expected": "вопрос по оплате"
            },
            {
                "request": "Ваш сервис работает ужасно, постоянно зависает",
                "expected": "жалоба"
            },
            {
                "request": "Забыл пароль от своего аккаунта, помогите восстановить",
                "expected": "техническая проблема"
            },
            {
                "request": "Можно ли оплатить заказ через СБП?",
                "expected": "вопрос по оплате"
            },
            {
                "request": "Товар пришел поврежденный, хочу оформить возврат",
                "expected": "запрос возврата"
            },
            {
                "request": "Где можно посмотреть историю заказов?",
                "expected": "информационный запрос"
            },
            {
                "request": "С вашего сервиса утекли персональные данные клиентов",
                "expected": "жалоба"
            },
            {
                "request": "Приложение вылетает при запуске, не могу открыть",
                "expected": "техническая проблема"
            },
            {
                "request": "Не проходит оплата картой, пишет ошибку",
                "expected": "вопрос по оплате"
            },
            {
                "request": "Нужно вернуть деньги за просроченный заказ",
                "expected": "запрос возврата"
            },
            {
                "request": "Как изменить адрес доставки для текущего заказа?",
                "expected": "информационный запрос"
            },
            {
                "request": "Операторы грубят и не решают проблему уже неделю",
                "expected": "жалоба"
            }
        ]

    def _extract_test_number(self) -> int:
        """Извлекает номер теста из test_id (например, t_support_request_classifier_3 -> 3)"""
        if not self.test_id:
            return 0

        # Ищем число в конце test_id
        import re
        match = re.search(r'_(\d+)$', self.test_id)
        if match:
            return int(match.group(1))
        return 0

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует задачу категоризации обращения в службу поддержки.
        Использует номер из test_id для выбора тестового случая.

        Returns:
            Dict[str, Any]: Словарь с prompt и ожидаемым ответом.
        """
        # Получаем номер теста из test_id
        test_number = self._extract_test_number()

        # Выбираем тестовый случай циклически
        selected_case = self.test_cases[test_number % len(self.test_cases)]

        categories = [
            "техническая проблема",
            "вопрос по оплате",
            "запрос возврата",
            "информационный запрос",
            "жалоба"
        ]

        prompt = f"Определи категорию обращения из списка: {', '.join(categories)}. Обращение: \"{selected_case['request']}\". Категория:"
        expected_output: ExpectedOutput = {"correct": selected_case['expected']}

        return {
            "prompt": prompt,
            "expected_output": expected_output,
        }

    def verify(self, output: str, expected_output: ExpectedOutput) -> Dict[str, Any]:
        """
        Проверяет ответ модели по точному совпадению категории.

        Args:
            llm_output (str): Ответ, полученный от модели.
            expected_output (ExpectedOutput): Ожидаемый ответ.

        Returns:
            Dict[str, Any]: Результат проверки.
        """
        correct_answer = expected_output["correct"]
        llm_output = self._cleanup_llm_response(output)
        cleaned_output = llm_output.strip().lower()
        expected_clean = correct_answer.strip().lower()

        # Проверка на пустой вывод
        if not cleaned_output:
            return {
                "is_correct": False,
                "details": {"reason": "Ответ модели пуст после очистки."},
            }

        # Простая проверка на вхождение ожидаемой категории
        is_correct = expected_clean in cleaned_output

        details = {
            "reason": "OK" if is_correct else "Некорректная категория",
            "expected": correct_answer,
            "actual": llm_output,
            "cleaned_actual": cleaned_output,
            "contains_check": is_correct,
        }

        return {
            "is_correct": is_correct,
            "details": details,
        }
