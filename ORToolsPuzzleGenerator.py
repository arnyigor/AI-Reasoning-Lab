# -*- coding: utf-8 -*-
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Set
from ortools.sat.python import cp_model
import math
import collections

class ORToolsPuzzleGenerator:
    """
    Генератор логических головоломок.
    Архитектура v22.0 "Драматург".

    Эта архитектура ставит во главу угла "интересность" головоломки.
    Она строит ядро исключительно на косвенных, сложных подсказках,
    и лишь в самом конце добавляет прямые связи для достижения уникальности.
    """
    def __init__(self, themes: Dict[str, Dict[str, List[str]]], story_elements: Dict[str, str]):
        self.themes = themes
        self.story_elements = story_elements
        self.difficulty: int = 0
        self.num_items: int = 0
        self.is_circular: bool = False
        self.categories: Dict[str, List[str]] = {}
        self.solution: Optional[pd.DataFrame] = None
        self.cat_keys: List[str] = []

    def generate_dramaturg(self, difficulty: int, max_retries: int = 5):
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")

            self._select_data_for_difficulty(difficulty)
            self._generate_solution()
            assert self.solution is not None

            # --- Фаза 1: Завязка (Построение на косвенных уликах) ---
            print("\n[Драматург]: Фаза 1: Завязка (построение на косвенных уликах)...")
            puzzle_core, remaining_direct_clues = self._build_indirect_core()
            if not puzzle_core:
                print("  - ПРОВАЛ: Не удалось построить ядро. Новая попытка...")
                continue

            # --- Фаза 2: Развязка (Добивание прямыми уликами) ---
            print("\n[Драматург]: Фаза 2: Развязка (достижение уникальности)...")
            unique_puzzle = self._finalize_with_direct_clues(puzzle_core, remaining_direct_clues)
            if not unique_puzzle:
                print("  - ПРОВАЛ: Не удалось достичь уникальности. Новая попытка...")
                continue

            # --- Фаза 3: Катарсис (Минимизация и Аудит) ---
            print("\n[Драматург]: Фаза 3: Катарсис (минимизация и аудит)...")
            minimized_puzzle = self._minimize_final_puzzle(unique_puzzle, self.anchors)

            final_puzzle, question_data = self._quality_audit_and_select_question(minimized_puzzle)

            if question_data:
                print("  - УСПЕХ: Найдена интересная головоломка!")
                _, final_branches = self._count_solutions_and_measure_complexity(final_puzzle)

                print("\n" + "="*60)
                print("ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА.")
                print(f"Итоговое число подсказок: {len(final_puzzle)}")
                print(f"Финальная сложность (ветвлений): {final_branches}")
                print("="*60)
                self._print_puzzle(final_puzzle, question_data)
                return
            else:
                print("  - ПРОВАЛ: Головоломка отбракована как 'скучная'. Новая попытка...")

        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА]: Не удалось сгенерировать качественную головоломку за {max_retries} попыток.")

    def _build_indirect_core(self):
        clue_pool_by_type = self._generate_clue_pool()
        direct_clues = clue_pool_by_type['positional'] + clue_pool_by_type['direct_link']
        indirect_clues = [c for k, v in clue_pool_by_type.items() if k not in ['positional', 'direct_link'] for c in v]
        random.shuffle(direct_clues)
        random.shuffle(indirect_clues)

        self.anchors = {('positional', (1, self.cat_keys[0], self.solution.loc[1, self.cat_keys[0]]))}
        if self.is_circular:
            self.anchors.add(('relative_pos', (self.cat_keys[0], self.solution.loc[1, self.cat_keys[0]], self.cat_keys[1], self.solution.loc[2, self.cat_keys[1]])))

        current_clues = list(self.anchors)

        # Добавляем косвенные подсказки, пока они есть
        while indirect_clues:
            current_clues.append(indirect_clues.pop(0))
            num_sols, _ = self._count_solutions_and_measure_complexity(current_clues)
            if num_sols == 1:
                return current_clues, direct_clues # Ранний выход, если уже уникально
            if num_sols == 0: # Противоречие
                current_clues.pop() # Откат

        return current_clues, direct_clues

    def _finalize_with_direct_clues(self, core_puzzle, direct_clues):
        current_clues = list(core_puzzle)
        while direct_clues:
            current_clues.append(direct_clues.pop(0))
            if self._check_solvability(current_clues) == 1:
                return current_clues
        return None # Не удалось достичь уникальности

    def _quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], min_path_len: int = 2):
        # ... (Этот метод теперь становится критически важным) ...
        graph = collections.defaultdict(list)
        all_items = {item for cat_items in self.categories.values() for item in cat_items}

        for clue_type, params in puzzle:
            clue_items = set()
            # Упрощенное извлечение всех сущностей из подсказки
            def extract_items(p):
                if isinstance(p, (list, tuple)):
                    for item in p:
                        extract_items(item)
                elif isinstance(p, str) and p in all_items:
                    clue_items.add(p)
            extract_items(params)

            # Связываем все сущности в подсказке друг с другом
            clue_items_list = list(clue_items)
            for i in range(len(clue_items_list)):
                for j in range(i + 1, len(clue_items_list)):
                    graph[clue_items_list[i]].append(clue_items_list[j])
                    graph[clue_items_list[j]].append(clue_items_list[i])

        best_question = None
        max_path_len = -1

        possible_questions = []
        for subject_cat in self.cat_keys:
            for attribute_cat in self.cat_keys:
                if subject_cat == attribute_cat: continue
                for subject_item in self.categories[subject_cat]:
                    answer_item = self.solution.loc[self.solution[subject_cat] == subject_item, attribute_cat].iloc[0]
                    possible_questions.append((subject_cat, subject_item, attribute_cat, answer_item))

        random.shuffle(possible_questions)

        for subject_cat, subject_item, attribute_cat, answer_item in possible_questions:
            # BFS для поиска кратчайшего пути
            q = collections.deque([(subject_item, [subject_item])])
            visited = {subject_item}

            path_found = False
            while q:
                curr_node, path = q.popleft()
                if curr_node == answer_item:
                    path_len = len(path) - 1
                    if path_len > max_path_len:
                        max_path_len = path_len
                        best_question = {
                            "question": f"Какой {self.story_elements.get(attribute_cat, attribute_cat)} у {self.story_elements.get(subject_cat, subject_cat)} по имени {subject_item}?",
                            "answer": f"Ответ для проверки: {answer_item}"
                        }
                    path_found = True
                    break

                for neighbor in graph.get(curr_node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append((neighbor, path + [neighbor]))

        if max_path_len >= min_path_len:
            print(f"  - Аудит пройден. Найден вопрос с длиной пути: {max_path_len}")
            return list(set(puzzle)), best_question
        else:
            return puzzle, None

    # --- Остальные методы (минимизация, хелперы) ---
    def _minimize_final_puzzle(self, puzzle: List[Tuple[str, Any]], anchors: set) -> List[Tuple[str, Any]]:
        minimized_puzzle = list(puzzle)
        clues_to_try_removing = [c for c in minimized_puzzle if c not in anchors]
        random.shuffle(clues_to_try_removing)

        for clue in clues_to_try_removing:
            temp_puzzle = [c for c in minimized_puzzle if c != clue]
            if self._check_solvability(temp_puzzle) == 1:
                minimized_puzzle = temp_puzzle
        return minimized_puzzle

    def _select_data_for_difficulty(self, difficulty: int):
        self.difficulty = difficulty
        if 1 <= difficulty <= 3: self.num_items = 4; self.is_circular = False
        elif 4 <= difficulty <= 6: self.num_items = 5; self.is_circular = False
        elif 7 <= difficulty <= 8: self.num_items = 6; self.is_circular = True
        else: self.num_items = 7; self.is_circular = True

        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"

        self.cat_keys = list(base_categories.keys())
        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories.items()}
        print(f"\n[Генератор]: Тема: '{selected_theme_name}', Сложность: {difficulty}/10, Размер: {self.num_items}x{len(self.cat_keys)}, Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

    def _generate_solution(self):
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        self.solution = pd.DataFrame(solution_data, index=range(1, self.num_items + 1))

    def _count_solutions_and_measure_complexity(self, clues: List[Tuple[str, Any]]) -> Tuple[int, int]:
        model = self._create_or_tools_model(clues)
        solver = cp_model.CpSolver()
        solution_counter = self.SolutionCounter(limit=3)
        status = solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count, solver.NumBranches()

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

    def _check_solvability(self, clues: List[Tuple[str, Any]]) -> int:
        model = self._create_or_tools_model(clues)
        solution_counter = self.SolutionCounter(limit=2)
        solver = cp_model.CpSolver()
        solver.SearchForAllSolutions(model, solution_counter)
        return solution_counter.solution_count

    def _generate_clue_pool(self) -> Dict[str, List[Tuple[str, Any]]]:
        pool: Dict[str, List[Any]] = {
            'positional': [], 'direct_link': [], 'negative_direct_link': [], 'conditional_link': [],
            'relative_pos': [], 'opposite_link': [], 'transitive_spatial_link': [], 'arithmetic_link': [],
            'distance_greater_than': [], 'not_opposite': [], 'sum_equals': [], 'ordered_chain': []
        }
        unique_clues = {key: set() for key in pool}
        cat_keys = list(self.categories.keys())
        assert self.solution is not None

        for i_pos in range(1, self.num_items + 1):
            row = self.solution.loc[i_pos]
            cat1, cat2, cat3 = random.sample(cat_keys, 3)
            unique_clues['positional'].add(('positional', (i_pos, cat1, row[cat1])))
            if self.is_circular or i_pos < self.num_items:
                next_row = self.solution.loc[(i_pos % self.num_items) + 1]
                unique_clues['relative_pos'].add(('relative_pos', (cat1, row[cat1], cat2, next_row[cat2])))
            if self.is_circular and self.num_items % 2 == 0 and self.num_items > 2:
                opposite_pos = (i_pos - 1 + self.num_items // 2) % self.num_items + 1
                opposite_row = self.solution.loc[opposite_pos]
                unique_clues['opposite_link'].add(('opposite_link', (cat1, row[cat1], cat2, opposite_row[cat2])))

        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]
        for i in range(len(all_items_flat)):
            for j in range(i + 1, len(all_items_flat)):
                (cat1, item1), (cat2, item2) = all_items_flat[i], all_items_flat[j]
                if cat1 == cat2: continue

                pos1 = self.solution[self.solution[cat1] == item1].index[0]
                pos2 = self.solution[self.solution[cat2] == item2].index[0]

                if pos1 == pos2: unique_clues['direct_link'].add(('direct_link', (cat1, item1, cat2, item2)))
                else: unique_clues['negative_direct_link'].add(('negative_direct_link', (cat1, item1, cat2, item2)))
                unique_clues['conditional_link'].add(('conditional_link', (cat1, item1, cat2, self.solution.loc[pos1, cat2])))
                if pos1 == pos2 * 2: unique_clues['arithmetic_link'].add(('arithmetic_link', (cat1, item1, cat2, item2, 'twice')))
                if abs(pos1 - pos2) == 2: unique_clues['arithmetic_link'].add(('arithmetic_link', (cat1, item1, cat2, item2, 'diff_2')))
                if abs(pos1 - pos2) > 1: unique_clues['distance_greater_than'].add(('distance_greater_than', (cat1, item1, cat2, item2, 1)))
                if pos1 + pos2 == self.num_items: unique_clues['sum_equals'].add(('sum_equals', (cat1, item1, cat2, item2, self.num_items)))
                if self.is_circular and self.num_items % 2 == 0 and abs(pos1 - pos2) != self.num_items // 2:
                    unique_clues['not_opposite'].add(('not_opposite', (cat1, item1, cat2, item2)))

        if len(cat_keys) >= 3:
            for _ in range(self.num_items * 5):
                p_indices = sorted(random.sample(range(1, self.num_items + 1), 3))
                cats = random.sample(cat_keys, 3)
                p1 = (cats[0], self.solution.loc[p_indices[0], cats[0]])
                p2 = (cats[1], self.solution.loc[p_indices[1], cats[1]])
                p3 = (cats[2], self.solution.loc[p_indices[2], cats[2]])
                if p_indices[0] + 1 == p_indices[1] and p_indices[1] + 1 == p_indices[2]:
                    unique_clues['transitive_spatial_link'].add(('transitive_spatial_link', (p1, p2, p3)))
                unique_clues['ordered_chain'].add(('ordered_chain', (p1, p2, p3)))

        for key in pool:
            pool[key] = list(unique_clues[key])
            random.shuffle(pool[key])
        return pool

    def _create_or_tools_model(self, clues: List[Tuple[str, Any]]) -> cp_model.CpModel:
        model = cp_model.CpModel()
        positions_domain = (1, self.num_items)
        variables = {
            item: model.NewIntVar(positions_domain[0], positions_domain[1], f"{cat}_{item}")
            for cat, items in self.categories.items() for item in items
        }
        for items in self.categories.values():
            model.AddAllDifferent([variables[item] for item in items])
        for clue_type, params in clues:
            self._add_clue_as_or_tools_constraint(model, variables, clue_type, params)
        return model

    def _add_clue_as_or_tools_constraint(self, model, variables, clue_type, params):
        get_var = lambda val: variables.get(val)

        if clue_type == 'positional':
            pos_idx, _, val = params
            if get_var(val) is not None: model.Add(get_var(val) == pos_idx)
        elif clue_type in ['direct_link', 'conditional_link']:
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) == get_var(val2))
        elif clue_type == 'negative_direct_link':
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) != get_var(val2))
        elif clue_type == 'relative_pos':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is None or p2 is None: return
            if self.is_circular:
                allowed_pairs = [(i, (i % self.num_items) + 1) for i in range(1, self.num_items + 1)]
                model.AddAllowedAssignments([p1, p2], allowed_pairs)
            else:
                model.Add(p1 + 1 == p2)
        elif clue_type == 'opposite_link':
            if self.is_circular:
                _, val1, _, val2 = params
                p1, p2 = get_var(val1), get_var(val2)
                if p1 is None or p2 is None: return
                offset = self.num_items // 2
                model.AddAbsEquality(offset, p1 - p2)
        elif clue_type == 'transitive_spatial_link':
            (c1, v1), (c2, v2), (c3, v3) = params
            p1, p2, p3 = get_var(v1), get_var(v2), get_var(v3)
            if p1 is None or p2 is None or p3 is None: return
            b1 = model.NewBoolVar(''); model.Add(p1 < p2).OnlyEnforceIf(b1); model.Add(p2 < p3).OnlyEnforceIf(b1)
            b2 = model.NewBoolVar(''); model.Add(p3 < p2).OnlyEnforceIf(b2); model.Add(p2 < p1).OnlyEnforceIf(b2)
            model.AddBoolOr([b1, b2])
        elif clue_type == 'arithmetic_link':
            cat1, item1, cat2, item2, op = params
            p1, p2 = get_var(item1), get_var(item2)
            if p1 is None or p2 is None: return
            if op == 'twice': model.Add(p1 == 2 * p2)
            elif op == 'diff_2': model.AddAbsEquality(2, p1 - p2)
        elif clue_type == 'distance_greater_than':
            cat1, item1, cat2, item2, dist = params
            p1, p2 = get_var(item1), get_var(item2)
            if p1 is None or p2 is None: return
            abs_diff = model.NewIntVar(0, self.num_items, '')
            model.AddAbsEquality(abs_diff, p1 - p2)
            model.Add(abs_diff > dist)
        elif clue_type == 'not_opposite':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is None or p2 is None: return
            if self.is_circular and self.num_items % 2 == 0:
                offset = self.num_items // 2
                abs_diff = model.NewIntVar(0, self.num_items, '')
                model.AddAbsEquality(abs_diff, p1 - p2)
                model.Add(abs_diff != offset)
        elif clue_type == 'sum_equals':
            cat1, item1, cat2, item2, total = params
            p1, p2 = get_var(item1), get_var(item2)
            if p1 is None or p2 is None: return
            model.Add(p1 + p2 == total)
        elif clue_type == 'ordered_chain':
            (c1, v1), (c2, v2), (c3, v3) = params
            p1, p2, p3 = get_var(v1), get_var(v2), get_var(v3)
            if p1 is None or p2 is None or p3 is None: return
            model.Add(p1 < p2)
            model.Add(p2 < p3)

    def _print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str]):
        assert self.solution is not None
        question = question_data['question']
        answer_for_check = question_data['answer']
        print(f"\n**Сценарий: {self.story_elements['scenario']} (Сложность: {self.difficulty}/10)**\n")
        print(f"Условия ({len(final_clues)} подсказок):\n")
        final_clues_text = sorted([self._format_clue(c) for c in final_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "="*40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "="*40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", self.solution)

    def _format_clue(self, clue: Tuple[str, Any]) -> str:
        clue_type, params = clue
        s = self.story_elements
        g = lambda c, v: f"{s.get(c,c)} '{v}'"
        try:
            if clue_type == 'direct_link': return f"Характеристикой {g(params[0], params[1])} является {g(params[2], params[3])}."
            if clue_type == 'negative_direct_link': return f"{g(params[0], params[1]).capitalize()} НЕ находится в одной локации с {g(params[2], params[3])}."
            if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {g(params[1], params[2])}."
            if clue_type == 'relative_pos': return f"{g(params[0], params[1]).capitalize()} находится в локации непосредственно слева от локации, где {g(params[2], params[3])}."
            if clue_type == 'opposite_link': return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} находятся в локациях друг напротив друга."
            if clue_type == 'conditional_link': return f"**Если** в локации находится {g(params[0], params[1])}, **то** там же находится и {g(params[2], params[3])}."
            if clue_type == 'transitive_spatial_link': return f"{g(params[1][0], params[1][1]).capitalize()} находится в локации между той, где {g(params[0][0], params[0][1])}, и той, где {g(params[2][0], params[2][1])}."
            if clue_type == 'arithmetic_link':
                op = params[4]
                if op == 'twice': return f"Номер локации, где {g(params[0], params[1])}, в два раза больше номера локации, где {g(params[2], params[3])}."
                if op == 'diff_2': return f"Между локациями, где {g(params[0], params[1])}, и где {g(params[2], params[3])}, находится ровно одна другая локация."
            if clue_type == 'distance_greater_than':
                return f"Между локациями, где {g(params[0], params[1])}, и где {g(params[2], params[3])}, находится более чем {params[4]} локация(й)."
            if clue_type == 'not_opposite':
                return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} НЕ находятся в локациях друг напротив друга."
            if clue_type == 'sum_equals':
                return f"Сумма номеров локаций, где {g(params[0], params[1])} и где {g(params[2], params[3])}, равна {params[4]}."
            if clue_type == 'ordered_chain':
                return f"Локация, где {g(params[0][0], params[0][1])}, находится где-то левее локации, где {g(params[1][0], params[1][1])}, которая в свою очередь левее локации, где {g(params[2][0], params[2][1])}."
        except (KeyError, IndexError) as e:
            return f"[Ошибка форматирования: {e}]"
        return f"[Неизвестный тип подсказки: {clue_type}]"


if __name__ == '__main__':
    THEMES = {
        "Офисная Тайна": {
            "Сотрудник": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Волков", "Соколов", "Лебедев"],
            "Отдел": ["Финансы", "Маркетинг", "IT", "HR", "Продажи", "Логистика", "Аналитика"],
            "Проект": ["Альфа", "Омега", "Квант", "Зенит", "Титан", "Орион", "Спектр"],
            "Напиток": ["Кофе", "Зеленый чай", "Черный чай", "Вода", "Латте", "Капучино", "Эспрессо"]
        },
        "Космическая Одиссея": {
            "Капитан": ["Рейнольдс", "Шепард", "Адама", "Старбак", "Пикар", "Соло", "Акбар"],
            "Корабль": ["Серенити", "Нормандия", "Галактика", "Звёздный Крейсер", "Энтерпрайз", "Сокол", "Прометей"],
            "Сектор": ["Орион", "Андромеда", "Плеяды", "Центавра", "Гидра", "Войд", "Квазар"],
            "Аномалия": ["Червоточина", "Грави-колодец", "Темпоральный сдвиг", "Нейтронная буря", "Пси-поле", "Ксено-артефакт", "Сингулярность"]
        }
    }
    puzzle_story_elements = {
        "scenario": "", "position": "локация",
        "Сотрудник": "сотрудник", "Отдел": "отдел", "Проект": "проект", "Напиток": "напиток",
        "Капитан": "капитан", "Корабль": "корабль", "Сектор": "сектор", "Аномалия": "аномалия"
    }

    generator = ORToolsPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("\n\n--- ГЕНЕРАЦИЯ ПРОСТОЙ ЗАДАЧИ ---")
    generator.generate_dramaturg(difficulty=4)

    print("\n\n--- ГЕНЕРАЦИЯ СЛОЖНОЙ ЗАДАЧИ ---")
    generator.generate_dramaturg(difficulty=8)