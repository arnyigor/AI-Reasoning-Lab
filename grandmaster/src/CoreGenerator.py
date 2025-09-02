# CoreGenerator.py
import functools
import random
import time
from typing import List, Optional, Tuple, Any

from clue_types import ClueType, Difficulty
from ortools.sat.python import cp_model
from PuzzleDefinition import PuzzleDefinition


def time_it(func):
    """
    Декоратор, который измеряет время выполнения обернутой функции
    и выводит результат в консоль. Это мощный инструмент для профилирования
    и понимания, какие этапы генерации являются самыми затратными.
    """
    @functools.wraps(func)  # Сохраняет метаданные оригинальной функции (имя, docstring и т.д.)
    def wrapper(*args, **kwargs):
        # args[0] будет 'self', что позволяет нам получить имя класса для информативного лога.
        class_name = args[0].__class__.__name__
        print(f"  - [TIMER] Запуск этапа: '{class_name}.{func.__name__}'...")
        start_time = time.perf_counter()

        # Выполняем саму декорируемую функцию
        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        run_time = end_time - start_time
        print(f"  - [TIMER] Этап '{class_name}.{func.__name__}' завершен за {run_time:.3f} сек.")
        return result
    return wrapper


class CoreGenerator:
    """
    Ядро генератора головоломок. Реализует универсальный трехфазный алгоритм
    v36.0 "Гроссмейстер-Профилировщик", с встроенным замером времени
    ключевых этапов генерации.

    Алгоритм состоит из трех фаз:
    1. Проектирование "Каркаса Интриги": Создание начального, разнообразного
       и неоднозначного набора улик. Сложность ядра адаптируется.
    2. Интеллектуальное Укрепление: Добавление улик до тех пор, пока у
       головоломки не останется ровно одно уникальное решение.
    3. Шлифовка и Аудит: Удаление всех избыточных улик и проверка
       головоломки на "интересность" (глубину логического пути).
    """

    def __init__(self, puzzle_definition: PuzzleDefinition, difficulty: Difficulty = Difficulty.MEDIUM):
        """
        Инициализирует генератор с заданным определением головоломки и уровнем сложности.

        Args:
            puzzle_definition (PuzzleDefinition): Объект, описывающий правила,
                                                  ограничения и форматирование
                                                  конкретного типа головоломки.
            difficulty (Difficulty, optional): Уровень сложности. По умолчанию MEDIUM.
        """
        self.definition = puzzle_definition
        self.difficulty = difficulty

    def generate(self, max_retries: int = 5) -> None:
        """
        Основной метод, запускающий полный цикл генерации головоломки.
        """
        total_start_time = time.perf_counter()  # Замеряем общее время всего процесса
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")

            start_time = time.perf_counter()
            solution = self.definition.generate_solution()
            print(f"  - [TIMER] Генерация эталонного решения: {time.perf_counter() - start_time:.3f} сек.")

            # --- Фаза 1: Проектирование каркаса ---
            print(f"\n[{self.definition.name}]: Фаза 1: Проектирование каркаса интриги...")
            start_time = time.perf_counter()
            core_puzzle, remaining_clues = self.definition.design_core_puzzle(solution)
            print(f"  - [TIMER] Проектирование ядра ('design_core_puzzle'): {time.perf_counter() - start_time:.3f} сек.")

            # <<< КОММЕНТАРИЙ: Блок адаптивной модификации ядра на основе сложности >>>
            # Здесь мы управляем "характером" головоломки на самом раннем этапе.
            num_items = solution.shape[0]
            base_core_size = len(core_puzzle)

            if self.difficulty == Difficulty.CLASSIC:
                classic_types = {ClueType.POSITIONAL, ClueType.DIRECT_LINK, ClueType.RELATIVE_POS}
                core_puzzle = [c for c in core_puzzle if c[0] in classic_types]
                simple_from_reserve = [c for c in remaining_clues if c[0] in classic_types]
                random.shuffle(simple_from_reserve)
                num_to_add = base_core_size - len(core_puzzle)
                if len(simple_from_reserve) >= num_to_add > 0:
                    core_puzzle.extend(simple_from_reserve[:num_to_add])
                print(f"  - [Сложность CLASSIC]: Ядро очищено от сложных улик. Размер ядра: {len(core_puzzle)}.")
            elif self.difficulty == Difficulty.EASY:
                num_to_remove = max(1, base_core_size // 2)
                if num_to_remove > 0 and len(core_puzzle) > num_to_remove:
                    removed = core_puzzle[-num_to_remove:]
                    core_puzzle = core_puzzle[:-num_to_remove]
                    remaining_clues.extend(removed)
                    print(f"  - [Сложность EASY]: Ядро упрощено, {num_to_remove} сложных улик возвращено в резерв.")
            elif self.difficulty == Difficulty.HARD:
                num_to_add = max(1, num_items // 2)
                if len(remaining_clues) >= num_to_add:
                    added = remaining_clues[:num_to_add]
                    core_puzzle.extend(added)
                    remaining_clues = remaining_clues[num_to_add:]
                    print(f"  - [Сложность HARD]: Ядро усилено, добавлено {num_to_add} улик из резерва.")
            elif self.difficulty == Difficulty.EXPERT:
                num_to_add = max(2, num_items)
                if len(remaining_clues) >= num_to_add:
                    added = remaining_clues[:num_to_add]
                    core_puzzle.extend(added)
                    remaining_clues = remaining_clues[num_to_add:]
                    print(f"  - [Сложность EXPERT]: Ядро значительно усилено, добавлено {num_to_add} улик из резерва.")

            # "Санитарная проверка" ядра после модификации.
            start_time = time.perf_counter()
            if self._check_solvability(core_puzzle) == 0:
                print(f"  - [TIMER] Санитарная проверка ядра: {time.perf_counter() - start_time:.3f} сек.")
                print("  - ПРОВАЛ: Модифицированное ядро оказалось противоречивым. Новая попытка...")
                continue
            print(f"  - [TIMER] Санитарная проверка ядра: {time.perf_counter() - start_time:.3f} сек.")

            # --- Фаза 2: Достижение уникальности ---
            print(f"\n[{self.definition.name}]: Фаза 2: Достижение уникальности...")
            unique_puzzle = self._build_walls(core_puzzle, remaining_clues)
            if not unique_puzzle:
                print("  - ПРОВАЛ: Не удалось достичь уникальности. Новая попытка...")
                continue

            # --- Фаза 3: Шлифовка и аудит ---
            print(f"\n[{self.definition.name}]: Фаза 3: Шлифовка и аудит...")
            minimized_puzzle = self._minimize_puzzle(unique_puzzle, self.definition.get_anchors(solution))

            start_time = time.perf_counter()
            final_puzzle, question_data = self.definition.quality_audit_and_select_question(minimized_puzzle, solution)
            print(f"  - [TIMER] Аудит качества и выбор вопроса: {time.perf_counter() - start_time:.3f} сек.")

            if question_data:
                print("  - УСПЕХ: Найдена интересная головоломка!")
                total_run_time = time.perf_counter() - total_start_time
                _, final_branches = self._count_solutions_and_measure_complexity(final_puzzle)
                print("\n" + "=" * 60)
                print("ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА.")
                print(f"Итоговое число подсказок: {len(final_puzzle)}")
                print(f"Финальная сложность (ветвлений): {final_branches}")
                print(f"Общее время генерации: {total_run_time:.3f} сек.")
                print("=" * 60)
                self.definition.print_puzzle(final_puzzle, question_data, solution)
                return
            else:
                print("  - ПРОВАЛ: Головоломка отбракована как 'скучная'. Новая попытка...")

        total_run_time = time.perf_counter() - total_start_time
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА]: Не удалось сгенерировать качественную головоломку за {max_retries} попыток.")
        print(f"Общее время: {total_run_time:.3f} сек.")

    @time_it
    def _build_walls(self, core_puzzle: List, wall_clues: List) -> Optional[List]:
        """
        Итеративно добавляет улики к ядру для достижения уникальности решения.
        Применяет пакетную обработку для высокой производительности.
        """
        global first_stage_name, first_stage_clues
        current_clues = list(core_puzzle)
        simple_walls = [c for c in wall_clues if c[0] in [ClueType.POSITIONAL, ClueType.DIRECT_LINK]]
        complex_walls = [c for c in wall_clues if c[0] not in [ClueType.POSITIONAL, ClueType.DIRECT_LINK]]
        random.shuffle(simple_walls)
        random.shuffle(complex_walls)

        if self.difficulty == Difficulty.CLASSIC:
            classic_types = {
                ClueType.POSITIONAL, ClueType.DIRECT_LINK, ClueType.NEGATIVE_DIRECT_LINK,
                ClueType.RELATIVE_POS, ClueType.ORDERED_CHAIN, ClueType.AT_EDGE, ClueType.IS_EVEN
            }
            first_stage_clues = [c for c in (simple_walls + complex_walls) if c[0] in classic_types]
            second_stage_clues = []
            first_stage_name = "классическими и структурными подсказками"
            second_stage_name = None
        elif self.difficulty == Difficulty.EASY:
            first_stage_clues, second_stage_clues = simple_walls, complex_walls
            first_stage_name = "простыми подсказками"
            second_stage_name = "сложными подсказками"
        elif self.difficulty in [Difficulty.MEDIUM, Difficulty.HARD, Difficulty.EXPERT]:
            first_stage_clues, second_stage_clues = complex_walls, simple_walls
            first_stage_name = "сложными и средними подсказками"
            second_stage_name = "прямыми подсказками"

        batch_size = 20

        print(f"  - [INFO] Этап 1: Укрепление {first_stage_name}...")
        for i in range(0, len(first_stage_clues), batch_size):
            batch = first_stage_clues[i:i + batch_size]
            current_clues.extend(batch)
            solvability = self._check_solvability(current_clues)
            if solvability == 0:
                current_clues = current_clues[:-len(batch)]
                continue
            if solvability == 1:
                print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
                return current_clues
        if self._check_solvability(current_clues) == 1:
            print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
            return current_clues

        if second_stage_name:
            print(f"  - [INFO] Этап 2: Доукрепление {second_stage_name}...")
            for i in range(0, len(second_stage_clues), batch_size):
                batch = second_stage_clues[i:i + batch_size]
                current_clues.extend(batch)
                if self._check_solvability(current_clues) == 1:
                    print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
                    return current_clues
            if self._check_solvability(current_clues) == 1:
                print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
                return current_clues
        return None

    @time_it
    def _minimize_puzzle(self, puzzle: List, anchors: set) -> List:
        """
        Удаляет из готовой головоломки все избыточные улики, делая ее элегантной.
        Это один из самых вычислительно дорогих этапов, так как он проверяет
        каждую улику по отдельности.
        """
        current_puzzle = list(puzzle)
        anchor_tuples = {tuple(a) for a in anchors}
        clues_to_check = [c for c in current_puzzle if tuple(c) not in anchor_tuples]

        if hasattr(self.definition, 'CLUE_STRENGTH'):
            clues_to_check.sort(key=lambda c: self.definition.CLUE_STRENGTH.get(c[0], 0))

        initial_clue_count = len(current_puzzle)
        removed_count = 0
        for clue in clues_to_check:
            if clue not in current_puzzle:
                continue
            temp_puzzle = [c for c in current_puzzle if c != clue]
            if self._check_solvability(temp_puzzle) == 1:
                current_puzzle = temp_puzzle
                removed_count += 1

        if removed_count > 0:
            print(f"  - Удалено {removed_count} избыточных подсказок (с {initial_clue_count - len(anchor_tuples)} до {len(current_puzzle) - len(anchor_tuples)}).")
        print(f"  - Минимизация завершена. Осталось {len(current_puzzle)} подсказок.")
        return current_puzzle

    def _create_or_tools_model(self, clues: List) -> cp_model.CpModel:
        """Вспомогательный метод для создания модели CP-SAT и добавления ограничений."""
        model, variables = self.definition.create_base_model_and_vars()
        for clue in clues:
            self.definition.add_clue_constraint(model, variables, clue)
        return model

    def _count_solutions_and_measure_complexity(self, clues: List) -> Tuple[int, int]:
        """Считает точное количество решений и измеряет сложность поиска (ветвления)."""
        model = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()
        solution_counter = self.SolutionCounter(limit=3)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count, solver.NumBranches()

    def _check_solvability(self, clues: List) -> int:
        """
        Быстро проверяет разрешимость системы: 0, 1 или >1 решений.
        Использует лимит по времени, чтобы избежать зависаний на сложных моделях.
        """
        model = self._create_or_tools_model(clues)
        solution_counter = self.SolutionCounter(limit=2)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0
        status = solver.SearchForAllSolutions(model, solution_counter)
        if status == cp_model.UNKNOWN:  # Если решатель "задумался" и не успел
            return 2  # Считаем, что решений много (неопределенность)
        return solution_counter.solution_count

    class SolutionCounter(cp_model.CpSolverSolutionCallback):
        """Вспомогательный класс для эффективного подсчета решений в CP-SAT."""
        def __init__(self, limit: int):
            super().__init__()
            self._solution_count = 0
            self._limit = limit

        def on_solution_callback(self) -> None:
            self._solution_count += 1
            if self._solution_count >= self._limit:
                self.StopSearch()  # Прекращаем поиск, как только достигли лимита

        @property
        def solution_count(self) -> int:
            return self._solution_count