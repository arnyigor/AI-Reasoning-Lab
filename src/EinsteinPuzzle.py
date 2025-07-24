# EinsteinPuzzle.py (рефакторинг с Enum)

import random
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import collections
from ortools.sat.python import cp_model

from PuzzleDefinition import PuzzleDefinition
from clue_types import ClueType # <<< ИМПОРТИРУЕМ НАШ ENUM

class EinsteinPuzzleDefinition(PuzzleDefinition):
    """
    Реализация "Загадки Эйнштейна" с использованием Enum для типов подсказок.
    """
    def __init__(self, themes: Dict, story_elements: Dict, num_items: int, num_categories: int, is_circular: bool):
        self._name = "Загадка Эйнштейна"
        self.themes = themes
        self.story_elements = story_elements
        self.num_items = num_items
        self.num_categories = num_categories
        self.is_circular = is_circular
        self._prepare_data()

    @property
    def SolutionCollector(self):
        """Возвращает вложенный класс SolutionCollector."""

        class Collector(cp_model.CpSolverSolutionCallback):
            """Собирает найденные решения в список."""
            def __init__(self, limit: int):
                super().__init__()
                self.solutions = []
                self._limit = limit
                self._variables = None

            def set_variables(self, variables: Dict[str, Any]):
                self._variables = variables

            def on_solution_callback(self):
                if self._variables:
                    current_solution = {
                        name: self.Value(var) for name, var in self._variables.items()
                    }
                    self.solutions.append(current_solution)
                if len(self.solutions) >= self._limit:
                    self.StopSearch()

            @property
            def solution_count(self):
                return len(self.solutions)

        return Collector

    def find_difference_and_create_clue(self, solution1: Dict, solution2: Dict, true_solution: pd.DataFrame) -> Optional[Tuple[Any, Any]]:
        """
        Находит первое различие между двумя решениями и создает простую
        улику (POSITIONAL или DIRECT_LINK), которая соответствует истинному решению
        и устраняет неоднозначность.
        """
        items = list(solution1.keys())
        random.shuffle(items)

        for item_name in items:
            if solution1[item_name] != solution2[item_name]:
                # Нашли различие! Например, в solution1 'Программист' в доме 2, а в solution2 - в доме 4.
                # Теперь нам нужно создать улику, которая соответствует ИСТИННОМУ решению.

                # Находим категорию этого объекта
                item_category = None
                for cat, cat_items in self.categories.items():
                    if item_name in cat_items:
                        item_category = cat
                        break

                if not item_category:
                    continue

                # Получаем правильную позицию из эталонного решения
                true_pos = true_solution[true_solution[item_category] == item_name].index[0]

                # Создаем самую простую и надежную "контр-улику" - позиционную
                # Это гарантированно отсечет одно из неверных решений.
                return (ClueType.POSITIONAL, (true_pos, item_category, item_name))

        return None # Не удалось найти различий, что маловероятно

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
        clue_pool = self.generate_clue_pool(solution)
        anchors = self.get_anchors(solution)
        core_puzzle = list(anchors)

        exotic_types = [
            ClueType.IF_NOT_THEN_NOT, ClueType.THREE_IN_A_ROW, ClueType.ORDERED_CHAIN,
            ClueType.AT_EDGE, ClueType.SUM_EQUALS, ClueType.EITHER_OR, ClueType.IF_AND_ONLY_IF,
            ClueType.NEITHER_NOR_POS
        ]

        random.shuffle(exotic_types)
        for clue_type in exotic_types:
            if clue_pool.get(clue_type):
                core_puzzle.append(random.choice(clue_pool[clue_type]))

        complex_candidates = []
        complex_candidates.extend(clue_pool.get(ClueType.IF_THEN, []))

        other_complex_types = [
            ClueType.RELATIVE_POS, ClueType.NEGATIVE_DIRECT_LINK,
            ClueType.IS_EVEN, ClueType.DISTANCE_GREATER_THAN
        ]
        for clue_type in other_complex_types:
            complex_candidates.extend(clue_pool.get(clue_type, []))

        random.shuffle(complex_candidates)
        core_set = {tuple(c) for c in core_puzzle}
        complex_candidates = [c for c in complex_candidates if tuple(c) not in core_set]

        # ИЗМЕНЕНИЕ: Делаем каркас более насыщенным и менее зависимым от размера
        num_to_add = int(self.num_items * 1.5) # Добавляем больше сложных улик в ядро
        if num_to_add > 0:
            core_puzzle.extend(complex_candidates[:num_to_add])
        # КОНЕЦ ИЗМЕНЕНИЯ

        core_set = {tuple(c) for c in core_puzzle}
        remaining_clues = [clue for clue_list in clue_pool.values() for clue in clue_list if tuple(clue) not in core_set]

        print(f"  - [Виртуоз] Спроектирован разнообразный каркас из {len(core_puzzle)} подсказок.")
        return core_puzzle, remaining_clues

    def get_anchors(self, solution: pd.DataFrame) -> set:
        # --- ИЗМЕНЕНИЕ: Используем Enum ---
        anchors = {(ClueType.POSITIONAL, (1, self.cat_keys[0], solution.loc[1, self.cat_keys[0]]))}
        if self.is_circular and len(self.cat_keys) > 1:
            anchor_cat2 = self.cat_keys[1]
            anchors.add((ClueType.RELATIVE_POS, (self.cat_keys[0], solution.loc[1, self.cat_keys[0]], anchor_cat2, solution.loc[2, anchor_cat2])))
        return anchors

    def generate_clue_pool(self, solution: pd.DataFrame) -> Dict[ClueType, List[Tuple[Any, Any]]]:
        pool = collections.defaultdict(list)
        unique_clues = collections.defaultdict(set)
        cat_keys = list(self.categories.keys())
        all_items_flat = [(cat, item) for cat, items in self.categories.items() for item in items]

        def add_clue(clue_type: ClueType, params: Tuple):
            unique_clues[clue_type].add((clue_type, params))

        for i in range(len(all_items_flat)):
            cat1, item1 = all_items_flat[i]
            pos1 = solution[solution[cat1] == item1].index[0]
            add_clue(ClueType.POSITIONAL, (pos1, cat1, item1))
            if pos1 == 1 or pos1 == self.num_items:
                add_clue(ClueType.AT_EDGE, (cat1, item1))
            add_clue(ClueType.IS_EVEN, (cat1, item1, pos1 % 2 == 0))

            for j in range(i + 1, len(all_items_flat)):
                cat2, item2 = all_items_flat[j]
                if cat1 == cat2: continue
                pos2 = solution[solution[cat2] == item2].index[0]
                if pos1 == pos2: add_clue(ClueType.DIRECT_LINK, (cat1, item1, cat2, item2))
                else: add_clue(ClueType.NEGATIVE_DIRECT_LINK, (cat1, item1, cat2, item2))
                if abs(pos1 - pos2) == 1: add_clue(ClueType.RELATIVE_POS, (cat1, item1, cat2, item2))
                if abs(pos1 - pos2) > 1: add_clue(ClueType.DISTANCE_GREATER_THAN, (cat1, item1, cat2, item2, 1))
                if pos1 + pos2 == self.num_items + 1: add_clue(ClueType.SUM_EQUALS, (cat1, item1, cat2, item2, self.num_items + 1))

        # ИЗМЕНЕНИЕ 1: Увеличиваем генерацию структурных улик
        if len(cat_keys) >= 3:
            for _ in range(self.num_items * self.num_items * 3): # Увеличили значительно
                try:
                    cats = random.sample(cat_keys, 3)
                    positions = sorted(random.sample(range(1, self.num_items + 1), 3))
                    items = [solution.loc[p, c] for p, c in zip(positions, cats)]
                    params = tuple(zip(cats, items))
                    if positions[0] + 1 == positions[1] and positions[1] + 1 == positions[2]:
                        add_clue(ClueType.THREE_IN_A_ROW, params)
                    add_clue(ClueType.ORDERED_CHAIN, params)
                except (ValueError, IndexError): break

        simple_facts = list(unique_clues[ClueType.POSITIONAL]) + list(unique_clues[ClueType.DIRECT_LINK])
        random.shuffle(simple_facts)
        # ИЗМЕНЕНИЕ 2: Увеличиваем генерацию условных улик
        if len(simple_facts) >= 2:
            for _ in range(self.num_items * self.num_categories * 5): # Увеличили значительно
                try:
                    c1, c2 = random.sample(simple_facts, 2)
                    if c1 != c2:
                        add_clue(ClueType.IF_THEN, (c1, c2))
                        add_clue(ClueType.EITHER_OR, (c1, c2))
                        add_clue(ClueType.IF_AND_ONLY_IF, (c1, c2))
                except (ValueError, IndexError): break

        false_facts = []
        all_items_in_cat = {cat: set(items) for cat, items in self.categories.items()}
        for pos in range(1, self.num_items + 1):
            for cat in self.cat_keys:
                true_item = solution.loc[pos, cat]
                for false_item in all_items_in_cat[cat] - {true_item}:
                    false_facts.append((ClueType.POSITIONAL, (pos, cat, false_item)))
        # ИЗМЕНЕНИЕ 3: Увеличиваем генерацию условных отрицаний
        if len(false_facts) >= 2:
            for _ in range(self.num_items * self.num_categories * 3): # Увеличили
                try:
                    p_false, q_false = random.sample(false_facts, 2)
                    if p_false != q_false:
                        add_clue(ClueType.IF_NOT_THEN_NOT, (p_false, q_false))
                except (ValueError, IndexError): break

        # Генерация "Ни... ни..."
        for p in range(1, self.num_items + 1):
            candidates = []
            for cat, item in all_items_flat:
                item_pos = solution[solution[cat] == item].index[0]
                if item_pos != p:
                    candidates.append((cat, item))
            if len(candidates) >= 2:
                for _ in range(self.num_categories):
                    num_items_in_clue = random.randint(2, min(len(candidates), 3))
                    selected_items = random.sample(candidates, num_items_in_clue)
                    add_clue(ClueType.NEITHER_NOR_POS, (tuple(selected_items), p))

        for key, clues_set in unique_clues.items():
            pool[key] = list(clues_set)
        return pool

    def create_base_model_and_vars(self) -> Tuple[cp_model.CpModel, Dict[str, Any]]:
        model = cp_model.CpModel()
        positions_domain = (1, self.num_items)
        variables = {item: model.NewIntVar(positions_domain[0], positions_domain[1], f"{cat}_{item.replace(' ', '_')}")
                     for cat, items in self.categories.items() for item in items}
        for items in self.categories.values():
            model.AddAllDifferent([variables[item] for item in items])
        return model, variables

    def add_clue_constraint(self, model: cp_model.CpModel, variables: Dict[str, Any], clue: Tuple[Any, Any]):
        clue_type, params = clue
        get_var = lambda val: variables.get(val)

        if clue_type == ClueType.POSITIONAL:
            pos_idx, _, val = params
            p = get_var(val)
            if p is not None: model.Add(p == pos_idx)
        elif clue_type == ClueType.DIRECT_LINK:
            _, v1, _, v2 = params
            p1, p2 = get_var(v1), get_var(v2)
            if p1 is not None and p2 is not None: model.Add(p1 == p2)
        elif clue_type == ClueType.NEGATIVE_DIRECT_LINK:
            _, v1, _, v2 = params
            p1, p2 = get_var(v1), get_var(v2)
            if p1 is not None and p2 is not None: model.Add(p1 != p2)
        elif clue_type == ClueType.RELATIVE_POS:
            _, val1, _, val2 = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.AddAbsEquality(1, p1 - p2)
        elif clue_type == ClueType.AT_EDGE:
            _, val = params
            p = get_var(val)
            if p is not None:
                b1, b2 = model.NewBoolVar(''), model.NewBoolVar('')
                model.Add(p == 1).OnlyEnforceIf(b1)
                model.Add(p == self.num_items).OnlyEnforceIf(b2)
                model.AddBoolOr([b1, b2])
        elif clue_type == ClueType.SUM_EQUALS:
            _, val1, _, val2, total = params
            p1, p2 = get_var(val1), get_var(val2)
            if p1 is not None and p2 is not None: model.Add(p1 + p2 == total)
        elif clue_type in [ClueType.THREE_IN_A_ROW, ClueType.ORDERED_CHAIN]:
            (c1,v1), (c2,v2), (c3,v3) = params
            p1, p2, p3 = get_var(v1), get_var(v2), get_var(v3)
            if p1 is not None and p2 is not None and p3 is not None:
                if clue_type == ClueType.THREE_IN_A_ROW:
                    max_var, min_var = model.NewIntVar(1, self.num_items, ''), model.NewIntVar(1, self.num_items, '')
                    model.AddMaxEquality(max_var, [p1, p2, p3])
                    model.AddMinEquality(min_var, [p1, p2, p3])
                    model.Add(max_var - min_var == 2)
                elif clue_type == ClueType.ORDERED_CHAIN:
                    model.Add(p1 < p2)
                    model.Add(p2 < p3)
        elif clue_type in [ClueType.IF_THEN, ClueType.IF_NOT_THEN_NOT, ClueType.EITHER_OR, ClueType.IF_AND_ONLY_IF]:
            p_clue, q_clue = params
            rand_id = random.randint(1, 1_000_000)
            b_p, b_q = model.NewBoolVar(f'bp_{rand_id}'), model.NewBoolVar(f'bq_{rand_id}')

            def reify(cl, bool_var):
                c_type, c_params = cl
                if c_type == ClueType.POSITIONAL:
                    pos, _, val = c_params
                    p = get_var(val)
                    if p is not None:
                        model.Add(p == pos).OnlyEnforceIf(bool_var)
                        model.Add(p != pos).OnlyEnforceIf(bool_var.Not())
                elif c_type == ClueType.DIRECT_LINK:
                    _, v1, _, v2 = c_params
                    p1, p2 = get_var(v1), get_var(v2)
                    if p1 is not None and p2 is not None:
                        model.Add(p1 == p2).OnlyEnforceIf(bool_var)
                        model.Add(p1 != p2).OnlyEnforceIf(bool_var.Not())

            reify(p_clue, b_p)
            reify(q_clue, b_q)

            if clue_type == ClueType.IF_THEN: model.AddImplication(b_p, b_q)
            elif clue_type == ClueType.IF_NOT_THEN_NOT: model.AddImplication(b_q.Not(), b_p.Not())
            elif clue_type == ClueType.EITHER_OR: model.AddBoolXOr([b_p, b_q])
            elif clue_type == ClueType.IF_AND_ONLY_IF: model.Add(b_p == b_q)
        elif clue_type == ClueType.NEITHER_NOR_POS:
            item_tuples, position = params
            for cat, item in item_tuples:
                p_var = get_var(item)
                if p_var is not None:
                    model.Add(p_var != position)

    def quality_audit_and_select_question(self, puzzle: List[Tuple[Any, Any]], solution: pd.DataFrame, min_path_len: int = 3) -> Tuple[List, Optional[Dict]]:
        # ... (без изменений) ...
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
            return list(set(map(tuple, puzzle))), best_question
        return puzzle, None

    def format_clue(self, clue: Tuple[Any, Any]) -> str:
        s = self.story_elements
        g = lambda c, v: f"{s.get(c, c.lower())} '{v}'"

        def format_fact(fact_clue: Tuple[Any, Any], is_negative: bool = False) -> str:
            fact_type, fact_params = fact_clue
            neg = " НЕ" if is_negative else ""
            if fact_type == ClueType.POSITIONAL:
                return f"в {s.get('position','локация')} №{fact_params[0]}{neg} находится {g(fact_params[1], fact_params[2])}"
            if fact_type == ClueType.DIRECT_LINK:
                return f"характеристикой {g(fact_params[0], fact_params[1])}{neg} является {g(fact_params[2], fact_params[3])}"
            return f"[неформатируемый факт: {fact_type.name}]"

        clue_type, params = clue
        try:
            # --- ИЗМЕНЕНИЕ: Используем Enum в if/elif ---
            if clue_type == ClueType.POSITIONAL: return f"В {s.get('position','локация')} №{params[0]} находится {g(params[1], params[2])}."
            if clue_type == ClueType.DIRECT_LINK: return f"Характеристикой {g(params[0], params[1])} является {g(params[2], params[3])}."
            if clue_type == ClueType.NEGATIVE_DIRECT_LINK: return f"{g(params[0], params[1]).capitalize()} НЕ находится в одной локации с {g(params[2], params[3])}."
            if clue_type == ClueType.RELATIVE_POS: return f"{g(params[0], params[1]).capitalize()} и {g(params[2], params[3])} находятся в соседних локациях."
            if clue_type == ClueType.AT_EDGE: return f"{g(params[0], params[1]).capitalize()} находится в одной из крайних локаций."
            if clue_type == ClueType.IS_EVEN: return f"Номер локации, где {g(params[0], params[1])}, — {'чётный' if params[2] else 'нечётный'}."
            if clue_type == ClueType.SUM_EQUALS: return f"Сумма номеров локаций, где {g(params[0], params[1])} и где {g(params[2], params[3])}, равна {params[4]}."
            if clue_type == ClueType.THREE_IN_A_ROW:
                p1,p2,p3 = params
                return f"Объекты {g(p1[0],p1[1])}, {g(p2[0],p2[1])} и {g(p3[0],p3[1])} находятся в трёх последовательных локациях (в любом порядке)."
            if clue_type == ClueType.ORDERED_CHAIN:
                p1,p2,p3 = params
                return f"Локация, где {g(p1[0],p1[1])}, находится где-то левее локации, где {g(p2[0],p2[1])}, которая в свою очередь левее локации, где {g(p3[0],p3[1])}."
            if clue_type == ClueType.IF_THEN:
                return f"Если {format_fact(params[0])}, то {format_fact(params[1])}."
            if clue_type == ClueType.IF_NOT_THEN_NOT:
                return f"Если {format_fact(params[0], is_negative=True)}, то {format_fact(params[1], is_negative=True)}."
            if clue_type == ClueType.EITHER_OR:
                return f"Либо {format_fact(params[0])}, либо {format_fact(params[1])}."
            if clue_type == ClueType.IF_AND_ONLY_IF:
                return f"Утверждение '{format_fact(params[0])}' истинно тогда и только тогда, когда истинно утверждение '{format_fact(params[1])}'."
            if clue_type == ClueType.NEITHER_NOR_POS:
                item_tuples, position = params
                # Форматируем каждый объект: "профессия 'Врач'", "национальность 'Англичанин'"
                formatted_items = [g(cat, item) for cat, item in item_tuples]
                # Соединяем их в одну строку: "Ни ..., ни ..."
                clue_text = "Ни " + ", ни ".join(formatted_items)
                return f"{clue_text}, не находится в локации №{position}."

        except (AttributeError, IndexError, KeyError) as e:
            return f"[ОШИБКА ФОРМАТИРОВАНИЯ для {clue_type.name}: {e}]"

        return f"[Неизвестный тип подсказки: {clue_type.name}]"

    def print_puzzle(self, final_clues: List[Tuple[Any, Any]], question_data: Dict[str, str], solution: pd.DataFrame):
        # ... (без изменений) ...
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
