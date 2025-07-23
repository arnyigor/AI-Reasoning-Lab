# CoreGenerator.py
import random
from typing import List, Tuple, Any
from PuzzleDefinition import PuzzleDefinition
from ortools.sat.python import cp_model

class CorePuzzleGenerator:
    """
    Ядро генератора головоломок. Реализует универсальный алгоритм
    "Бульдозер-Профи", работающий с любым PuzzleDefinition.
    """
    def __init__(self, puzzle_definition: PuzzleDefinition):
        self.definition = puzzle_definition

    def generate(self, max_retries: int = 5):
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")

            solution = self.definition.generate_solution()

            # --- Фаза 1: Проектирование Каркаса ---
            print(f"\n[{self.definition.name}]: Фаза 1: Проектирование каркаса сложности...")
            core_puzzle, remaining_clues = self.definition.design_core_puzzle(solution)

            # --- Фаза 2: Построение ---
            print(f"\n[{self.definition.name}]: Фаза 2: Достижение уникальности...")
            unique_puzzle = self._build_walls(core_puzzle, remaining_clues)
            if not unique_puzzle:
                print("  - ПРОВАЛ: Не удалось достичь уникальности. Новая попытка...")
                continue

            # --- Фаза 3: Шлифовка и Аудит ---
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
                print("  - ПРОВАЛ: Головоломка отбракована. Новая попытка...")

        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА]: Не удалось сгенерировать головоломку за {max_retries} попыток.")

    def _build_walls(self, core_puzzle, wall_clues):
        current_clues = list(core_puzzle)
        random.shuffle(wall_clues)
        for clue in wall_clues:
            current_clues.append(clue)
            if self._check_solvability(current_clues) == 1:
                print(f"  - Уникальность достигнута с {len(current_clues)} подсказками.")
                return current_clues
        return None

    def _build_initial_puzzle(self, max_steps=300):
        solution = self.definition.generate_solution()
        clue_pool = [clue for clues in self.definition.generate_clue_pool(solution).values() for clue in clues]
        random.shuffle(clue_pool)
        anchors = self.definition.get_anchors(solution)
        current_clues = list(anchors)

        for _ in range(max_steps):
            if not clue_pool: return None
            current_clues.append(clue_pool.pop(0))
            if self._check_solvability(current_clues) == 1:
                print(f"  - Заготовка найдена с {len(current_clues)} подсказками.")
                return current_clues, solution, anchors
        return None

    def _minimize_puzzle(self, puzzle: List[Tuple[str, Any]], anchors: set) -> List[Tuple[str, Any]]:
        current_puzzle = list(puzzle)
        while True:
            removable_clues = []
            clues_to_check = [c for c in current_puzzle if c not in anchors]
            if not clues_to_check: break

            for clue in clues_to_check:
                temp_puzzle = [c for c in current_puzzle if c != clue]
                if self._check_solvability(temp_puzzle) == 1:
                    removable_clues.append(clue)

            if not removable_clues:
                print(f"  - Минимизация завершена. Осталось {len(current_puzzle)} подсказок.")
                break

            clue_to_remove = random.choice(removable_clues)
            current_puzzle.remove(clue_to_remove)
            print(f"  - Удалена избыточная подсказка. Осталось: {len(current_puzzle)}")

        return current_puzzle

    def _create_or_tools_model(self, clues: List[Tuple[str, Any]]):
        model, variables = self.definition.create_base_model_and_vars()
        for clue_type, params in clues:
            self.definition.add_clue_constraint(model, variables, (clue_type, params))
        return model

    def _count_solutions_and_measure_complexity(self, clues: List[Tuple[str, Any]]) -> Tuple[int, int]:
        model = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()
        solution_counter = self.SolutionCounter(limit=3)
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count, solver.NumBranches()

    def _check_solvability(self, clues: List[Tuple[str, Any]]) -> int:
        model = self._create_or_tools_model(clues)
        solution_counter = self.SolutionCounter(limit=2)
        solver = cp_model.CpSolver()
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