# CoreGenerator.py (Исправленная версия)

import random
from typing import List, Tuple, Any, Optional, Dict

import pandas as pd

from PuzzleDefinition import PuzzleDefinition
from clue_types import CLUE_STRENGTH
from ortools.sat.python import cp_model

class CorePuzzleGenerator:
    """
    Ядро генератора головоломок. Реализует гибридную архитектуру "Виртуоз-Архитектор".
    """
    def __init__(self, puzzle_definition: PuzzleDefinition):
        self.definition = puzzle_definition

    def generate(self, max_retries: int = 5):
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")

            solution = self.definition.generate_solution()
            core_puzzle, remaining_clues = self.definition.design_core_puzzle(solution)

            print(f"\n[{self.definition.name}]: Фаза 2а: Стандартное укрепление...")
            unique_puzzle = self._build_walls(core_puzzle, remaining_clues)

            if not unique_puzzle:
                print(f"\n[{self.definition.name}]: Фаза 2б: Динамическое укрепление...")
                # Собираем все улики вместе для динамического укрепления
                all_available_clues = core_puzzle + remaining_clues
                unique_puzzle = self._dynamic_reinforcement(all_available_clues, solution)

            if not unique_puzzle:
                print("  - ПРОВАЛ: Не удалось достичь уникальности даже с динамическим укреплением. Новая попытка...")
                continue

            print(f"\n[{self.definition.name}]: Фаза 3: Шлифовка и аудит...")
            minimized_puzzle = self._minimize_puzzle(unique_puzzle, self.definition.get_anchors(solution))
            final_puzzle, question_data = self.definition.quality_audit_and_select_question(minimized_puzzle, solution)

            if question_data:
                print("  - УСПЕХ: Найдена интересная головоломка!")
                _, final_branches = self._count_solutions_and_measure_complexity(final_puzzle)

                print("\n" + "="*60)
                print("ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА.")
                print(f"Итоговое число подсказок: {len(final_puzzle)}")
                print(f"Финальная сложность (ветвлений): {final_branches}")
                print("="*60)
                self.definition.print_puzzle(final_puzzle, question_data, solution)
                return
            else:
                print("  - ПРОВАЛ: Головоломка отбракована как 'скучная'. Новая попытка...")

        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА]: Не удалось сгенерировать качественную головоломку за {max_retries} попыток.")

    def _build_walls(self, core_puzzle: List, wall_clues: List) -> Optional[List]:
        current_clues = list(core_puzzle)
        random.shuffle(wall_clues)
        sorted_walls = sorted(wall_clues, key=lambda clue: CLUE_STRENGTH.get(clue[0], 0), reverse=True)
        high_strength_walls = [c for c in sorted_walls if CLUE_STRENGTH.get(c[0], 0) == 3]
        medium_strength_walls = [c for c in sorted_walls if CLUE_STRENGTH.get(c[0], 0) == 2]
        low_strength_walls = [c for c in sorted_walls if CLUE_STRENGTH.get(c[0], 0) <= 1]
        for wall_tier, tier_name, batch_size in [(high_strength_walls, "сильными", 2), (medium_strength_walls, "средними", 3), (low_strength_walls, "слабыми", 5)]:
            print(f"  - [INFO] Этап: Укрепление {tier_name} подсказками...")
            clue_batch = []
            for clue in wall_tier:
                clue_batch.append(clue)
                if len(clue_batch) >= batch_size:
                    current_clues.extend(clue_batch)
                    clue_batch = []
                    if self._check_solvability(current_clues) == 1:
                        print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
                        return current_clues
            if clue_batch:
                current_clues.extend(clue_batch)
                if self._check_solvability(current_clues) == 1:
                    print(f"  - Уникальность достигнута! Подсказок: {len(current_clues)}")
                    return current_clues
        if self._check_solvability(current_clues) == 1:
            print(f"  - Уникальность достигнута на последнем этапе! Подсказок: {len(current_clues)}")
            return current_clues
        return None

    def _dynamic_reinforcement(self, clues: List[Tuple[Any, Any]], solution: pd.DataFrame) -> Optional[List[Tuple[Any, Any]]]:
        print("  - [INFO] Запуск Динамического Укрепления...")
        current_clues = list(clues)
        for i in range(self.definition.num_items * 2):
            # ИСПРАВЛЕНИЕ: Распаковываем кортеж
            model, variables = self._create_or_tools_model(current_clues)
            solver = cp_model.CpSolver()

            SolutionCollectorClass = self.definition.SolutionCollector
            solution_collector = SolutionCollectorClass(limit=2)
            solution_collector.set_variables(variables)
            solver.SearchForAllSolutions(model, solution_collector)

            if solution_collector.solution_count <= 1:
                print(f"  - Успех! Уникальность достигнута после {i+1} циклов укрепления.")
                return current_clues
            print(f"  - Найдено {solution_collector.solution_count} решений. Создание контр-улики...")
            try:
                solution1, solution2 = solution_collector.solutions
                counter_clue = self.definition.find_difference_and_create_clue(solution1, solution2, solution)
                if counter_clue:
                    print(f"    - Добавлена контр-улика: {self.definition.format_clue(counter_clue)}")
                    current_clues.append(counter_clue)
                else:
                    print("    - Не удалось создать контр-улику. Прерывание.")
                    return None
            except (IndexError, ValueError):
                return None
        return None

    def _minimize_puzzle(self, puzzle: List[Tuple[Any, Any]], anchors: set) -> List[Tuple[Any, Any]]:
        current_puzzle = list(puzzle)
        anchor_tuples = {tuple(a) for a in anchors}
        clues_to_check = [c for c in current_puzzle if tuple(c) not in anchor_tuples]
        random.shuffle(clues_to_check)
        for clue in clues_to_check:
            temp_puzzle = [c for c in current_puzzle if c != clue]
            if self._check_solvability(temp_puzzle) == 1:
                current_puzzle = temp_puzzle
                print(f"  - Удалена избыточная подсказка. Осталось: {len(current_puzzle)}")
        print(f"  - Минимизация завершена. Осталось {len(current_puzzle)} подсказок.")
        return current_puzzle

    def _create_or_tools_model(self, clues: List[Tuple[Any, Any]]) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        model, variables = self.definition.create_base_model_and_vars()
        for clue in clues:
            self.definition.add_clue_constraint(model, variables, clue)
        return model, variables

    def _count_solutions_and_measure_complexity(self, clues: List[Tuple[Any, Any]]) -> Tuple[int, int]:
        # ИСПРАВЛЕНИЕ: Распаковываем кортеж
        model, _ = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()

        SolutionCounterClass = self.SolutionCounter
        solution_counter = SolutionCounterClass(limit=3)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count, solver.NumBranches()

    def _check_solvability(self, clues: List[Tuple[Any, Any]]) -> int:
        # ИСПРАВЛЕНИЕ: Распаковываем кортеж
        model, _ = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0

        SolutionCounterClass = self.SolutionCounter
        solution_counter = SolutionCounterClass(limit=2)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count

    class SolutionCounter(cp_model.CpSolverSolutionCallback):
        def __init__(self, limit):
            super().__init__()
            self._solution_count = 0
            self._limit = limit
        def on_solution_callback(self):
            self._solution_count += 1
            if self._solution_count >= self._limit:
                self.StopSearch()
        @property
        def solution_count(self):
            return self._solution_count

