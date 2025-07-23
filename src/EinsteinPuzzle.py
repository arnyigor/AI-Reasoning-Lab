# EinsteinPuzzle.py
import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import collections
from ortools.sat.python import cp_model
from PuzzleDefinition import PuzzleDefinition

class EinsteinPuzzleDefinition(PuzzleDefinition):
    """
    Конкретная реализация для классической "Загадки Эйнштейна".
    """
    def __init__(self, themes: Dict, story_elements: Dict, num_items: int, num_categories: int, is_circular: bool):
        self._name = "Архитектор"
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

    def get_anchors(self, solution: pd.DataFrame) -> set:
        anchors = {('positional', (1, self.cat_keys[0], solution.loc[1, self.cat_keys[0]]))}
        if self.is_circular:
            anchors.add(('relative_pos', (self.cat_keys[0], solution.loc[1, self.cat_keys[0]], self.cat_keys[1], solution.loc[2, self.cat_keys[1]])))
        return anchors

    def design_core_puzzle(self, solution: pd.DataFrame) -> Tuple[List, List]:
        clue_pool = self.generate_clue_pool(solution)
        anchors = self.get_anchors(solution)

        strong_clues = clue_pool.get('direct_link', []) + clue_pool.get('positional', [])
        complex_clues = [c for k, v in clue_pool.items() if k not in ['direct_link', 'positional'] for c in v]
        random.shuffle(strong_clues)
        random.shuffle(complex_clues)

        num_core_clues = self.num_items # Количество сложных подсказок в ядре = размеру сетки
        core_puzzle = list(anchors) + complex_clues[:num_core_clues]

        # Остальные - "стены"
        remaining_clues = strong_clues + complex_clues[num_core_clues:]

        print(f"  - Спроектирован каркас из {len(core_puzzle)} сложных подсказок.")
        return core_puzzle, remaining_clues

    def generate_clue_pool(self, solution: pd.DataFrame) -> Dict[str, List[Tuple[str, Any]]]:
        # (Полная версия _generate_clue_pool из v26.1)
        pool = collections.defaultdict(list)
        unique_clues = collections.defaultdict(set)

        cat_keys = list(self.categories.keys())
        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]

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
                if self.is_circular and self.num_items % 2 == 0 and abs(pos1-pos2) == self.num_items//2: unique_clues['opposite_link'].add(('opposite_link', (cat1,item1,cat2,item2)))
                if abs(pos1 - pos2) > 1: unique_clues['distance_greater_than'].add(('distance_greater_than', (cat1, item1, cat2, item2, 1)))
                if pos1 + pos2 == self.num_items + 1: unique_clues['sum_equals'].add(('sum_equals', (cat1, item1, cat2, item2, self.num_items + 1)))

        if len(cat_keys) >= 3:
            for _ in range(self.num_items * 5):
                cats = random.sample(cat_keys, 3)
                positions = sorted(random.sample(range(1, self.num_items + 1), 3))
                items = [solution.loc[p, c] for p, c in zip(positions, cats)]
                params = tuple(zip(cats, items))
                if positions[0] + 1 == positions[1] and positions[1] + 1 == positions[2]:
                    unique_clues['three_in_a_row'].add(('three_in_a_row', params))
                unique_clues['ordered_chain'].add(('ordered_chain', params))

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
        # (Полная версия _add_clue_as_or_tools_constraint из v26.1)
        clue_type, params = clue
        get_var = lambda val: variables.get(val)

        if clue_type == 'positional':
            pos_idx, _, val = params
            if get_var(val) is not None: model.Add(get_var(val) == pos_idx)
        elif clue_type == 'direct_link':
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) == get_var(val2))
        elif clue_type == 'negative_direct_link':
            _, val1, _, val2 = params
            if get_var(val1) is not None and get_var(val2) is not None: model.Add(get_var(val1) != get_var(val2))
        elif clue_type == 'relative_pos':
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.AddAbsEquality(1, p1-p2)
        elif clue_type == 'opposite_link':
            if self.is_circular:
                _, val1, _, val2 = params
                p1, p2 = get_var(val1), get_var(val2)
                if p1 is not None and p2 is not None: model.AddAbsEquality(self.num_items // 2, p1-p2)
        elif clue_type in ['three_in_a_row', 'ordered_chain']:
            (c1,v1),(c2,v2),(c3,v3) = params
            p1,p2,p3 = get_var(v1),get_var(v2),get_var(v3)
            if p1 is not None and p2 is not None and p3 is not None:
                if clue_type == 'three_in_a_row':
                    max_var, min_var = model.NewIntVar(1, self.num_items, ''), model.NewIntVar(1, self.num_items, '')
                    model.AddMaxEquality(max_var, [p1,p2,p3]); model.AddMinEquality(min_var, [p1,p2,p3])
                    model.Add(max_var - min_var == 2)
                elif clue_type == 'ordered_chain':
                    model.Add(p1 < p2); model.Add(p2 < p3)
        elif clue_type == 'at_edge':
            _, val = params
            p = get_var(val)
            if p is not None:
                b1, b2 = model.NewBoolVar(''), model.NewBoolVar('')
                model.Add(p==1).OnlyEnforceIf(b1); model.Add(p==self.num_items).OnlyEnforceIf(b2)
                model.AddBoolOr([b1,b2])
        elif clue_type == 'is_even':
            _, val, is_even = params
            p = get_var(val)
            if p is not None: model.AddModuloEquality(0 if is_even else 1, p, 2)
        elif clue_type == 'sum_equals':
            _, val1, _, val2, total = params
            p1,p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.Add(p1+p2==total)
        elif clue_type == 'distance_greater_than':
            _, val1, _, val2, dist = params
            p1,p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None:
                abs_diff = model.NewIntVar(0, self.num_items, '')
                model.AddAbsEquality(abs_diff, p1 - p2)
                model.Add(abs_diff > dist)

    def quality_audit_and_select_question(self, puzzle: List[Tuple[str, Any]], solution: pd.DataFrame, min_path_len: int = 3):
        # (Полная версия _quality_audit_and_select_question из v26.1)
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
                    answer_item = solution.loc[solution[subject_cat] == subject_item, attribute_cat].iloc[0]
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

    def format_clue(self, clue: Tuple[str, Any]) -> str:
        # (Полная версия _format_clue из v26.1)
        clue_type, params = clue
        s = self.story_elements
        g = lambda c, v: f"{s.get(c, c)} '{v}'"

        try:
            if clue_type == 'positional': return f"В {s.get('position','локация')} №{params[0]} находится {g(params[1], params[2])}."
            if clue_type == 'direct_link': return f"Характеристикой {g(params[0], params[1])} является {g(params[2], params[3])}."
            if clue_type == 'negative_direct_link': return f"{g(params[0], params[1]).capitalize()} НЕ находится в одной локации с {g(params[2], params[3])}."
            if clue_type == 'relative_pos': return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} находятся в соседних локациях."
            if clue_type == 'opposite_link': return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} находятся в локациях друг напротив друга."
            if clue_type == 'at_edge': return f"{g(params[0], params[1]).capitalize()} находится в одной из крайних локаций."
            if clue_type == 'is_even': return f"Номер локации, где {g(params[0], params[1])}, — {'чётный' if params[2] else 'нечётный'}."
            if clue_type == 'three_in_a_row':
                p1,p2,p3 = params
                return f"Объекты {g(p1[0],p1[1])}, {g(p2[0],p2[1])} и {g(p3[0],p3[1])} находятся в трёх последовательных локациях (в любом порядке)."
            if clue_type == 'ordered_chain':
                p1,p2,p3 = params
                return f"Локация, где {g(p1[0],p1[1])}, находится где-то левее локации, где {g(p2[0],p2[1])}, которая в свою очередь левее локации, где {g(p3[0],p3[1])}."
            if clue_type == 'sum_equals':
                return f"Сумма номеров локаций, где {g(params[0], params[1])} и где {g(params[2], params[3])}, равна {params[4]}."
            if clue_type == 'distance_greater_than':
                return f"Между локациями, где {g(params[0], params[1])}, и где {g(params[2], params[3])}, находится более чем {params[4]} локация(й)."
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