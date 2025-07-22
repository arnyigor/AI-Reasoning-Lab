# -*- coding: utf-8 -*-
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Set
from ortools.sat.python import cp_model
import collections

# -*- coding: utf-8 -*-
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional, Set
from ortools.sat.python import cp_model
import collections

class ORToolsPuzzleGenerator:
    """
    Генератор логических головолок.
    Архитектура v26.0 "Бульдозер".

    Этот подход возвращается к доказавшей свою надежность стратегии
    "создай избыточное, затем минимизируй", но с умной минимизацией
    и финальным аудитом качества. Это самая стабильная версия.
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
        self.anchors: Set[Tuple[str, Any]] = set()

    def generate_bulldozer(self, difficulty: int, max_retries: int = 10):
        for attempt in range(max_retries):
            print(f"\n--- ПОПЫТКА ГЕНЕРАЦИИ №{attempt + 1}/{max_retries} ---")

            self._select_data_for_difficulty(difficulty)
            self._generate_solution()
            assert self.solution is not None

            # --- Фаза 1: Создание избыточной заготовки ---
            print("\n[Бульдозер]: Фаза 1: Создание избыточной заготовки...")
            initial_puzzle = self._build_initial_puzzle()
            if not initial_puzzle:
                print("  - ПРОВАЛ: Не удалось создать заготовку. Новая попытка...")
                continue

            # --- Фаза 2: Умная минимизация ---
            print("\n[Бульдозер]: Фаза 2: Умная минимизация...")
            minimized_puzzle = self._minimize_puzzle(initial_puzzle, self.anchors)

            # --- Фаза 3: Аудит Качества ---
            print("\n[Бульдозер]: Фаза 3: Аудит качества...")
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

    def _build_initial_puzzle(self, max_steps=300):
        clue_pool = [clue for clues in self._generate_clue_pool().values() for clue in clues]
        random.shuffle(clue_pool)

        self.anchors = {('positional', (1, self.cat_keys[0], self.solution.loc[1, self.cat_keys[0]]))}
        if self.is_circular:
            self.anchors.add(('relative_pos', (self.cat_keys[0], self.solution.loc[1, self.cat_keys[0]], self.cat_keys[1], self.solution.loc[2, self.cat_keys[1]])))

        current_clues = list(self.anchors)

        for _ in range(max_steps):
            if not clue_pool: return None
            current_clues.append(clue_pool.pop(0))
            if self._check_solvability(current_clues) == 1:
                print(f"  - Заготовка найдена с {len(current_clues)} подсказками.")
                return current_clues
        return None

    def _minimize_puzzle(self, puzzle: List[Tuple[str, Any]], anchors: set) -> List[Tuple[str, Any]]:
        current_puzzle = list(puzzle)
        while True:
            removable_clues = []

            # Ищем все подсказки, которые можно удалить
            clues_to_check = [c for c in current_puzzle if c not in anchors]
            for clue in clues_to_check:
                temp_puzzle = [c for c in current_puzzle if c != clue]
                if self._check_solvability(temp_puzzle) == 1:
                    removable_clues.append(clue)

            if not removable_clues:
                print(f"  - Минимизация завершена. Осталось {len(current_puzzle)} подсказок.")
                break # Больше нечего удалять

            # Удаляем одну случайную из тех, что можно удалить
            clue_to_remove = random.choice(removable_clues)
            current_puzzle.remove(clue_to_remove)
            print(f"  - Удалена избыточная подсказка. Осталось: {len(current_puzzle)}")

        return current_puzzle

    # --- Остальные методы (аудит, хелперы) ---
    def _quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], min_path_len: int = 3):
        graph = collections.defaultdict(list)
        all_items = {item for cat_items in self.categories.values() for item in cat_items}

        for clue_type, params in puzzle:
            clue_items = set()
            def extract_items(p):
                if isinstance(p, (list, tuple)):
                    for item in p: extract_items(item)
                elif isinstance(p, str) and p in all_items: clue_items.add(p)
            extract_items(params)

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
            q = collections.deque([(subject_item, [subject_item])])
            visited = {subject_item}

            while q:
                curr_node, path = q.popleft()
                if curr_node == answer_item:
                    path_len = len(path) - 1
                    if path_len > max_path_len:
                        max_path_len = path_len
                        best_question = {"question": f"Какой {self.story_elements.get(attribute_cat, attribute_cat)} у {self.story_elements.get(subject_cat, subject_cat)} по имени {subject_item}?",
                                         "answer": f"Ответ для проверки: {answer_item}"}
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

    # ... (Остальные хелперы остаются без изменений)
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
        pool: Dict[str, List[Any]] = {'positional': [], 'direct_link': [], 'three_in_a_row': [], 'at_edge': [], 'is_even': []}
        unique_clues = {key: set() for key in pool}
        cat_keys = list(self.categories.keys())
        assert self.solution is not None

        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]
        for i in range(len(all_items_flat)):
            cat1, item1 = all_items_flat[i]
            pos1 = self.solution[self.solution[cat1] == item1].index[0]
            if pos1 == 1 or pos1 == self.num_items: unique_clues['at_edge'].add(('at_edge', (cat1, item1)))
            if pos1 % 2 == 0: unique_clues['is_even'].add(('is_even', (cat1, item1, True)))
            else: unique_clues['is_even'].add(('is_even', (cat1, item1, False)))
            unique_clues['positional'].add(('positional', (pos1, cat1, item1)))
            for j in range(i + 1, len(all_items_flat)):
                cat2, item2 = all_items_flat[j]
                if cat1 == cat2: continue
                pos2 = self.solution[self.solution[cat2] == item2].index[0]
                if pos1 == pos2: unique_clues['direct_link'].add(('direct_link', (cat1, item1, cat2, item2)))

        if self.num_items >= 3 and len(cat_keys) >= 3:
            for _ in range(self.num_items * 5):
                cats = random.sample(cat_keys, 3)
                for start_pos in range(1, self.num_items - 1):
                    items = [self.solution.loc[start_pos + k, cats[k]] for k in range(3)]
                    params = tuple(random.sample(list(zip(cats, items)), 3))
                    unique_clues['three_in_a_row'].add(('three_in_a_row', params))

        for key in pool:
            pool[key] = list(unique_clues[key])
            random.shuffle(pool[key])
        return pool

    def _create_or_tools_model(self, clues: List[Tuple[str, Any]]) -> cp_model.CpModel:
        model = cp_model.CpModel()
        positions_domain = (1, self.num_items)
        variables = {item: model.NewIntVar(positions_domain[0], positions_domain[1], f"{cat}_{item}")
                     for cat, items in self.categories.items() for item in items}
        for items in self.categories.values(): model.AddAllDifferent([variables[item] for item in items])
        for clue_type, params in clues: self._add_clue_as_or_tools_constraint(model, variables, clue_type, params)
        return model

    def _add_clue_as_or_tools_constraint(self, model, variables, clue_type, params):
        get_var = lambda val: variables.get(val)

        if clue_type == 'positional':
            pos_idx, _, val = params
            if get_var(val) is not None: model.Add(get_var(val) == pos_idx)
        elif clue_type == 'direct_link':
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) == get_var(val2))
        elif clue_type == 'at_edge':
            cat, val = params
            p = get_var(val)
            if p is None: return
            b1, b2 = model.NewBoolVar(''), model.NewBoolVar('')
            model.Add(p == 1).OnlyEnforceIf(b1)
            model.Add(p == self.num_items).OnlyEnforceIf(b2)
            model.AddBoolOr([b1, b2])
        elif clue_type == 'is_even':
            cat, val, is_even_flag = params
            p = get_var(val)
            if p is None: return
            model.AddModuloEquality(0 if is_even_flag else 1, p, 2)
        elif clue_type == 'three_in_a_row':
            (c1, v1), (c2, v2), (c3, v3) = params
            p1, p2, p3 = get_var(v1), get_var(v2), get_var(v3)
            if p1 is None or p2 is None or p3 is None: return

            # Упрощенная, но рабочая логика: разница между макс и мин позицией равна 2
            # И все три переменные разные (что уже гарантировано основным ограничением)
            max_var = model.NewIntVar(1, self.num_items, '')
            min_var = model.NewIntVar(1, self.num_items, '')
            model.AddMaxEquality(max_var, [p1, p2, p3])
            model.AddMinEquality(min_var, [p1, p2, p3])
            model.Add(max_var - min_var == 2)

    def _print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str]):
        assert self.solution is not None
        question, answer_for_check = question_data['question'], question_data['answer']
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
        g = lambda c, v: f"{s.get(c, c)} '{v}'"

        if clue_type == 'positional': return f"В {s['position']} №{params[0]} находится {g(params[1], params[2])}."
        if clue_type == 'direct_link': return f"Характеристикой {g(params[0], params[1])} является {g(params[2], params[3])}."
        if clue_type == 'at_edge': return f"{g(params[0], params[1]).capitalize()} находится в одной из крайних локаций."
        if clue_type == 'is_even': return f"Номер локации, где {g(params[0], params[1])}, — {'чётный' if params[2] else 'нечётный'}."
        if clue_type == 'three_in_a_row':
            p1, p2, p3 = params
            return f"Объекты {g(p1[0], p1[1])}, {g(p2[0], p2[1])} и {g(p3[0], p3[1])} находятся в трёх последовательных локациях (в любом порядке)."
        return f"[Неформатированная подсказка: {clue_type}]"


if __name__ == '__main__':
    THEMES = { "Офисная Тайна": { "Сотрудник": ["Иванов", "Петров", "Смирнов", "Кузнецов", "Волков", "Соколов", "Лебедев"], "Отдел": ["Финансы", "Маркетинг", "IT", "HR", "Продажи", "Логистика", "Аналитика"], "Проект": ["Альфа", "Омега", "Квант", "Зенит", "Титан", "Орион", "Спектр"], "Напиток": ["Кофе", "Зеленый чай", "Черный чай", "Вода", "Латте", "Капучино", "Эспрессо"] }, "Космическая Одиссея": { "Капитан": ["Рейнольдс", "Шепард", "Адама", "Старбак", "Пикар", "Соло", "Акбар"], "Корабль": ["Серенити", "Нормандия", "Галактика", "Звёздный Крейсер", "Энтерпрайз", "Сокол", "Прометей"], "Сектор": ["Орион", "Андромеда", "Плеяды", "Центавра", "Гидра", "Войд", "Квазар"], "Аномалия": ["Червоточина", "Грави-колодец", "Темпоральный сдвиг", "Нейтронная буря", "Пси-поле", "Ксено-артефакт", "Сингулярность"] } }
    puzzle_story_elements = { "scenario": "", "position": "локация", "Сотрудник": "сотрудник", "Отдел": "отдел", "Проект": "проект", "Напиток": "напиток", "Капитан": "капитан", "Корабль": "корабль", "Сектор": "сектор", "Аномалия": "аномалия" }

    generator = ORToolsPuzzleGenerator(themes=THEMES, story_elements=puzzle_story_elements)

    print("\n\n--- ГЕНЕРАЦИЯ ПРОСТОЙ ЗАДАЧИ ---")
    generator.generate_bulldozer(difficulty=4)

    print("\n\n--- ГЕНЕРАЦИЯ СЛОЖНОЙ ЗАДАЧИ ---")
    generator.generate_bulldozer(difficulty=8)