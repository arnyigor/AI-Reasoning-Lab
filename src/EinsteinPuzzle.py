# EinsteinPuzzle.py
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import collections
from ortools.sat.python import cp_model
from PuzzleDefinition import PuzzleDefinition

class EinsteinPuzzleDefinition(PuzzleDefinition):
    """
    Конкретная реализация для "Загадки Эйнштейна".
    Гибридная модель: надежная базовая архитектура с целевым добавлением
    сложных условных подсказок ("Если-То", "Если-Не-То-Не") для повышения
    сложности и разнообразия головоломок.
    """
    def __init__(self, themes: Dict, story_elements: Dict, num_items: int, num_categories: int, is_circular: bool):
        self._name = "Загадка Эйнштейна"
        self.themes = themes
        self.story_elements = story_elements
        self.num_items = num_items
        self.num_categories = num_categories
        self.is_circular = is_circular
        self._prepare_data()

    def _prepare_data(self):
        selected_theme_name = random.choice(list(self.themes.keys()))
        base_categories = self.themes[selected_theme_name]
        self.story_elements["scenario"] = f"Тайна в сеттинге: {selected_theme_name}"
        self.cat_keys = random.sample(list(base_categories.keys()), self.num_categories)
        self.categories = {key: random.sample(values, self.num_items) for key, values in base_categories.items() if key in self.cat_keys}
        print(f"\n[Генератор]: Тема: '{selected_theme_name}', Размер: {self.num_items}x{len(self.cat_keys)}, Геометрия: {'Круговая' if self.is_circular else 'Линейная'}.")

    @property
    def name(self) -> str:
        return self._name

    def generate_solution(self) -> pd.DataFrame:
        solution_data = {cat: random.sample(items, self.num_items) for cat, items in self.categories.items()}
        return pd.DataFrame(solution_data, index=range(1, self.num_items + 1))


    def design_core_puzzle(self, solution: pd.DataFrame) -> Tuple[List, List]:
        """
        Целенаправленно создает ядро из РАЗНООБРАЗНЫХ сложных подсказок,
        гарантируя представленность "экзотических" типов.
        """
        clue_pool = self.generate_clue_pool(solution)
        anchors = self.get_anchors(solution)

        # --- Гарантируем разнообразие в ядре ---
        core_puzzle = list(anchors)

        # 1. Принудительно добавляем по одной "экзотической" улике, если они есть
        exotic_types = ['if_not_then_not', 'three_in_a_row', 'ordered_chain', 'at_edge', 'sum_equals']
        for clue_type in exotic_types:
            if clue_pool.get(clue_type):
                core_puzzle.append(random.choice(clue_pool[clue_type]))

        # 2. Добираем ядро до нужного размера самыми сложными из оставшихся
        # Собираем всех оставшихся "кандидатов" в сложные улики
        complex_candidates = []
        # Условные - самые желанные
        complex_candidates.extend(clue_pool.get('if_then', []))
        # Остальные непрямые
        other_complex_types = ['relative_pos', 'negative_direct_link', 'is_even', 'distance_greater_than']
        for clue_type in other_complex_types:
            complex_candidates.extend(clue_pool.get(clue_type, []))

        random.shuffle(complex_candidates)

        # Удаляем из кандидатов то, что уже могло попасть в ядро
        core_set = set(core_puzzle)
        complex_candidates = [c for c in complex_candidates if c not in core_set]

        # Дополняем ядро до размера N
        num_to_add = self.num_items - len(core_puzzle)
        if num_to_add > 0:
            core_puzzle.extend(complex_candidates[:num_to_add])

        # --- Формируем оставшиеся подсказки для стен ---
        core_set = set(core_puzzle) # Обновляем сет после добавления
        remaining_clues = [
            clue
            for clue_list in clue_pool.values()
            for clue in clue_list
            if clue not in core_set
        ]

        print(f"  - [Виртуоз] Спроектирован разнообразный каркас из {len(core_puzzle)} подсказок.")
        return core_puzzle, remaining_clues

    def get_anchors(self, solution: pd.DataFrame) -> set:
        anchors = {('positional', (1, self.cat_keys[0], solution.loc[1, self.cat_keys[0]]))}
        if self.is_circular and len(self.cat_keys) > 1:
            anchor_cat2 = self.cat_keys[1]
            anchors.add(('relative_pos', (self.cat_keys[0], solution.loc[1, self.cat_keys[0]], anchor_cat2, solution.loc[2, anchor_cat2])))
        return anchors

    def generate_clue_pool(self, solution: pd.DataFrame) -> Dict[str, List[Tuple[str, Any]]]:
        pool = collections.defaultdict(list)
        unique_clues = collections.defaultdict(set)

        cat_keys = list(self.categories.keys())
        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]

        # Генерируем все базовые типы подсказок
        for i in range(len(all_items_flat)):
            cat1, item1 = all_items_flat[i]
            pos1 = solution[solution[cat1] == item1].index[0]
            unique_clues['positional'].add(('positional', (pos1, cat1, item1)))
            if pos1 == 1 or pos1 == self.num_items: unique_clues['at_edge'].add(('at_edge', (cat1, item1)))
            if pos1 % 2 == 0: unique_clues['is_even'].add(('is_even', (cat1, item1, True)))
            else: unique_clues['is_even'].add(('is_even', (cat1, item1, False)))
            for j in range(i + 1, len(all_items_flat)):
                cat2, item2 = all_items_flat[j]
                if cat1 == cat2: continue
                pos2 = solution[solution[cat2] == item2].index[0]
                if pos1 == pos2: unique_clues['direct_link'].add(('direct_link', (cat1, item1, cat2, item2)))
                else: unique_clues['negative_direct_link'].add(('negative_direct_link', (cat1, item1, cat2, item2)))
                if abs(pos1 - pos2) == 1: unique_clues['relative_pos'].add(('relative_pos', (cat1, item1, cat2, item2)))

        # Генерируем позитивные условные подсказки ("Если P, то Q")
        simple_facts = list(unique_clues['positional']) + list(unique_clues['direct_link'])
        random.shuffle(simple_facts)
        if len(simple_facts) >= 2:
            for _ in range(self.num_items * self.num_categories):
                try:
                    c1, c2 = random.sample(simple_facts, 2)
                    if c1 != c2: unique_clues['if_then'].add(('if_then', (c1, c2)))
                except (ValueError, IndexError): break

        # Генерируем НЕГАТИВНЫЕ условные подсказки ("Если не P, то не Q")
        false_facts = []
        all_items_in_cat = {cat: set(items) for cat, items in self.categories.items()}
        for pos in range(1, self.num_items + 1):
            for cat in self.cat_keys:
                true_item = solution.loc[pos, cat]
                for false_item in all_items_in_cat[cat] - {true_item}:
                    false_facts.append(('positional', (pos, cat, false_item)))

        if len(false_facts) >= 2:
            for _ in range(self.num_items * self.num_categories):
                try:
                    p_false, q_false = random.sample(false_facts, 2)
                    if p_false != q_false:
                        unique_clues['if_not_then_not'].add(('if_not_then_not', (p_false, q_false)))
                except (ValueError, IndexError): break

        for key, clues_set in unique_clues.items():
            pool[key] = list(clues_set)
        return pool

    def create_base_model_and_vars(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        model = cp_model.CpModel()
        positions_domain = (1, self.num_items)
        variables = {item: model.NewIntVar(positions_domain[0], positions_domain[1], f"{cat}_{item}")
                     for cat, items in self.categories.items() for item in items}
        for items in self.categories.values():
            model.AddAllDifferent([variables[item] for item in items])
        return model, variables

    def add_clue_constraint(self, model: cp_model.CpModel, variables: Dict[str, Any], clue: Tuple[str, Any]):
        clue_type, params = clue
        get_var = lambda val: variables.get(val)

        if clue_type == 'positional':
            pos_idx, _, val = params
            p = get_var(val)
            if p is not None: model.Add(p == pos_idx)
        elif clue_type == 'direct_link':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.Add(p1 == p2)
        elif clue_type == 'negative_direct_link':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.Add(p1 != p2)
        elif clue_type == 'relative_pos':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.AddAbsEquality(1, p1 - p2)
        # ... (здесь можно добавить реализацию для других ваших типов, если они есть)

        elif clue_type == 'if_then' or clue_type == 'if_not_then_not':
            p_clue, q_clue = params
            b_p = model.NewBoolVar('')
            b_q = model.NewBoolVar('')

            def reify(cl, bool_var):
                c_type, c_params = cl
                if c_type == 'positional':
                    pos, _, val = c_params
                    p = get_var(val)
                    if p is not None:
                        model.Add(p == pos).OnlyEnforceIf(bool_var)
                        model.Add(p != pos).OnlyEnforceIf(bool_var.Not())
                elif c_type == 'direct_link':
                    _, v1, _, v2 = c_params
                    p1, p2 = get_var(v1), get_var(v2)
                    if p1 is not None and p2 is not None:
                        model.Add(p1 == p2).OnlyEnforceIf(bool_var)
                        model.Add(p1 != p2).OnlyEnforceIf(bool_var.Not())

            reify(p_clue, b_p)
            reify(q_clue, b_q)

            if clue_type == 'if_then':
                # P -> Q
                model.AddImplication(b_p, b_q)
            elif clue_type == 'if_not_then_not':
                # (не P) -> (не Q) эквивалентно Q -> P (контрапозиция)
                model.AddImplication(b_q, b_p)

    def quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], solution: pd.DataFrame, min_path_len: int = 3) -> Tuple[List, Optional[Dict]]:
        graph = collections.defaultdict(list)
        all_items = {item for cat_items in self.categories.values() for item in cat_items}

        def _extract_items_recursive(p, item_set):
            if isinstance(p, (list, tuple)):
                for item in p: _extract_items_recursive(item, item_set)
            elif isinstance(p, str) and p in all_items: item_set.add(p)

        for _, params in puzzle:
            clue_items = set()
            _extract_items_recursive(params, clue_items)
            clue_items_list = list(clue_items)
            for i in range(len(clue_items_list)):
                for j in range(i + 1, len(clue_items_list)):
                    graph[clue_items_list[i]].append(clue_items_list[j])
                    graph[clue_items_list[j]].append(clue_items_list[i])

        best_question, max_path_len = None, -1
        possible_questions = []
        for subject_cat in self.cat_keys:
            for attribute_cat in self.cat_keys:
                if subject_cat == attribute_cat: continue
                for subject_item in self.categories[subject_cat]:
                    answer_item = solution.loc[solution[subject_cat] == subject_item, attribute_cat].iloc[0]
                    possible_questions.append((subject_cat, subject_item, attribute_cat, answer_item))

        random.shuffle(possible_questions)
        for subject_cat, subject_item, attribute_cat, answer_item in possible_questions:
            q = collections.deque([(subject_item, [subject_item])])
            visited = {subject_item}
            while q:
                curr_node, path = q.popleft()
                if curr_node == answer_item:
                    if len(path) - 1 > max_path_len:
                        max_path_len = len(path) - 1
                        best_question = {"question": f"Какой {self.story_elements.get(attribute_cat, attribute_cat.lower())} у {self.story_elements.get(subject_cat, subject_cat.lower())} по имени {subject_item}?",
                                         "answer": f"Ответ для проверки: {answer_item}"}
                    break
                for neighbor in graph.get(curr_node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append((neighbor, path + [neighbor]))

        if max_path_len >= min_path_len:
            print(f"  - Аудит пройден. Найден вопрос с длиной пути: {max_path_len}")
            return list(set(puzzle)), best_question
        return puzzle, None

    def format_clue(self, clue: Tuple[str, Any]) -> str:
        s = self.story_elements
        g = lambda c, v: f"{s.get(c, c.lower())} '{v}'"

        def format_fact(fact_clue: Tuple[str, Any], is_negative: bool = False) -> str:
            fact_type, fact_params = fact_clue
            neg = " НЕ" if is_negative else ""
            if fact_type == 'positional':
                return f"в {s.get('position','локация')} №{fact_params[0]}{neg} находится {g(fact_params[1], fact_params[2])}"
            if fact_type == 'direct_link':
                return f"характеристикой {g(fact_params[0], fact_params[1])}{neg} является {g(fact_params[2], fact_params[3])}"
            return "[неформатируемый факт]"

        clue_type, params = clue
        try:
            if clue_type == 'positional': return f"В {s.get('position','локация')} №{params[0]} находится {g(params[1], params[2])}."
            if clue_type == 'direct_link': return f"Характеристикой {g(params[0], params[1])} является {g(params[2], params[3])}."
            if clue_type == 'negative_direct_link': return f"{g(params[0], params[1]).capitalize()} НЕ находится в одной локации с {g(params[2], params[3])}."
            if clue_type == 'relative_pos': return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} находятся в соседних локациях."

            if clue_type == 'if_then':
                cond_text = format_fact(params[0])
                cons_text = format_fact(params[1])
                return f"Если {cond_text}, то {cons_text}."

            if clue_type == 'if_not_then_not':
                cond_text = format_fact(params[0], is_negative=True)
                cons_text = format_fact(params[1], is_negative=True)
                return f"Если {cond_text}, то {cons_text}."

        except (AttributeError, IndexError, KeyError) as e:
            return f"[Ошибка форматирования для {clue_type}: {e}]"
        return f"[Неформатированная подсказка: {clue_type}]"

    def print_puzzle(self, final_clues: List[Tuple[str, Any]], question_data: Dict[str, str], solution: pd.DataFrame):
        question, answer_for_check = question_data['question'], question_data['answer']
        print(f"\n**Сценарий: {self.story_elements['scenario']}**\n")
        print(f"Условия ({len(final_clues)} подсказок):\n")
        final_clues_text = sorted([self.format_clue(c) for c in final_clues])
        for i, clue_text in enumerate(final_clues_text, 1): print(f"{i}. {clue_text}")
        print("\n" + "="*40 + "\n")
        print(f"Вопрос: {question}")
        print("\n" + "="*40 + "\n")
        print(answer_for_check)
        print("\n--- Скрытое Решение для самопроверки ---\n", solution)