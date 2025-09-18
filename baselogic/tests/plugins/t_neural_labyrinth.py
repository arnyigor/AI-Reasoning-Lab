import ast
import logging
import random
import re
from typing import Dict, Any

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class NeuralLabyrinthTestGenerator(AbstractTestGenerator):
    """
    Комплексный генератор тестов на основе BrainCraft Challenge.

    Проверяет способность LLM решать задачи, объединяющие:
    - Рекурсивный обход лабиринта
    - Динамическое программирование для оптимизации весов
    - Матричные операции нейронной сети
    - Логические цепочки принятия решений
    - Обработку ошибок и ограничений
    """

    # Базовые конфигурации лабиринтов (0=стена, 1=путь, 2=энергия, 3=ловушка)
    MAZE_TEMPLATES = [
        [
            [1, 0, 1, 1, 2],
            [1, 0, 0, 1, 0],
            [1, 1, 1, 1, 0],
            [0, 3, 1, 0, 1],
            [1, 1, 1, 1, 1]
        ],
        [
            [1, 1, 0, 2, 1],
            [0, 1, 0, 0, 1],
            [1, 1, 1, 1, 1],
            [1, 0, 3, 0, 1],
            [1, 1, 1, 1, 1]
        ]
    ]

    def generate(self) -> Dict[str, Any]:
        """
        Генерирует комплексную задачу нейронного лабиринта.
        """
        maze = random.choice(self.MAZE_TEMPLATES)
        start_pos = (0, 0)
        initial_energy = random.randint(15, 25)
        max_steps = random.randint(20, 30)

        # Создаем случайные начальные веса для нейросети
        hidden_size = 4
        input_weights = [[round(random.uniform(-1, 1), 2) for _ in range(3)] for _ in range(hidden_size)]
        output_weights = [round(random.uniform(-1, 1), 2) for _ in range(hidden_size)]

        prompt = f"""
Реализуй систему управления ботом в лабиринте с нейронной сетью.

ЗАДАЧА:
Создай класс NeuralBot, который использует простую нейронную сеть для навигации по лабиринту 5x5.

СПЕЦИФИКАЦИИ:
1. Лабиринт: {maze}
   - 0: стена (непроходимо)
   - 1: свободный путь
   - 2: источник энергии (+5 энергии)
   - 3: ловушка (-3 энергии)

2. Начальные параметры:
   - Позиция: {start_pos}
   - Энергия: {initial_energy}
   - Максимум шагов: {max_steps}

3. Архитектура нейросети:
   - Вход: [направление_x, направление_y, текущая_энергия] (3 нейрона)
   - Скрытый слой: {hidden_size} нейронов
   - Выход: 1 нейрон (решение: 0=стоп, 1=двигаться)
   - Начальные веса входного слоя: {input_weights}
   - Начальные веса выходного слоя: {output_weights}

4. Формулы нейросети:
   - hidden[i] = tanh(sum(input[j] * W_in[i][j] for j in range(3)))
   - output = sigmoid(sum(hidden[i] * W_out[i] for i in range({hidden_size})))

ТРЕБУЕМЫЙ КОД:
Создай полный класс NeuralBot со следующими методами:

1. __init__(self, maze, start_pos, initial_energy, max_steps, input_weights, output_weights)
2. get_valid_moves(self) -> List[Tuple[int, int]] # Возвращает допустимые ходы
3. neural_decision(self, target_pos) -> bool # Принимает решение через нейросеть
4. dynamic_pathfind(self, targets) -> Optional[List[Tuple[int, int]]] # DP поиск оптимального пути
5. execute_step(self, direction) -> str # Выполняет ход с обработкой ошибок
6. run_simulation(self) -> Dict[str, Any] # Основной цикл симуляции

КРИТЕРИИ УСПЕХА:
- Бот должен найти хотя бы 1 источник энергии
- Энергия в конце должна быть > 0
- Код должен обрабатывать все типы ошибок
- Использовать рекурсию в pathfind и DP для оптимизации

Верни ТОЛЬКО Python код класса без объяснений.
"""

        # Вычисляем ожидаемый результат
        expected_energy_sources = sum(row.count(2) for row in maze)
        expected_traps = sum(row.count(3) for row in maze)

        # Минимальный успешный результат
        min_energy_found = max(1, expected_energy_sources // 2)

        return {
            'prompt': prompt,
            'expected_output': {
                'min_energy_sources_found': min_energy_found,
                'max_energy_sources': expected_energy_sources,
                'total_traps': expected_traps,
                'maze_size': (5, 5),
                'required_methods': [
                    '__init__', 'get_valid_moves', 'neural_decision',
                    'dynamic_pathfind', 'execute_step', 'run_simulation'
                ],
                'success_criteria': {
                    'final_energy_positive': True,
                    'found_energy_sources': True,
                    'proper_error_handling': True,
                    'uses_neural_network': True,
                    'uses_dynamic_programming': True
                }
            },
            'test_name': f"neural_labyrinth_{initial_energy}_{max_steps}",
            'metadata': {
                'maze': maze,
                'start_position': start_pos,
                'initial_energy': initial_energy,
                'max_steps': max_steps,
                'input_weights': input_weights,
                'output_weights': output_weights,
                'complexity_level': 'expert',
                'test_categories': [
                    'recursion', 'dynamic_programming', 'matrix_operations',
                    'logical_chains', 'error_handling'
                ]
            }
        }

    def verify(self, llm_output: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """Комплексная проверка решения на основе CodeGenTestGenerator подхода."""
        try:
            # 1. Извлекаем и санитизируем код
            clean_code = self._extract_python_code(llm_output)
            if not clean_code:
                return self._failure_result("Не найден Python код в ответе")

            # 2. Санитизируем код
            clean_code = self._sanitize_code(clean_code)

            # 3. Проверяем синтаксис
            try:
                compile(clean_code, '<string>', 'exec')
            except SyntaxError as e:
                return self._failure_result(f"Синтаксическая ошибка: {e}")

            # 4. Выполняем и проверяем
            verification_results = self._execute_and_verify(clean_code, expected_output)

            return verification_results

        except Exception as e:
            log.error(f"Критическая ошибка в verify: {e}")
            return self._failure_result(f"Критическая ошибка проверки: {str(e)}")


    def _extract_python_code(self, llm_output: str) -> str:
        """УЛУЧШЕННОЕ извлечение Python кода на основе CodeGenTestGenerator."""

        # Удаляем thinking блоки
        output = re.sub(r'<think>.*?</think>', '', llm_output, flags=re.DOTALL)

        # 1. Ищем код в markdown блоках python (приоритет 1)
        code_match = re.search(r"``````", output, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # 2. Ищем код в обычных markdown блоках (приоритет 2)
        code_match = re.search(r"``````", output, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # 3. Ищем прямо определение класса (приоритет 3)
        code_match = re.search(r"class\s+NeuralBot.*", output, re.DOTALL)
        if code_match:
            return code_match.group(0).strip()

        # 4. Последняя попытка - любое определение функции или класса
        code_match = re.search(r"def\s.*|class\s.*", output, re.DOTALL)
        if code_match:
            return code_match.group(0).strip()

        return ""

    def _sanitize_code(self, code: str) -> str:
        """Санитизация кода - замена типографских символов на стандартные Python."""

        # Замены из CodeGenTestGenerator + дополнительные
        replacements = {
            # Кавычки
            ''': "'",  # Левая одинарная кавычка
            ''': "'",  # Правая одинарная кавычка
            '"': '"',  # Левая двойная кавычка
            '"': '"',  # Правая двойная кавычка

            # Тире и минусы
            '—': '-',  # Длинное тире
            '–': '-',  # Среднее тире
            '−': '-',  # Математический минус

            # Пробелы
            '\xa0': ' ',  # Неразрывный пробел
            '\u2009': ' ',  # Тонкий пробел

            # Специальные символы
            '…': '...',  # Многоточие
        }

        for old, new in replacements.items():
            code = code.replace(old, new)

        return code



    def _execute_and_verify(self, code: str, expected_output: Dict[str, Any]) -> Dict[str, Any]:
        """УЛУЧШЕННОЕ выполнение на основе CodeGenTestGenerator."""
        verification_score = 0
        max_score = 100
        details = {}

        try:
            # УЛУЧШЕНИЕ: Санитизация кода перед выполнением
            clean_code = self._sanitize_code(code)

            # УЛУЧШЕНИЕ: Более безопасный namespace (как в CodeGenTestGenerator)
            import builtins
            namespace = {
                '__builtins__': {
                    'range': range, 'len': len, 'sum': sum, 'max': max, 'min': min,
                    'abs': abs, 'round': round, 'int': int, 'float': float,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'enumerate': enumerate, 'zip': zip, 'print': print,
                    '__build_class__': builtins.__build_class__,  # ✅ ПРАВИЛЬНЫЙ ИМПОРТ
                    '__name__': '__main__',
                    '__import__': __import__  # Для math/random
                },
                'math': __import__('math'),
                'random': __import__('random')
            }

            # Выполняем код
            local_scope = {}
            try:
                exec(clean_code, namespace, local_scope)
            except SyntaxError as e:
                return self._failure_result(f"Синтаксическая ошибка: {str(e)}")
            except Exception as exec_error:
                return self._failure_result(f"Ошибка выполнения кода: {str(exec_error)}")

            # Проверяем наличие класса NeuralBot (аналог проверки функции в CodeGenTestGenerator)
            if 'NeuralBot' not in local_scope:
                return self._failure_result("Класс NeuralBot не найден в коде")

            bot_class = local_scope['NeuralBot']

            # Безопасное получение метаданных
            try:
                metadata = expected_output.get('metadata')
                if not metadata:
                    test_data = self.generate()
                    metadata = test_data['metadata']

                # Создаем экземпляр в том же scope
                bot = bot_class(
                    maze=metadata['maze'],
                    start_pos=metadata['start_position'],
                    initial_energy=metadata['initial_energy'],
                    max_steps=metadata['max_steps'],
                    input_weights=metadata['input_weights'],
                    output_weights=metadata['output_weights']
                )

            except Exception as init_error:
                return self._failure_result(f"Ошибка создания экземпляра NeuralBot: {str(init_error)}")

            # Проверка методов
            required_methods = expected_output.get('required_methods', [
                '__init__', 'get_valid_moves', 'neural_decision',
                'dynamic_pathfind', 'execute_step', 'run_simulation'
            ])

            missing_methods = []
            for method in required_methods:
                if not hasattr(bot, method):
                    missing_methods.append(method)
                else:
                    verification_score += 20 // len(required_methods)

            details['missing_methods'] = missing_methods

            # Если все методы есть, запускаем "тесты" (аналог test_case в CodeGenTestGenerator)
            if not missing_methods:
                try:
                    # Запускаем симуляцию как основной "тест"
                    simulation_result = bot.run_simulation()
                    details['simulation_result'] = simulation_result

                    # "Тесты" производительности (аналог assert'ов в CodeGenTestGenerator)
                    if simulation_result.get('final_energy', 0) > 0:
                        verification_score += 10
                        details['final_energy_positive'] = True
                    else:
                        details['final_energy_positive'] = False

                    energy_found = simulation_result.get('energy_sources_found', 0)
                    min_required = expected_output.get('min_energy_sources_found', 1)
                    if energy_found >= min_required:
                        verification_score += 10
                        details['found_sufficient_energy'] = True

                    # Проверяем что нейросеть использовалась
                    if 'neural_decisions' in simulation_result and len(simulation_result['neural_decisions']) > 0:
                        verification_score += 10
                        details['uses_neural_network'] = True

                    # Проверяем обработку ошибок
                    if 'errors_handled' in simulation_result:
                        verification_score += 10
                        details['proper_error_handling'] = True

                    verification_score += 40  # Бонус за успешное выполнение

                except AssertionError as e:
                    details['simulation_error'] = f'Логическая ошибка (AssertionError): {str(e)}'
                except Exception as e:
                    details['simulation_error'] = f'Ошибка симуляции: {str(e)}'
            else:
                # Инициализируем поля даже при отсутствующих методах
                details['final_energy_positive'] = False
                details['found_sufficient_energy'] = False
                details['uses_neural_network'] = False
                details['proper_error_handling'] = False

            # Анализ структуры кода
            try:
                code_analysis = self._analyze_code_structure(clean_code)
                details['code_analysis'] = code_analysis

                if code_analysis.get('has_recursion', False):
                    verification_score += 10
                if code_analysis.get('has_dynamic_programming', False):
                    verification_score += 10
            except Exception as analysis_error:
                details['code_analysis_error'] = str(analysis_error)

        except Exception as e:
            return self._failure_result(f"Критическая ошибка: {str(e)}")

        is_correct = verification_score >= 70

        return {
            'is_correct': is_correct,
            'score': verification_score,
            'max_score': max_score,
            'details': details
        }






    def _analyze_code_structure(self, code: str) -> Dict[str, bool]:
        """Исправленный анализ структуры кода."""
        analysis = {
            'has_recursion': False,
            'has_dynamic_programming': False,
            'has_matrix_operations': False,
            'has_error_handling': False
        }

        try:
            # ИСПРАВЛЕНИЕ: Безопасный поиск рекурсии
            lines = code.split('\n')
            current_function = None

            for line in lines:
                line = line.strip()

                # Нашли определение функции
                func_match = re.match(r'def\s+(\w+)', line)
                if func_match:
                    current_function = func_match.group(1)

                # Если мы внутри функции и нашли ее вызов
                elif current_function and f'{current_function}(' in line:
                    analysis['has_recursion'] = True
                    break

            # DP паттерны
            code_lower = code.lower()
            dp_keywords = ['memo', 'cache', 'dp', 'dynamic', 'table']
            analysis['has_dynamic_programming'] = any(keyword in code_lower for keyword in dp_keywords)

            # Матричные операции
            matrix_keywords = ['sum(', 'dot', '@', 'multiply', '*']
            analysis['has_matrix_operations'] = any(keyword in code for keyword in matrix_keywords)

            # Обработка ошибок
            error_keywords = ['try:', 'except:', 'raise', 'assert']
            analysis['has_error_handling'] = any(keyword in code for keyword in error_keywords)

        except Exception:
            # В случае ошибки возвращаем безопасные значения
            pass

        return analysis


    def _failure_result(self, reason: str) -> Dict[str, Any]:
        """Создает результат неудачного теста."""
        return {
            'is_correct': False,
            'score': 0,
            'max_score': 100,
            'details': {
                'reason': reason,
                'success': False
            }
        }

    def get_test_description(self) -> str:
        """Возвращает описание комплексного теста."""
        return (
            "Комплексный тест Neural Labyrinth проверяет способность модели "
            "интегрировать множественные алгоритмические концепции: рекурсивную "
            "навигацию, динамическое программирование, матричные вычисления нейросети, "
            "логические цепочки принятия решений и обработку ошибок в единой системе "
            "управления ботом."
        )
