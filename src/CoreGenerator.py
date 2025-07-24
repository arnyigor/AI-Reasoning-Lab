# CoreGenerator.py
import random
from typing import List, Tuple, Any, Optional
from PuzzleDefinition import PuzzleDefinition
from ortools.sat.python import cp_model
from clue_types import ClueType # <<< ИМПОРТ

class CorePuzzleGenerator:
    """
    Ядро генератора головоломок. Реализует универсальный алгоритм
    v31.0 "Гроссмейстер-Виртуоз", работающий с любым PuzzleDefinition.
    """
    def __init__(self, puzzle_definition: PuzzleDefinition):
        self.definition = puzzle_definition

    def generate(self, max_retries: int = 5):
        # ... (весь метод generate без изменений)
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")
            solution = self.definition.generate_solution()
            print(f"\n[{self.definition.name}]: Фаза 1: Проектирование каркаса интриги...")
            core_puzzle, remaining_clues = self.definition.design_core_puzzle(solution)
            print(f"\n[{self.definition.name}]: Фаза 2: Достижение уникальности...")
            unique_puzzle = self._build_walls(core_puzzle, remaining_clues)
            if not unique_puzzle:
                print("  - ПРОВАЛ: Не удалось достичь уникальности. Новая попытка...")
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
        # --- РЕФАКТОРИНГ: Используем Enum ---
        simple_walls = [c for c in wall_clues if c[0] in [ClueType.POSITIONAL, ClueType.DIRECT_LINK]]
        complex_walls = [c for c in wall_clues if c[0] not in [ClueType.POSITIONAL, ClueType.DIRECT_LINK]]
        random.shuffle(simple_walls)
        random.shuffle(complex_walls)

        print("  - [INFO] Этап 1/2: Укрепление сложными и средними подсказками...")
        for clue in complex_walls:
            current_clues.append(clue)
            if self._check_solvability(current_clues) == 0:
                current_clues.pop() # Откатываем противоречивую улику
                continue
            if len(current_clues) % 10 == 0:
                if self._check_solvability(current_clues) == 1:
                    print(f"  - Уникальность достигнута на сложных уликах! Подсказок: {len(current_clues)}")
                    return current_clues
        if self._check_solvability(current_clues) == 1:
            print(f"  - Уникальность достигнута на сложных уликах! Подсказок: {len(current_clues)}")
            return current_clues

        print("  - [INFO] Этап 2/2: Доукрепление прямыми подсказками...")
        for clue in simple_walls:
            current_clues.append(clue)
            if self._check_solvability(current_clues) == 1:
                print(f"  - Уникальность достигнута с добавлением простых улик. Подсказок: {len(current_clues)}")
                return current_clues
        return None

    def _minimize_puzzle(self, puzzle: List, anchors: set) -> List:
        current_puzzle = list(puzzle)
        anchor_tuples = {tuple(a) for a in anchors}
        clues_to_check = [c for c in current_puzzle if tuple(c) not in anchor_tuples]

        # Оптимизация: Сначала пытаемся удалить самые СЛАБЫЕ улики
        clues_to_check.sort(key=lambda c: self.definition.CLUE_STRENGTH.get(c[0], 0))

        for clue in clues_to_check:
            temp_puzzle = [c for c in current_puzzle if c != clue]
            if self._check_solvability(temp_puzzle) == 1:
                current_puzzle = temp_puzzle
                print(f"  - Удалена избыточная подсказка. Осталось: {len(current_puzzle)}")
        print(f"  - Минимизация завершена. Осталось {len(current_puzzle)} подсказок.")
        return current_puzzle

    def _create_or_tools_model(self, clues: List) -> cp_model.CpModel:
        model, variables = self.definition.create_base_model_and_vars()
        for clue in clues:
            self.definition.add_clue_constraint(model, variables, clue)
        return model

    def _count_solutions_and_measure_complexity(self, clues: List) -> Tuple[int, int]:
        model = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()
        solution_counter = self.SolutionCounter(limit=3)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count, solver.NumBranches()

    def _check_solvability(self, clues: List) -> int:
        model = self._create_or_tools_model(clues)
        solution_counter = self.SolutionCounter(limit=2)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.SearchForAllSolutions(model, solution_counter)
        if status == cp_model.UNKNOWN: return 2
        return solution_counter.solution_count

    class SolutionCounter(cp_model.CpSolverSolutionCallback):
        def __init__(self, limit):
            super().__init__(); self._solution_count = 0; self._limit = limit
        def on_solution_callback(self):
            self._solution_count += 1
            if self._solution_count >= self._limit: self.StopSearch()
        @property
        def solution_count(self): return self._solution_count