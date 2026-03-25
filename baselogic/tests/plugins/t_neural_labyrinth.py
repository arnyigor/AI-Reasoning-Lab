import logging
import math
import random
import re
import traceback
from typing import Dict, Any, Optional, List, Tuple

from baselogic.tests.abstract_test_generator import AbstractTestGenerator

log = logging.getLogger(__name__)


class NeuralLabyrinthTestGenerator(AbstractTestGenerator):
    """
    Комплексный генератор тестов: нейросеть + навигация по лабиринту.

    ИСПРАВЛЕНИЯ v4:
    - Контролируемый __import__ вместо None (белый список модулей)
    - Полный traceback в деталях ошибки
    - Устойчивость к багам модели (бесконечный цикл, etc.)
    """

    MAZE_TEMPLATES = [
        [
            [1, 0, 1, 1, 2],
            [1, 0, 0, 1, 0],
            [1, 1, 1, 1, 0],
            [0, 3, 1, 0, 1],
            [1, 1, 1, 1, 1],
        ],
        [
            [1, 1, 0, 2, 1],
            [0, 1, 0, 0, 1],
            [1, 1, 1, 1, 1],
            [1, 0, 3, 0, 1],
            [1, 1, 1, 1, 1],
        ],
    ]

    # Белый список модулей, которые модель может импортировать
    ALLOWED_MODULES = {
        'math', 'collections', 'heapq', 'itertools',
        'functools', 'operator', 'copy', 'random',
        'typing', 'abc', 'enum', 'dataclasses',
    }

    SAFE_BUILTINS = {
        # Типы
        'bool': bool, 'int': int, 'float': float, 'str': str,
        'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
        'frozenset': frozenset, 'bytes': bytes, 'bytearray': bytearray,
        'complex': complex, 'type': type, 'object': object,
        # Функции
        'abs': abs, 'all': all, 'any': any, 'bin': bin,
        'callable': callable, 'chr': chr, 'dir': dir,
        'divmod': divmod, 'enumerate': enumerate,
        'filter': filter, 'format': format,
        'getattr': getattr, 'hasattr': hasattr, 'setattr': setattr,
        'hash': hash, 'hex': hex, 'id': id,
        'isinstance': isinstance, 'issubclass': issubclass,
        'iter': iter, 'len': len, 'map': map,
        'max': max, 'min': min, 'next': next,
        'oct': oct, 'ord': ord, 'pow': pow,
        'print': print, 'range': range, 'repr': repr,
        'reversed': reversed, 'round': round,
        'slice': slice, 'sorted': sorted, 'sum': sum,
        'zip': zip,
        # Константы
        'True': True, 'False': False, 'None': None,
        # Исключения (нужны для try/except в коде модели)
        'Exception': Exception, 'ValueError': ValueError,
        'TypeError': TypeError, 'IndexError': IndexError,
        'KeyError': KeyError, 'RuntimeError': RuntimeError,
        'StopIteration': StopIteration, 'RecursionError': RecursionError,
        'ZeroDivisionError': ZeroDivisionError,
        'AttributeError': AttributeError, 'NameError': NameError,
        'OverflowError': OverflowError,
        # Декораторы и класс-инструменты
        'property': property, 'staticmethod': staticmethod,
        'classmethod': classmethod, 'super': super,
    }

    def _make_safe_import(self):
        """
        Создаёт контролируемую функцию __import__, которая
        разрешает импорт только из белого списка.
        """
        allowed = self.ALLOWED_MODULES

        def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            # Извлекаем корневой модуль (для 'collections.abc' → 'collections')
            root_module = name.split('.')[0]
            if root_module not in allowed:
                raise ImportError(
                    f"Импорт модуля '{name}' заблокирован. "
                    f"Разрешены: {', '.join(sorted(allowed))}"
                )
            return __builtins__['__import__'](name, globals, locals, fromlist, level)

        return safe_import

    def generate(self) -> Dict[str, Any]:
        maze = random.choice(self.MAZE_TEMPLATES)
        start_pos = (0, 0)
        initial_energy = random.randint(15, 25)
        max_steps = random.randint(20, 30)

        hidden_size = 4
        input_weights = [
            [round(random.uniform(-1, 1), 2) for _ in range(3)]
            for _ in range(hidden_size)
        ]
        output_weights = [
            round(random.uniform(-1, 1), 2) for _ in range(hidden_size)
        ]

        expected_energy_sources = sum(row.count(2) for row in maze)
        expected_traps = sum(row.count(3) for row in maze)
        min_energy_found = max(1, expected_energy_sources // 2)

        prompt = f"""Реализуй систему управления ботом в лабиринте с нейронной сетью.

ЗАДАЧА:
Создай класс NeuralBot, который использует простую нейронную сеть для навигации по лабиринту 5x5.

ВАЖНО: В начале кода добавь все необходимые импорты (math, heapq и т.д.).

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
   - Выход: 1 нейрон (решение: значение > 0.5 означает "двигаться")
   - Веса входного слоя: {input_weights}
   - Веса выходного слоя: {output_weights}

4. Формулы нейросети:
   - hidden[i] = tanh(sum(input[j] * W_in[i][j] for j in range(3)))
   - output = sigmoid(sum(hidden[i] * W_out[i] for i in range(4)))
   - sigmoid(x) = 1 / (1 + exp(-x))

ТРЕБУЕМЫЕ МЕТОДЫ КЛАССА NeuralBot:

1. __init__(self, maze, start_pos, initial_energy, max_steps, input_weights, output_weights)
   - Сохрани все параметры. Сделай копию лабиринта.

2. get_valid_moves(self) -> List[Tuple[int, int]]
   - Возвращает список допустимых направлений (dx, dy) из текущей позиции.
   - Направления: (0,1)=вправо, (0,-1)=влево, (1,0)=вниз, (-1,0)=вверх.
   - Клетка допустима если она в пределах лабиринта и не стена (значение != 0).

3. neural_decision(self, target_pos) -> bool
   - input = [target_pos[0] - pos[0], target_pos[1] - pos[1], energy / 100.0]
   - Прогоняет через нейросеть по формулам выше.
   - Возвращает True если output > 0.5.

4. dynamic_pathfind(self, targets) -> Optional[List[Tuple[int, int]]]
   - Находит кратчайший путь от текущей позиции до ближайшей цели из списка targets.
   - Использует BFS с мемоизацией посещённых клеток.
   - Возвращает список координат [(x1,y1), (x2,y2), ...] или None если путь не найден.

5. execute_step(self, direction) -> str
   - direction — кортеж (dx, dy).
   - Проверяет валидность хода.
   - Обновляет позицию: pos = (pos[0]+dx, pos[1]+dy).
   - Обрабатывает клетку: 2 → энергия +5, 3 → энергия -3.
   - После посещения клетки 2 или 3 — ставит 1 (уже посещено).
   - Увеличивает счётчик шагов.
   - Возвращает строку описания результата.

6. run_simulation(self) -> Dict[str, Any]
   - Основной цикл: пока есть шаги и энергия > 0.
   - На каждом шаге: получает допустимые ходы, использует нейросеть для принятия решения.
   - Записывает историю решений нейросети.
   - ОБЯЗАТЕЛЬНЫЙ ФОРМАТ ВОЗВРАТА:
     {{
         "final_energy": int,
         "steps_taken": int,
         "energy_sources_found": int,
         "neural_decisions": list,
         "errors_handled": int,
         "path": list
     }}

Верни ТОЛЬКО Python код (класс + импорты) внутри блока ```python ... ```.
Не добавляй блок if __name__ и не добавляй объяснений."""

        return {
            'prompt': prompt,
            'expected_output': {
                'min_energy_sources_found': min_energy_found,
                'max_energy_sources': expected_energy_sources,
                'total_traps': expected_traps,
                'maze_size': (5, 5),
                'required_methods': [
                    '__init__', 'get_valid_moves', 'neural_decision',
                    'dynamic_pathfind', 'execute_step', 'run_simulation',
                ],
                'success_criteria': {
                    'final_energy_positive': True,
                    'found_energy_sources': True,
                    'proper_error_handling': True,
                    'uses_neural_network': True,
                },
                'metadata': {
                    'maze': maze,
                    'start_position': start_pos,
                    'initial_energy': initial_energy,
                    'max_steps': max_steps,
                    'input_weights': input_weights,
                    'output_weights': output_weights,
                },
            },
        }

    # ==================================================================
    #  verify — точка входа
    # ==================================================================

    def verify(
            self, llm_output: str, expected_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            code = self._extract_python_code_safe(llm_output)
            if not code:
                return self._failure_result(
                    "Не найден Python код в ответе",
                    raw_preview=llm_output[:500],
                )

            code = self._sanitize_code_safe(code)
            code = self._remove_main_block(code)

            log.debug(
                "Извлечённый код (первые 300 символов):\n%s", code[:300]
            )

            try:
                compiled = compile(code, '<llm_generated>', 'exec')
            except SyntaxError as e:
                lines = code.split('\n')
                error_context = self._format_error_context(lines, e.lineno)
                return self._failure_result(
                    f"Синтаксическая ошибка в строке {e.lineno}: {e.msg}",
                    error_context=error_context,
                    code_preview=code[:800],
                )

            return self._execute_and_verify(code, compiled, expected_output)

        except Exception as e:
            log.error("Критическая ошибка в verify: %s", e, exc_info=True)
            return self._failure_result(
                f"Критическая ошибка проверки: {e}"
            )

    # ==================================================================
    #  Извлечение кода — БЕЗОПАСНАЯ версия (без _cleanup_llm_response)
    # ==================================================================

    def _extract_python_code_safe(self, llm_output: str) -> Optional[str]:
        """
        Извлекает Python-код из ответа LLM.
        НЕ вызывает _cleanup_llm_response() — та удаляет * и _.
        """
        output = self._remove_think_blocks(llm_output)
        output = self._extract_response_block(output)

        # Стратегия 1: ```python ... ```
        matches = re.findall(
            r'```python\s*\n(.*?)```', output, flags=re.DOTALL
        )
        if matches:
            code = max(matches, key=len).strip()
            if self._looks_like_python_class(code):
                log.debug("Код: markdown_python (%d симв.)", len(code))
                return code

        # Стратегия 2: ```py ... ```
        matches = re.findall(
            r'```py\s*\n(.*?)```', output, flags=re.DOTALL
        )
        if matches:
            code = max(matches, key=len).strip()
            if self._looks_like_python_class(code):
                log.debug("Код: markdown_py")
                return code

        # Стратегия 3: ``` ... ```
        matches = re.findall(
            r'```\s*\n(.*?)```', output, flags=re.DOTALL
        )
        if matches:
            blocks = [
                m.strip() for m in matches
                if self._looks_like_python_class(m)
            ]
            if blocks:
                code = max(blocks, key=len)
                log.debug("Код: markdown_generic")
                return code

        # Стратегия 4: ```<язык> ... ```
        matches = re.findall(
            r'```\w+\s*\n(.*?)```', output, flags=re.DOTALL
        )
        if matches:
            blocks = [
                m.strip() for m in matches
                if self._looks_like_python_class(m)
            ]
            if blocks:
                code = max(blocks, key=len)
                log.debug("Код: markdown_any_lang")
                return code

        # Стратегия 5: Прямой поиск class
        class_match = re.search(
            r'((?:import\s+\w+[^\n]*\n)*'
            r'(?:from\s+\w+[^\n]*\n)*'
            r'\s*class\s+NeuralBot.*)',
            output,
            flags=re.DOTALL,
        )
        if class_match:
            code = class_match.group(1).strip()
            code = self._remove_main_block(code)
            if len(code) > 100:
                log.debug("Код: direct_class_search")
                return code

        log.warning(
            "Код не извлечён. Превью: %s",
            output[:200].replace('\n', '\\n'),
        )
        return None

    def _remove_think_blocks(self, text: str) -> str:
        return re.sub(
            r'<think>.*?</think>', '', text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    def _extract_response_block(self, text: str) -> str:
        match = re.search(
            r'<response>(.*?)</response>', text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        return match.group(1).strip() if match else text

    def _remove_main_block(self, code: str) -> str:
        """Удаляет if __name__ == '__main__': и всё после него."""
        # С комментарием перед if
        pattern = r'\n#[^\n]*\n*if\s+__name__\s*==\s*["\']__main__["\']\s*:'
        match = re.search(pattern, code)
        if match:
            return code[:match.start()].rstrip()

        # Без комментария
        pattern2 = r'\nif\s+__name__\s*==\s*["\']__main__["\']\s*:'
        match2 = re.search(pattern2, code)
        if match2:
            return code[:match2.start()].rstrip()

        return code

    def _looks_like_python_class(self, code: str) -> bool:
        if not code or len(code.strip()) < 50:
            return False
        return 'class ' in code and 'def ' in code

    # ==================================================================
    #  Санитизация
    # ==================================================================

    def _sanitize_code_safe(self, code: str) -> str:
        """
        Замена типографских символов. НЕ удаляет *, _, `, ~.
        """
        replacements = {
            '\u2014': '-', '\u2013': '-', '\u2212': '-',
            '\u2018': "'", '\u2019': "'", '\u201a': "'",
            '\u201c': '"', '\u201d': '"', '\u201e': '"',
            '\u2026': '...', '\u00a0': ' ',
            '\u200b': '', '\u200c': '', '\u200d': '', '\ufeff': '',
            '\u2009': ' ',
        }
        for old, new in replacements.items():
            code = code.replace(old, new)

        lines = code.split('\n')
        return '\n'.join(line.rstrip() for line in lines)

    def _format_error_context(
            self, lines: List[str], error_line: Optional[int]
    ) -> str:
        if not error_line or error_line < 1:
            return ""
        result = []
        start = max(0, error_line - 3)
        end = min(len(lines), error_line + 2)
        for i in range(start, end):
            marker = ">>>" if i == error_line - 1 else "   "
            result.append(f"{marker} {i + 1:3d} | {lines[i]}")
        return '\n'.join(result)

    # ==================================================================
    #  Выполнение и верификация
    # ==================================================================

    def _execute_and_verify(
            self,
            code: str,
            compiled: Any,
            expected_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        score = 0
        max_score = 100
        details: Dict[str, Any] = {}

        # --- Подготовка namespace с КОНТРОЛИРУЕМЫМ __import__ ---
        import builtins as builtins_module

        safe_import = self._make_safe_import()

        builtins_dict = {
            **self.SAFE_BUILTINS,
            '__build_class__': builtins_module.__build_class__,
            '__name__': '__main__',
            '__import__': safe_import,  # ← Контролируемый импорт!
        }

        namespace: Dict[str, Any] = {
            '__builtins__': builtins_dict,
        }

        # Предоставляем часто используемые модули заранее
        # (чтобы import math не требовал вызова __import__)
        import heapq
        import collections
        namespace['math'] = math
        namespace['heapq'] = heapq
        namespace['collections'] = collections

        # typing для аннотаций
        from typing import (
            List as TList, Tuple as TTuple, Dict as TDict,
            Any as TAny, Optional as TOptional,
        )
        namespace['List'] = TList
        namespace['Tuple'] = TTuple
        namespace['Dict'] = TDict
        namespace['Any'] = TAny
        namespace['Optional'] = TOptional

        # --- ЭТАП 1: Выполнение кода ---
        local_scope: Dict[str, Any] = {}
        try:
            exec(compiled, namespace, local_scope)
        except ImportError as e:
            return self._failure_result(
                f"Заблокированный импорт: {e}",
                code_preview=code[:500],
            )
        except Exception as e:
            return self._failure_result(
                f"Ошибка выполнения: {type(e).__name__}: {e}",
                traceback_info=traceback.format_exc(),
                code_preview=code[:500],
            )

        # --- ЭТАП 2: Поиск класса ---
        bot_class = local_scope.get('NeuralBot') or namespace.get('NeuralBot')
        if bot_class is None:
            for name, obj in {**namespace, **local_scope}.items():
                if (
                        isinstance(obj, type)
                        and hasattr(obj, 'run_simulation')
                        and name not in ('type', 'object')
                ):
                    bot_class = obj
                    log.info("Класс '%s' вместо 'NeuralBot'", name)
                    break

        if bot_class is None:
            defined = [
                n for n, o in {**namespace, **local_scope}.items()
                if isinstance(o, type) and not n.startswith('_')
                   and n not in self.SAFE_BUILTINS
            ]
            return self._failure_result(
                "Класс NeuralBot не найден",
                defined_classes=defined,
            )

        details['class_found'] = True
        score += 10

        # --- ЭТАП 3: Проверка методов ---
        required_methods = expected_output.get('required_methods', [
            '__init__', 'get_valid_moves', 'neural_decision',
            'dynamic_pathfind', 'execute_step', 'run_simulation',
        ])

        found_methods = []
        missing_methods = []
        for method in required_methods:
            if hasattr(bot_class, method):
                found_methods.append(method)
            else:
                missing_methods.append(method)

        details['found_methods'] = found_methods
        details['missing_methods'] = missing_methods
        method_score = int(
            15 * len(found_methods) / max(len(required_methods), 1)
        )
        score += method_score

        if 'run_simulation' not in found_methods:
            details['early_stop'] = "Метод run_simulation отсутствует"
            return {
                'is_correct': False, 'score': score,
                'max_score': max_score, 'details': details,
            }

        # --- ЭТАП 4: Создание экземпляра ---
        metadata = expected_output.get('metadata', {})
        if not metadata:
            log.warning("metadata отсутствует, генерируем заново")
            test_data = self.generate()
            metadata = test_data['expected_output']['metadata']

        try:
            bot = bot_class(
                maze=metadata['maze'],
                start_pos=metadata['start_position'],
                initial_energy=metadata['initial_energy'],
                max_steps=metadata['max_steps'],
                input_weights=metadata['input_weights'],
                output_weights=metadata['output_weights'],
            )
            details['instantiation'] = 'success'
            score += 10
        except Exception as e:
            return self._failure_result(
                f"Ошибка создания NeuralBot: {type(e).__name__}: {e}",
                traceback_info=traceback.format_exc(),
            )

        # --- ЭТАП 5: Тестирование отдельных методов ---

        # 5a. get_valid_moves()
        if 'get_valid_moves' in found_methods:
            try:
                valid_moves = bot.get_valid_moves()
                if isinstance(valid_moves, list):
                    details['get_valid_moves'] = (
                        f"OK ({len(valid_moves)} ходов)"
                    )
                    score += 5
                else:
                    details['get_valid_moves'] = (
                        f"Тип {type(valid_moves).__name__} вместо list"
                    )
            except Exception as e:
                details['get_valid_moves'] = f"Ошибка: {e}"

        # 5b. neural_decision()
        if 'neural_decision' in found_methods:
            try:
                decision = bot.neural_decision((4, 4))
                if isinstance(decision, (bool, int)):
                    details['neural_decision'] = f"OK → {decision}"
                    score += 5
                else:
                    details['neural_decision'] = (
                        f"Тип {type(decision).__name__}"
                    )
            except Exception as e:
                details['neural_decision'] = f"Ошибка: {e}"

        # --- ЭТАП 6: Запуск симуляции (с таймаутом) ---
        import signal
        import threading

        sim_result = None
        sim_error = None

        def run_sim():
            nonlocal sim_result, sim_error
            try:
                sim_result = bot.run_simulation()
            except Exception as e:
                sim_error = e

        # Запускаем в отдельном потоке с таймаутом
        thread = threading.Thread(target=run_sim, daemon=True)
        thread.start()
        thread.join(timeout=10.0)  # 10 секунд максимум

        if thread.is_alive():
            details['simulation_error'] = (
                "Таймаут: симуляция не завершилась за 10 секунд "
                "(вероятно, бесконечный цикл)"
            )
        elif sim_error is not None:
            if isinstance(sim_error, RecursionError):
                details['simulation_error'] = "RecursionError"
            else:
                details['simulation_error'] = (
                    f"{type(sim_error).__name__}: {sim_error}"
                )
                log.warning(
                    "Ошибка симуляции: %s", sim_error, exc_info=True
                )
        elif sim_result is not None:
            details['simulation_ran'] = True
            score += 15

            if not isinstance(sim_result, dict):
                details['simulation_type_error'] = (
                    f"Вернул {type(sim_result).__name__} вместо dict"
                )
            else:
                details['simulation_keys'] = list(sim_result.keys())

                # final_energy
                final_energy = self._get_alt(
                    sim_result, 'final_energy',
                    ['energy', 'remaining_energy', 'hp'],
                )
                if final_energy is not None:
                    details['final_energy'] = final_energy
                    if final_energy > 0:
                        details['final_energy_positive'] = True
                        score += 10
                    else:
                        details['final_energy_positive'] = False
                else:
                    details['final_energy_positive'] = 'not_found'

                # energy_sources_found
                energy_found = self._get_alt(
                    sim_result, 'energy_sources_found',
                    ['energy_collected', 'sources_found', 'pickups'],
                )
                min_req = expected_output.get(
                    'min_energy_sources_found', 1
                )
                if energy_found is not None:
                    details['energy_sources_found'] = energy_found
                    if energy_found >= min_req:
                        details['found_sufficient_energy'] = True
                        score += 10
                    else:
                        details['found_sufficient_energy'] = False
                else:
                    details['found_sufficient_energy'] = 'not_found'

                # neural_decisions
                nn_decisions = self._get_alt(
                    sim_result, 'neural_decisions',
                    ['decisions', 'nn_decisions', 'nn_outputs'],
                )
                if (
                        isinstance(nn_decisions, (list, tuple))
                        and len(nn_decisions) > 0
                ):
                    details['uses_neural_network'] = True
                    details['neural_decisions_count'] = len(nn_decisions)
                    score += 5
                else:
                    details['uses_neural_network'] = (
                        'not_found' if nn_decisions is None else 'empty'
                    )

                # errors_handled
                err_handled = self._get_alt(
                    sim_result, 'errors_handled',
                    ['error_count', 'exceptions_caught'],
                )
                if err_handled is not None and err_handled >= 0:
                    details['proper_error_handling'] = True
                    score += 5
                else:
                    details['proper_error_handling'] = 'not_found'

        # --- ЭТАП 7: Анализ кода ---
        code_analysis = self._analyze_code_structure(code)
        details['code_analysis'] = code_analysis

        if code_analysis.get('has_neural_network'):
            score += 5
        if code_analysis.get('has_recursion') or code_analysis.get('has_bfs'):
            score += 5
        if code_analysis.get('has_error_handling'):
            score += 5

        is_correct = score >= 50

        return {
            'is_correct': is_correct,
            'score': score,
            'max_score': max_score,
            'details': details,
        }

    # ==================================================================
    #  Вспомогательные методы
    # ==================================================================

    @staticmethod
    def _get_alt(
            d: Dict[str, Any], primary: str, alternatives: List[str]
    ) -> Any:
        val = d.get(primary)
        if val is not None:
            return val
        for alt in alternatives:
            val = d.get(alt)
            if val is not None:
                return val
        return None

    def _analyze_code_structure(self, code: str) -> Dict[str, bool]:
        analysis = {
            'has_recursion': False,
            'has_bfs': False,
            'has_dynamic_programming': False,
            'has_error_handling': False,
            'has_neural_network': False,
        }
        try:
            code_lower = code.lower()

            lines = code.split('\n')
            current_method = None
            for line in lines:
                stripped = line.strip()
                func_match = re.match(r'def\s+(\w+)', stripped)
                if func_match:
                    current_method = func_match.group(1)
                elif (
                        current_method
                        and f'self.{current_method}(' in stripped
                ):
                    analysis['has_recursion'] = True
                    break

            bfs_kw = [
                'deque', 'queue', 'bfs', 'dfs', 'visited', 'frontier',
            ]
            analysis['has_bfs'] = any(kw in code_lower for kw in bfs_kw)

            dp_kw = ['memo', 'cache', 'dp[', 'dp =', 'lru_cache']
            analysis['has_dynamic_programming'] = any(
                kw in code_lower for kw in dp_kw
            )

            analysis['has_error_handling'] = (
                    'try:' in code and 'except' in code
            )

            nn_kw = [
                'tanh', 'sigmoid', 'hidden', 'w_in', 'w_out',
                'input_weights', 'output_weights',
            ]
            analysis['has_neural_network'] = (
                    sum(1 for kw in nn_kw if kw in code_lower) >= 2
            )
        except Exception:
            pass
        return analysis

    def _failure_result(self, reason: str, **extra) -> Dict[str, Any]:
        details = {'reason': reason, 'success': False}
        details.update(extra)
        return {
            'is_correct': False,
            'score': 0,
            'max_score': 100,
            'details': details,
        }

    def get_test_description(self) -> str:
        return (
            "Комплексный тест Neural Labyrinth: нейросеть для "
            "навигации по лабиринту с pathfinding и управлением энергией."
        )